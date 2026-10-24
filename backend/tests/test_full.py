import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import scheduler
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import Appointment, Clinic, Document, OutboundMessage, Session as AuthSession, User
from app.core.security import hash_password

client = TestClient(app)
A = "/api/v1"
PW = "Str0ngPass!"


@pytest.fixture(autouse=True)
def fresh():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def h(t):
    return {"Authorization": f"Bearer {t}"}


def login(email, pw=PW):
    return client.post(f"{A}/auth/login", json={"email": email, "password": pw})


def first_login(email, temp, new="Permanent123!"):
    """Accounts created by someone else must change the temporary password before anything else works."""
    tok = login(email, temp).json()["access_token"]
    assert client.get(f"{A}/patients", headers=h(tok)).status_code == 403
    assert client.post(f"{A}/auth/change-password", headers=h(tok), json={"current_password": temp, "new_password": new}).status_code == 204
    return tok


def clinic(plan="group"):
    r = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Noor Clinic", "clinic_type": "General", "city": "Lahore", "country": "Pakistan", "full_name": "Dr Noor", "email": "owner@c.pk", "password": PW}).json()
    with SessionLocal() as db:
        db.get(Clinic, uuid.UUID(r["me"]["clinic"]["id"])).plan = plan
        db.commit()
    t = {"owner": r["access_token"], "refresh": r["refresh_token"], "clinic_id": r["me"]["clinic"]["id"]}
    for role in ("doctor", "receptionist", "nurse"):
        s = client.post(f"{A}/staff", headers=h(t["owner"]), json={"email": f"{role}@c.pk", "full_name": f"{role.title()} X", "role": role, "password": "TempPass123"}).json()
        t[role + "_member"] = s["member_id"]
        t[role] = first_login(f"{role}@c.pk", "TempPass123")
    return t


def patient(t, **kw):
    r = client.post(f"{A}/patients", headers=h(t["receptionist"]), json={"full_name": "Ali Hassan", "phone": "0300111", "email": "ali@mail.pk", **kw})
    assert r.status_code == 201, r.text
    return r.json()


def soon(hours=2):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


# ---------- security ----------
def test_sessions_logout_refresh_reuse_and_password_flows():
    r = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Noor Clinic", "clinic_type": "General", "city": "L", "country": "PK", "full_name": "Dr N", "email": "o@c.pk", "password": PW}).json()
    a1, r1 = r["access_token"], r["refresh_token"]
    r2 = client.post(f"{A}/auth/refresh", json={"refresh_token": r1}).json()
    assert client.get(f"{A}/auth/me", headers=h(r2["access_token"])).status_code == 200
    assert client.post(f"{A}/auth/refresh", json={"refresh_token": r1}).status_code == 401           # replayed old token
    assert client.get(f"{A}/auth/me", headers=h(a1)).status_code == 401                                # whole session revoked
    tok = login("o@c.pk").json()["access_token"]
    assert len(client.get(f"{A}/auth/sessions", headers=h(tok)).json()) == 1
    assert client.post(f"{A}/auth/change-password", headers=h(tok), json={"current_password": "wrong", "new_password": "NewPass123!"}).status_code == 400
    other = login("o@c.pk").json()["access_token"]
    assert client.post(f"{A}/auth/change-password", headers=h(tok), json={"current_password": PW, "new_password": "NewPass123!"}).status_code == 204
    assert client.get(f"{A}/auth/me", headers=h(other)).status_code == 401 and client.get(f"{A}/auth/me", headers=h(tok)).status_code == 200
    assert client.post(f"{A}/auth/logout", headers=h(tok)).status_code == 204
    assert client.get(f"{A}/auth/me", headers=h(tok)).status_code == 401
    assert login("o@c.pk", "NewPass123!").status_code == 200


def test_lockout_after_failed_logins():
    clinic()
    codes = [login("owner@c.pk", "bad").status_code for _ in range(5)]
    assert codes == [401] * 5
    r = login("owner@c.pk")
    assert r.status_code == 429 and "minute" in r.json()["detail"]


def test_password_reset_and_email_verification_by_real_smtp(monkeypatch):
    from aiosmtpd.controller import Controller

    box = []

    class H:
        async def handle_DATA(self, server, session, envelope):
            import email as _e; box.append(_e.message_from_bytes(envelope.content).get_payload(decode=True).decode() + "\nSubject: " + str(_e.message_from_bytes(envelope.content)["Subject"])); return "250 OK"

    ctl = Controller(H(), hostname="127.0.0.1", port=8026)
    ctl.start()
    try:
        monkeypatch.setattr(settings.__class__, "smtp_host", "127.0.0.1", raising=False)
        object.__setattr__(settings, "smtp_host", "127.0.0.1"); object.__setattr__(settings, "smtp_port", 8026); object.__setattr__(settings, "smtp_tls", False)
        clinic()
        time.sleep(0.5)
        verify = next(m for m in box if "Verify your ClinicOS email" in m)
        vt = re.search(r"token=([\w-]+)", verify).group(1)
        tok = login("owner@c.pk").json()["access_token"]
        assert client.get(f"{A}/auth/me", headers=h(tok)).json()["email_verified"] is False
        assert client.post(f"{A}/auth/verify-email", json={"token": vt}).status_code == 204
        assert client.post(f"{A}/auth/verify-email", json={"token": vt}).status_code == 400   # single use
        assert client.get(f"{A}/auth/me", headers=h(tok)).json()["email_verified"] is True
        assert client.post(f"{A}/auth/forgot-password", json={"email": "nobody@x.pk"}).status_code == 202
        client.post(f"{A}/auth/forgot-password", json={"email": "owner@c.pk"})
        time.sleep(0.5)
        rt = re.search(r"token=([\w-]+)", next(m for m in box if "Reset your ClinicOS password" in m)).group(1)
        assert client.post(f"{A}/auth/reset-password", json={"token": rt, "password": "BrandNew123!"}).status_code == 204
        assert client.get(f"{A}/auth/me", headers=h(tok)).status_code == 401           # old sessions ended
        assert login("owner@c.pk", "BrandNew123!").status_code == 200
        assert client.post(f"{A}/auth/reset-password", json={"token": rt, "password": "Another123!"}).status_code == 400
    finally:
        object.__setattr__(settings, "smtp_host", ""); ctl.stop()


# ---------- plans ----------
def test_plan_limits_and_suspension_via_admin():
    r = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Small", "clinic_type": "General", "city": "Lahore", "country": "Pakistan", "full_name": "Dr S", "email": "s@c.pk", "password": PW}).json()
    tok, cid = r["access_token"], r["me"]["clinic"]["id"]
    add = lambda i: client.post(f"{A}/staff", headers=h(tok), json={"email": f"u{i}@c.pk", "full_name": "Staff User", "role": "nurse", "password": "TempPass123"})
    assert add(1).status_code == 201 and add(2).status_code == 201 and add(3).status_code == 402
    with SessionLocal() as db:
        db.add(User(email="root@x.pk", full_name="Root", password_hash=hash_password("RootPass12345"), is_superadmin=True)); db.commit()
    adm = login("root@x.pk", "RootPass12345").json()
    assert adm["me"]["role"] == "superadmin"
    at = adm["access_token"]
    assert client.get(f"{A}/admin/stats", headers=h(tok)).status_code == 403
    assert client.get(f"{A}/patients", headers=h(at)).status_code == 401 or client.get(f"{A}/patients", headers=h(at)).status_code == 403
    assert client.patch(f"{A}/admin/clinics/{cid}", headers=h(at), json={"plan": "clinic"}).status_code == 200
    assert add(3).status_code == 201
    assert client.get(f"{A}/admin/stats", headers=h(at)).json()["clinics"] == 1
    assert client.get(f"{A}/admin/clinics", headers=h(at)).json()[0]["owner_email"] == "s@c.pk"
    assert client.patch(f"{A}/admin/clinics/{cid}", headers=h(at), json={"status": "suspended"}).status_code == 200
    assert client.get(f"{A}/auth/me", headers=h(tok)).status_code == 401
    assert login("s@c.pk").status_code == 403
    assert client.get(f"{A}/admin/health", headers=h(at)).json()["database"] is True
    client.post(f"{A}/public/contact", json={"name": "Dr Sara", "email": "s@x.pk", "topic": "demo", "message": "Please call me back"})
    m = client.get(f"{A}/admin/messages", headers=h(at)).json()
    assert client.post(f"{A}/admin/messages/{m[0]['id']}/handled", headers=h(at)).status_code == 204


# ---------- queue & appointments ----------
def test_confirmed_walkin_callnext_recurring_and_durations():
    t = clinic()
    p = patient(t)
    series = client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": soon(48), "repeat_every_days": 7, "repeat_count": 3}).json()
    assert series["series_id"] and len(client.get(f"{A}/appointments?patient_id={p['id']}", headers=h(t["owner"])).json()) == 3
    a = client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": soon(1), "doctor_id": t["doctor_member"]}).json()
    assert client.patch(f"{A}/appointments/{a['id']}", headers=h(t["receptionist"]), json={"status": "confirmed"}).json()["status"] == "confirmed"
    assert client.patch(f"{A}/appointments/{a['id']}", headers=h(t["receptionist"]), json={"status": "arrived"}).json()["queue_no"] == 1
    w = client.post(f"{A}/appointments/walk-in", headers=h(t["receptionist"]), json={"patient_id": p["id"], "reason": "Pain"}).json()
    assert w["is_walk_in"] and w["status"] == "arrived" and w["queue_no"] == 2
    assert client.post(f"{A}/appointments/queue/call-next", headers=h(t["receptionist"])).status_code == 403
    first = client.post(f"{A}/appointments/queue/call-next", headers=h(t["doctor"])).json()
    assert first["id"] == a["id"] and first["status"] == "in_consultation" and first["started_at"]
    assert client.patch(f"{A}/appointments/{a['id']}", headers=h(t["doctor"]), json={"status": "completed"}).json()["completed_at"]
    second = client.post(f"{A}/appointments/queue/call-next", headers=h(t["doctor"])).json()
    assert second["id"] == w["id"]
    assert client.post(f"{A}/appointments/queue/call-next", headers=h(t["doctor"])).status_code == 404
    assert len(client.get(f"{A}/appointments?doctor_id={t['doctor_member']}", headers=h(t["owner"])).json()) >= 1
    d = client.get(f"{A}/analytics/summary", headers=h(t["owner"])).json()
    assert d["doctor_utilization"] and "avg_consultation_minutes" in d and d["patient_mix_30d"]["new"] >= 1


# ---------- documents ----------
def test_documents_upload_validation_download_and_purge_removes_file():
    t = clinic()
    p = patient(t)
    up = lambda name, data, **kw: client.post(f"{A}/patients/{p['id']}/documents", headers=h(t["nurse"]), files={"file": (name, data)}, data=kw)
    assert up("evil.exe", b"MZ").status_code == 415
    assert up("fake.pdf", b"not a pdf").status_code == 422
    assert up("big.pdf", b"%PDF" + b"0" * (10 * 1024 * 1024)).status_code == 413
    d = up("cbc.pdf", b"%PDF-1.4 test", category="lab", shared="true")
    assert d.status_code == 201, d.text
    did = d.json()["id"]
    dl = client.get(f"{A}/documents/{did}/download", headers=h(t["doctor"]))
    assert dl.content == b"%PDF-1.4 test" and dl.headers["x-content-type-options"] == "nosniff"
    with SessionLocal() as db:
        key = db.get(Document, uuid.UUID(did)).storage_key
    assert os.path.exists(os.path.join(settings.storage_dir, key))
    assert client.delete(f"{A}/documents/{did}", headers=h(t["nurse"])).status_code == 204
    assert client.get(f"{A}/documents/{did}/download", headers=h(t["doctor"])).status_code == 404
    assert client.delete(f"{A}/trash/documents/{did}", headers=h(t["owner"])).status_code == 204
    assert not os.path.exists(os.path.join(settings.storage_dir, key))
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(OutboundMessage).where(OutboundMessage.subject == "New document available")) >= 1


# ---------- patient portal ----------
def test_patient_portal_end_to_end_and_isolation():
    t = clinic()
    p = patient(t)
    q = patient(t, full_name="Other Patient", email="other@mail.pk", phone="0300999")
    assert client.post(f"{A}/patients/{p['id']}/portal-access", headers=h(t["nurse"]), json={"email": "ali@mail.pk", "password": "PortalPass1"}).status_code == 403
    assert client.post(f"{A}/patients/{p['id']}/portal-access", headers=h(t["receptionist"]), json={"email": "ali@mail.pk", "password": "PortalPass1"}).status_code == 201
    client.post(f"{A}/patients/{q['id']}/portal-access", headers=h(t["receptionist"]), json={"email": "other@mail.pk", "password": "PortalPass1"})
    pt = {"access_token": first_login("ali@mail.pk", "PortalPass1")}
    assert client.get(f"{A}/auth/me", headers=h(pt["access_token"])).json()["role"] == "patient"
    P = h(pt["access_token"])
    for path in ("/patients", "/consultations", "/invoices", "/staff", "/trash/patients", "/analytics/summary", "/chat"):
        assert client.get(f"{A}{path}", headers=P).status_code == 403, path
    cons = client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": p["id"], "complaint": "SECRET NOTE", "assessment": "PRIVATE", "follow_up_on": (datetime.now().date() + timedelta(days=5)).isoformat(),
                                                                         "prescription": [{"medicine": "Paracetamol", "dose": "500mg"}]}).json()
    hidden = client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": p["id"], "complaint": "x", "shared_with_patient": False, "prescription": [{"medicine": "Hidden drug"}]}).json()
    rx = client.get(f"{A}/portal/prescriptions", headers=P).json()
    assert [r["id"] for r in rx] == [cons["id"]] and "SECRET" not in str(rx) and "PRIVATE" not in str(rx)
    assert client.get(f"{A}/portal/prescriptions/{cons['id']}/pdf", headers=P).content.startswith(b"%PDF")
    assert client.get(f"{A}/portal/prescriptions/{hidden['id']}/pdf", headers=P).status_code == 404
    assert client.get(f"{A}/consultations/{cons['id']}/prescription.pdf", headers=h(t["doctor"])).content.startswith(b"%PDF")
    d1 = client.post(f"{A}/patients/{p['id']}/documents", headers=h(t["nurse"]), files={"file": ("a.pdf", b"%PDF-1")}, data={"shared": "true"}).json()
    d2 = client.post(f"{A}/patients/{p['id']}/documents", headers=h(t["nurse"]), files={"file": ("b.pdf", b"%PDF-2")}).json()
    assert [d["id"] for d in client.get(f"{A}/portal/documents", headers=P).json()] == [d1["id"]]
    assert client.get(f"{A}/portal/documents/{d2['id']}/download", headers=P).status_code == 404
    assert client.get(f"{A}/portal/documents/{d1['id']}/download", headers=P).content == b"%PDF-1"
    inv = client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "Visit", "price": 1500}]}).json()
    inv_q = client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": q["id"], "items": [{"description": "Visit", "price": 900}]}).json()
    assert [i["id"] for i in client.get(f"{A}/portal/invoices", headers=P).json()] == [inv["id"]]
    assert client.get(f"{A}/portal/invoices/{inv_q['id']}/receipt.pdf", headers=P).status_code == 404
    assert client.get(f"{A}/portal/invoices/{inv['id']}/receipt.pdf", headers=P).content.startswith(b"%PDF")
    assert client.post(f"{A}/portal/appointments", headers=P, json={"scheduled_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}).status_code == 422
    ap = client.post(f"{A}/portal/appointments", headers=P, json={"scheduled_at": soon(30), "reason": "Checkup"}).json()
    assert client.get(f"{A}/notifications", headers=h(t["receptionist"])).json()["unread"] >= 1
    assert client.post(f"{A}/portal/appointments/{ap['id']}/cancel", headers=P).status_code == 204
    assert client.get(f"{A}/portal/home", headers=P).json()["next_follow_up"]
    client.post(f"{A}/portal/messages", headers=P, json={"body": "Can I take it with food?"})
    inbox = client.get(f"{A}/messages/inbox", headers=h(t["doctor"])).json()
    assert inbox[0]["patient_name"] == "Ali Hassan" and inbox[0]["unread"] == 1
    assert client.get(f"{A}/patients/{p['id']}/messages", headers=h(t["doctor"])).json()[0]["from_patient"] is True
    client.post(f"{A}/patients/{p['id']}/messages", headers=h(t["doctor"]), json={"body": "Yes, with food."})
    msgs = client.get(f"{A}/portal/messages", headers=P).json()
    assert [m["from_patient"] for m in msgs] == [True, False]
    assert client.get(f"{A}/portal/messages", headers=h(first_login("other@mail.pk", "PortalPass1"))).json() == []
    # revoking access ends the patient's session; purging the patient removes their login too
    assert client.delete(f"{A}/patients/{q['id']}/portal-access", headers=h(t["receptionist"])).status_code == 204
    assert login("other@mail.pk", "PortalPass1").status_code == 401
    client.delete(f"{A}/patients/{p['id']}", headers=h(t["doctor"]))
    assert client.delete(f"{A}/trash/patients/{p['id']}", headers=h(t["owner"])).status_code == 204
    assert login("ali@mail.pk", "Permanent123!").status_code == 401        # the portal login is gone with the patient
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Document)) == 0


def test_chat_events_do_not_reach_patients():
    t = clinic()
    p = patient(t)
    client.post(f"{A}/patients/{p['id']}/portal-access", headers=h(t["receptionist"]), json={"email": "ali@mail.pk", "password": "PortalPass1"})
    pt = first_login("ali@mail.pk", "PortalPass1")
    with client.websocket_connect(f"{A}/ws") as pws, client.websocket_connect(f"{A}/ws") as sws:
        pws.send_json({"token": pt}); sws.send_json({"token": t["doctor"]})
        assert pws.receive_json()["type"] == "ready" and sws.receive_json()["type"] == "ready"
        client.post(f"{A}/chat", headers=h(t["owner"]), json={"body": "staff only"})
        assert sws.receive_json()["type"] == "chat"
        client.post(f"{A}/patients/{p['id']}/messages", headers=h(t["doctor"]), json={"body": "hello"})
        first = pws.receive_json()                                           # the patient only ever receives events meant for them
        assert first["type"] in ("portal", "notification") and first.get("category", "messages") == "messages" and "staff only" not in str(first)


# ---------- messaging & reminders ----------
def test_reminders_and_outbound_log():
    t = clinic()
    p = patient(t)
    a = client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": soon(5)}).json()
    far = client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": soon(72)}).json()
    c = client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": p["id"], "complaint": "x", "follow_up_on": (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()})
    assert c.status_code == 201
    assert scheduler.run_reminders() == 2 and scheduler.run_reminders() == 0
    with SessionLocal() as db:
        subjects = [m.subject for m in db.scalars(select(OutboundMessage))]
        assert "Appointment reminder" in subjects and "Follow-up reminder" in subjects and "Appointment booked" in subjects
        assert db.get(Appointment, uuid.UUID(far["id"])).reminded_at is None
        assert {m.status for m in db.scalars(select(OutboundMessage))} == {"skipped"}      # no SMTP/Twilio configured in tests
    client.patch(f"{A}/appointments/{a['id']}", headers=h(t["receptionist"]), json={"status": "cancelled"})
    with SessionLocal() as db:
        assert "Appointment cancelled" in [m.subject for m in db.scalars(select(OutboundMessage))]


# ---------- settings, permissions, inventory, audit ----------
def test_settings_permissions_inventory_audit_timeline():
    t = clinic()
    p = patient(t)
    assert client.patch(f"{A}/clinic", headers=h(t["doctor"]), json={"name": "Hacked"}).status_code == 403
    c = client.patch(f"{A}/clinic", headers=h(t["owner"]), json={"name": "Noor Care", "working_hours": {"mon": {"open": "09:00", "close": "17:00"}, "sun": None}}).json()
    assert c["name"] == "Noor Care" and c["plan"] == "group" and c["usage"]["patients"] == 1
    sv = client.post(f"{A}/services", headers=h(t["owner"]), json={"name": "Consultation", "price": 2000}).json()
    assert client.get(f"{A}/services", headers=h(t["receptionist"])).json()[0]["price"] == 2000
    assert client.post(f"{A}/services", headers=h(t["receptionist"]), json={"name": "x", "price": 1}).status_code == 403
    client.post(f"{A}/medicine-templates", headers=h(t["doctor"]), json={"medicine": "Paracetamol", "dose": "500mg"})
    assert client.get(f"{A}/medicine-templates", headers=h(t["receptionist"])).status_code == 403
    loc = client.post(f"{A}/locations", headers=h(t["owner"]), json={"name": "Main Branch"}).json()
    a = client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": soon(), "location_id": loc["id"]}).json()
    assert a["location_id"] == loc["id"]
    assert client.delete(f"{A}/locations/{loc['id']}", headers=h(t["owner"])).status_code == 204
    assert client.get(f"{A}/appointments?patient_id={p['id']}", headers=h(t["owner"])).json()[0]["location_id"] is None
    # reception can read clinical records only if the owner allows it
    assert client.get(f"{A}/consultations", headers=h(t["receptionist"])).status_code == 403
    assert client.patch(f"{A}/staff/{t['receptionist_member']}/permissions", headers=h(t["owner"]), json={"can_view_clinical": True}).status_code == 200
    assert client.get(f"{A}/consultations", headers=h(t["receptionist"])).status_code == 200
    assert client.post(f"{A}/consultations", headers=h(t["receptionist"]), json={"patient_id": p["id"]}).status_code == 403
    # inventory
    it = client.post(f"{A}/inventory", headers=h(t["receptionist"]), json={"name": "Gloves", "unit": "box", "quantity": 10, "reorder_level": 4}).json()
    assert client.post(f"{A}/inventory/{it['id']}/adjust", headers=h(t["receptionist"]), json={"delta": -20}).status_code == 422
    r = client.post(f"{A}/inventory/{it['id']}/adjust", headers=h(t["receptionist"]), json={"delta": -7}).json()
    assert r["quantity"] == 3 and r["low"]
    assert any(n["title"] == "Low stock" for n in client.get(f"{A}/notifications", headers=h(t["owner"])).json()["items"])
    client.delete(f"{A}/inventory/{it['id']}", headers=h(t["doctor"]))
    assert client.get(f"{A}/inventory", headers=h(t["owner"])).json() == []
    assert client.post(f"{A}/trash/inventory/{it['id']}/restore", headers=h(t["owner"])).status_code == 204
    assert len(client.get(f"{A}/inventory", headers=h(t["owner"])).json()) == 1
    # timeline is role-aware
    client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": p["id"], "complaint": "Cough"})
    types = lambda tok: {i["type"] for i in client.get(f"{A}/patients/{p['id']}/timeline", headers=h(tok)).json()}
    client.patch(f"{A}/staff/{t['receptionist_member']}/permissions", headers=h(t["owner"]), json={"can_view_clinical": False})
    assert "consultation" in types(t["doctor"]) and "consultation" in types(t["nurse"]) and "consultation" not in types(t["receptionist"])
    assert "invoice" not in types(t["nurse"])
    # audit log
    log = client.get(f"{A}/audit", headers=h(t["owner"])).json()
    assert any(e["action"] == "inventory.deleted" for e in log) and client.get(f"{A}/audit", headers=h(t["doctor"])).status_code == 403


def test_invoice_pdf_payment_method_and_extended_analytics():
    t = clinic()
    p = patient(t)
    inv = client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "Consultation", "price": 2000}, {"description": "Lab", "price": 500}]}).json()
    assert client.post(f"{A}/invoices/{inv['id']}/payments", headers=h(t["receptionist"]), json={"amount": 1000, "method": "bank"}).json()["status"] == "partial"
    assert client.get(f"{A}/invoices/{inv['id']}/receipt.pdf", headers=h(t["receptionist"])).content.startswith(b"%PDF")
    d = client.get(f"{A}/analytics/summary", headers=h(t["owner"])).json()
    assert d["pending_invoices"] == {"count": 1, "due": 1500}
    assert d["revenue_by_service"][0] == {"service": "Consultation", "amount": 2000}
    for k in ("cancellation_rate_30d", "follow_ups_due_7d", "retention_90d"):
        assert k in d
