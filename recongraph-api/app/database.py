"""Async SQLAlchemy engine and session factory for ReconGraph.

Production uses PostgreSQL (``postgresql+asyncpg://``). Local development and
tests use SQLite via ``sqlite+aiosqlite://`` so the full ORM/repository path
works without a database server.

Configure via ``DATABASE_URL``. All schema changes go through Alembic.
"""

import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.pool import NullPool


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./data/recongraph.db",
)

# A single module-level async engine cannot safely share pooled connections
# across independent event loops (e.g. multiple ``asyncio.run`` calls in tests
# or a test client's portal). SQLite tests use a fresh connection per checkout
# via NullPool; Postgres keeps the default async pool for production.
_use_null_pool = DATABASE_URL.startswith("sqlite")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool if _use_null_pool else None,
)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session