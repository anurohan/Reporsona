"""Password hashing and signed bearer-token authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

PBKDF2_ROUNDS = 600_000
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> str:
    value = normalize_email(email)
    if len(value) > 255 or not EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${encode(salt)}${encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_text, digest_text = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        pad = lambda value: value + "=" * (-len(value) % 4)
        salt = base64.urlsafe_b64decode(pad(salt_text))
        expected = base64.urlsafe_b64decode(pad(digest_text))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _encode(value: dict) -> str:
    raw = base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).decode().rstrip("=")
    signature = hmac.new(settings.auth_secret.encode(), raw.encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{raw}.{sig}"


def issue_token(user: User) -> str:
    return _encode({"sub": user.id, "ver": user.token_version or 1, "exp": int(time.time()) + settings.auth_token_ttl_seconds})


def decode_token(token: str) -> dict:
    try:
        raw, provided_signature = token.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(settings.auth_secret.encode(), raw.encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if not hmac.compare_digest(provided_signature, expected):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError
        if not payload.get("sub"):
            raise ValueError
        return payload
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")


def _user_from_token(token: str, db: Session) -> User:
    payload = decode_token(token)
    user = db.get(User, payload["sub"])
    if not user or (user.token_version or 1) != int(payload.get("ver", 0)):
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.", headers={"WWW-Authenticate": "Bearer"})
    return user


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    return _user_from_token(authorization.split(" ", 1)[1].strip(), db)


def get_current_user_from_query(access_token: str | None = Query(default=None), db: Session = Depends(get_db)) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="Authentication required.", headers={"WWW-Authenticate": "Bearer"})
    return _user_from_token(access_token, db)
