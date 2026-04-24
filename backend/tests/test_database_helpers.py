"""Tests for DATABASE_URL -> sync URL conversion."""

import database as database_module


def test_sync_database_url_sqlite_aiosqlite(monkeypatch):
    monkeypatch.setattr(database_module, "DATABASE_URL", "sqlite+aiosqlite:///./local.db")
    assert database_module._sync_database_url() == "sqlite:///./local.db"


def test_sync_database_url_asyncpg_to_psycopg(monkeypatch):
    monkeypatch.setattr(
        database_module,
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@host:5432/dbname?ssl=require",
    )
    out = database_module._sync_database_url()
    assert out.startswith("postgresql://")
    assert "sslmode=require" in out


def test_sync_database_url_plain_postgresql_unchanged(monkeypatch):
    monkeypatch.setattr(database_module, "DATABASE_URL", "postgresql://user:pass@host/db")
    assert database_module._sync_database_url() == "postgresql://user:pass@host/db"
