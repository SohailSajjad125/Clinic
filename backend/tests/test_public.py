import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "t" * 48)
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.public import _hits
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import ContactMessage, NewsletterSubscriber

client = TestClient(app)
API = "/api/v1/public"
GOOD = {"name": "Dr Sara", "email": "Sara@Clinic.pk", "topic": "demo", "message": "We run a 3-doctor clinic in Lahore."}


@pytest.fixture(autouse=True)
def fresh():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _hits.clear()


def count(model):
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(model))


def test_contact_saved_and_validated():
    assert client.post(f"{API}/contact", json=GOOD).status_code == 201
    with SessionLocal() as db:
        assert db.scalar(select(ContactMessage)).email == "sara@clinic.pk"
    assert client.post(f"{API}/contact", json={**GOOD, "message": "short"}).status_code == 422
    assert client.post(f"{API}/contact", json={**GOOD, "topic": "x"}).status_code == 422
    assert count(ContactMessage) == 1


def test_honeypot_and_rate_limit():
    assert client.post(f"{API}/contact", json={**GOOD, "website": "http://spam"}).status_code == 201
    assert count(ContactMessage) == 0
    codes = [client.post(f"{API}/contact", json=GOOD).status_code for _ in range(6)]
    assert codes[-1] == 429 and count(ContactMessage) == 4


def test_newsletter_idempotent():
    for _ in range(2):
        assert client.post(f"{API}/newsletter", json={"email": "A@b.pk"}).status_code == 201
    assert count(NewsletterSubscriber) == 1
    assert client.post(f"{API}/newsletter", json={"email": "bad"}).status_code == 422
