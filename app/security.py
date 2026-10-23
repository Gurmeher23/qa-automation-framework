"""Password hashing and current-user dependencies."""

from __future__ import annotations

import hashlib
import hmac
import os

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 hash in ``salt$digest`` hex form."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of ``password`` against a stored hash."""
    try:
        salt_hex, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _ITERATIONS)
    return hmac.compare_digest(candidate.hex(), digest_hex)


def authenticate(db: Session, username: str, password: str) -> User | None:
    """Return the user when credentials are valid, else ``None``."""
    user = db.scalar(select(User).where(User.username == username))
    if user and verify_password(password, user.password_hash):
        return user
    return None


def current_user_or_none(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Resolve the session cookie to a user, if any."""
    user_id = request.session.get("user_id")
    return db.get(User, user_id) if user_id else None


def require_user(user: User | None = Depends(current_user_or_none)) -> User:
    """API dependency: 401 when not logged in."""
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """API dependency: 403 unless the user is an admin."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
