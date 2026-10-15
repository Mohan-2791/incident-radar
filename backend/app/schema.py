import base64
import datetime as dt
from collections.abc import AsyncGenerator
from typing import Annotated, Union

import strawberry
from graphql import GraphQLError
from sqlalchemy import and_, func, or_, select
from strawberry.extensions import QueryDepthLimiter
from strawberry.fastapi import BaseContext
from strawberry.types import Info

from . import models as m
from .db import SessionLocal
from .loaders import Loaders
from .pubsub import pubsub

Severity = strawberry.enum(m.Severity)
Status = strawberry.enum(m.Status)


class Context(BaseContext):
    def __init__(self, loaders: Loaders) -> None:
        super().__init__()
        self.loaders = loaders


def _utc(d: dt.datetime) -> dt.datetime:
    return d.replace(tzinfo=dt.timezone.utc)


def _to_int(value: strawberry.ID, what: str = "ID") -> int:
    try:
        return int(value)
    except ValueError:
        raise GraphQLError(f"Invalid {what}: {value!r}") from None


# ---------------------------------------------------------------- types


@strawberry.type
class ServiceType:
    id: strawberry.ID
    name: str
    tier: int
    owner_team: str

    @classmethod
    def from_row(cls, r: m.Service) -> "ServiceType":
        return cls(id=strawberry.ID(str(r.id)), name=r.name, tier=r.tier, owner_team=r.owner_team)

    @strawberry.field
    async def open_incident_count(self, info: Info[Context, None]) -> int:
        return await info.context.loaders.open_count.load(int(self.id))


@strawberry.type
class UpdateType:
    id: strawberry.ID
    message: str
    status: Status
    created_at: dt.datetime

    @classmethod
    def from_row(cls, r: m.IncidentUpdate) -> "UpdateType":
        return cls(
            id=strawberry.ID(str(r.id)),
            message=r.message,
            status=r.status,
            created_at=_utc(r.created_at),
        )


@strawberry.type
class IncidentType:
    id: strawberry.ID
    title: str
    severity: Severity
    status: Status
    created_at: dt.datetime
    resolved_at: dt.datetime | None
    service_id: strawberry.Private[int]

    @classmethod
    def from_row(cls, r: m.Incident) -> "IncidentType":
        return cls(
            id=strawberry.ID(str(r.id)),
            title=r.title,
            severity=r.severity,
            status=r.status,
            created_at=_utc(r.created_at),
            resolved_at=_utc(r.resolved_at) if r.resolved_at else None,
            service_id=r.service_id,
        )

    @strawberry.field
    def duration_minutes(self) -> int:
        end = self.resolved_at or dt.datetime.now(dt.timezone.utc)
        return int((end - self.created_at).total_seconds() // 60)

    @strawberry.field
    async def service(self, info: Info[Context, None]) -> ServiceType:
        row = await info.context.loaders.service.load(self.service_id)
        if row is None:  # FK guarantees this can't happen; fail loudly if it does
            raise GraphQLError("Service not found")
        return ServiceType.from_row(row)

    @strawberry.field
    async def updates(self, info: Info[Context, None]) -> list[UpdateType]:
        rows = await info.context.loaders.updates.load(int(self.id))
        return [UpdateType.from_row(r) for r in rows]


@strawberry.type
class PageInfo:
    has_next_page: bool
    end_cursor: str | None


@strawberry.type
class IncidentEdge:
    cursor: str
    node: IncidentType


@strawberry.type
class IncidentConnection:
    edges: list[IncidentEdge]
    page_info: PageInfo
    total_count: int


@strawberry.type
class SeverityCount:
    severity: Severity
    count: int


@strawberry.type
class Stats:
    open_total: int
    open_by_severity: list[SeverityCount]
    resolved_last_30_days: int
    mean_minutes_to_resolve: float | None


@strawberry.input
class IncidentFilter:
    status: list[Status] | None = None
    severity: list[Severity] | None = None
    service_id: strawberry.ID | None = None
    search: str | None = None


@strawberry.input
class OpenIncidentInput:
    service_id: strawberry.ID
    title: str
    severity: Severity
    message: str


@strawberry.input
class PostUpdateInput:
    incident_id: strawberry.ID
    status: Status
    message: str


@strawberry.type
class UserError:
    """Expected, user-fixable failures are data, not exceptions."""

    field: str
    message: str


IncidentPayload = Annotated[
    Union[IncidentType, UserError], strawberry.union("IncidentPayload")
]

# ---------------------------------------------------------------- cursors
# Keyset pagination on (created_at DESC, id DESC): stable under inserts, no OFFSET scans.


def _encode_cursor(r: m.Incident) -> str:
    return base64.urlsafe_b64encode(f"{r.created_at.isoformat()}|{r.id}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[dt.datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts, _, iid = raw.partition("|")
        return dt.datetime.fromisoformat(ts), int(iid)
    except Exception:
        raise GraphQLError("Invalid cursor") from None


def _filter_clauses(f: IncidentFilter | None) -> list:
    clauses: list = []
    if f is None:
        return clauses
    if f.status:
        clauses.append(m.Incident.status.in_(f.status))
    if f.severity:
        clauses.append(m.Incident.severity.in_(f.severity))
    if f.service_id is not None:
        clauses.append(m.Incident.service_id == _to_int(f.service_id, "service ID"))
    if f.search and f.search.strip():
        clauses.append(m.Incident.title.ilike(f"%{f.search.strip()}%"))
    return clauses


# ---------------------------------------------------------------- operations


@strawberry.type
class Query:
    @strawberry.field
    async def services(self) -> list[ServiceType]:
        async with SessionLocal() as s:
            rows = (await s.scalars(select(m.Service).order_by(m.Service.tier, m.Service.name))).all()
        return [ServiceType.from_row(r) for r in rows]

    @strawberry.field
    async def incident(self, id: strawberry.ID) -> IncidentType | None:
        async with SessionLocal() as s:
            row = await s.get(m.Incident, _to_int(id))
        return IncidentType.from_row(row) if row else None

    @strawberry.field
    async def incidents(
        self, filter: IncidentFilter | None = None, first: int = 20, after: str | None = None
    ) -> IncidentConnection:
        first = max(1, min(first, 100))
        clauses = _filter_clauses(filter)
        query = select(m.Incident).where(*clauses)
        if after:
            ts, iid = _decode_cursor(after)
            query = query.where(
                or_(m.Incident.created_at < ts, and_(m.Incident.created_at == ts, m.Incident.id < iid))
            )
        query = query.order_by(m.Incident.created_at.desc(), m.Incident.id.desc()).limit(first + 1)

        async with SessionLocal() as s:
            total = await s.scalar(select(func.count()).select_from(m.Incident).where(*clauses))
            rows = list((await s.scalars(query)).all())

        has_next = len(rows) > first
        rows = rows[:first]
        return IncidentConnection(
            edges=[IncidentEdge(cursor=_encode_cursor(r), node=IncidentType.from_row(r)) for r in rows],
            page_info=PageInfo(has_next_page=has_next, end_cursor=_encode_cursor(rows[-1]) if rows else None),
            total_count=total or 0,
        )

    @strawberry.field
    async def stats(self) -> Stats:
        since = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None) - dt.timedelta(days=30)
        async with SessionLocal() as s:
            open_rows = (
                await s.execute(
                    select(m.Incident.severity, func.count())
                    .where(m.Incident.status != m.Status.RESOLVED)
                    .group_by(m.Incident.severity)
                )
            ).all()
            resolved = (
                await s.execute(
                    select(m.Incident.created_at, m.Incident.resolved_at).where(
                        m.Incident.status == m.Status.RESOLVED, m.Incident.resolved_at >= since
                    )
                )
            ).all()
        counts = {sev: n for sev, n in open_rows}
        minutes = [(end - start).total_seconds() / 60 for start, end in resolved]
        return Stats(
            open_total=sum(counts.values()),
            open_by_severity=[SeverityCount(severity=sev, count=counts.get(sev, 0)) for sev in m.Severity],
            resolved_last_30_days=len(resolved),
            mean_minutes_to_resolve=round(sum(minutes) / len(minutes), 1) if minutes else None,
        )


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def open_incident(self, input: OpenIncidentInput) -> IncidentPayload:
        title, message = input.title.strip(), input.message.strip()
        if not title:
            return UserError(field="title", message="Give the incident a title.")
        if len(title) > 120:
            return UserError(field="title", message="Keep the title under 120 characters.")
        if not message:
            return UserError(field="message", message="Describe what you're seeing.")

        async with SessionLocal() as s:
            service = await s.get(m.Service, _to_int(input.service_id, "service ID"))
            if service is None:
                return UserError(field="serviceId", message="That service doesn't exist.")
            incident = m.Incident(
                service_id=service.id, title=title, severity=input.severity, status=m.Status.INVESTIGATING
            )
            s.add(incident)
            await s.flush()
            s.add(m.IncidentUpdate(incident_id=incident.id, message=message, status=m.Status.INVESTIGATING))
            await s.commit()

        pubsub.publish(incident.id)
        return IncidentType.from_row(incident)

    @strawberry.mutation
    async def post_update(self, input: PostUpdateInput) -> IncidentPayload:
        message = input.message.strip()
        if not message:
            return UserError(field="message", message="Write a short update for the timeline.")

        async with SessionLocal() as s:
            incident = await s.get(m.Incident, _to_int(input.incident_id, "incident ID"))
            if incident is None:
                return UserError(field="incidentId", message="That incident doesn't exist.")
            if incident.status == m.Status.RESOLVED:
                return UserError(field="status", message="This incident is resolved. Open a new one if it recurs.")
            incident.status = input.status
            if input.status == m.Status.RESOLVED:
                incident.resolved_at = m.utcnow()
            s.add(m.IncidentUpdate(incident_id=incident.id, message=message, status=input.status))
            await s.commit()

        pubsub.publish(incident.id)
        return IncidentType.from_row(incident)


@strawberry.type
class Subscription:
    @strawberry.subscription
    async def incident_changed(self) -> AsyncGenerator[IncidentType, None]:
        async for incident_id in pubsub.subscribe():
            async with SessionLocal() as s:
                row = await s.get(m.Incident, incident_id)
            if row is not None:
                yield IncidentType.from_row(row)


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    extensions=[lambda: QueryDepthLimiter(max_depth=8)],  # cheap protection against abusive nesting
)
