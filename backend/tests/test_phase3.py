import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "t" * 48)
os.environ.setdefault("ENVIRONMENT", "test")

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app import ai
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import AuditLog, Consultation, Invoice, Patient, Payment

client = TestClient(app)
A = "/api/v1"


@pytest.fixture(autouse=True)
def fresh():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def h(t):
    return {"Authorization": f"Bearer {t}"}


def setup():
    r = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Noor Clinic", "clinic_type": "General", "city": "Lahore", "country": "Pakistan",
                                                      "full_name": "Dr Noor", "email": "owner@c.pk", "password": "Str0ngPass!"}).json()
    owner = r["access_token"]
    from app.models import Clinic
    with SessionLocal() as db:
        c = db.get(Clinic, uuid.UUID(r["me"]["clinic"]["id"]))
        c.plan = "group"
        db.commit()
    toks = {"owner": owner, "owner_member": r["me"]["member_id"]}
    for role in ("doctor", "receptionist", "nurse"):
        s = client.post(f"{A}/staff", headers=h(owner), json={"email": f"{role}@c.pk", "full_name": f"{role.title()} X", "role": role, "password": "TempPass123"}).json()
        toks[role + "_member"] = s["member_id"]
        toks[role] = client.post(f"{A}/auth/login", json={"email": f"{role}@c.pk", "password": "TempPass123"}).json()["access_token"]
        assert client.post(f"{A}/auth/change-password", headers=h(toks[role]), json={"current_password": "TempPass123", "new_password": "Permanent123!"}).status_code == 204
    return toks


def patient(t, name="Ahmed Raza"):
    r = client.post(f"{A}/patients", headers=h(t["receptionist"]), json={"full_name": name, "phone": "0300111"})
    assert r.status_code == 201, r.text
    return r.json()


def when(hours=1):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def test_patients_roles_search_delete():
    t = setup()
    p = patient(t)
    assert client.get(f"{A}/patients?q=ahm", headers=h(t["nurse"])).json()[0]["id"] == p["id"]
    assert client.patch(f"{A}/patients/{p['id']}", headers=h(t["nurse"]), json={"allergies": "Penicillin"}).json()["allergies"] == "Penicillin"
    assert client.delete(f"{A}/patients/{p['id']}", headers=h(t["receptionist"])).status_code == 403
    assert client.delete(f"{A}/patients/{p['id']}", headers=h(t["doctor"])).status_code == 204
    assert client.get(f"{A}/patients/{p['id']}", headers=h(t["doctor"])).status_code == 404
    assert client.get(f"{A}/patients", headers=h(t["doctor"])).json() == []
    assert [x["id"] for x in client.get(f"{A}/trash/patients", headers=h(t["owner"])).json()] == [p["id"]]
    assert client.get(f"{A}/trash/patients", headers=h(t["doctor"])).status_code == 403


def test_appointment_queue_and_notification():
    t = setup()
    p = patient(t)
    a = client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": when(), "doctor_id": t["doctor_member"], "reason": "Fever"}).json()
    assert a["status"] == "booked"
    assert client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": when(), "doctor_id": t["receptionist_member"]}).status_code == 422
    up = lambda tok, s: client.patch(f"{A}/appointments/{a['id']}", headers=h(tok), json={"status": s})
    assert up(t["receptionist"], "completed").status_code == 409          # invalid jump
    r = up(t["receptionist"], "arrived").json()
    assert r["queue_no"] == 1
    n = client.get(f"{A}/notifications", headers=h(t["doctor"])).json()
    titles = [i["title"].lower() for i in n["items"]]
    assert n["unread"] == 2 and any("arrived" in t for t in titles) and any("new appointment" in t for t in titles)   # assigned to this doctor + patient arrived
    arrived = next(i for i in n["items"] if "arrived" in i["title"].lower())
    assert arrived["category"] == "queue" and arrived["link"]
    assert client.get(f"{A}/notifications", headers=h(t["receptionist"])).json()["unread"] == 0
    assert up(t["receptionist"], "in_consultation").status_code == 403   # reception can't start consultations
    assert up(t["doctor"], "in_consultation").json()["status"] == "in_consultation"
    assert up(t["doctor"], "completed").json()["status"] == "completed"
    client.post(f"{A}/notifications/read-all", headers=h(t["doctor"]))
    assert client.get(f"{A}/notifications", headers=h(t["doctor"])).json()["unread"] == 0
    nid = client.get(f"{A}/notifications", headers=h(t["doctor"])).json()["items"][0]["id"]
    assert client.delete(f"{A}/notifications/{nid}", headers=h(t["receptionist"])).status_code == 404
    assert client.delete(f"{A}/notifications/{nid}", headers=h(t["doctor"])).status_code == 204


def test_consultation_permissions_and_ai_summary(monkeypatch):
    t = setup()
    p = patient(t)
    body = {"patient_id": p["id"], "complaint": "Cough", "assessment": "Viral", "prescription": [{"medicine": "Paracetamol", "dose": "500mg", "frequency": "TDS", "duration": "3 days"}]}
    assert client.post(f"{A}/consultations", headers=h(t["receptionist"]), json=body).status_code == 403
    assert client.post(f"{A}/consultations", headers=h(t["nurse"]), json=body).status_code == 403
    c = client.post(f"{A}/consultations", headers=h(t["doctor"]), json=body)
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    assert client.get(f"{A}/consultations/{cid}", headers=h(t["nurse"])).status_code == 200
    assert client.get(f"{A}/consultations", headers=h(t["receptionist"])).status_code == 403
    captured = {}
    monkeypatch.setattr(ai, "call_llm", lambda m, tools=None: captured.update(m=m) or {"content": "Cough, viral. Paracetamol."})
    s = client.post(f"{A}/consultations/{cid}/summarize", headers=h(t["doctor"])).json()
    assert s["ai_summary"].startswith("AI draft") and "Ahmed" not in json.dumps(captured["m"])
    monkeypatch.undo()
    r = client.post(f"{A}/consultations/{cid}/summarize", headers=h(t["doctor"]))
    assert r.status_code == 503  # no Groq key configured


def test_billing_flow():
    t = setup()
    p = patient(t)
    inv = client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "Consultation", "qty": 1, "price": 2000}, {"description": "Lab", "qty": 2, "price": 500}], "discount": 200, "tax": 100}).json()
    assert inv["number"] == 1 and inv["total"] == 2900 and inv["status"] == "pending"
    assert client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "x", "price": 100}], "discount": 500}).status_code == 422
    assert client.post(f"{A}/invoices", headers=h(t["nurse"]), json={"patient_id": p["id"], "items": [{"description": "x", "price": 100}]}).status_code == 403
    pay = lambda amt: client.post(f"{A}/invoices/{inv['id']}/payments", headers=h(t["receptionist"]), json={"amount": amt})
    assert pay(1000).json()["status"] == "partial"
    assert pay(5000).status_code == 422
    assert pay(1900).json()["status"] == "paid"
    assert client.get(f"{A}/notifications", headers=h(t["owner"])).json()["unread"] == 1
    assert client.post(f"{A}/invoices/{inv['id']}/refund", headers=h(t["receptionist"])).json()["status"] == "refunded"
    assert pay(10).status_code == 409
    assert client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "x", "price": 100}]}).json()["number"] == 2


def test_trash_restore_and_cascading_purge():
    t = setup()
    p = patient(t)
    a = client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "scheduled_at": when()}).json()
    c = client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": p["id"], "appointment_id": a["id"], "complaint": "x"}).json()
    inv = client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "x", "price": 100}]}).json()
    client.post(f"{A}/invoices/{inv['id']}/payments", headers=h(t["receptionist"]), json={"amount": 100})
    client.delete(f"{A}/patients/{p['id']}", headers=h(t["doctor"]))
    for path in ("appointments", "invoices"):
        assert client.get(f"{A}/{path}", headers=h(t["owner"])).json() == []
    assert client.delete(f"{A}/trash/patients/{p['id']}", headers=h(t["receptionist"])).status_code == 403
    # restoring an item whose patient is deleted is refused until the patient is restored
    client.delete(f"{A}/appointments/{a['id']}", headers=h(t["owner"]))
    assert client.post(f"{A}/trash/appointments/{a['id']}/restore", headers=h(t["owner"])).status_code == 409
    assert client.post(f"{A}/trash/patients/{p['id']}/restore", headers=h(t["owner"])).status_code == 204
    assert client.post(f"{A}/trash/appointments/{a['id']}/restore", headers=h(t["owner"])).status_code == 204
    assert len(client.get(f"{A}/appointments", headers=h(t["owner"])).json()) == 1
    # not in trash -> cannot purge
    assert client.delete(f"{A}/trash/invoices/{inv['id']}", headers=h(t["owner"])).status_code == 409
    client.delete(f"{A}/patients/{p['id']}", headers=h(t["doctor"]))
    assert client.delete(f"{A}/trash/patients/{p['id']}", headers=h(t["owner"])).status_code == 204
    with SessionLocal() as db:
        for M in (Patient, Consultation, Invoice, Payment):
            assert db.scalar(select(func.count()).select_from(M)) == 0, M
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "patients.purged")) == 1


def test_isolation_between_clinics():
    t = setup()
    p = patient(t)
    other = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Other Clinic", "clinic_type": "Dental", "city": "K", "country": "PK", "full_name": "Dr O", "email": "o@o.pk", "password": "Str0ngPass!"}).json()["access_token"]
    assert client.get(f"{A}/patients/{p['id']}", headers=h(other)).status_code == 404
    assert client.post(f"{A}/appointments", headers=h(other), json={"patient_id": p["id"], "scheduled_at": when()}).status_code == 404
    assert client.get(f"{A}/patients", headers=h(other)).json() == []


def test_chat_and_analytics():
    t = setup()
    p = patient(t)
    client.post(f"{A}/chat", headers=h(t["doctor"]), json={"body": "Room 2 is free"})
    msgs = client.get(f"{A}/chat", headers=h(t["receptionist"])).json()
    assert msgs[0]["body"] == "Room 2 is free"
    assert client.delete(f"{A}/chat/{msgs[0]['id']}", headers=h(t["receptionist"])).status_code == 404
    assert client.delete(f"{A}/chat/{msgs[0]['id']}", headers=h(t["owner"])).status_code == 204
    inv = client.post(f"{A}/invoices", headers=h(t["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "x", "price": 700}]}).json()
    client.post(f"{A}/invoices/{inv['id']}/payments", headers=h(t["receptionist"]), json={"amount": 700})
    d = client.get(f"{A}/analytics/summary?tz_offset_minutes=300", headers=h(t["owner"])).json()
    assert d["patients_total"] == 1 and d["revenue"]["today"] == 700 and d["revenue"]["month"] == 700 and len(d["last7"]) == 7
    assert client.get(f"{A}/analytics/summary", headers=h(t["receptionist"])).status_code == 403


def test_websocket_realtime():
    t = setup()
    with client.websocket_connect(f"{A}/ws") as ws:
        ws.send_json({"token": t["doctor"]})
        assert ws.receive_json() == {"type": "ready"}
        patient(t)
        evt = ws.receive_json()
        assert evt == {"type": "data", "entity": "patients"}
    with pytest.raises(Exception):
        with client.websocket_connect(f"{A}/ws") as ws2:
            ws2.send_json({"token": "bad"})
            ws2.receive_json()


def fake_groq(script):
    it = iter(script)
    return lambda messages, tools=None: next(it)


def tool_call(name, args, cid="c1"):
    return {"content": "", "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}


def test_assistant_propose_confirm_and_permissions(monkeypatch):
    t = setup()
    p = patient(t, "Ali Hassan")
    when_iso = when(24)
    monkeypatch.setattr(ai, "call_llm", fake_groq([tool_call("search_patients", {"query": "Ali"}), tool_call("book_appointment", {"patient_id": p["id"], "scheduled_at": when_iso, "reason": "Checkup"}, "c2"), {"content": "I've prepared the booking. Please confirm."}]))
    r = client.post(f"{A}/ai/chat", headers=h(t["receptionist"]), json={"messages": [{"role": "user", "content": "Book Ali tomorrow"}]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "confirm" in body["reply"].lower() and len(body["actions"]) == 1
    aid = body["actions"][0]["id"]
    assert "Ali Hassan" in body["actions"][0]["summary"]
    # nothing was booked yet
    assert client.get(f"{A}/appointments", headers=h(t["owner"])).json() == []
    # another user cannot confirm someone else's action
    assert client.post(f"{A}/ai/actions/{aid}/confirm", headers=h(t["doctor"])).status_code == 404
    ok = client.post(f"{A}/ai/actions/{aid}/confirm", headers=h(t["receptionist"]))
    assert ok.status_code == 200 and "Booked" in ok.json()["message"]
    assert len(client.get(f"{A}/appointments", headers=h(t["owner"])).json()) == 1
    assert client.post(f"{A}/ai/actions/{aid}/confirm", headers=h(t["receptionist"])).status_code == 409
    # a receptionist asking to delete a patient is refused by the tool layer; no action is created
    monkeypatch.setattr(ai, "call_llm", fake_groq([tool_call("delete_patient", {"patient_id": p["id"]}), {"content": "You don't have permission for that."}]))
    r2 = client.post(f"{A}/ai/chat", headers=h(t["receptionist"]), json={"messages": [{"role": "user", "content": "delete Ali"}]}).json()
    assert r2["actions"] == []
    # cancel path + owner may delete
    monkeypatch.setattr(ai, "call_llm", fake_groq([tool_call("delete_patient", {"patient_id": p["id"]}), {"content": "Confirm?"}]))
    a3 = client.post(f"{A}/ai/chat", headers=h(t["owner"]), json={"messages": [{"role": "user", "content": "delete Ali"}]}).json()["actions"][0]["id"]
    assert client.post(f"{A}/ai/actions/{a3}/cancel", headers=h(t["owner"])).status_code == 204
    assert client.get(f"{A}/patients", headers=h(t["owner"])).json() != []
    # without a key the assistant fails politely
    monkeypatch.undo()
    assert client.post(f"{A}/ai/chat", headers=h(t["owner"]), json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 503
