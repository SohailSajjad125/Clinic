"""Security checklist, executed. Each test maps to an item in docs/SECURITY_AUDIT.md."""
import dataclasses
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings, validate
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.models import EmailToken, Invoice, User
from tests.test_full import A, PW, client, clinic, first_login, h, login, patient, soon

PUBLIC = {"/health", "/api/v1/auth/login", "/api/v1/auth/register-clinic", "/api/v1/auth/refresh", "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password",
          "/api/v1/auth/verify-email", "/api/v1/public/contact", "/api/v1/public/newsletter", "/api/v1/auth/register-patient", "/api/v1/public/clinics"}
U = lambda: str(uuid.uuid4())


@pytest.fixture(autouse=True)
def fresh():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def routes():
    """Every operation in the OpenAPI schema (this also proves nothing hides outside it, see test below)."""
    out = []
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            if method.upper() in ("GET", "POST", "PATCH", "PUT", "DELETE"):
                out.append((method.upper(), re.sub(r"\{[^}]+\}", U(), path), path))
    return out


def call(m, path, tok=None, **kw):
    return client.request(m, path, headers=h(tok) if tok else None, json={} if m in ("POST", "PATCH", "PUT") else None, **kw)


# ---- protect admin routes / proper authentication / secure endpoints ----
def test_every_non_public_endpoint_requires_a_valid_session():
    leaks = [(m, p) for m, p, tpl in routes() if tpl not in PUBLIC and call(m, p).status_code != 401]
    assert leaks == [], f"endpoints reachable without authentication: {leaks}"
    assert len([1 for _, _, t in routes() if t not in PUBLIC]) > 90          # sanity: we really checked the whole API


def test_admin_routes_reject_every_non_superadmin():
    t = clinic()
    client.post(f"{A}/patients/{patient(t)['id']}/portal-access", headers=h(t["receptionist"]), json={"email": "ali@mail.pk", "password": "PortalPass1"})
    patient_tok = first_login("ali@mail.pk", "PortalPass1")
    admin = [(m, p) for m, p, tpl in routes() if tpl.startswith("/api/v1/admin")]
    assert len(admin) >= 6
    for role in ("owner", "doctor", "receptionist", "nurse"):
        assert [(m, p) for m, p in admin if call(m, p, t[role]).status_code != 403] == [], role
    assert [(m, p) for m, p in admin if call(m, p, patient_tok).status_code != 403] == []


def test_superadmin_cannot_be_created_through_the_api():
    r = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Evil Co", "clinic_type": "General", "city": "L", "country": "PK", "full_name": "Eve Evil", "email": "eve@x.pk", "password": PW, "is_superadmin": True})
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == "eve@x.pk")).is_superadmin is False
    assert client.get(f"{A}/admin/stats", headers=h(r.json()["access_token"])).status_code == 403


def test_patient_and_superadmin_tokens_cannot_use_staff_endpoints():
    t = clinic()
    client.post(f"{A}/patients/{patient(t)['id']}/portal-access", headers=h(t["receptionist"]), json={"email": "ali@mail.pk", "password": "PortalPass1"})
    ptok = first_login("ali@mail.pk", "PortalPass1")
    with SessionLocal() as db:
        from app.core.security import hash_password
        db.add(User(email="root@x.pk", full_name="Root", password_hash=hash_password("RootPass12345!"), is_superadmin=True)); db.commit()
    atok = login("root@x.pk", "RootPass12345!").json()["access_token"]
    staff_only = [(m, p) for m, p, tpl in routes() if tpl.startswith("/api/v1") and not tpl.startswith(("/api/v1/portal", "/api/v1/admin", "/api/v1/auth", "/api/v1/public", "/api/v1/notifications"))
                  and tpl not in ("/api/v1/ws",)]
    assert [(m, p) for m, p in staff_only if call(m, p, ptok).status_code not in (403,)] == []
    assert [(m, p) for m, p in staff_only if call(m, p, atok).status_code not in (401, 403)] == []


def test_token_forgery_and_tampering_rejected():
    t = clinic()
    good = jwt.decode(t["owner"], options={"verify_signature": False})
    me = lambda tok: client.get(f"{A}/auth/me", headers=h(tok)).status_code
    assert me(t["owner"]) == 200
    assert me(jwt.encode({**good, "exp": int(time.time()) - 10}, settings.jwt_secret, algorithm="HS256")) == 401          # expired
    assert me(jwt.encode(good, "some-other-secret-value-of-sufficient-length", algorithm="HS256")) == 401                   # wrong key
    assert me(jwt.encode(good, None, algorithm="none")) == 401                                                               # alg=none
    assert me(jwt.encode({k: v for k, v in good.items() if k != "sid"}, settings.jwt_secret, algorithm="HS256")) == 401      # missing claim
    assert me(jwt.encode({**good, "type": "refresh"}, settings.jwt_secret, algorithm="HS256")) == 401                        # wrong type
    assert me(jwt.encode({**good, "sid": U()}, settings.jwt_secret, algorithm="HS256")) == 401                               # unknown session
    assert me(t["owner"][:-3] + "abc") == 401                                                                                # bad signature


# ---- hash passwords ----
def test_passwords_and_tokens_are_hashed_and_never_returned():
    t = clinic()
    with SessionLocal() as db:
        hashes = [u.password_hash for u in db.scalars(select(User))]
    assert hashes and all(re.match(r"^\$2[aby]\$12\$", x) for x in hashes) and PW not in "".join(hashes)
    bodies = [client.get(f"{A}{p}", headers=h(t["owner"])).text for p in ("/auth/me", "/staff", "/auth/sessions", "/clinic", "/audit")]
    assert not any("password_hash" in b or "$2b$" in b or PW in b for b in bodies)
    client.post(f"{A}/auth/forgot-password", json={"email": "owner@c.pk"})
    with SessionLocal() as db:
        tok = db.scalar(select(EmailToken).where(EmailToken.kind == "reset"))
        assert len(tok.token_hash) == 64 and tok.kind == "reset"                  # sha-256 of the emailed token, never the token itself


def test_password_policy_and_input_sanitising():
    base = {"clinic_name": "Noor Clinic", "clinic_type": "General", "city": "L", "country": "PK", "full_name": "Dr Noor"}
    reg = lambda email, pw: client.post(f"{A}/auth/register-clinic", json={**base, "email": email, "password": pw})
    for bad in ("password", "12345678", "aaaaaaaa", "Password123"[:0] + "qwerty123", "x" * 80, "has\x00nul123"):
        assert reg("a@b.pk", bad).status_code == 422, bad
    assert reg("jonathan@b.pk", "jonathan2026!").status_code == 422             # contains the email name
    assert reg("ok@b.pk", PW).status_code == 201
    t = clinic()
    r = client.post(f"{A}/patients", headers=h(t["owner"]), json={"full_name": "  Ali\x00 Has\x07san \n", "allergies": "a\x00b"})
    assert r.status_code == 201 and r.json()["full_name"] == "Ali Hassan" and r.json()["allergies"] == "ab"
    assert client.get(f"{A}/patients?q={'a' * 101}", headers=h(t["owner"])).status_code == 422
    assert client.patch(f"{A}/clinic", headers=h(t["owner"]), json={"working_hours": {"mon": {"open": "9am", "close": "5pm"}}}).status_code == 422
    assert client.patch(f"{A}/clinic", headers=h(t["owner"]), json={"working_hours": {"funday": None}}).status_code == 422
    pid = r.json()["id"]
    assert client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": pid, "vitals": {str(i): "1" for i in range(13)}}).status_code == 422
    assert client.post(f"{A}/patients", headers=h(t["owner"]), json={"full_name": "A" * 121}).status_code == 422
    assert client.post(f"{A}/patients", headers=h(t["owner"]), json={"full_name": "Ali", "email": "not-an-email"}).status_code == 422
    assert client.post(f"{A}/invoices", headers=h(t["owner"]), json={"patient_id": pid, "items": [{"description": "x", "price": -5}]}).status_code == 422


# ---- XSS ----
def test_html_in_data_is_inert_in_pdfs_and_json():
    t = clinic()
    p = patient(t, full_name="<script>alert(1)</script> & <b>Bob</b>")
    assert client.get(f"{A}/patients/{p['id']}", headers=h(t["owner"])).headers["content-type"].startswith("application/json")
    c = client.post(f"{A}/consultations", headers=h(t["doctor"]), json={"patient_id": p["id"], "prescription": [{"medicine": "<font color=red>X</para></b> &amp; <img src=x>", "instructions": "<seq/><a href='javascript:1'>"}]}).json()
    pdf = client.get(f"{A}/consultations/{c['id']}/prescription.pdf", headers=h(t["doctor"]))
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    inv = client.post(f"{A}/invoices", headers=h(t["owner"]), json={"patient_id": p["id"], "items": [{"description": "<b>x</i>", "price": 1}]}).json()
    assert client.get(f"{A}/invoices/{inv['id']}/receipt.pdf", headers=h(t["owner"])).content.startswith(b"%PDF")
    up = client.post(f"{A}/patients/{p['id']}/documents", headers=h(t["nurse"]), files={"file": ("x.svg", b"<svg onload=alert(1)>")})
    assert up.status_code == 415                                                                     # active content types are refused
    ok = client.post(f"{A}/patients/{p['id']}/documents", headers=h(t["nurse"]), files={"file": ('a"<b>.txt', b"hello")}).json()
    dl = client.get(f"{A}/documents/{ok['id']}/download", headers=h(t["nurse"]))
    assert dl.headers["content-disposition"].startswith("attachment") and '"<' not in dl.headers["content-disposition"] and dl.headers["x-content-type-options"] == "nosniff"


# ---- headers, CORS, errors ----
def test_security_headers_cors_and_error_hygiene():
    r = client.get("/health")
    for k, v in {"x-content-type-options": "nosniff", "x-frame-options": "DENY", "referrer-policy": "no-referrer", "cache-control": "no-store"}.items():
        assert r.headers[k] == v
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"] and "camera=()" in r.headers["permissions-policy"]
    allowed = settings.cors_origins[0]
    ok = client.options(f"{A}/auth/login", headers={"Origin": allowed, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert ok.headers.get("access-control-allow-origin") == allowed and "access-control-allow-credentials" not in ok.headers
    evil = client.options(f"{A}/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in evil.headers
    bad_method = client.options(f"{A}/auth/login", headers={"Origin": allowed, "Access-Control-Request-Method": "TRACE"})
    assert bad_method.status_code == 400
    put_ok = client.options(f"{A}/admin/settings", headers={"Origin": allowed, "Access-Control-Request-Method": "PUT", "Access-Control-Request-Headers": "authorization,content-type"})
    assert put_ok.status_code == 200 and "PUT" in put_ok.headers["access-control-allow-methods"]      # the admin settings editor needs PUT
    # validation errors never echo what was submitted
    leak = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "X", "email": "nope", "password": "SuperSecret-Value-123"})
    assert leak.status_code == 422 and "SuperSecret-Value-123" not in leak.text and '"input"' not in leak.text
    # unexpected exceptions return a generic message, no traceback
    app.add_api_route("/__boom", lambda: 1 / 0)
    boom = TestClient(app, raise_server_exceptions=False).get("/__boom")
    assert boom.status_code == 500 and "ZeroDivision" not in boom.text and "Traceback" not in boom.text and boom.headers["x-content-type-options"] == "nosniff"
    app.router.routes = [x for x in app.router.routes if getattr(x, "path", "") != "/__boom"]


def test_request_size_limits():
    big = "x" * (1024 * 1024 + 10)
    assert client.post(f"{A}/auth/login", json={"email": "a@b.pk", "password": big}).status_code == 413
    def gen():
        for _ in range(40):
            yield b"y" * 65536
    assert client.post(f"{A}/auth/login", content=gen(), headers={"content-type": "application/json"}).status_code == 413     # chunked, no Content-Length
    t = clinic()
    p = patient(t)
    huge = client.post(f"{A}/patients/{p['id']}/documents", headers=h(t["nurse"]), files={"file": ("a.pdf", b"%PDF" + b"0" * (13 * 1024 * 1024))})
    assert huge.status_code == 413


# ---- rate limiting ----
def test_rate_limits_ip_user_and_global(monkeypatch):
    from app import main
    from app.util import _hits
    codes = [login("nobody@x.pk", "whatever1").status_code for _ in range(32)]
    assert codes[0] == 401 and codes[-1] == 429
    _hits.clear()
    assert [client.post(f"{A}/auth/forgot-password", json={"email": "a@b.pk"}).status_code for _ in range(6)][-1] == 429
    _hits.clear()
    t = clinic()
    sent = [client.post(f"{A}/chat", headers=h(t["doctor"]), json={"body": "hi"}).status_code for _ in range(62)]
    assert sent[59] == 201 and sent[-1] == 429
    assert client.post(f"{A}/chat", headers=h(t["nurse"]), json={"body": "hi"}).status_code == 201          # limit is per user, not shared
    _hits.clear()
    assert [client.post(f"{A}/ai/chat", headers=h(t["owner"]), json={"messages": [{"role": "user", "content": "hi"}]}).status_code for _ in range(22)][-1] == 429
    monkeypatch.setattr(main, "GLOBAL_LIMIT", 5)
    main._ip_hits.clear()
    assert [client.get("/health").status_code for _ in range(8)][-1] == 429


# ---- access control ----
def test_cross_clinic_access_is_impossible_for_every_object_type():
    a = clinic()
    p = patient(a)
    appt = client.post(f"{A}/appointments", headers=h(a["receptionist"]), json={"patient_id": p["id"], "scheduled_at": soon()}).json()
    cons = client.post(f"{A}/consultations", headers=h(a["doctor"]), json={"patient_id": p["id"], "complaint": "secret", "prescription": [{"medicine": "x"}]}).json()
    inv = client.post(f"{A}/invoices", headers=h(a["receptionist"]), json={"patient_id": p["id"], "items": [{"description": "x", "price": 10}]}).json()
    doc = client.post(f"{A}/patients/{p['id']}/documents", headers=h(a["nurse"]), files={"file": ("a.pdf", b"%PDF-1")}).json()
    item = client.post(f"{A}/inventory", headers=h(a["owner"]), json={"name": "Gloves", "quantity": 5}).json()
    svc = client.post(f"{A}/services", headers=h(a["owner"]), json={"name": "Visit", "price": 1}).json()
    loc = client.post(f"{A}/locations", headers=h(a["owner"]), json={"name": "Main"}).json()
    tpl = client.post(f"{A}/medicine-templates", headers=h(a["doctor"]), json={"medicine": "X"}).json()
    client.patch(f"{A}/appointments/{appt['id']}", headers=h(a["receptionist"]), json={"status": "arrived"})          # creates a notification for the doctor
    note = client.get(f"{A}/notifications", headers=h(a["doctor"])).json()
    assert note["items"]
    msg = client.post(f"{A}/chat", headers=h(a["doctor"]), json={"body": "hello"}).json()
    client.delete(f"{A}/patients/{p['id']}", headers=h(a["doctor"]))                                          # now in trash too
    client.delete(f"{A}/documents/{doc['id']}", headers=h(a["nurse"]))
    b = client.post(f"{A}/auth/register-clinic", json={"clinic_name": "Rival Clinic", "clinic_type": "General", "city": "K", "country": "PK", "full_name": "Dr Rival", "email": "rival@x.pk", "password": PW}).json()["access_token"]
    def attempts():
        P, ID = p["id"], {}
        yield "GET", f"/patients/{P}"; yield "PATCH", f"/patients/{P}"; yield "DELETE", f"/patients/{P}"; yield "GET", f"/patients/{P}/timeline"
        yield "POST", f"/patients/{P}/portal-access"; yield "GET", f"/patients/{P}/messages"; yield "POST", f"/patients/{P}/messages"; yield "GET", f"/documents?patient_id={P}"
        yield "PATCH", f"/appointments/{appt['id']}"; yield "DELETE", f"/appointments/{appt['id']}"
        yield "GET", f"/consultations/{cons['id']}"; yield "PATCH", f"/consultations/{cons['id']}"; yield "DELETE", f"/consultations/{cons['id']}"
        yield "GET", f"/consultations/{cons['id']}/prescription.pdf"; yield "POST", f"/consultations/{cons['id']}/summarize"
        yield "POST", f"/invoices/{inv['id']}/payments"; yield "POST", f"/invoices/{inv['id']}/refund"; yield "DELETE", f"/invoices/{inv['id']}"; yield "GET", f"/invoices/{inv['id']}/receipt.pdf"
        yield "GET", f"/documents/{doc['id']}/download"; yield "PATCH", f"/documents/{doc['id']}"; yield "DELETE", f"/documents/{doc['id']}"
        yield "PATCH", f"/inventory/{item['id']}"; yield "POST", f"/inventory/{item['id']}/adjust"; yield "DELETE", f"/inventory/{item['id']}"
        yield "DELETE", f"/services/{svc['id']}"; yield "DELETE", f"/locations/{loc['id']}"; yield "DELETE", f"/medicine-templates/{tpl['id']}"
        yield "DELETE", f"/staff/{a['doctor_member']}"; yield "PATCH", f"/staff/{a['receptionist_member']}/permissions"
        yield "POST", f"/notifications/{note['items'][0]['id']}/read"; yield "DELETE", f"/notifications/{note['items'][0]['id']}"
        yield "DELETE", f"/chat/{msg['id']}"
        for kind, oid in (("patients", P), ("documents", doc["id"]), ("appointments", appt["id"]), ("consultations", cons["id"]), ("invoices", inv["id"]), ("inventory", item["id"])):
            yield "POST", f"/trash/{kind}/{oid}/restore"; yield "DELETE", f"/trash/{kind}/{oid}"
        yield "DELETE", f"/staff/{a['doctor_member']}"
    body = {"POST": {"amount": 1, "body": "x", "delta": 1, "email": "z@z.pk", "password": "Whatever123"}, "PATCH": {"complaint": "hacked", "full_name": "Hacked", "can_view_clinical": True, "shared_with_patient": True}}
    results = {}
    for m, path in attempts():
        r = client.request(m, f"{A}{path}", headers=h(b), json=body.get(m))
        results[(m, path)] = r.status_code
    bad = {k: v for k, v in results.items() if v not in (403, 404)}
    assert bad == {}, f"cross-clinic access allowed: {bad}"
    assert len(results) >= 40
    # and clinic A's data is untouched
    assert client.get(f"{A}/consultations/{cons['id']}", headers=h(a["doctor"])).json()["complaint"] == "secret"
    with SessionLocal() as db:
        assert db.get(Invoice, uuid.UUID(inv["id"])).paid == 0


def test_role_matrix():
    t = clinic()
    p = patient(t)
    m = lambda method, path, role, **kw: client.request(method, f"{A}{path}", headers=h(t[role]), **kw).status_code
    matrix = [  # (method, path, json, roles that must be allowed)
        ("GET", "/analytics/summary", None, {"owner", "doctor"}), ("GET", "/audit", None, {"owner"}), ("GET", "/trash/patients", None, {"owner"}),
        ("POST", "/staff", {"email": "n@c.pk", "full_name": "New Person", "role": "nurse", "password": "Whatever123"}, {"owner"}),
        ("GET", "/invoices", None, {"owner", "doctor", "receptionist"}), ("GET", "/consultations", None, {"owner", "doctor", "nurse"}),
        ("POST", "/services", {"name": "S", "price": 1}, {"owner"}), ("GET", "/medicine-templates", None, {"owner", "doctor"}),
        ("POST", "/consultations", {"patient_id": p["id"]}, {"owner", "doctor"}), ("PATCH", "/clinic", {"city": "Karachi"}, {"owner"}),
    ]
    for method, path, body, allowed in matrix:
        for role in ("owner", "doctor", "receptionist", "nurse"):
            code = m(method, path, role, json=body)
            assert (code < 300) == (role in allowed), (method, path, role, code)
            assert code < 300 or code == 403, (method, path, role, code)


# ---- production config / debug mode / files ----
def test_production_refuses_unsafe_configuration_and_hides_docs():
    s = settings
    ok = dataclasses.replace(s, jwt_secret="Zk3-93hD0pQw8nLm2VxR7tYbC4fGhJ6uKa1SdE5oPiN", database_url="postgresql+psycopg://app:S0me-Long-Pass@db.internal/clinicos", cors_origins=("https://app.example.com",), app_url="https://app.example.com")
    assert validate(ok) == []
    for change in ({"jwt_secret": "changeme"}, {"jwt_secret": "a" * 40}, {"database_url": "sqlite://"}, {"database_url": "postgresql+psycopg://clinicos:clinicos@localhost/clinicos"},
                   {"cors_origins": ("*",)}, {"cors_origins": ("http://app.example.com",)}, {"cors_origins": ("http://localhost:3001",)}, {"app_url": "http://app.example.com"}):
        assert validate(dataclasses.replace(ok, **change)), change
    env = {**os.environ, "ENVIRONMENT": "production", "JWT_SECRET": ok.jwt_secret, "DATABASE_URL": "sqlite://", "CORS_ORIGINS": "https://app.example.com", "APP_URL": "https://app.example.com"}
    r = subprocess.run([sys.executable, "-c", "import app.main"], env=env, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    assert r.returncode != 0 and "Unsafe production configuration" in r.stderr                  # refuses to start
    env.update(DATABASE_URL="postgresql+psycopg://app:S0me-Long-Pass@localhost/x?host=/nonexistent", GLOBAL_RATE_LIMIT="1000")
    code = ("from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); "
            "print(c.get('/docs').status_code, c.get('/openapi.json').status_code, c.get('/health').headers.get('strict-transport-security'), app.debug)")
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
    assert r.stdout.split() == ["404", "404", "max-age=31536000;", "includeSubDomains", "False"], r.stdout + r.stderr


def test_uploaded_files_are_private_on_disk():
    t = clinic()
    p = patient(t)
    d = client.post(f"{A}/patients/{p['id']}/documents", headers=h(t["nurse"]), files={"file": ("a.pdf", b"%PDF-1")}).json()
    from app.models import Document
    with SessionLocal() as db:
        key = db.get(Document, uuid.UUID(d["id"])).storage_key
    path = os.path.join(settings.storage_dir, key)
    assert oct(os.stat(path).st_mode & 0o777) == "0o600" and re.fullmatch(r"[0-9a-f]{32}", key)
