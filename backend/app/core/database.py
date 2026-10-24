from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings

_kwargs = {}
if settings.database_url.startswith("sqlite"):  # used by tests only
    _kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
else:
    _kwargs = {"pool_pre_ping": True}

engine = create_engine(settings.database_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
