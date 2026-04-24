"""Secrets for JWT signing and Starlette sessions (read from env; never commit real values)."""

import os


def jwt_secret() -> str:
    s = os.getenv("JWT_SECRET", "").strip()
    if not s:
        raise ValueError("JWT_SECRET must be set (e.g. in .env)")
    return s


def session_secret() -> str:
    s = os.getenv("SESSION_SECRET", "").strip()
    if not s:
        raise ValueError("SESSION_SECRET must be set (e.g. in .env)")
    return s
