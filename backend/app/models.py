import datetime as dt
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> dt.datetime:
    """Naive UTC. SQLite drops tzinfo, so we store UTC and re-attach it at the API edge."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class Severity(enum.Enum):
    SEV1 = "SEV1"
    SEV2 = "SEV2"
    SEV3 = "SEV3"


class Status(enum.Enum):
    INVESTIGATING = "INVESTIGATING"
    IDENTIFIED = "IDENTIFIED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    tier: Mapped[int]
    owner_team: Mapped[str] = mapped_column(String(80))


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_created", "created_at", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    severity: Mapped[Severity] = mapped_column(Enum(Severity))
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.INVESTIGATING)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime, default=None)


class IncidentUpdate(Base):
    __tablename__ = "incident_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[Status] = mapped_column(Enum(Status))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
