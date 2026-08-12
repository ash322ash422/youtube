"""
Minimal JWT auth for a single configured user (see AUTH_USERNAME /
AUTH_PASSWORD in config.py). There's no user database - this app has
exactly one account, matching its single-user deployment target.

Credentials are compared as plain env-var values (via secrets.compare_digest,
so a wrong guess can't be timed) rather than hashed, since there's a single
static credential pair rather than a user table - hashing buys little here
and adds a dependency. If this ever grows into a multi-user app with a real
account table, switch to a hashed-password store (e.g. bcrypt) then.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app import config


def verify_credentials(username: str, password: str) -> bool:
    if not config.AUTH_PASSWORD:
        return False  # auth not configured - fail closed, not open
    return (
        secrets.compare_digest(username, config.AUTH_USERNAME)
        and secrets.compare_digest(password, config.AUTH_PASSWORD)
    )


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Returns the subject (username) if `token` is valid and unexpired, else None."""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
