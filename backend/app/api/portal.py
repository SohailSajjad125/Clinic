import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .. import messaging
from ..core.database import get_db
from ..core.security import hash_password
from ..deps import Ctx, require_roles
from ..models import (Appointment, ClinicMember, Consultation, Document, Invoice, Patient, PortalMessage, Role, Session as AuthSession, User, utcnow)
from ..pdf import prescription_pdf, receipt_pdf
from ..realtime import publish
from ..schemas import MessageIn, PortalBookIn, PortalInviteIn
from ..util import Notifier, audit, changed, clear_chat, cleared_at, cleared_map, rate_limit_user, scoped, utc
from .billing import inv_out, inv_status
from .clinical import _check_doctor, _check_free, appt_out
from .doctors import active_doctors, compute_slots, doctor_card
from .documents import doc_out, serve

router = APIRouter(tags=["portal"])
staff = require_roles(*Role.STAFF)
inviter = require_roles(Role.OWNER, Role.DOCTOR, Role.RECEPTIONIST)
patient_only = require_roles(Role.PATIENT)


# ---------- staff side ----------
@router.post("/patients/{pid}/portal-access", status_code=201)
def invite(pid: uuid.UUID, body: PortalInviteIn, ctx: Ctx = Depends(inviter), db: Session = Depends(get_db)):
    p = scoped(db, Patient, pid, ctx)
    if p.user_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "This patient already has portal access.")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    u = User(email=email, full_name=p.full_name, password_hash=hash_password(body.password), must_change_password=True)
    db.add(u)
    db.flush()
    db.add(ClinicMember(user_id=u.id, clinic_id=ctx.clinic.id, role=Role.PATIENT))
    p.user_id = u.id
    if not p.email:
        p.email = email
    audit(db, ctx, "portal.invited", "patient", p.id)
    db.commit()
    changed(ctx, "patients")
    messaging.notify_patient(ctx.clinic.id, p.id, "Your patient portal is ready", f"{ctx.clinic.name} created a portal account for you. Sign in with {email} and the password the clinic gave you.")
    return {"ok": True}


def drop_portal_user(db: Session, user_id):
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    db.execute(delete(ClinicMember).where(ClinicMember.user_id == user_id, ClinicMember.role == Role.PATIENT))
    u = db.get(User, user_id)
    if u and not u.is_superadmin and not db.scalar(select(func.count()).select_from(ClinicMember).where(ClinicMember.user_id == user_id)):
        db.delete(u)


@router.delete("/patients/{pid}/portal-access", status_code=204)
def revoke(pid: uuid.UUID, ctx: Ctx = Depends(inviter), db: Session = Depends(get_db)):
    p = scoped(db, Patient, pid, ctx)
    if p.user_id:
        drop_portal_user(db, p.user_id)
        p.user_id = None
        audit(db, ctx, "portal.revoked", "patient", p.id)
        db.commit()
        changed(ctx, "patients")


@router.get("/messages/inbox")
def inbox(ctx: Ctx = Depends(staff), db: Session = Depends(get_db)):
    rows = db.scalars(select(PortalMessage).join(Patient, Patient.id == PortalMessage.patient_id).where(PortalMessage.clinic_id == ctx.clinic.id, Patient.deleted_at.is_(None)).order_by(PortalMessage.created_at.desc())).all()
    out: dict = {}
    gone = cleared_map(db, ctx.user.id, "patient")
    for m in rows:
        if gone.get(str(m.patient_id)) and utc(m.created_at) <= gone[str(m.patient_id)]:
            continue                                                                  # cleared from this person's view only
        e = out.setdefault(m.patient_id, {"patient_id": m.patient_id, "patient_name": m.patient.full_name if hasattr(m, "patient") else "", "last": m.body, "at": m.created_at, "unread": 0})
        e["unread"] += 1 if (m.from_patient and not m.read) else 0
    names = {p.id: p.full_name for p in db.scalars(select(Patient).where(Patient.id.in_(list(out)))).all()} if out else {}
    for k, e in out.items():
        e["patient_name"] = names.get(k, "")
    return list(out.values())


def _msg(m: PortalMessage) -> dict:
    return {"id": m.id, "from_patient": m.from_patient, "sender_name": m.sender_name, "body": m.body, "created_at": m.created_at}


@router.get("/patients/{pid}/messages")
def thread(pid: uuid.UUID, ctx: Ctx = Depends(staff), db: Session = Depends(get_db)):
    scoped(db, Patient, pid, ctx)
    rows = db.scalars(select(PortalMessage).where(PortalMessage.patient_id == pid, PortalMessage.clinic_id == ctx.clinic.id).order_by(PortalMessage.created_at)).all()
    gone = cleared_at(db, ctx.user.id, f"patient:{pid}")
    if gone:
        rows = [m for m in rows if utc(m.created_at) > gone]
    unread = [m for m in rows if m.from_patient and not m.read]
    for m in unread:
        m.read = True
    if unread:
        db.commit()
        changed(ctx, "portal-messages")
    return [_msg(m) for m in rows[-200:]]


@router.post("/patients/{pid}/messages/clear", status_code=204)
def clear_thread(pid: uuid.UUID, ctx: Ctx = Depends(staff), db: Session = Depends(get_db)):
    scoped(db, Patient, pid, ctx)
    clear_chat(db, ctx.user.id, ctx.clinic.id, f"patient:{pid}")
    audit(db, ctx, "chat.cleared_own_view", "patient", pid)
    db.commit()
    changed(ctx, "portal-messages")


@router.post("/patients/{pid}/messages", status_code=201)
def reply(pid: uuid.UUID, body: MessageIn, ctx: Ctx = Depends(staff), db: Session = Depends(get_db)):
    p = scoped(db, Patient, pid, ctx)
    m = PortalMessage(clinic_id=ctx.clinic.id, patient_id=p.id, sender_id=ctx.user.id, sender_name=ctx.user.full_name, from_patient=False, body=body.body.strip(), read=True)
    db.add(m)
    audit(db, ctx, "staff.message_sent", "patient", p.id)
    db.commit()
    changed(ctx, "portal-messages")
    if p.user_id:
        nt = Notifier(db, ctx).add(f"New message from {ctx.clinic.name}", body.body.strip()[:140], "messages", "/portal?tab=messages", user_ids=[p.user_id])
        db.commit()
        nt.push()
        publish(ctx.clinic.id, {"type": "portal"}, user_ids=[p.user_id])
    messaging.notify_patient(ctx.clinic.id, p.id, f"New message from {ctx.clinic.name}", body.body.strip()[:300])
    return _msg(m)


# ---------- patient side ----------
def me_patient(db: Session, ctx: Ctx) -> Patient:
    p = db.scalar(select(Patient).where(Patient.user_id == ctx.user.id, Patient.clinic_id == ctx.clinic.id, Patient.deleted_at.is_(None)))
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Your patient record isn't available. Contact the clinic.")
    return p


def _shared(db, p):
    return db.scalars(select(Consultation).where(Consultation.patient_id == p.id, Consultation.deleted_at.is_(None), Consultation.shared_with_patient.is_(True)).order_by(Consultation.created_at.desc())).all()


def _doctor(db, c):
    m = db.get(ClinicMember, c.doctor_id) if c.doctor_id else None
    return m.user.full_name if m else None


@router.get("/portal/home")
def home(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    nxt = db.scalars(select(Appointment).where(Appointment.patient_id == p.id, Appointment.deleted_at.is_(None), Appointment.status.in_(("booked", "confirmed")), Appointment.scheduled_at >= utcnow()).order_by(Appointment.scheduled_at).limit(1)).first()
    gone = cleared_at(db, ctx.user.id, "portal")
    uq = select(func.count()).select_from(PortalMessage).where(PortalMessage.patient_id == p.id, PortalMessage.from_patient.is_(False), PortalMessage.read.is_(False))
    unread = db.scalar(uq.where(PortalMessage.created_at > gone) if gone else uq)
    follow = [c.follow_up_on for c in _shared(db, p) if c.follow_up_on and c.follow_up_on >= date.today()]
    return {"name": p.full_name, "clinic": ctx.clinic.name, "next_appointment": appt_out(nxt) if nxt else None, "unread_messages": unread, "next_follow_up": min(follow) if follow else None}


@router.get("/portal/appointments")
def my_appts(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    return [appt_out(a) for a in db.scalars(select(Appointment).where(Appointment.patient_id == p.id, Appointment.deleted_at.is_(None)).order_by(Appointment.scheduled_at.desc()).limit(100)).all()]


@router.get("/portal/doctors")
def portal_doctors(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    me_patient(db, ctx)
    return [doctor_card(db, m) for m in active_doctors(db, ctx.clinic.id)]


@router.get("/portal/slots")
def portal_slots(date_: date = Query(alias="date"), doctor_id: uuid.UUID | None = None, tz_offset_minutes: int = Query(0, ge=-840, le=840), ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    me_patient(db, ctx)
    m = db.get(ClinicMember, doctor_id) if doctor_id else None
    if doctor_id and (not m or m.clinic_id != ctx.clinic.id or m.deleted_at is not None or m.role not in (Role.DOCTOR, Role.OWNER)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found.")
    return compute_slots(db, ctx.clinic, m, date_, tz_offset_minutes)


@router.post("/portal/appointments", status_code=201)
def book(body: PortalBookIn, ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    """A patient asks for a time. It stays 'requested' until the clinic approves it."""
    rate_limit_user(ctx, "portal_book", 10, 600)
    p = me_patient(db, ctx)
    when = utc(body.scheduled_at)
    if when < utcnow():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a time in the future.")
    _check_doctor(db, ctx, body.doctor_id)
    _check_free(db, ctx, body.doctor_id, when)
    a = Appointment(clinic_id=ctx.clinic.id, patient_id=p.id, doctor_id=body.doctor_id, scheduled_at=when, reason=body.reason, status="requested")
    db.add(a)
    db.flush()
    nt = Notifier(db, ctx).add("New appointment request", f"{p.full_name} · {when:%d %b %H:%M} UTC", "appointments", "/appointments?tab=requests",
                               roles=(Role.RECEPTIONIST, Role.OWNER), user_ids=Notifier(db, ctx).doctor_user(body.doctor_id))
    audit(db, ctx, "portal.appointment_requested", "appointment", a.id)
    db.commit()
    changed(ctx, "appointments", "notifications")
    nt.push()
    return appt_out(a)


@router.post("/portal/appointments/{aid}/cancel", status_code=204)
def cancel(aid: uuid.UUID, ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    a = db.get(Appointment, aid)
    if not a or a.patient_id != p.id or a.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appointment not found.")
    if a.status not in ("requested", "booked", "confirmed"):
        raise HTTPException(status.HTTP_409_CONFLICT, "This appointment can no longer be cancelled online.")
    a.status = "cancelled"
    nt = Notifier(db, ctx).add("Appointment cancelled by patient", f"{p.full_name} cancelled {a.scheduled_at:%d %b %H:%M} UTC.", "appointments", "/appointments",
                               roles=(Role.RECEPTIONIST, Role.OWNER), user_ids=Notifier(db, ctx).doctor_user(a.doctor_id))
    audit(db, ctx, "portal.appointment_cancelled", "appointment", a.id)
    db.commit()
    changed(ctx, "appointments", "notifications")
    nt.push()


@router.get("/portal/prescriptions")
def my_rx(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    return [{"id": c.id, "date": c.created_at, "doctor": _doctor(db, c), "prescription": c.prescription, "follow_up_on": c.follow_up_on} for c in _shared(db, p) if c.prescription]


@router.get("/portal/prescriptions/{cid}/pdf")
def my_rx_pdf(cid: uuid.UUID, ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    c = next((x for x in _shared(db, p) if x.id == cid), None)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found.")
    return Response(prescription_pdf(ctx.clinic.name, p.full_name, _doctor(db, c), c), media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="prescription.pdf"'})


@router.get("/portal/followups")
def my_followups(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    return [{"id": c.id, "due": c.follow_up_on, "doctor": _doctor(db, c)} for c in _shared(db, p) if c.follow_up_on and c.follow_up_on >= date.today() - timedelta(days=7)]


@router.get("/portal/documents")
def my_docs(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    return [doc_out(d) for d in db.scalars(select(Document).where(Document.patient_id == p.id, Document.deleted_at.is_(None), Document.shared_with_patient.is_(True)).order_by(Document.created_at.desc())).all()]


@router.get("/portal/documents/{did}/download")
def my_doc(did: uuid.UUID, ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    d = db.get(Document, did)
    if not d or d.patient_id != p.id or d.deleted_at is not None or not d.shared_with_patient:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return serve(d)


@router.get("/portal/invoices")
def my_invoices(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    return [inv_out(i) for i in db.scalars(select(Invoice).where(Invoice.patient_id == p.id, Invoice.deleted_at.is_(None)).order_by(Invoice.number.desc())).all()]


@router.get("/portal/invoices/{iid}/receipt.pdf")
def my_receipt(iid: uuid.UUID, ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    i = db.get(Invoice, iid)
    if not i or i.patient_id != p.id or i.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found.")
    return Response(receipt_pdf(ctx.clinic.name, i, inv_status(i)), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="invoice-{i.number}.pdf"'})


@router.get("/portal/messages")
def my_messages(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    p = me_patient(db, ctx)
    rows = db.scalars(select(PortalMessage).where(PortalMessage.patient_id == p.id).order_by(PortalMessage.created_at)).all()
    gone = cleared_at(db, ctx.user.id, "portal")
    if gone:
        rows = [m for m in rows if utc(m.created_at) > gone]
    for m in rows:
        if not m.from_patient and not m.read:
            m.read = True
    db.commit()
    return [_msg(m) for m in rows[-200:]]


@router.post("/portal/messages/clear", status_code=204)
def clear_my_thread(ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    me_patient(db, ctx)
    clear_chat(db, ctx.user.id, ctx.clinic.id, "portal")
    audit(db, ctx, "chat.cleared_own_view", "portal_chat", None)
    db.commit()


@router.post("/portal/messages", status_code=201)
def send_message(body: MessageIn, ctx: Ctx = Depends(patient_only), db: Session = Depends(get_db)):
    rate_limit_user(ctx, "portal_msg", 30, 600)
    p = me_patient(db, ctx)
    m = PortalMessage(clinic_id=ctx.clinic.id, patient_id=p.id, sender_id=ctx.user.id, sender_name=p.full_name, from_patient=True, body=body.body.strip())
    db.add(m)
    nt = Notifier(db, ctx).add(f"Message from {p.full_name}", body.body.strip()[:140], "messages", "/messages", roles=(Role.RECEPTIONIST, Role.DOCTOR, Role.OWNER))
    audit(db, ctx, "portal.message_sent", "patient", p.id)
    db.commit()
    changed(ctx, "portal-messages", "notifications")
    nt.push()
    return _msg(m)
