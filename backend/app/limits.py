from fastapi import HTTPException, status
from sqlalchemy import func, select

from .models import ClinicMember, Patient, Role

LIMITS = {"starter": {"patients": 200, "staff": 2}, "clinic": {"doctors": 5}, "group": {}, "enterprise": {}}


def usage(db, clinic) -> dict:
    cid = clinic.id
    active = (ClinicMember.clinic_id == cid, ClinicMember.deleted_at.is_(None))
    return {
        "patients": db.scalar(select(func.count()).select_from(Patient).where(Patient.clinic_id == cid, Patient.deleted_at.is_(None))),
        "staff": db.scalar(select(func.count()).select_from(ClinicMember).where(*active, ClinicMember.role.in_(Role.INVITABLE))),
        "doctors": db.scalar(select(func.count()).select_from(ClinicMember).where(*active, ClinicMember.role == Role.DOCTOR)),
    }


def _deny(what, lim, plan):
    raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, f"Your {plan} plan allows up to {lim} {what}. Contact us to upgrade.")


def check_patient_quota(db, ctx):
    lim = LIMITS.get(ctx.clinic.plan, {}).get("patients")
    if lim and usage(db, ctx.clinic)["patients"] >= lim:
        _deny("patients", lim, ctx.clinic.plan)


def check_staff_quota(db, ctx, role):
    lims, u = LIMITS.get(ctx.clinic.plan, {}), usage(db, ctx.clinic)
    if lims.get("staff") and u["staff"] >= lims["staff"]:
        _deny("team members", lims["staff"], ctx.clinic.plan)
    if lims.get("doctors") and role == Role.DOCTOR and u["doctors"] >= lims["doctors"]:
        _deny("doctors", lims["doctors"], ctx.clinic.plan)
