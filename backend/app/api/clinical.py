import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..deps import Ctx, require_roles
from ..models import Appointment, ClinicMember, Consultation, Document, Invoice, Location, Patient, Role
from .. import limits, messaging
from ..pdf import prescription_pdf
from ..schemas import (WalkInIn, AppointmentIn, AppointmentOut, AppointmentPatch, ConsultationIn, ConsultationOut, ConsultationPatch, PatientIn,
                       PatientOut, PatientPatch)
from ..util import Notifier, audit, changed, scoped, utc
from ..models import utcnow

router = APIRouter(tags=["clinical"])
ALL = require_roles(*Role.STAFF)


def clinical_read(ctx: Ctx = Depends(ALL)) -> Ctx:
    if ctx.member.role not in (Role.OWNER, Role.DOCTOR, Role.NURSE) and not ctx.member.can_view_clinical:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have permission to do this.")
    return ctx


CLINICAL_READ = clinical_read
DOCTORS = (Role.OWNER, Role.DOCTOR)

# ---------------- patients ----------------


@router.get("/patients", response_model=list[PatientOut])
def list_patients(q: str | None = Query(None, max_length=100), limit: int = Query(200, le=500), ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    stmt = select(Patient).where(Patient.clinic_id == ctx.clinic.id, Patient.deleted_at.is_(None))
    if q and q.strip():
        t = q.strip()
        stmt = stmt.where(Patient.full_name.icontains(t, autoescape=True) | Patient.phone.icontains(t, autoescape=True) | Patient.email.icontains(t, autoescape=True))
    return db.scalars(stmt.order_by(Patient.created_at.desc()).limit(limit)).all()


@router.post("/patients", response_model=PatientOut, status_code=201)
def create_patient(body: PatientIn, ctx: Ctx = Depends(require_roles(Role.OWNER, Role.RECEPTIONIST, Role.NURSE)), db: Session = Depends(get_db)):
    limits.check_patient_quota(db, ctx)
    p = Patient(clinic_id=ctx.clinic.id, **body.model_dump())
    db.add(p)
    db.flush()
    audit(db, ctx, "patient.created", "patient", p.id)
    db.commit()
    changed(ctx, "patients")
    return p


@router.get("/patients/{pid}", response_model=PatientOut)
def get_patient(pid: uuid.UUID, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    return scoped(db, Patient, pid, ctx)


@router.patch("/patients/{pid}", response_model=PatientOut)
def update_patient(pid: uuid.UUID, body: PatientPatch, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    p = scoped(db, Patient, pid, ctx)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "full_name" and v is None:
            continue
        setattr(p, k, v)
    audit(db, ctx, "patient.updated", "patient", p.id)
    db.commit()
    changed(ctx, "patients")
    return p


@router.delete("/patients/{pid}", status_code=204)
def delete_patient(pid: uuid.UUID, ctx: Ctx = Depends(require_roles(Role.OWNER, Role.DOCTOR)), db: Session = Depends(get_db)):
    p = scoped(db, Patient, pid, ctx)
    p.deleted_at, p.deleted_by = utcnow(), ctx.user.id
    audit(db, ctx, "patient.deleted", "patient", p.id)
    db.commit()
    changed(ctx, "patients", "appointments", "invoices", "consultations", "trash")


# ---------------- appointments ----------------

ALLOWED = {
    "requested": {"booked", "confirmed", "cancelled"},
    "booked": {"confirmed", "arrived", "cancelled", "no_show"},
    "confirmed": {"arrived", "cancelled", "no_show", "booked"},
    "arrived": {"in_consultation", "cancelled", "no_show"},
    "in_consultation": {"completed", "arrived"},
    "completed": set(),
    "cancelled": {"booked", "requested"},
    "no_show": {"booked"},
}
CLINICAL_STATUSES = {"in_consultation", "completed"}


def appt_out(a: Appointment) -> dict:
    return {"id": a.id, "patient_id": a.patient_id, "patient_name": a.patient.full_name, "doctor_id": a.doctor_id,
            "doctor_name": a.doctor.user.full_name if a.doctor else None, "scheduled_at": a.scheduled_at, "reason": a.reason,
            "status": a.status, "queue_no": a.queue_no, "is_walk_in": a.is_walk_in, "location_id": a.location_id, "series_id": a.series_id,
            "started_at": a.started_at, "completed_at": a.completed_at}


def _check_doctor(db: Session, ctx: Ctx, doctor_id):
    if doctor_id is None:
        return
    m = db.get(ClinicMember, doctor_id)
    if not m or m.clinic_id != ctx.clinic.id or m.deleted_at is not None or m.role not in DOCTORS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a doctor from this clinic.")


@router.get("/appointments", response_model=list[AppointmentOut])
def list_appointments(start: datetime | None = None, end: datetime | None = None, status_: str | None = Query(None, alias="status"),
                      patient_id: uuid.UUID | None = None, doctor_id: uuid.UUID | None = None, location_id: uuid.UUID | None = None,
                      ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    stmt = select(Appointment).join(Patient, Patient.id == Appointment.patient_id).where(
        Appointment.clinic_id == ctx.clinic.id, Appointment.deleted_at.is_(None), Patient.deleted_at.is_(None))
    if start:
        stmt = stmt.where(Appointment.scheduled_at >= utc(start))
    if end:
        stmt = stmt.where(Appointment.scheduled_at < utc(end))
    if status_:
        stmt = stmt.where(Appointment.status == status_)
    if patient_id:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if doctor_id:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if location_id:
        stmt = stmt.where(Appointment.location_id == location_id)
    return [appt_out(a) for a in db.scalars(stmt.order_by(Appointment.scheduled_at).limit(500)).all()]


def _check_free(db: Session, ctx: Ctx, doctor_id, when, ignore=None):
    """One doctor can't have two live appointments at the same time."""
    if doctor_id is None:
        return
    q = select(Appointment.id).where(Appointment.clinic_id == ctx.clinic.id, Appointment.doctor_id == doctor_id, Appointment.deleted_at.is_(None),
                                     Appointment.status.notin_(("cancelled", "no_show", "completed")), Appointment.scheduled_at >= when - timedelta(minutes=1), Appointment.scheduled_at <= when + timedelta(minutes=1))
    if ignore:
        q = q.where(Appointment.id != ignore)
    if db.scalars(q).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "That time is already booked for this doctor. Pick another slot.")


def nt_doctors(db: Session, ctx: Ctx, doctor_id) -> list:
    """The assigned doctor if there is one; otherwise every doctor and the owner (anyone could take this patient)."""
    if doctor_id:
        m = db.get(ClinicMember, doctor_id)
        return [m.user_id] if m else []
    return list(db.scalars(select(ClinicMember.user_id).where(ClinicMember.clinic_id == ctx.clinic.id, ClinicMember.deleted_at.is_(None), ClinicMember.role.in_((Role.DOCTOR, Role.OWNER)))).all())


def _check_location(db: Session, ctx: Ctx, location_id):
    if location_id is None:
        return
    loc = db.get(Location, location_id)
    if not loc or loc.clinic_id != ctx.clinic.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose a location from this clinic.")


def _next_queue_no(db: Session, ctx: Ctx, when) -> int:
    day = when.replace(hour=0, minute=0, second=0, microsecond=0)
    top = db.scalar(select(func.max(Appointment.queue_no)).where(Appointment.clinic_id == ctx.clinic.id, Appointment.scheduled_at >= day, Appointment.scheduled_at < day + timedelta(days=1)))
    return (top or 0) + 1


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
def create_appointment(body: AppointmentIn, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    p = scoped(db, Patient, body.patient_id, ctx)
    _check_doctor(db, ctx, body.doctor_id)
    _check_location(db, ctx, body.location_id)
    first = utc(body.scheduled_at)
    for k in range(body.repeat_count if (body.repeat_every_days and body.repeat_count) else 1):
        _check_free(db, ctx, body.doctor_id, first + timedelta(days=k * (body.repeat_every_days or 0)))
    n = body.repeat_count if (body.repeat_every_days and body.repeat_count) else 1
    series = uuid.uuid4() if n > 1 else None
    made = []
    for i in range(n):
        a = Appointment(clinic_id=ctx.clinic.id, patient_id=p.id, doctor_id=body.doctor_id, location_id=body.location_id, reason=body.reason, series_id=series,
                        scheduled_at=first + timedelta(days=i * (body.repeat_every_days or 0)))
        db.add(a)
        made.append(a)
    db.flush()
    audit(db, ctx, "appointment.created", "appointment", made[0].id)
    nt = Notifier(db, ctx)
    nt.add("New appointment", f"{p.full_name} · {made[0].scheduled_at:%d %b %H:%M} UTC", "appointments", "/appointments", user_ids=nt.doctor_user(body.doctor_id))
    if p.user_id:
        nt.add("Appointment booked", f"{made[0].scheduled_at:%d %b %Y, %H:%M} UTC at {ctx.clinic.name}", "appointments", "/portal?tab=appointments", user_ids=[p.user_id])
    db.commit()
    changed(ctx, "appointments", "notifications")
    nt.push()
    when = ", ".join(f"{a.scheduled_at:%d %b %H:%M}" for a in made[:4]) + (" …" if n > 4 else "")
    messaging.notify_patient(ctx.clinic.id, p.id, "Appointment booked", f"Your appointment at {ctx.clinic.name} is booked for {when} (UTC).")
    return appt_out(made[0])


@router.get("/appointments/requests", response_model=list[AppointmentOut])
def requests(ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    stmt = select(Appointment).join(Patient, Patient.id == Appointment.patient_id).where(
        Appointment.clinic_id == ctx.clinic.id, Appointment.deleted_at.is_(None), Patient.deleted_at.is_(None), Appointment.status == "requested")
    if ctx.member.role == Role.DOCTOR:
        stmt = stmt.where((Appointment.doctor_id.is_(None)) | (Appointment.doctor_id == ctx.member.id))
    return [appt_out(a) for a in db.scalars(stmt.order_by(Appointment.scheduled_at).limit(200)).all()]


@router.post("/appointments/walk-in", response_model=AppointmentOut, status_code=201)
def walk_in(body: WalkInIn, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    p = scoped(db, Patient, body.patient_id, ctx)
    _check_doctor(db, ctx, body.doctor_id)
    _check_location(db, ctx, body.location_id)
    now = utcnow()
    a = Appointment(clinic_id=ctx.clinic.id, patient_id=p.id, doctor_id=body.doctor_id, location_id=body.location_id, reason=body.reason, scheduled_at=now, status="arrived",
                    is_walk_in=True, queue_no=_next_queue_no(db, ctx, now))
    db.add(a)
    db.flush()
    nt = Notifier(db, ctx).add("Walk-in patient", f"{p.full_name} is waiting (queue #{a.queue_no}).", "queue", "/queue", user_ids=nt_doctors(db, ctx, body.doctor_id))
    audit(db, ctx, "appointment.walk_in", "appointment", a.id)
    db.commit()
    changed(ctx, "appointments", "notifications")
    nt.push()
    return appt_out(a)


@router.post("/appointments/queue/call-next", response_model=AppointmentOut)
def call_next(ctx: Ctx = Depends(require_roles(Role.OWNER, Role.DOCTOR, Role.NURSE)), db: Session = Depends(get_db)):
    stmt = select(Appointment).join(Patient, Patient.id == Appointment.patient_id).where(
        Appointment.clinic_id == ctx.clinic.id, Appointment.deleted_at.is_(None), Patient.deleted_at.is_(None), Appointment.status == "arrived")
    if ctx.member.role == Role.DOCTOR:
        stmt = stmt.where((Appointment.doctor_id.is_(None)) | (Appointment.doctor_id == ctx.member.id))
    a = db.scalars(stmt.order_by(Appointment.queue_no, Appointment.scheduled_at).limit(1)).first()
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No patients are waiting.")
    a.status, a.started_at = "in_consultation", utcnow()
    if a.doctor_id is None and ctx.member.role == Role.DOCTOR:
        a.doctor_id = ctx.member.id
    audit(db, ctx, "appointment.called", "appointment", a.id)
    db.commit()
    changed(ctx, "appointments")
    return appt_out(a)


@router.patch("/appointments/{aid}", response_model=AppointmentOut)
def update_appointment(aid: uuid.UUID, body: AppointmentPatch, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    a = scoped(db, Appointment, aid, ctx)
    data = body.model_dump(exclude_unset=True)
    nt = Notifier(db, ctx)
    old_time, old_status, pu = a.scheduled_at, a.status, a.patient.user_id
    if "doctor_id" in data:
        _check_doctor(db, ctx, data["doctor_id"])
        if data["doctor_id"] != a.doctor_id and data["doctor_id"]:
            nt.add("Appointment assigned to you", f"{a.patient.full_name} · {a.scheduled_at:%d %b %H:%M} UTC", "appointments", "/appointments", user_ids=nt.doctor_user(data["doctor_id"]))
        a.doctor_id = data["doctor_id"]
    if data.get("scheduled_at"):
        if a.status in ("completed", "in_consultation"):
            raise HTTPException(status.HTTP_409_CONFLICT, "This visit has already started and can't be rescheduled.")
        a.scheduled_at = utc(data["scheduled_at"])
    if (data.get("scheduled_at") or "doctor_id" in data) and a.status in ("requested", "booked", "confirmed"):
        _check_free(db, ctx, a.doctor_id, a.scheduled_at, ignore=a.id)
    if "location_id" in data:
        _check_location(db, ctx, data["location_id"])
        a.location_id = data["location_id"]
    if "reason" in data:
        a.reason = data["reason"]
    new = data.get("status")
    if new and new != a.status:
        if new not in ALLOWED[a.status]:
            raise HTTPException(status.HTTP_409_CONFLICT, f"A {a.status.replace('_', ' ')} appointment can't be changed to {new.replace('_', ' ')}.")
        if new in CLINICAL_STATUSES and ctx.member.role not in (Role.OWNER, Role.DOCTOR, Role.NURSE):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only clinical staff can start or finish a consultation.")
        if new == "arrived" and a.queue_no is None:
            a.queue_no = _next_queue_no(db, ctx, a.scheduled_at)
            nt.add("Patient arrived", f"{a.patient.full_name} is waiting (queue #{a.queue_no}).", "queue", "/queue", user_ids=nt_doctors(db, ctx, a.doctor_id))
        if new == "in_consultation":
            a.started_at = utcnow()
        if new == "completed":
            a.completed_at = utcnow()
        a.status = new
        if pu and new in ("confirmed", "cancelled", "booked") and old_status != new:
            msg = {"confirmed": "Your appointment is confirmed", "booked": "Your appointment request was approved", "cancelled": "Your appointment was cancelled" if old_status != "requested" else "Your appointment request was declined"}[new]
            nt.add(msg, f"{a.scheduled_at:%d %b %Y, %H:%M} UTC at {ctx.clinic.name}", "appointments", "/portal?tab=appointments", user_ids=[pu])
        if new == "cancelled":
            messaging.notify_patient(ctx.clinic.id, a.patient_id, "Appointment cancelled", f"Your appointment on {a.scheduled_at:%d %b %Y, %H:%M} (UTC) at {ctx.clinic.name} was cancelled.")
    if pu and a.scheduled_at != old_time and not any(x[3] == "appointments" and pu in x[0] for x in nt.sent):
        nt.add("Your appointment was rescheduled", f"New time: {a.scheduled_at:%d %b %Y, %H:%M} UTC", "appointments", "/portal?tab=appointments", user_ids=[pu])
    audit(db, ctx, "appointment.updated", "appointment", a.id)
    db.commit()
    changed(ctx, "appointments", "notifications")
    nt.push()
    return appt_out(a)


@router.delete("/appointments/{aid}", status_code=204)
def delete_appointment(aid: uuid.UUID, ctx: Ctx = Depends(require_roles(Role.OWNER, Role.RECEPTIONIST)), db: Session = Depends(get_db)):
    a = scoped(db, Appointment, aid, ctx)
    a.deleted_at, a.deleted_by = utcnow(), ctx.user.id
    audit(db, ctx, "appointment.deleted", "appointment", a.id)
    db.commit()
    changed(ctx, "appointments", "trash")


# ---------------- consultations ----------------


def consult_out(c: Consultation) -> dict:
    return {"id": c.id, "patient_id": c.patient_id, "patient_name": c.patient.full_name, "appointment_id": c.appointment_id,
            "complaint": c.complaint, "examination": c.examination, "assessment": c.assessment, "plan": c.plan, "vitals": c.vitals or {},
            "prescription": c.prescription or [], "follow_up_on": c.follow_up_on, "ai_summary": c.ai_summary, "shared_with_patient": c.shared_with_patient, "created_at": c.created_at}


@router.get("/consultations", response_model=list[ConsultationOut])
def list_consultations(patient_id: uuid.UUID | None = None, ctx: Ctx = Depends(CLINICAL_READ), db: Session = Depends(get_db)):
    stmt = select(Consultation).join(Patient, Patient.id == Consultation.patient_id).where(
        Consultation.clinic_id == ctx.clinic.id, Consultation.deleted_at.is_(None), Patient.deleted_at.is_(None))
    if patient_id:
        stmt = stmt.where(Consultation.patient_id == patient_id)
    return [consult_out(c) for c in db.scalars(stmt.order_by(Consultation.created_at.desc()).limit(200)).all()]


@router.post("/consultations", response_model=ConsultationOut, status_code=201)
def create_consultation(body: ConsultationIn, ctx: Ctx = Depends(require_roles(*DOCTORS)), db: Session = Depends(get_db)):
    scoped(db, Patient, body.patient_id, ctx)
    if body.appointment_id:
        a = scoped(db, Appointment, body.appointment_id, ctx)
        if a.patient_id != body.patient_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That appointment belongs to a different patient.")
    c = Consultation(clinic_id=ctx.clinic.id, doctor_id=ctx.member.id, patient_id=body.patient_id, appointment_id=body.appointment_id,
                     complaint=body.complaint, examination=body.examination, assessment=body.assessment, plan=body.plan, vitals=body.vitals,
                     prescription=[i.model_dump() for i in body.prescription], follow_up_on=body.follow_up_on, shared_with_patient=body.shared_with_patient)
    db.add(c)
    db.flush()
    audit(db, ctx, "consultation.created", "consultation", c.id)
    db.commit()
    changed(ctx, "consultations")
    pat = db.get(Patient, c.patient_id)
    if c.prescription and c.shared_with_patient and pat.user_id:
        nt = Notifier(db, ctx).add("New prescription", f"From {ctx.clinic.name}", "prescriptions", "/portal?tab=prescriptions", user_ids=[pat.user_id])
        db.commit()
        nt.push()
    if c.prescription and c.shared_with_patient:
        messaging.notify_patient(ctx.clinic.id, c.patient_id, "Your prescription is ready", f"Your prescription from {ctx.clinic.name} is now available in your patient portal.")
    return consult_out(c)


@router.get("/consultations/{cid}", response_model=ConsultationOut)
def get_consultation(cid: uuid.UUID, ctx: Ctx = Depends(CLINICAL_READ), db: Session = Depends(get_db)):
    return consult_out(scoped(db, Consultation, cid, ctx))


@router.patch("/consultations/{cid}", response_model=ConsultationOut)
def update_consultation(cid: uuid.UUID, body: ConsultationPatch, ctx: Ctx = Depends(require_roles(*DOCTORS)), db: Session = Depends(get_db)):
    c = scoped(db, Consultation, cid, ctx)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "prescription" and v is not None:
            v = [dict(i) for i in v]
        if k in ("vitals", "prescription") and v is None:
            continue
        setattr(c, k, v)
    audit(db, ctx, "consultation.updated", "consultation", c.id)
    db.commit()
    changed(ctx, "consultations")
    return consult_out(c)


@router.delete("/consultations/{cid}", status_code=204)
def delete_consultation(cid: uuid.UUID, ctx: Ctx = Depends(require_roles(*DOCTORS)), db: Session = Depends(get_db)):
    c = scoped(db, Consultation, cid, ctx)
    c.deleted_at, c.deleted_by = utcnow(), ctx.user.id
    audit(db, ctx, "consultation.deleted", "consultation", c.id)
    db.commit()
    changed(ctx, "consultations", "trash")


@router.post("/consultations/{cid}/summarize", response_model=ConsultationOut)
def summarize(cid: uuid.UUID, ctx: Ctx = Depends(require_roles(*DOCTORS)), db: Session = Depends(get_db)):
    from .. import ai
    from ..util import rate_limit_user

    rate_limit_user(ctx, "ai_summary", 20, 600)
    c = scoped(db, Consultation, cid, ctx)
    c.ai_summary = ai.summarize_consultation(c)
    audit(db, ctx, "consultation.ai_summary", "consultation", c.id)
    db.commit()
    changed(ctx, "consultations")
    return consult_out(c)


@router.get("/consultations/{cid}/prescription.pdf")
def prescription_file(cid: uuid.UUID, ctx: Ctx = Depends(CLINICAL_READ), db: Session = Depends(get_db)):
    c = scoped(db, Consultation, cid, ctx)
    doc = db.get(ClinicMember, c.doctor_id) if c.doctor_id else None
    return Response(prescription_pdf(ctx.clinic.name, c.patient.full_name, doc.user.full_name if doc else None, c), media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="prescription.pdf"'})


@router.get("/patients/{pid}/timeline")
def timeline(pid: uuid.UUID, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    p = scoped(db, Patient, pid, ctx)
    items = [{"type": "appointment", "id": a.id, "at": a.scheduled_at, "title": f"Appointment ({a.status.replace('_', ' ')})", "detail": a.reason}
             for a in db.scalars(select(Appointment).where(Appointment.patient_id == p.id, Appointment.deleted_at.is_(None))).all()]
    items += [{"type": "document", "id": d.id, "at": d.created_at, "title": f"{d.category.title()} uploaded", "detail": d.filename}
              for d in db.scalars(select(Document).where(Document.patient_id == p.id, Document.deleted_at.is_(None))).all()]
    if ctx.member.role in (Role.OWNER, Role.DOCTOR, Role.NURSE) or ctx.member.can_view_clinical:
        items += [{"type": "consultation", "id": c.id, "at": c.created_at, "title": "Consultation", "detail": (c.complaint or "")[:120]}
                  for c in db.scalars(select(Consultation).where(Consultation.patient_id == p.id, Consultation.deleted_at.is_(None))).all()]
        items += [{"type": "prescription", "id": c.id, "at": c.created_at, "title": "Prescription issued", "detail": ", ".join(r.get("medicine", "") for r in c.prescription)[:120]}
                  for c in db.scalars(select(Consultation).where(Consultation.patient_id == p.id, Consultation.deleted_at.is_(None))).all() if c.prescription]
    if ctx.member.role in (Role.OWNER, Role.DOCTOR, Role.RECEPTIONIST):
        items += [{"type": "invoice", "id": i.id, "at": i.created_at, "title": f"Invoice #{i.number}", "detail": f"{i.paid}/{i.total} paid"}
                  for i in db.scalars(select(Invoice).where(Invoice.patient_id == p.id, Invoice.deleted_at.is_(None))).all()]
    return sorted(items, key=lambda x: x["at"], reverse=True)[:100]
