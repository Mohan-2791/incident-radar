"""Per-request DataLoaders. They batch the N+1 lookups a nested GraphQL query would cause."""
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select
from strawberry.dataloader import DataLoader

from . import models as m
from .db import SessionLocal


async def _load_services(keys: list[int]) -> list[m.Service | None]:
    async with SessionLocal() as s:
        rows = (await s.scalars(select(m.Service).where(m.Service.id.in_(keys)))).all()
    by_id = {r.id: r for r in rows}
    return [by_id.get(k) for k in keys]


async def _load_updates(keys: list[int]) -> list[list[m.IncidentUpdate]]:
    async with SessionLocal() as s:
        rows = (
            await s.scalars(
                select(m.IncidentUpdate)
                .where(m.IncidentUpdate.incident_id.in_(keys))
                .order_by(m.IncidentUpdate.created_at, m.IncidentUpdate.id)
            )
        ).all()
    grouped: dict[int, list[m.IncidentUpdate]] = defaultdict(list)
    for row in rows:
        grouped[row.incident_id].append(row)
    return [grouped[k] for k in keys]


async def _load_open_counts(keys: list[int]) -> list[int]:
    async with SessionLocal() as s:
        rows = (
            await s.execute(
                select(m.Incident.service_id, func.count())
                .where(m.Incident.service_id.in_(keys), m.Incident.status != m.Status.RESOLVED)
                .group_by(m.Incident.service_id)
            )
        ).all()
    counts = dict(rows)
    return [counts.get(k, 0) for k in keys]


@dataclass
class Loaders:
    service: DataLoader[int, m.Service | None]
    updates: DataLoader[int, list[m.IncidentUpdate]]
    open_count: DataLoader[int, int]


def make_loaders() -> Loaders:
    return Loaders(
        service=DataLoader(_load_services),
        updates=DataLoader(_load_updates),
        open_count=DataLoader(_load_open_counts),
    )
