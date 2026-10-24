import secrets
import uuid
from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from .. import messaging
from .. import platform_settings as ps
from .. import limits
from ..core.config import settings
from ..core.database import get_db
from ..core.security import DUMMY_HASH, create_token, decode_token, hash_password, hash_token, verify_password
from ..deps import Actor, Ctx, actor_from_payload, get_actor, get_ctx, member_from_payload
from ..models import AuditLog, Clinic, ClinicMember, EmailToken, Patient, Role, Session, User, utcnow
from ..schemas import AuthOut, ChangePasswordIn, ForgotIn, LoginIn, MeOut, RefreshIn, RegisterClinicIn, RegisterPatientIn, ResetIn, TokenIn
from ..realtime import publish
from ..util import STAFF_ROLES, Notifier, notify_admins, rate_limit, utc

router = APIRouter(prefix="/auth", tags=["auth"])
MAX_FAILS, LOCK_MIN = 5, 15


def _me(user: User, member: ClinicMember | None) -> dict:
    if member is None:
        return {"user_id": user.id, "email": user.email, "full_name": user.full_name, "role": "superadmin", "email_verified": user.email_verified, "must_change_password": user.must_change_password}
    c = member.clinic
    return {"user_id": user.id, "member_id": member.id, "email": user.email, "full_name": user.full_name, "role": member.role, "clinic": {"id": c.id, "name": c.name},
            "email_verified": user.email_verified, "must_change_password": user.must_change_password, "plan": c.plan, "can_view_clinical": member.can_view_clinical}


def _issue(db: DBSession, user: User, member: ClinicMember | None, request: Request) -> dict:
    jti = secrets.token_hex(16)
    sess = Session(user_id=user.id, member_id=member.id if member else None, refresh_jti=jti, user_agent=(request.headers.get("user-agent") or "")[:200])
    db.add(sess)
    user.last_login_at = utcnow()
    db.commit()
    mid = member.id if member else None
    return {"access_token": create_token(user.id, mid, "access", sess.id), "refresh_token": create_token(user.id, mid, "refresh", sess.id, jti), "me": _me(user, member)}


def _email_token(db: DBSession, user: User, kind: str, hours: int) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(EmailToken(user_id=user.id, kind=kind, token_hash=hash_token(raw), expires_at=utcnow() + timedelta(hours=hours)))
    return raw


def _send_verification(db: DBSession, user: User):
    raw = _email_token(db, user, "verify", 72)
    db.commit()
    messaging.email_user(user.email, "Verify your ClinicOS email", f"Hello {user.full_name},\n\nConfirm your email address:\n{settings.app_url}/verify-email?token={raw}\n\nThis link expires in 3 days.")


@router.post("/register-clinic", response_model=AuthOut, status_code=201)
def register_clinic(body: RegisterClinicIn, request: Request, db: DBSession = Depends(get_db)):
    rate_limit(request, "register", 10, 3600)
    if not ps.get("allow_clinic_signups"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "New clinic sign-ups are closed right now. Please contact us.")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    clinic = Clinic(name=body.clinic_name, clinic_type=body.clinic_type, city=body.city, country=body.country)
    user = User(email=email, full_name=body.full_name, password_hash=hash_password(body.password))
    db.add_all([clinic, user])
    db.flush()
    member = ClinicMember(user_id=user.id, clinic_id=clinic.id, role=Role.OWNER)
    db.add(member)
    db.flush()
    db.add(AuditLog(clinic_id=clinic.id, actor_id=user.id, action="clinic.created", entity_type="clinic", entity_id=clinic.id))
    push_admins = notify_admins(db, "New clinic signed up", f"{clinic.name} · {clinic.city}", "admin_clinics", "/admin?tab=clinics")
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    push_admins()
    _send_verification(db, user)
    return _issue(db, user, member, request)


@router.post("/register-patient", response_model=AuthOut, status_code=201)
def register_patient(body: RegisterPatientIn, request: Request, db: DBSession = Depends(get_db)):
    """Public sign-up for patients. Always creates a NEW record: it never attaches to a record staff created, because an e-mail address alone is not proof of identity."""
    rate_limit(request, "register_patient", 10, 3600)
    if not ps.get("allow_patient_signups"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Patient sign-ups are closed right now.")
    clinic = db.get(Clinic, body.clinic_id)
    if not clinic or clinic.deleted_at is not None or clinic.status != "active" or not clinic.public_listing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "We couldn't find that clinic. Check the name and try again.")
    lim = limits.LIMITS.get(clinic.plan, {}).get("patients")
    if lim and limits.usage(db, clinic)["patients"] >= lim:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This clinic isn't accepting new online patients right now. Please call the clinic.")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=email, full_name=body.full_name, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    member = ClinicMember(user_id=user.id, clinic_id=clinic.id, role=Role.PATIENT)
    patient = Patient(clinic_id=clinic.id, full_name=body.full_name, email=email, phone=body.phone, date_of_birth=body.date_of_birth, user_id=user.id, self_registered=True)
    db.add_all([member, patient])
    db.flush()
    db.add(AuditLog(clinic_id=clinic.id, actor_id=user.id, action="patient.self_registered", entity_type="patient", entity_id=patient.id))
    nt = Notifier(db, None, clinic.id).add("New patient registered", body.full_name, "patients", "/patients", roles=(Role.RECEPTIONIST, Role.OWNER))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    publish(clinic.id, {"type": "data", "entity": "patients"}, roles=STAFF_ROLES)
    nt.push()
    _send_verification(db, user)
    return _issue(db, user, member, request)


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, request: Request, db: DBSession = Depends(get_db)):
    rate_limit(request, "login", 30, 600)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.locked_until and utc(user.locked_until) > utcnow():
        mins = int((utc(user.locked_until) - utcnow()).total_seconds() // 60) + 1
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Too many failed attempts. Try again in {mins} minute{'s' if mins != 1 else ''}.")
    ok = verify_password(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not ok or not user.is_active:
        if user:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILS:
                user.failed_logins, user.locked_until = 0, utcnow() + timedelta(minutes=LOCK_MIN)
            db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect.")
    user.failed_logins, user.locked_until = 0, None
    if user.is_superadmin:
        if body.audience == "patient":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This is the patient login. Platform admins sign in on the staff login page.")
        return _issue(db, user, None, request)
    q = select(ClinicMember).join(Clinic, Clinic.id == ClinicMember.clinic_id).where(ClinicMember.user_id == user.id, ClinicMember.deleted_at.is_(None), Clinic.deleted_at.is_(None))
    if body.clinic_id:
        q = q.where(ClinicMember.clinic_id == body.clinic_id)
    members = db.scalars(q.order_by(ClinicMember.created_at)).all()
    if body.audience:
        wanted = [m for m in members if (m.role == Role.PATIENT) == (body.audience == "patient")]
        if members and not wanted:
            db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "This is the patient login. Clinic staff sign in on the staff login page." if body.audience == "patient" else "This is the staff login. Patients sign in on the patient login page.")
        members = wanted
    if not members:
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account no longer has access to a clinic.")
    member = next((m for m in members if m.clinic.status == "active"), None)
    if not member:
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This clinic's account is suspended. Please contact support.")
    db.add(AuditLog(clinic_id=member.clinic_id, actor_id=user.id, action="auth.login", entity_type="session", entity_id=None))
    return _issue(db, user, member, request)


@router.post("/refresh", response_model=AuthOut)
def refresh(body: RefreshIn, db: DBSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token, "refresh")
        sess = db.get(Session, uuid.UUID(payload["sid"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.")
    if not sess or sess.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.")
    if payload.get("jti") != sess.refresh_jti:  # an old token was replayed: assume theft and end the session
        sess.revoked_at = utcnow()
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session has expired. Sign in again.")
    actor = actor_from_payload(db, payload)
    member = None
    if not actor.user.is_superadmin:
        member = member_from_payload(db, payload).member
    sess.refresh_jti, sess.last_used_at = secrets.token_hex(16), utcnow()
    db.commit()
    mid = member.id if member else None
    return {"access_token": create_token(actor.user.id, mid, "access", sess.id), "refresh_token": create_token(actor.user.id, mid, "refresh", sess.id, sess.refresh_jti), "me": _me(actor.user, member)}


@router.get("/me", response_model=MeOut)
def me(actor: Actor = Depends(get_actor), db: DBSession = Depends(get_db)):
    member = db.get(ClinicMember, actor.session.member_id) if actor.session.member_id else None
    if member and (member.deleted_at is not None or member.clinic.deleted_at is not None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Your session is invalid or has expired. Sign in again.")
    return _me(actor.user, member)


@router.post("/logout", status_code=204)
def logout(actor: Actor = Depends(get_actor), db: DBSession = Depends(get_db)):
    actor.session.revoked_at = utcnow()
    db.commit()


@router.get("/sessions")
def sessions(actor: Actor = Depends(get_actor), db: DBSession = Depends(get_db)):
    rows = db.scalars(select(Session).where(Session.user_id == actor.user.id, Session.revoked_at.is_(None)).order_by(Session.last_used_at.desc())).all()
    return [{"id": s.id, "device": s.user_agent or "Unknown device", "signed_in": s.created_at, "last_used": s.last_used_at, "current": s.id == actor.session.id} for s in rows]


@router.delete("/sessions/{sid}", status_code=204)
def revoke(sid: uuid.UUID, actor: Actor = Depends(get_actor), db: DBSession = Depends(get_db)):
    s = db.get(Session, sid)
    if not s or s.user_id != actor.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    s.revoked_at = utcnow()
    db.commit()


@router.post("/change-password", status_code=204)
def change_password(body: ChangePasswordIn, actor: Actor = Depends(get_actor), db: DBSession = Depends(get_db)):
    if not verify_password(body.current_password, actor.user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your current password is incorrect.")
    if verify_password(body.new_password, actor.user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose a password you haven't used just now.")
    actor.user.password_hash = hash_password(body.new_password)
    actor.user.must_change_password = False
    db.execute(update(Session).where(Session.user_id == actor.user.id, Session.id != actor.session.id, Session.revoked_at.is_(None)).values(revoked_at=utcnow()))
    db.commit()


@router.post("/forgot-password", status_code=202)
def forgot(body: ForgotIn, request: Request, db: DBSession = Depends(get_db)):
    rate_limit(request, "forgot", 5, 3600)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active:
        raw = _email_token(db, user, "reset", 1)
        db.commit()
        messaging.email_user(user.email, "Reset your ClinicOS password", f"Use this link to choose a new password (valid for 1 hour):\n{settings.app_url}/reset-password?token={raw}\n\nIf you didn't ask for this, ignore this email.")
    return {"ok": True}  # same answer whether or not the address exists


def _consume(db: DBSession, raw: str, kind: str) -> User:
    t = db.scalar(select(EmailToken).where(EmailToken.token_hash == hash_token(raw), EmailToken.kind == kind))
    if not t or t.used_at is not None or utc(t.expires_at) < utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This link is invalid or has expired.")
    t.used_at = utcnow()
    return db.get(User, t.user_id)


@router.post("/reset-password", status_code=204)
def reset(body: ResetIn, db: DBSession = Depends(get_db)):
    user = _consume(db, body.token, "reset")
    user.password_hash, user.failed_logins, user.locked_until = hash_password(body.password), 0, None
    db.execute(update(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None)).values(revoked_at=utcnow()))
    db.commit()


@router.post("/verify-email", status_code=204)
def verify(body: TokenIn, db: DBSession = Depends(get_db)):
    _consume(db, body.token, "verify").email_verified = True
    db.commit()


@router.post("/resend-verification", status_code=202)
def resend(request: Request, actor: Actor = Depends(get_actor), db: DBSession = Depends(get_db)):
    rate_limit(request, "resend", 5, 3600)
    if not actor.user.email_verified:
        _send_verification(db, actor.user)
    return {"ok": True}
