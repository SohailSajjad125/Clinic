"""Doctor profiles, availability (time slots) and the doctor's own dashboard data."""
import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..deps import Ctx, require_roles
from ..models import Appointment, ClinicMember, Consultation, DoctorProfile, Patient, Role, utcnow
from ..schemas import DoctorProfileIn
from ..util import audit, changed, utc

router = APIRouter(tags=["doctors"])
ALL = require_roles(*Role.STAFF)
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_PROFILE = DoctorProfileIn().model_dump()
PRACTISING = (Role.DOCTOR, Role.OWNER)


def profile_dict(db: Session, m: ClinicMember) -> dict:
    prof = db.get(DoctorProfile, m.id)
    keys = list(DEFAULT_PROFILE)
    return {k: (getattr(prof, k) if getattr(prof, k) is not None else DEFAULT_PROFILE[k]) for k in keys} if prof else dict(DEFAULT_PROFILE)


def doctor_card(db: Session, m: ClinicMember) -> dict:
    return {"member_id": m.id, "full_name": m.user.full_name, "role": m.role, "profile": profile_dict(db, m)}


def active_doctors(db: Session, clinic_id, include_owner_without_profile=False) -> list:
    rows = db.scalars(select(ClinicMember).where(ClinicMember.clinic_id == clinic_id, ClinicMember.deleted_at.is_(None), ClinicMember.role.in_(PRACTISING)).order_by(ClinicMember.created_at)).all()
    return [m for m in rows if m.role == Role.DOCTOR or db.get(DoctorProfile, m.id) is not None or include_owner_without_profile]


def compute_slots(db: Session, clinic, member: ClinicMember | None, day: date, tz_offset: int) -> list:
    prof = db.get(DoctorProfile, member.id) if member else None
    key = DAYS[day.weekday()]
    if prof:
        days, start, end, step = prof.available_days or [], prof.start_time, prof.end_time, prof.slot_minutes
    else:
        hours = (clinic.working_hours or {}).get(key, "unset")
        days = DAYS[:6] if hours == "unset" else ([key] if hours else [])
        start, end, step = (hours["open"], hours["close"], 20) if isinstance(hours, dict) else ("09:00", "17:00", 20)
    if key not in days:
        return []
    off = timedelta(minutes=tz_offset)
    h, mi = map(int, start.split(":")); eh, em = map(int, end.split(":"))
    cur = datetime(day.year, day.month, day.day, h, mi) - off
    stop = datetime(day.year, day.month, day.day, eh, em) - off
    cur, stop = cur.replace(tzinfo=timezone.utc), stop.replace(tzinfo=timezone.utc)
    day0 = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) - off
    q = select(Appointment.scheduled_at).where(Appointment.clinic_id == clinic.id, Appointment.deleted_at.is_(None), Appointment.status.notin_(("cancelled", "no_show")),
                                               Appointment.scheduled_at >= day0, Appointment.scheduled_at < day0 + timedelta(days=1))
    if member:
        q = q.where(Appointment.doctor_id == member.id)
    booked = [utc(x) for x in db.scalars(q).all()] if member else []
    now, out = utcnow(), []
    while cur + timedelta(minutes=step) <= stop:
        taken = any(cur <= b < cur + timedelta(minutes=step) for b in booked)
        out.append({"time": (cur + off).strftime("%H:%M"), "start": cur.isoformat(), "taken": taken, "past": cur <= now})
        cur += timedelta(minutes=step)
    return out


def _member(db: Session, ctx: Ctx, doctor_id):
    m = db.get(ClinicMember, doctor_id) if doctor_id else None
    if doctor_id and (not m or m.clinic_id != ctx.clinic.id or m.deleted_at is not None or m.role not in PRACTISING):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found.")
    return m


@router.get("/doctors")
def list_doctors(ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    return [doctor_card(db, m) for m in active_doctors(db, ctx.clinic.id)]


def _upsert(db: Session, m: ClinicMember, body: DoctorProfileIn):
    prof = db.get(DoctorProfile, m.id) or DoctorProfile(member_id=m.id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(prof, k, v)
    db.add(prof)
    if prof.end_time <= prof.start_time:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Finishing time must be after the starting time.")


@router.patch("/staff/{member_id}/profile")
def edit_profile(member_id: uuid.UUID, body: DoctorProfileIn, ctx: Ctx = Depends(require_roles(Role.OWNER)), db: Session = Depends(get_db)):
    m = _member(db, ctx, member_id)
    _upsert(db, m, body)
    audit(db, ctx, "doctor.profile_updated", "staff", m.id)
    db.commit()
    changed(ctx, "staff", "doctors")
    return doctor_card(db, m)


@router.patch("/me/profile")
def edit_my_profile(body: DoctorProfileIn, ctx: Ctx = Depends(require_roles(*PRACTISING)), db: Session = Depends(get_db)):
    _upsert(db, ctx.member, body)
    db.commit()
    changed(ctx, "staff", "doctors")
    return doctor_card(db, ctx.member)


@router.get("/me/profile")
def my_profile(ctx: Ctx = Depends(require_roles(*PRACTISING)), db: Session = Depends(get_db)):
    return doctor_card(db, ctx.member)


@router.get("/slots")
def slots(date_: date = Query(alias="date"), doctor_id: uuid.UUID | None = None, tz_offset_minutes: int = Query(0, ge=-840, le=840), ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    return compute_slots(db, ctx.clinic, _member(db, ctx, doctor_id), date_, tz_offset_minutes)


@router.get("/doctor/summary")
def doctor_summary(tz_offset_minutes: int = Query(0, ge=-840, le=840), ctx: Ctx = Depends(require_roles(Role.DOCTOR, Role.OWNER)), db: Session = Depends(get_db)):
    me, cid, now = ctx.member, ctx.clinic.id, utcnow()
    off = timedelta(minutes=tz_offset_minutes)
    today0 = (now + off).replace(hour=0, minute=0, second=0, microsecond=0) - off
    base = select(Appointment).join(Patient, Patient.id == Appointment.patient_id).where(Appointment.clinic_id == cid, Appointment.deleted_at.is_(None), Patient.deleted_at.is_(None))
    mine = lambda lo, hi: base.where(Appointment.doctor_id == me.id, Appointment.scheduled_at >= lo, Appointment.scheduled_at < hi)
    today = db.scalars(mine(today0, today0 + timedelta(days=1)).order_by(Appointment.scheduled_at)).all()
    waiting = db.scalars(base.where(Appointment.status == "arrived", (Appointment.doctor_id == me.id) | Appointment.doctor_id.is_(None))).all()
    last7 = []
    for i in range(6, -1, -1):
        a = today0 - timedelta(days=i)
        last7.append({"date": (a + off).date().isoformat(), "visits": len([x for x in db.scalars(mine(a, a + timedelta(days=1))).all() if x.status == "completed"])})
    done = db.scalars(base.where(Appointment.doctor_id == me.id, Appointment.status == "completed", Appointment.scheduled_at >= now - timedelta(days=30))).all()
    mins = [(utc(x.completed_at) - utc(x.started_at)).total_seconds() / 60 for x in done if x.started_at and x.completed_at]
    mins = [m for m in mins if 0 <= m < 600]
    today_local = (now + off).date()
    follow = db.scalar(select(func.count()).select_from(Consultation).join(Patient, Patient.id == Consultation.patient_id).where(
        Consultation.clinic_id == cid, Consultation.deleted_at.is_(None), Patient.deleted_at.is_(None), Consultation.doctor_id == me.id,
        Consultation.follow_up_on >= today_local, Consultation.follow_up_on <= today_local + timedelta(days=7))) or 0
    upcoming = [x for x in today if x.status in ("requested", "booked", "confirmed") and utc(x.scheduled_at) >= now][:6]
    requests = db.scalar(select(func.count()).select_from(Appointment).where(Appointment.clinic_id == cid, Appointment.deleted_at.is_(None), Appointment.status == "requested", Appointment.doctor_id == me.id)) or 0
    return {"today": {"mine": len(today), "waiting": len(waiting), "in_consultation": sum(x.status == "in_consultation" for x in today), "completed": sum(x.status == "completed" for x in today)},
            "last7": last7, "avg_consultation_minutes": round(sum(mins) / len(mins), 1) if mins else None, "patients_seen_30d": len({x.patient_id for x in done}),
            "follow_ups_due_7d": follow, "requests_for_me": requests,
            "upcoming": [{"id": x.id, "patient_id": x.patient_id, "patient_name": x.patient.full_name, "scheduled_at": x.scheduled_at, "reason": x.reason, "status": x.status} for x in upcoming]}
