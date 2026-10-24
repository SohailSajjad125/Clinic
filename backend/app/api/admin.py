"""Platform (super admin) endpoints. Super admins are created with `python -m app.cli create-superadmin` and belong to no clinic."""
import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..deps import Actor, get_admin
from .. import platform_settings as ps
from ..models import Appointment, AuditLog, Invoice, Clinic, ClinicMember, ContactMessage, OutboundMessage, Patient, Role, Session as AuthSession, User, utcnow
from ..realtime import hub
from ..schemas import AdminClinicPatch, AdminUserPatch, SettingsUpdateIn

router = APIRouter(prefix="/admin", tags=["admin"])


def _count(db, model, *where):
    return db.scalar(select(func.count()).select_from(model).where(*where)) or 0


@router.get("/stats")
def stats(_: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    now = utcnow()
    plans = dict(db.execute(select(Clinic.plan, func.count()).where(Clinic.deleted_at.is_(None)).group_by(Clinic.plan)).all())
    return {"clinics": _count(db, Clinic, Clinic.deleted_at.is_(None)), "active_clinics": _count(db, Clinic, Clinic.status == "active"), "new_clinics_30d": _count(db, Clinic, Clinic.created_at >= now - timedelta(days=30)),
            "users": _count(db, User), "patients": _count(db, Patient, Patient.deleted_at.is_(None)), "appointments_30d": _count(db, Appointment, Appointment.created_at >= now - timedelta(days=30)),
            "unhandled_messages": _count(db, ContactMessage, ContactMessage.handled.is_(False)), "plans": plans}


@router.get("/clinics")
def clinics(_: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(Clinic).where(Clinic.deleted_at.is_(None)).order_by(Clinic.created_at.desc()).limit(500)).all()
    out = []
    for c in rows:
        owner = db.scalars(select(User).join(ClinicMember, ClinicMember.user_id == User.id).where(ClinicMember.clinic_id == c.id, ClinicMember.role == Role.OWNER)).first()
        out.append({"id": c.id, "name": c.name, "clinic_type": c.clinic_type, "city": c.city, "country": c.country, "plan": c.plan, "status": c.status, "created_at": c.created_at,
                    "owner_email": owner.email if owner else None, "patients": _count(db, Patient, Patient.clinic_id == c.id, Patient.deleted_at.is_(None)),
                    "team": _count(db, ClinicMember, ClinicMember.clinic_id == c.id, ClinicMember.deleted_at.is_(None), ClinicMember.role.in_(Role.STAFF))})
    return out


@router.patch("/clinics/{cid}")
def update_clinic(cid: uuid.UUID, body: AdminClinicPatch, actor: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    c = db.get(Clinic, cid)
    if not c or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic not found.")
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(c, k, v)
    if c.status == "suspended":  # sign everyone in this clinic out
        from sqlalchemy import update
        mids = select(ClinicMember.id).where(ClinicMember.clinic_id == c.id)
        db.execute(update(AuthSession).where(AuthSession.member_id.in_(mids), AuthSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    db.add(AuditLog(clinic_id=c.id, actor_id=actor.user.id, action="admin.clinic_updated", entity_type="clinic", entity_id=c.id))
    db.commit()
    return {"id": c.id, "plan": c.plan, "status": c.status}


@router.get("/messages")
def messages(_: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    return [{"id": m.id, "name": m.name, "email": m.email, "clinic_name": m.clinic_name, "phone": m.phone, "topic": m.topic, "message": m.message, "handled": m.handled, "created_at": m.created_at}
            for m in db.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(200))]


@router.post("/messages/{mid}/handled", status_code=204)
def handled(mid: uuid.UUID, _: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    m = db.get(ContactMessage, mid)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found.")
    m.handled = True
    db.commit()


@router.get("/health")
def health(_: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    try:
        db.execute(text("select 1"))
        db_ok = True
    except Exception:
        db_ok = False
    day = utcnow() - timedelta(hours=24)
    return {"database": db_ok, "websocket_connections": hub.count(), "scheduler_enabled": settings.run_scheduler,
            "email_configured": bool(ps.get('smtp_host')), "sms_configured": bool(ps.get('twilio_sid') and ps.get('twilio_sms_from')), "whatsapp_configured": bool(ps.get('twilio_sid') and ps.get('twilio_whatsapp_from')),
            "assistant_configured": bool(ps.get('groq_api_key')) and bool(ps.get("assistant_enabled")), "storage_writable": os.access(settings.storage_dir, os.W_OK) if os.path.isdir(settings.storage_dir) else True,
            "messages_failed_24h": _count(db, OutboundMessage, OutboundMessage.status == "failed", OutboundMessage.created_at >= day),
            "messages_sent_24h": _count(db, OutboundMessage, OutboundMessage.status == "sent", OutboundMessage.created_at >= day)}


# ---------------- settings (API keys, model, e-mail, SMS, switches) ----------------
@router.get("/settings")
def get_settings(_: Actor = Depends(get_admin)):
    return ps.view()


@router.put("/settings")
def update_settings(body: SettingsUpdateIn, actor: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    unknown = [k for k in list(body.values) + body.clear if k not in ps.SPEC]
    if unknown:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown setting: {unknown[0]}")
    try:
        changed = ps.save(db, body.values, body.clear, actor.user.id)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))
    if changed:  # names only, never values
        db.add(AuditLog(clinic_id=None, actor_id=actor.user.id, action="admin.settings:" + ",".join(sorted(changed))[:90], entity_type="settings", entity_id=None))
    db.commit()
    ps.invalidate()
    return ps.view()


@router.post("/settings/test/{what}")
def test_setting(what: str, actor: Actor = Depends(get_admin)):
    """Checks the saved configuration. Returns a plain-language result; secrets are never echoed."""
    import httpx

    from .. import messaging

    if what == "email":
        try:
            messaging.send_email(actor.user.email, "ClinicOS test email", "If you can read this, your email settings work.")
        except Exception as e:
            return {"ok": False, "message": str(e).replace("skipped: ", "")[:200] or "Could not send."}
        return {"ok": True, "message": f"Test email sent to {actor.user.email}."}
    if what == "assistant":
        key = ps.get("groq_api_key")
        if not key:
            return {"ok": False, "message": "No API key is saved yet."}
        try:
            r = httpx.get(f"{ps.get('groq_base_url').rstrip('/')}/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
        except httpx.HTTPError:
            return {"ok": False, "message": "Couldn't reach the AI service."}
        return {"ok": r.status_code < 300, "message": "The key was accepted." if r.status_code < 300 else f"The AI service rejected the request (HTTP {r.status_code})."}
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown test.")


# ---------------- tracking: audit log, users, clinic detail, message log ----------------
@router.get("/audit")
def platform_audit(clinic_id: uuid.UUID | None = None, action: str | None = Query(None, max_length=60), entity: str | None = Query(None, max_length=40), limit: int = Query(100, le=500),
                   before: str | None = None, _: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if clinic_id:
        q = q.where(AuditLog.clinic_id == clinic_id)
    if action:
        q = q.where(AuditLog.action.icontains(action, autoescape=True))
    if entity:
        q = q.where(AuditLog.entity_type == entity)
    if before:
        try:
            q = q.where(AuditLog.created_at < datetime.fromisoformat(before))
        except ValueError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Bad date.")
    rows = db.scalars(q).all()
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.actor_id for r in rows if r.actor_id})))} if rows else {}
    clinics = {c.id: c.name for c in db.scalars(select(Clinic).where(Clinic.id.in_({r.clinic_id for r in rows if r.clinic_id})))} if rows else {}
    return [{"id": r.id, "at": r.created_at, "action": r.action, "entity": r.entity_type, "entity_id": r.entity_id, "clinic": clinics.get(r.clinic_id, "Platform" if r.clinic_id is None else "Removed clinic"),
             "clinic_id": r.clinic_id, "actor": users[r.actor_id].full_name if r.actor_id in users else ("Removed user" if r.actor_id else "System"),
             "actor_email": users[r.actor_id].email if r.actor_id in users else None} for r in rows]


@router.get("/clinics/{cid}")
def clinic_detail(cid: uuid.UUID, _: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    c = db.get(Clinic, cid)
    if not c or c.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clinic not found.")
    team = db.execute(select(ClinicMember, User).join(User, User.id == ClinicMember.user_id).where(ClinicMember.clinic_id == cid, ClinicMember.deleted_at.is_(None)).order_by(ClinicMember.created_at)).all()
    now = utcnow()
    return {"id": c.id, "name": c.name, "clinic_type": c.clinic_type, "city": c.city, "country": c.country, "plan": c.plan, "status": c.status, "public_listing": c.public_listing, "created_at": c.created_at,
            "counts": {"patients": _count(db, Patient, Patient.clinic_id == cid, Patient.deleted_at.is_(None)), "appointments_30d": _count(db, Appointment, Appointment.clinic_id == cid, Appointment.created_at >= now - timedelta(days=30)),
                       "requests_open": _count(db, Appointment, Appointment.clinic_id == cid, Appointment.status == "requested", Appointment.deleted_at.is_(None)), "invoices": _count(db, Invoice, Invoice.clinic_id == cid, Invoice.deleted_at.is_(None))},
            "team": [{"user_id": u.id, "name": u.full_name, "email": u.email, "role": m.role, "active": u.is_active, "last_login": u.last_login_at} for m, u in team]}


@router.get("/users")
def users(q: str | None = Query(None, max_length=100), limit: int = Query(100, le=300), _: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    if q and q.strip():
        stmt = stmt.where(User.email.icontains(q.strip(), autoescape=True) | User.full_name.icontains(q.strip(), autoescape=True))
    out = []
    for u in db.scalars(stmt).all():
        ms = db.execute(select(ClinicMember, Clinic).join(Clinic, Clinic.id == ClinicMember.clinic_id).where(ClinicMember.user_id == u.id, ClinicMember.deleted_at.is_(None))).all()
        out.append({"id": u.id, "name": u.full_name, "email": u.email, "is_active": u.is_active, "is_superadmin": u.is_superadmin, "email_verified": u.email_verified, "created_at": u.created_at, "last_login": u.last_login_at,
                    "memberships": [{"clinic": c.name, "role": m.role} for m, c in ms], "sessions": _count(db, AuthSession, AuthSession.user_id == u.id, AuthSession.revoked_at.is_(None))})
    return out


@router.patch("/users/{uid}")
def set_user_active(uid: uuid.UUID, body: AdminUserPatch, actor: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    from sqlalchemy import update

    u = db.get(User, uid)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    if u.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform admin accounts can't be changed here.")
    u.is_active = body.is_active
    if not body.is_active:
        db.execute(update(AuthSession).where(AuthSession.user_id == u.id, AuthSession.revoked_at.is_(None)).values(revoked_at=utcnow()))
    db.add(AuditLog(clinic_id=None, actor_id=actor.user.id, action="admin.user_" + ("enabled" if body.is_active else "disabled"), entity_type="user", entity_id=u.id))
    db.commit()
    return {"id": u.id, "is_active": u.is_active}


@router.get("/outbound")
def outbound(status_: str | None = Query(None, alias="status", max_length=10), limit: int = Query(100, le=300), _: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    q = select(OutboundMessage).order_by(OutboundMessage.created_at.desc()).limit(limit)
    if status_:
        q = q.where(OutboundMessage.status == status_)
    rows = db.scalars(q).all()
    names = {c.id: c.name for c in db.scalars(select(Clinic).where(Clinic.id.in_({r.clinic_id for r in rows})))} if rows else {}
    return [{"id": r.id, "at": r.created_at, "clinic": names.get(r.clinic_id, ""), "channel": r.channel, "subject": r.subject, "status": r.status, "error": r.error} for r in rows]  # no recipients or bodies


@router.get("/signups")
def signups(_: Actor = Depends(get_admin), db: Session = Depends(get_db)):
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for i in range(13, -1, -1):
        a = today - timedelta(days=i)
        out.append({"date": a.date().isoformat(), "clinics": _count(db, Clinic, Clinic.created_at >= a, Clinic.created_at < a + timedelta(days=1)),
                    "patients": _count(db, Patient, Patient.self_registered.is_(True), Patient.created_at >= a, Patient.created_at < a + timedelta(days=1))})
    return out
