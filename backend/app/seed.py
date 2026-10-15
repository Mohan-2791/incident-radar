"""Deterministic demo data so the dashboard has something real to show on first run."""
import datetime as dt
import random

from sqlalchemy import func, select

from . import models as m
from .db import SessionLocal

SERVICES = [
    ("checkout-api", 1, "Payments"),
    ("auth", 1, "Identity"),
    ("billing-worker", 1, "Payments"),
    ("search", 2, "Discovery"),
    ("media-cdn", 2, "Platform"),
    ("notifications", 3, "Messaging"),
]

TITLES = {
    "checkout-api": ["Elevated 5xx on payment confirmation", "Card tokenisation timeouts", "Duplicate order webhooks"],
    "auth": ["Login latency above 2s", "Token refresh failing for mobile clients", "SSO callback returning 502"],
    "billing-worker": ["Invoice batch stuck in queue", "Proration job double-charging", "Ledger export delayed"],
    "search": ["Stale results after reindex", "Autocomplete p99 regression", "Shard rebalance causing timeouts"],
    "media-cdn": ["Image resize backlog", "Cache hit ratio dropped to 40%", "Origin shield certificate expiring"],
    "notifications": ["Push delivery delayed", "Email provider rate limiting", "Duplicate SMS to some users"],
}

FLOW = [
    (m.Status.INVESTIGATING, "Investigating. We're looking at dashboards and recent deploys."),
    (m.Status.IDENTIFIED, "Identified the cause and working on a fix."),
    (m.Status.MONITORING, "Fix deployed. Watching error rates before closing out."),
    (m.Status.RESOLVED, "Resolved. Metrics are back to baseline."),
]


async def seed_if_empty() -> None:
    async with SessionLocal() as s:
        if (await s.scalar(select(func.count()).select_from(m.Service))) or 0:
            return

        rng = random.Random(7)
        now = m.utcnow()
        services = [m.Service(name=n, tier=t, owner_team=o) for n, t, o in SERVICES]
        s.add_all(services)
        await s.flush()

        for i in range(42):
            service = rng.choice(services)
            created = now - dt.timedelta(days=rng.random() * 45, hours=rng.random() * 6)
            if i < 4:  # keep a few genuinely open incidents near "now"
                created = now - dt.timedelta(minutes=rng.randint(20, 400))
            is_open = i < 4 or (now - created) < dt.timedelta(hours=5) and rng.random() < 0.5
            steps = rng.randint(1, 3) if is_open else 4
            sev = m.Severity.SEV1 if i == 0 else rng.choices(list(m.Severity), weights=[1, 3, 5])[0]

            incident = m.Incident(
                service_id=service.id,
                title=rng.choice(TITLES[service.name]),
                severity=sev,
                status=FLOW[steps - 1][0],
                created_at=created,
            )
            s.add(incident)
            await s.flush()

            at = created
            for status, message in FLOW[:steps]:
                s.add(m.IncidentUpdate(incident_id=incident.id, message=message, status=status, created_at=at))
                at += dt.timedelta(minutes=rng.randint(8, 70))
            if not is_open:
                incident.resolved_at = at - dt.timedelta(minutes=1)
        await s.commit()
