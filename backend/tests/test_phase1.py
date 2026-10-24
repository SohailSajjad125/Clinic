import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "t" * 48)
os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import AuditLog, ClinicMember, User

client = TestClient(app)
API = "/api/v1"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


def register(email="owner@clinic.pk"):
    r = client.post(f"{API}/auth/register-clinic", json={
        "clinic_name": "Noor Clinic", "clinic_type": "General", "city": "Lahore", "country": "Pakistan",
        "full_name": "Dr Noor", "email": email, "password": "Str0ngPass!"})
    assert r.status_code == 201, r.text
    return r.json()


def add_staff(tok, email="rec@clinic.pk", role="receptionist"):
    r = client.post(f"{API}/staff", headers=h(tok), json={"email": email, "full_name": "Sara Khan", "role": role, "password": "TempPass123"})
    assert r.status_code == 201, r.text
    return r.json()


def test_register_login_me_refresh():
    a = register()
    assert a["me"]["role"] == "owner"
    assert client.post(f"{API}/auth/register-clinic", json={
        "clinic_name": "XX", "clinic_type": "YY", "city": "Z", "country": "PK",
        "full_name": "Dup", "email": "OWNER@clinic.pk", "password": "Str0ngPass!"}).status_code == 409
    l = client.post(f"{API}/auth/login", json={"email": "Owner@Clinic.pk", "password": "Str0ngPass!"})
    assert l.status_code == 200
    assert client.get(f"{API}/auth/me", headers=h(l.json()["access_token"])).json()["clinic"]["name"] == "Noor Clinic"
    assert client.post(f"{API}/auth/login", json={"email": "owner@clinic.pk", "password": "wrong"}).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": l.json()["refresh_token"]}).status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": l.json()["access_token"]}).status_code == 401
    assert client.get(f"{API}/auth/me", headers=h(l.json()["refresh_token"])).status_code == 401
    assert client.get(f"{API}/auth/me").status_code == 401


def test_permissions_and_validation():
    tok = register()["access_token"]
    add_staff(tok)
    rec = client.post(f"{API}/auth/login", json={"email": "rec@clinic.pk", "password": "TempPass123"}).json()["access_token"]
    assert client.get(f"{API}/staff", headers=h(rec)).status_code == 403          # temporary password must be changed first
    assert client.post(f"{API}/auth/change-password", headers=h(rec), json={"current_password": "TempPass123", "new_password": "Permanent123!"}).status_code == 204
    assert client.get(f"{API}/staff", headers=h(rec)).status_code == 200
    r = client.post(f"{API}/staff", headers=h(rec), json={"email": "x@y.pk", "full_name": "X Y", "role": "doctor", "password": "TempPass123"})
    assert r.status_code == 403
    assert client.get(f"{API}/trash/staff", headers=h(rec)).status_code == 403
    r = client.post(f"{API}/staff", headers=h(tok), json={"email": "a@b.pk", "full_name": "A B", "role": "owner", "password": "TempPass123"})
    assert r.status_code == 422
    assert client.post(f"{API}/staff", headers=h(tok), json={"email": "rec@clinic.pk", "full_name": "S K", "role": "nurse", "password": "TempPass123"}).status_code == 409


def test_delete_history_restore_purge():
    a = register()
    tok = a["access_token"]
    s = add_staff(tok)
    mid, uid = s["member_id"], s["user_id"]
    # delete -> disappears from list, appears in history, loses access at once
    rec = client.post(f"{API}/auth/login", json={"email": "rec@clinic.pk", "password": "TempPass123"}).json()["access_token"]
    assert client.delete(f"{API}/staff/{mid}", headers=h(tok)).status_code == 204
    assert [x["member_id"] for x in client.get(f"{API}/staff", headers=h(tok)).json()] == [a["me"]["member_id"]]
    assert [x["member_id"] for x in client.get(f"{API}/trash/staff", headers=h(tok)).json()] == [mid]
    assert client.get(f"{API}/auth/me", headers=h(rec)).status_code == 401
    assert client.post(f"{API}/auth/login", json={"email": "rec@clinic.pk", "password": "TempPass123"}).status_code == 403
    # re-adding a trashed person is blocked with a helpful message
    assert client.post(f"{API}/staff", headers=h(tok), json={"email": "rec@clinic.pk", "full_name": "S K", "role": "nurse", "password": "TempPass123"}).status_code == 409
    # restore brings access back
    assert client.post(f"{API}/trash/staff/{mid}/restore", headers=h(tok)).status_code == 200
    assert client.post(f"{API}/auth/login", json={"email": "rec@clinic.pk", "password": "TempPass123"}).status_code == 200
    # cannot purge something that is not in history
    assert client.delete(f"{API}/trash/staff/{mid}", headers=h(tok)).status_code == 409
    # delete again, then purge permanently
    client.delete(f"{API}/staff/{mid}", headers=h(tok))
    assert client.delete(f"{API}/trash/staff/{mid}", headers=h(tok)).status_code == 204
    with SessionLocal() as db:
        assert db.get(ClinicMember, __import__("uuid").UUID(mid)) is None
        assert db.get(User, __import__("uuid").UUID(uid)) is None
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "staff.purged")) == 1
    assert client.get(f"{API}/trash/staff", headers=h(tok)).json() == []


def test_owner_cannot_be_removed_and_tenant_isolation():
    a = register()
    tok = a["access_token"]
    assert client.delete(f"{API}/staff/{a['me']['member_id']}", headers=h(tok)).status_code == 400
    s = add_staff(tok)
    other = register("other@clinic.pk")["access_token"]
    assert client.delete(f"{API}/staff/{s['member_id']}", headers=h(other)).status_code == 404
    assert client.get(f"{API}/staff", headers=h(other)).json()[0]["email"] == "other@clinic.pk"
