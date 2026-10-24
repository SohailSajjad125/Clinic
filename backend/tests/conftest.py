import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "t" * 48)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ["MESSAGING_SYNC"] = "1"
os.environ.setdefault("GLOBAL_RATE_LIMIT", "100000")
os.environ["RUN_SCHEDULER"] = "0"
os.environ.setdefault("STORAGE_DIR", "/tmp/clinicos-test-storage")

import pytest


@pytest.fixture(autouse=True)
def _reset_limits():
    from app.util import _hits

    _hits.clear()
    from app import platform_settings

    platform_settings.invalidate()
    yield
    platform_settings.invalidate()
