import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..deps import Ctx, require_roles
from ..core import storage
from ..models import Appointment, Consultation, Document, InventoryItem, Invoice, OutboundMessage, Patient, Payment, PortalMessage, Role
from ..util import audit, changed, scoped

router = APIRouter(prefix="/trash", tags=["trash"])
Kind = Literal["patients", "appointments", "consultations", "invoices", "documents", "inventory"]
MODELS = {"patients": Patient, "appointments": Appointment, "consultations": Consultation, "invoices": Invoice, "documents": Document, "inventory": InventoryItem}
owner_only = require_roles(Role.OWNER)


def label(kind: str, o) -> str:
    if kind == "patients":
        return o.full_name
    if kind == "inventory":
        return f"{o.name} · {o.quantity} {o.unit}"
    who = o.patient.full_name
    if kind == "documents":
        return f"{o.filename} · {who}"
    if kind == "appointments":
        return f"{who} · appointment {o.scheduled_at:%d %b %Y, %H:%M}"
    if kind == "consultations":
        return f"{who} · consultation {o.created_at:%d %b %Y}"
    return f"Invoice #{o.number} · {who}"


@router.get("/{kind}")
def list_deleted(kind: Kind, ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    M = MODELS[kind]
    rows = db.scalars(select(M).where(M.clinic_id == ctx.clinic.id, M.deleted_at.is_not(None)).order_by(M.deleted_at.desc())).all()
    return [{"id": o.id, "kind": kind, "label": label(kind, o), "deleted_at": o.deleted_at} for o in rows]


@router.post("/{kind}/{oid}/restore", status_code=204)
def restore(kind: Kind, oid: uuid.UUID, ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    o = scoped(db, MODELS[kind], oid, ctx, include_deleted=True)
    if o.deleted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This item isn't in deleted history.")
    if kind not in ("patients", "inventory") and o.patient.deleted_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Restore the patient first.")
    o.deleted_at = o.deleted_by = None
    audit(db, ctx, f"{kind}.restored", kind, o.id)
    db.commit()
    changed(ctx, kind, "trash")


@router.delete("/{kind}/{oid}", status_code=204)
def purge(kind: Kind, oid: uuid.UUID, ctx: Ctx = Depends(owner_only), db: Session = Depends(get_db)):
    """Permanent delete. Removes the row (and, for a patient, everything that belongs to them)."""
    o = scoped(db, MODELS[kind], oid, ctx, include_deleted=True)
    if o.deleted_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Delete this item first, then remove it permanently from history.")
    if kind == "patients":
        inv_ids = select(Invoice.id).where(Invoice.patient_id == o.id)
        db.execute(delete(Payment).where(Payment.invoice_id.in_(inv_ids)))
        for d in db.scalars(select(Document).where(Document.patient_id == o.id)).all():
            storage.delete(d.storage_key)
        for M in (Invoice, Consultation, Appointment, Document, PortalMessage):
            db.execute(delete(M).where(M.patient_id == o.id))
        db.execute(delete(OutboundMessage).where(OutboundMessage.patient_id == o.id))
        if o.user_id:
            from .portal import drop_portal_user

            drop_portal_user(db, o.user_id)
    elif kind == "appointments":
        db.execute(update(Consultation).where(Consultation.appointment_id == o.id).values(appointment_id=None))
    elif kind == "documents":
        storage.delete(o.storage_key)
    elif kind == "invoices":
        db.execute(delete(Payment).where(Payment.invoice_id == o.id))
    oid_ = o.id
    db.delete(o)
    audit(db, ctx, f"{kind}.purged", kind, oid_)  # id only
    db.commit()
    changed(ctx, kind, "trash")
