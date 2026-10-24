"""File storage. Local disk by default; swap the three functions for S3/R2/Supabase in production."""
import os
import uuid

from .config import settings


def _path(key: str) -> str:
    if not key.replace("-", "").isalnum():
        raise ValueError("bad key")
    return os.path.join(settings.storage_dir, key)


def save(data: bytes) -> str:
    os.makedirs(settings.storage_dir, mode=0o700, exist_ok=True)
    key = uuid.uuid4().hex
    fd = os.open(_path(key), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # owner-only, never overwrites
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return key


def read(key: str) -> bytes:
    with open(_path(key), "rb") as f:
        return f.read()


def delete(key: str) -> None:
    try:
        os.remove(_path(key))
    except FileNotFoundError:
        pass
