import os

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./incidents.db")

# NullPool keeps SQLite simple and safe across event loops (tests, reload).
# Swap the URL for Postgres (postgresql+asyncpg://...) and drop NullPool in production.
engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
