import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import hash_password
from ..deps import Ctx, get_ctx, require_roles
from sqlalchemy import update

from .. import limits
from ..models import DoctorProfile, Appointment, AuditLog, ClinicMember, Consultation, Role, User
from ..util import changed
from ..schemas import StaffCreateIn, StaffOut

router = APIRouter(prefix="/staff", tags=["staff"])
trash = APIRouter(prefix="/trash/staff", tags=["trash"])
owner_only = require_roles(Role.OWNER)


def _out(m: ClinicMember) -> dict:
    from sqlalchemy.orm import object_session
    from .doctors import profile_dict

    return {"profile": profile_dict(object_session(m), m) if m.role in (Role.DOCTOR, Role.OWNER) else None, "can_view_clinical": m.can_view_clinical, 
        "member_id": m.id, "user_id": m.user_id, "email": m.user.email, "full_name": m.user.full_name,
        "role": m.role, "created_at": m.created_at, "deleted_at": m.deleted_at,
    }


def _audit(db: Session, ctx: Ctx, action: str, member_id: uuid.UUID):
    db.add(AuditLog(clinic_id=ctx.clinic.id, actor_id=ctx.user.id, action=action, entity_type="staff", entity_id=member_id))


def _member(db: Session, ctx: Ctx, member_id: uuid.UUID) -> ClinicMember:
    m = db.scalar(select(ClinicMember).where(ClinicMember.id == member_id, ClinicMember.clinic_id == ctx.clinic.id))
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found.")
    return m


@router.get("", response_model=list[StaffOut])
def list_staff(ctx: Ctx = Depends(require_roles(*Role.STAFF)), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ClinicMember).where(
            ClinicMember.clinic_id == ctx.clinic.id, ClinicMember.deleted_at.is_(None), ClinicMember.role.in_(Role.STAFF)
        ).order_by(ClinicMember.created_at)
    ).all()
    return [_out(m) for m in rows]


@router.post("", response_model=StaffOut, status_code=201)
def add_staff(body: StaffCreateIn, ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    limits.check_staff_quota(db, ctx, body.role)
    email = body.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user:
        existing = db.scalar(select(ClinicMember).where(ClinicMember.user_id == user.id, ClinicMember.clinic_id == ctx.clinic.id))
        if existing:
            msg = "This person is in your deleted history. Restore them from there." if existing.deleted_at else "This person is already on your team."
            raise HTTPException(status.HTTP_409_CONFLICT, msg)
    else:
        user = User(email=email, full_name=body.full_name, password_hash=hash_password(body.password), must_change_password=True)
        db.add(user)
        db.flush()
    member = ClinicMember(user_id=user.id, clinic_id=ctx.clinic.id, role=body.role)
    db.add(member)
    db.flush()
    if body.role == Role.DOCTOR:
        db.add(DoctorProfile(member_id=member.id, **(body.profile.model_dump() if body.profile else {})))
    _audit(db, ctx, "staff.added", member.id)
    db.commit()
    changed(ctx, "staff")
    return _out(member)


@router.delete("/{member_id}", status_code=204)
def delete_staff(member_id: uuid.UUID, ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    m = _member(db, ctx, member_id)
    if m.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found.")
    if m.id == ctx.member.id or m.role == Role.OWNER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The clinic owner can't be removed.")
    m.deleted_at, m.deleted_by = datetime.now(timezone.utc), ctx.user.id
    _audit(db, ctx, "staff.deleted", m.id)
    db.commit()
    changed(ctx, "staff", "trash")


@trash.get("", response_model=list[StaffOut])
def list_deleted(ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(ClinicMember).where(ClinicMember.clinic_id == ctx.clinic.id, ClinicMember.deleted_at.is_not(None))
        .order_by(ClinicMember.deleted_at.desc())
    ).all()
    return [_out(m) for m in rows]


@trash.post("/{member_id}/restore", response_model=StaffOut)
def restore(member_id: uuid.UUID, ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    m = _member(db, ctx, member_id)
    if m.deleted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This staff member isn't in deleted history.")
    m.deleted_at = m.deleted_by = None
    _audit(db, ctx, "staff.restored", m.id)
    db.commit()
    changed(ctx, "staff", "trash")
    return _out(m)


@trash.delete("/{member_id}", status_code=204)
def purge(member_id: uuid.UUID, ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    """Permanent delete: removes the database row(s). Only items already in deleted history qualify."""
    m = _member(db, ctx, member_id)
    if m.deleted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Delete this staff member first, then remove them permanently from history.")
    user_id, mid = m.user_id, m.id
    for model in (Appointment, Consultation):  # keep clinical records, drop the link to the removed doctor
        db.execute(update(model).where(model.doctor_id == mid).values(doctor_id=None))
    db.delete(m)
    db.flush()
    remaining = db.scalar(select(func.count()).select_from(ClinicMember).where(ClinicMember.user_id == user_id))
    user = db.get(User, user_id)
    if user and remaining == 0 and not user.is_superadmin:
        db.delete(user)
    _audit(db, ctx, "staff.purged", mid)  # id only; no personal data retained
    db.commit()
    changed(ctx, "trash")
