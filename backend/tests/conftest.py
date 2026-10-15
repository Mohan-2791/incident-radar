import datetime as dt
import os
import tempfile

# Must be set before the app imports its engine.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp.name}"

import pytest  # noqa: E402

from app import models as m  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.loaders import make_loaders  # noqa: E402
from app.schema import Context  # noqa: E402

BASE = dt.datetime(2026, 1, 1, 12, 0, 0)


@pytest.fixture(autouse=True)
async def db():
    """Fresh, tiny, deterministic dataset for every test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as s:
        s.add_all([m.Service(id=1, name="api", tier=1, owner_team="A"), m.Service(id=2, name="web", tier=2, owner_team="B")])
        await s.flush()
        for i in range(1, 8):  # incident 7 is newest
            resolved = i <= 3
            s.add(
                m.Incident(
                    id=i,
                    service_id=1 if i % 2 else 2,
                    title=f"Incident {i}",
                    severity=m.Severity.SEV1 if i == 7 else m.Severity.SEV3,
                    status=m.Status.RESOLVED if resolved else m.Status.INVESTIGATING,
                    created_at=BASE + dt.timedelta(hours=i),
                    resolved_at=BASE + dt.timedelta(hours=i, minutes=30) if resolved else None,
                )
            )
            s.add(m.IncidentUpdate(incident_id=i, message="Looking", status=m.Status.INVESTIGATING, created_at=BASE))
        await s.commit()


@pytest.fixture
def ctx() -> Context:
    return Context(loaders=make_loaders())
