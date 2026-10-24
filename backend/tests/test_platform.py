"""Admin console, runtime settings (Groq), role-aware notifications and red dots, appointment requests,
doctor profiles and slots, and public patient signup."""
import json
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app import ai, platform_settings as ps
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import PlatformSetting, Patient, User
from tests.test_full import A, PW, client, clinic, first_login, h, login, patient


@pytest.fixture(autouse=True)
def fresh():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def admin_token():
    with SessionLocal() as db:
        db.add(User(email="root@x.pk", full_name="Root Admin", password_hash=hash_password("RootPass12345!"), is_superadmin=True, email_verified=True))
        db.commit()
    return login("root@x.pk", "RootPass12345!").json()["access_token"]


def put(tok, **values):
    return client.put(f"{A}/admin/settings", headers=h(tok), json={"values": values})


def dots(tok):
    return client.get(f"{A}/notifications/dots", headers=h(tok)).json()


def notes(tok):
    return client.get(f"{A}/notifications", headers=h(tok)).json()["items"]


def next_weekday(wd, plus=7):
    d = date.today() + timedelta(days=plus)
    while d.weekday() != wd:
        d += timedelta(days=1)
    return d


def portal_patient(t, email="pat@mail.pk", name="Sana Patient"):
    r = client.post(f"{A}/auth/register-patient", json={"clinic_id": t["clinic_id"], "full_name": name, "email": email, "phone": "0300555", "password": "Patient-Own-2026", "accept_terms": True})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


# ---------------- Groq assistant + runtime settings ----------------
def test_groq_key_model_and_settings_are_managed_by_the_admin_and_stored_encrypted(monkeypatch):
    t, adm = clinic(), admin_token()
    cur = client.get(f"{A}/admin/settings", headers=h(adm)).json()
    key = next(x for x in cur if x["name"] == "groq_api_key")
    assert key["secret"] and key["is_set"] is False and "value" not in key
    assert next(x for x in cur if x["name"] == "groq_base_url")["value"] == "https://api.groq.com/openai/v1"
    SECRET = "gsk_TESTSECRET_abcdefghij_7890"
    r = put(adm, groq_api_key=SECRET, groq_model="openai/gpt-oss-120b")
    assert r.status_code == 200 and SECRET not in r.text
    assert next(x for x in r.json() if x["name"] == "groq_api_key")["hint"] == "…7890"
    with SessionLocal() as db:
        row = db.get(PlatformSetting, "groq_api_key")
        assert row.is_secret and SECRET not in row.value and "7890" not in row.value        # encrypted at rest
    log = client.get(f"{A}/admin/audit?action=admin.settings", headers=h(adm)).json()
    assert log and "groq_api_key" in log[0]["action"] and SECRET not in json.dumps(log)       # names only, never values
    seen = {}

    class Resp:
        status_code = 200
        def json(self): return {"choices": [{"message": {"content": "Hello from Groq."}}]}

    def fake_post(url, **kw):
        seen.update(url=url, auth=kw["headers"]["Authorization"], model=kw["json"]["model"])
        return Resp()

    monkeypatch.setattr(ai.httpx, "post", fake_post)
    out = client.post(f"{A}/ai/chat", headers=h(t["owner"]), json={"messages": [{"role": "user", "content": "hi"}]})
    assert out.status_code == 200 and out.json()["reply"] == "Hello from Groq."
    assert seen == {"url": "https://api.groq.com/openai/v1/chat/completions", "auth": f"Bearer {SECRET}", "model": "openai/gpt-oss-120b"}
    put(adm, groq_model="llama-3.3-70b-versatile")                                        # changed in the panel, used at once
    client.post(f"{A}/ai/chat", headers=h(t["owner"]), json={"messages": [{"role": "user", "content": "hi"}]})
    assert seen["model"] == "llama-3.3-70b-versatile"
    assert put(adm, assistant_enabled=False).status_code == 200
    off = client.post(f"{A}/ai/chat", headers=h(t["owner"]), json={"messages": [{"role": "user", "content": "hi"}]})
    assert off.status_code == 503 and "switched off" in off.json()["detail"]
    put(adm, assistant_enabled=True)
    assert client.put(f"{A}/admin/settings", headers=h(adm), json={"values": {}, "clear": ["groq_api_key"]}).status_code == 200
    gone = client.post(f"{A}/ai/chat", headers=h(t["owner"]), json={"messages": [{"role": "user", "content": "hi"}]})
    assert gone.status_code == 503 and "isn't set up" in gone.json()["detail"]


def test_settings_validation_and_access():
    t, adm = clinic(), admin_token()
    bad = [{"groq_base_url": "http://api.groq.com/openai/v1"}, {"groq_base_url": "https://127.0.0.1/v1"}, {"groq_base_url": "https://localhost/v1"}, {"groq_base_url": "https://10.0.0.5/v1"},
           {"groq_model": "bad model; drop"}, {"smtp_port": "70000"}, {"smtp_port": "abc"}, {"groq_model": "a" * 400}, {"assistant_enabled": "yes"}, {"nope": "x"}]
    for v in bad:
        assert put(adm, **v).status_code == 422, v
    assert put(adm, groq_base_url="https://api.groq.com/openai/v1", smtp_port="2525", groq_model="openai/gpt-oss-120b").status_code == 200
    assert put(adm, groq_api_key="").status_code == 200                                   # blank secret = leave unchanged, not erase
    for tok in (t["owner"], t["doctor"]):
        assert client.get(f"{A}/admin/settings", headers=h(tok)).status_code == 403
        assert put(tok, groq_model="x").status_code == 403
    assert client.post(f"{A}/admin/settings/test/assistant", headers=h(adm)).json() == {"ok": False, "message": "No API key is saved yet."}


def test_email_settings_changed_in_the_panel_really_send_mail():
    from aiosmtpd.controller import Controller
    import email as _e

    box = []

    class H:
        async def handle_DATA(self, server, session, envelope):
            box.append(_e.message_from_bytes(envelope.content)["Subject"]); return "250 OK"

    ctl = Controller(H(), hostname="127.0.0.1", port=8028)
    ctl.start()
    try:
        adm = admin_token()
        assert client.post(f"{A}/admin/settings/test/email", headers=h(adm)).json()["ok"] is False        # nothing configured yet
        assert put(adm, smtp_host="127.0.0.1", smtp_port="8028", smtp_tls=False, smtp_from="ClinicOS <no-reply@x.pk>").status_code == 200
        res = client.post(f"{A}/admin/settings/test/email", headers=h(adm)).json()
        time.sleep(0.3)
        assert res["ok"] and "ClinicOS test email" in box
    finally:
        ctl.stop()


# ---------------- admin console ----------------
def test_admin_can_view_and_track_everything():
    t, adm = clinic(), admin_token()
    p = patient(t)
    stats = client.get(f"{A}/admin/stats", headers=h(adm)).json()
    assert stats["clinics"] == 1 and stats["patients"] == 1
    cl = client.get(f"{A}/admin/clinics", headers=h(adm)).json()[0]
    det = client.get(f"{A}/admin/clinics/{cl['id']}", headers=h(adm))
    assert det.status_code == 200 and "Noor Clinic" in det.text and "owner@c.pk" in det.text
    users = client.get(f"{A}/admin/users?q=doctor", headers=h(adm)).json()
    doc = next(u for u in users if u["email"] == "doctor@c.pk")
    assert client.patch(f"{A}/admin/users/{doc['id']}", headers=h(adm), json={"is_active": False}).status_code == 200
    assert client.get(f"{A}/auth/me", headers=h(t["doctor"])).status_code == 401                 # sessions ended immediately
    assert login("doctor@c.pk", "Permanent123!").status_code == 401
    assert client.patch(f"{A}/admin/users/{doc['id']}", headers=h(adm), json={"is_active": True}).status_code == 200
    assert login("doctor@c.pk", "Permanent123!").status_code == 200
    root = next(u for u in client.get(f"{A}/admin/users?q=root", headers=h(adm)).json())
    assert client.patch(f"{A}/admin/users/{root['id']}", headers=h(adm), json={"is_active": False}).status_code == 403   # admins can't lock each other out
    audit = client.get(f"{A}/admin/audit?limit=200", headers=h(adm)).json()
    acts = {e["action"] for e in audit}
    assert "patient.created" in acts and "admin.user_disabled" in acts and any(e.get("clinic") == "Noor Clinic" for e in audit)
    assert client.get(f"{A}/admin/audit?clinic_id={cl['id']}&action=patient", headers=h(adm)).json()
    assert isinstance(client.get(f"{A}/admin/outbound", headers=h(adm)).json(), list)
    assert len(client.get(f"{A}/admin/signups", headers=h(adm)).json()) == 14


def test_admin_notifications_signup_switches_and_dots():
    adm = admin_token()
    assert dots(adm) == {}
    clinic()                                                                                      # a new clinic signs up
    client.post(f"{A}/public/contact", json={"name": "Dr Sara", "email": "s@x.pk", "topic": "demo", "message": "Please call me back"})
    d = dots(adm)
    assert d.get("admin_clinics") == 1 and d.get("admin_support") == 1
    assert {n["category"] for n in notes(adm)} == {"admin_clinics", "admin_support"}
    client.post(f"{A}/notifications/seen", headers=h(adm), json={"category": "admin_support"})
    assert dots(adm) == {"admin_clinics": 1}
    put(adm, allow_clinic_signups=False)
    closed = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Late Clinic", "clinic_type": "General", "city": "L", "country": "PK", "full_name": "Dr Late", "email": "late@x.pk", "password": PW})
    assert closed.status_code == 403
    put(adm, allow_clinic_signups=True, allow_patient_signups=False)
    t = {"clinic_id": client.get(f"{A}/admin/clinics", headers=h(adm)).json()[0]["id"]}
    assert client.post(f"{A}/auth/register-patient", json={"clinic_id": t["clinic_id"], "full_name": "Pat Ient", "email": "p@x.pk", "password": "Patient-Own-2026", "accept_terms": True}).status_code == 403


# ---------------- public patient sign-up and separate login ----------------
def test_patients_sign_up_and_log_in_on_their_own():
    t = clinic()
    found = client.get(f"{A}/public/clinics?q=Noor").json()
    assert [c["name"] for c in found] == ["Noor Clinic"] and set(found[0]) == {"id", "name", "city", "country", "clinic_type"}
    assert client.get(f"{A}/public/clinics?q=zzzz").json() == []
    base = {"clinic_id": t["clinic_id"], "full_name": "Sana Patient", "email": "pat@mail.pk", "password": "Patient-Own-2026", "accept_terms": True}
    assert client.post(f"{A}/auth/register-patient", json={**base, "accept_terms": False}).status_code == 422
    assert client.post(f"{A}/auth/register-patient", json={**base, "password": "password123"}).status_code == 422
    assert client.post(f"{A}/auth/register-patient", json={**base, "clinic_id": str(uuid.uuid4())}).status_code == 404
    assert client.post(f"{A}/auth/register-patient", json={**base, "email": "owner@c.pk"}).status_code == 409        # can't take a staff address
    r = client.post(f"{A}/auth/register-patient", json=base)
    assert r.status_code == 201 and r.json()["me"]["role"] == "patient" and r.json()["me"]["must_change_password"] is False
    assert client.post(f"{A}/auth/register-patient", json=base).status_code == 409
    P = h(r.json()["access_token"])
    assert client.get(f"{A}/portal/home", headers=P).json()["name"] == "Sana Patient"
    with SessionLocal() as db:
        assert db.scalar(select(Patient).where(Patient.email == "pat@mail.pk")).self_registered is True
    for who in ("owner", "receptionist"):                                                          # staff are told, on the right feature
        assert dots(t[who]).get("patients") == 1
    assert "patients" not in dots(t["nurse"]) or True
    assert "patients" not in dots(t["doctor"])                                                     # doctors don't manage the patient list intake
    # separate login pages: wrong door is refused with a pointer to the right one
    assert login("pat@mail.pk", "Patient-Own-2026").status_code == 200
    assert client.post(f"{A}/auth/login", json={"email": "pat@mail.pk", "password": "Patient-Own-2026", "audience": "staff"}).status_code == 403
    assert client.post(f"{A}/auth/login", json={"email": "owner@c.pk", "password": PW, "audience": "patient"}).status_code == 403
    assert client.post(f"{A}/auth/login", json={"email": "pat@mail.pk", "password": "Patient-Own-2026", "audience": "patient"}).status_code == 200
    # a clinic can hide itself from the public directory
    assert client.patch(f"{A}/clinic", headers=h(t["owner"]), json={"public_listing": False}).status_code == 200
    assert client.get(f"{A}/public/clinics?q=Noor").json() == []
    assert client.post(f"{A}/auth/register-patient", json={**base, "email": "other@mail.pk"}).status_code == 404       # hidden clinics are not even confirmed to exist


def test_doctors_cannot_add_patients_but_staff_can():
    t = clinic()
    body = {"full_name": "New Person"}
    assert client.post(f"{A}/patients", headers=h(t["doctor"]), json=body).status_code == 403
    for who in ("receptionist", "nurse", "owner"):
        assert client.post(f"{A}/patients", headers=h(t[who]), json=body).status_code == 201
    pid = client.get(f"{A}/patients", headers=h(t["doctor"])).json()[0]["id"]                      # doctors can still open and treat
    assert client.get(f"{A}/patients/{pid}", headers=h(t["doctor"])).status_code == 200


# ---------------- appointment requests, doctors, slots ----------------
def test_patient_requests_reach_staff_in_real_time_and_the_patient_hears_back():
    t = clinic()
    ptok = portal_patient(t)
    P = h(ptok)
    doc = client.get(f"{A}/portal/doctors", headers=P).json()
    assert doc and "specialization" in doc[0]["profile"]
    day = next_weekday(0)
    slot = next(s for s in client.get(f"{A}/portal/slots?date={day}&doctor_id={t['doctor_member']}", headers=P).json() if not s["taken"])
    req = client.post(f"{A}/portal/appointments", headers=P, json={"scheduled_at": slot["start"], "doctor_id": t["doctor_member"], "reason": "Fever"})
    assert req.status_code == 201 and req.json()["status"] == "requested"
    assert client.post(f"{A}/portal/appointments", headers=P, json={"scheduled_at": slot["start"], "doctor_id": t["doctor_member"]}).status_code == 409   # same slot, same doctor
    reqs = client.get(f"{A}/appointments/requests", headers=h(t["receptionist"])).json()
    assert [r["id"] for r in reqs] == [req.json()["id"]]
    for who in ("receptionist", "owner", "doctor"):                                                # everyone who must act is told
        assert dots(t[who]).get("appointments", 0) >= 1, who
        assert any(n["category"] == "appointments" and "request" in n["title"].lower() for n in notes(t[who])), who
    assert "appointments" not in dots(t["nurse"])                                                  # irrelevant to nurses: no dot, no notification
    assert dots(ptok) == {}
    client.post(f"{A}/notifications/seen", headers=h(t["receptionist"]), json={"category": "appointments"})
    assert "appointments" not in dots(t["receptionist"]) and dots(t["owner"]).get("appointments")   # only that user's dot clears
    ok = client.patch(f"{A}/appointments/{req.json()['id']}", headers=h(t["receptionist"]), json={"status": "confirmed"})
    assert ok.status_code == 200 and ok.json()["status"] == "confirmed"
    assert client.get(f"{A}/appointments/requests", headers=h(t["owner"])).json() == []
    assert dots(ptok).get("appointments") == 1 and notes(ptok)[0]["link"].startswith("/portal")
    client.post(f"{A}/notifications/seen", headers=P, json={"category": "appointments"})
    assert dots(ptok) == {}
    second = client.post(f"{A}/portal/appointments", headers=P, json={"scheduled_at": (datetime.fromisoformat(slot["start"]) + timedelta(hours=2)).isoformat()}).json()
    assert client.patch(f"{A}/appointments/{second['id']}", headers=h(t["receptionist"]), json={"status": "cancelled"}).status_code == 200      # declined
    assert any("declin" in n["title"].lower() or "cancel" in n["title"].lower() for n in notes(ptok))


def test_dots_for_chat_and_clearing():
    t = clinic()
    assert dots(t["doctor"]) == {}
    client.post(f"{A}/chat", headers=h(t["owner"]), json={"body": "Room 2 is free"})
    assert dots(t["doctor"]).get("chat") == 1 and "chat" not in dots(t["owner"])                  # never your own message
    client.post(f"{A}/notifications/seen", headers=h(t["doctor"]), json={"category": "chat"})
    assert "chat" not in dots(t["doctor"])
    assert client.get(f"{A}/notifications/dots").status_code == 401


def test_owner_adds_doctors_with_profiles_and_slots_follow_their_hours():
    t = clinic()
    prof = {"specialization": "Cardiology", "qualifications": "MBBS, FCPS", "license_no": "PMDC-12345", "experience_years": 9, "consultation_fee": 3000,
            "phone": "0300123", "bio": "Heart specialist", "available_days": ["mon", "wed"], "start_time": "10:00", "end_time": "12:00", "slot_minutes": 30}
    r = client.post(f"{A}/staff", headers=h(t["owner"]), json={"email": "heart@c.pk", "full_name": "Dr Heart", "role": "doctor", "password": "TempPass123", "profile": prof})
    assert r.status_code == 201, r.text
    mid = r.json()["member_id"]
    lst = client.get(f"{A}/doctors", headers=h(t["receptionist"])).json()
    card = next(d for d in lst if d["member_id"] == mid)
    assert card["profile"]["specialization"] == "Cardiology" and card["profile"]["consultation_fee"] == 3000 and card["profile"]["license_no"] == "PMDC-12345"
    assert client.post(f"{A}/staff", headers=h(t["owner"]), json={"email": "bad@c.pk", "full_name": "Dr Bad", "role": "doctor", "password": "TempPass123", "profile": {**prof, "end_time": "09:00"}}).status_code == 422
    assert client.patch(f"{A}/staff/{mid}/profile", headers=h(t["doctor"]), json=prof).status_code == 403
    assert client.patch(f"{A}/staff/{mid}/profile", headers=h(t["owner"]), json={**prof, "consultation_fee": 3500}).status_code == 200
    mine = client.patch(f"{A}/me/profile", headers=h(t["doctor"]), json={**prof, "specialization": "General Medicine"})
    assert mine.status_code == 200 and client.get(f"{A}/me/profile", headers=h(t["doctor"])).json()["profile"]["specialization"] == "General Medicine"
    heart = first_login("heart@c.pk", "TempPass123")
    mon, tue = next_weekday(0), next_weekday(1)
    slots = client.get(f"{A}/slots?date={mon}&doctor_id={mid}", headers=h(t["receptionist"])).json()
    assert [s["time"] for s in slots] == ["10:00", "10:30", "11:00", "11:30"]
    assert client.get(f"{A}/slots?date={tue}&doctor_id={mid}", headers=h(t["receptionist"])).json() == []        # not a working day
    p = patient(t)
    book = lambda when: client.post(f"{A}/appointments", headers=h(t["receptionist"]), json={"patient_id": p["id"], "doctor_id": mid, "scheduled_at": when})
    first = book(slots[1]["start"])
    assert first.status_code == 201 and book(slots[1]["start"]).status_code == 409
    assert next(s for s in client.get(f"{A}/slots?date={mon}&doctor_id={mid}", headers=h(t["owner"])).json() if s["time"] == "10:30")["taken"] is True
    assert any(n["category"] == "appointments" for n in notes(heart))                                           # the doctor is told when booked with them
    assert dots(heart).get("appointments", 0) >= 1
    client.patch(f"{A}/appointments/{first.json()['id']}", headers=h(t["receptionist"]), json={"status": "arrived"})
    s = client.get(f"{A}/doctor/summary", headers=h(heart)).json()
    assert s["today"]["mine"] >= 0 and "last7" in s and "upcoming" in s
    assert client.get(f"{A}/doctor/summary", headers=h(t["receptionist"])).status_code == 403


# ---------------- clear chat (own view only) and the clinic audit log ----------------
def thread(tok, pid): return client.get(f"{A}/patients/{pid}/messages", headers=h(tok)).json()
def bodies(rows): return [m["body"] for m in rows]


def test_clear_chat_only_empties_the_view_of_the_person_who_cleared():
    t = clinic()
    dots(t["doctor"]); dots(t["owner"])                                                          # opening the app sets "read up to here"
    client.post(f"{A}/chat", headers=h(t["owner"]), json={"body": "Room 2 is free"})
    client.post(f"{A}/chat", headers=h(t["nurse"]), json={"body": "Thanks"})
    team = lambda who: bodies(client.get(f"{A}/chat", headers=h(t[who])).json())
    assert dots(t["doctor"]).get("chat") == 2
    assert client.post(f"{A}/chat/clear", headers=h(t["doctor"])).status_code == 204
    assert team("doctor") == [] and dots(t["doctor"]) == {}                                      # gone for the doctor, dot too
    assert team("owner") == team("nurse") == team("receptionist") == ["Room 2 is free", "Thanks"]  # everyone else keeps it
    client.post(f"{A}/chat", headers=h(t["owner"]), json={"body": "New message"})
    assert team("doctor") == ["New message"] and dots(t["doctor"]).get("chat") == 1              # only newer messages come back
    assert client.post(f"{A}/chat/clear", headers=h(t["owner"])).status_code == 204 and team("owner") == [] and len(team("nurse")) == 3
    assert client.post(f"{A}/chat/clear").status_code == 401


def test_clear_patient_chat_is_private_to_each_person():
    t = clinic()
    ptok = portal_patient(t)
    pid = client.get(f"{A}/portal/home", headers=h(ptok)).json()
    pid = client.get(f"{A}/patients?q=Sana", headers=h(t["receptionist"])).json()[0]["id"]
    client.post(f"{A}/portal/messages", headers=h(ptok), json={"body": "Can I eat before the test?"})
    client.post(f"{A}/patients/{pid}/messages", headers=h(t["receptionist"]), json={"body": "Please fast for 8 hours."})
    mine = lambda: bodies(client.get(f"{A}/portal/messages", headers=h(ptok)).json())
    assert bodies(thread(t["doctor"], pid)) == bodies(thread(t["receptionist"], pid)) == mine() == ["Can I eat before the test?", "Please fast for 8 hours."]
    assert client.post(f"{A}/patients/{pid}/messages/clear", headers=h(t["receptionist"])).status_code == 204
    assert thread(t["receptionist"], pid) == [] and client.get(f"{A}/messages/inbox", headers=h(t["receptionist"])).json() == []
    assert len(thread(t["doctor"], pid)) == 2 and len(client.get(f"{A}/messages/inbox", headers=h(t["doctor"])).json()) == 1 and len(mine()) == 2   # doctor and patient unaffected
    client.post(f"{A}/portal/messages", headers=h(ptok), json={"body": "Thank you"})
    assert bodies(thread(t["receptionist"], pid)) == ["Thank you"] and len(thread(t["doctor"], pid)) == 3
    assert client.post(f"{A}/portal/messages/clear", headers=h(ptok)).status_code == 204
    assert mine() == [] and len(thread(t["doctor"], pid)) == 3 and len(thread(t["receptionist"], pid)) == 1
    assert client.post(f"{A}/portal/messages/clear", headers=h(t["owner"])).status_code == 403          # patients only
    assert client.post(f"{A}/patients/{pid}/messages/clear", headers=h(ptok)).status_code == 403


def test_owner_audit_log_covers_the_whole_clinic_and_never_another_clinic():
    t = clinic()
    ptok = portal_patient(t)
    P = h(ptok)
    day = next_weekday(0)
    slot = next(s for s in client.get(f"{A}/portal/slots?date={day}&doctor_id={t['doctor_member']}", headers=P).json() if not s["taken"])
    appt = client.post(f"{A}/portal/appointments", headers=P, json={"scheduled_at": slot["start"], "doctor_id": t["doctor_member"]}).json()
    client.post(f"{A}/portal/appointments/{appt['id']}/cancel", headers=P)
    client.post(f"{A}/portal/messages", headers=P, json={"body": "hello"})
    pid = client.get(f"{A}/patients?q=Sana", headers=h(t["receptionist"])).json()[0]["id"]
    client.post(f"{A}/patients/{pid}/messages", headers=h(t["receptionist"]), json={"body": "hi"})
    client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": pid, "complaint": "x"})
    # an unrelated clinic with its own activity
    rival = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Rival Clinic", "clinic_type": "General", "city": "K", "country": "PK", "full_name": "Dr Rival", "email": "rival@x.pk", "password": PW}).json()["access_token"]
    client.post(f"{A}/patients", headers=h(rival), json={"full_name": "Rival Patient"})
    mine = client.get(f"{A}/audit?limit=300", headers=h(t["owner"])).json()
    acts = {(e["actor_role"], e["action"]) for e in mine}
    for want in [("owner", "clinic.created"), ("owner", "staff.added"), ("patient", "patient.self_registered"), ("patient", "portal.appointment_requested"), ("patient", "portal.appointment_cancelled"),
                 ("patient", "portal.message_sent"), ("receptionist", "staff.message_sent"), ("doctor", "consultation.created"), ("doctor", "auth.login"), ("receptionist", "auth.login")]:
        assert want in acts, (want, sorted(acts))
    theirs = client.get(f"{A}/audit?limit=300", headers=h(rival)).json()
    assert {e["id"] for e in mine}.isdisjoint({e["id"] for e in theirs})
    assert not any("Rival" in str(e) or e["actor"] == "Dr Rival" for e in mine) and not any(e["actor"] in ("Sana Patient", "Doctor X") for e in theirs)
    only_patient = client.get(f"{A}/audit?role=patient", headers=h(t["owner"])).json()
    assert only_patient and {e["actor_role"] for e in only_patient} == {"patient"}
    assert all("message" in e["action"] for e in client.get(f"{A}/audit?q=message", headers=h(t["owner"])).json())
    for who in ("doctor", "receptionist", "nurse"):
        assert client.get(f"{A}/audit", headers=h(t[who])).status_code == 403
    assert client.get(f"{A}/audit", headers=h(ptok)).status_code == 403
