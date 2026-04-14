"""Pytest: force test env before importing the app (isolated from .env / shell DATABASE_URL)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_ROOT / "pytest_agriexam.db"

for p in sorted(_BACKEND_ROOT.glob("pytest_agriexam.db*"), key=lambda x: len(str(x)), reverse=True):
    try:
        p.unlink()
    except OSError:
        pass

# Must override, not setdefault — developers often have DATABASE_URL in .env or the shell.
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}"
os.environ["OPENAI_API_KEY"] = "test-openai-key-not-used-in-unit-tests"
os.environ["JWT_SECRET"] = "pytest-jwt-secret"
os.environ["SESSION_SECRET"] = "pytest-session-secret"
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""

from server import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c
