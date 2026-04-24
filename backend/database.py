"""Async SQLAlchemy engine, sessions, and a small sync helper to create tables at startup."""

import os
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# PostgreSQL async URL for Neon deployment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@endpoint.neon.tech/neondb?ssl=require")

# Neon *-pooler* hosts use PgBouncer (transaction mode); asyncpg's statement cache breaks on pooled connections.
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=280,
        connect_args={"statement_cache_size": 0},
    )
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=280,
    )
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


def _sync_database_url() -> str:
    """psycopg2 / sync SQLAlchemy URL (async drivers cannot run create_all the same way)."""
    u = DATABASE_URL
    if u.startswith("postgresql+asyncpg://"):
        u = "postgresql://" + u[len("postgresql+asyncpg://") :]
    elif u.startswith("sqlite+aiosqlite:///"):
        return "sqlite:///" + u[len("sqlite+aiosqlite:///") :]

    if not u.startswith("postgresql://"):
        return u

    # asyncpg accepts ?ssl=require; libpq/psycopg2 require sslmode= instead
    parsed = urlparse(u)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if "ssl" in qs and "sslmode" not in qs:
        raw = (qs.pop("ssl")[0] or "").lower()
        if raw in ("require", "true", "1", "on"):
            qs["sslmode"] = ["require"]
        elif raw in ("disable", "false", "0", "off"):
            qs["sslmode"] = ["disable"]
        elif raw:
            qs["sslmode"] = [raw]
    new_q = urlencode(qs, doseq=True)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_q, parsed.fragment)
    )


def init_schema_sync() -> None:
    """Create missing ORM tables. Call once at process startup (import time)."""
    import models  # noqa: F401 — register tables on Base.metadata

    from sqlalchemy import create_engine

    sync_engine = create_engine(_sync_database_url(), pool_pre_ping=True)
    Base.metadata.create_all(sync_engine)


async def get_db():
    """FastAPI dependency: one request-scoped async session, then close."""
    async with async_session() as session:
        yield session
