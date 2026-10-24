import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


DUMMY_HASH = hash_password("not-a-real-password")  # equalises login timing for unknown emails


def hash_token(raw: str) -> str:
    import hashlib

    return hashlib.sha256(raw.encode()).hexdigest()


def create_token(user_id: uuid.UUID, member_id: uuid.UUID | None, kind: str, sid: uuid.UUID, jti: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    ttl = timedelta(minutes=settings.access_minutes) if kind == "access" else timedelta(days=settings.refresh_days)
    payload = {"sub": str(user_id), "mid": str(member_id) if member_id else "", "sid": str(sid), "type": kind, "iat": now, "exp": now + ttl}
    if jti:
        payload["jti"] = jti
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, kind: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM], options={"require": ["exp", "iat", "sub", "sid", "type"]})
    if payload.get("type") != kind:
        raise jwt.InvalidTokenError("wrong token type")
    return payload
