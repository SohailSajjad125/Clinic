import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..deps import Ctx, require_roles
from ..models import Invoice, Patient, Payment, Role, utcnow
from ..schemas import InvoiceIn, InvoiceOut, PaymentIn
from .. import messaging
from ..pdf import receipt_pdf
from ..util import Notifier, audit, changed, scoped

router = APIRouter(prefix="/invoices", tags=["billing"])
READ = require_roles(Role.OWNER, Role.RECEPTIONIST, Role.DOCTOR)
WRITE = require_roles(Role.OWNER, Role.RECEPTIONIST)


def inv_status(i: Invoice) -> str:
    if i.refunded:
        return "refunded"
    if i.paid >= i.total:
        return "paid"
    return "partial" if i.paid > 0 else "pending"


def inv_out(i: Invoice) -> dict:
    return {"id": i.id, "number": i.number, "patient_id": i.patient_id, "patient_name": i.patient.full_name, "items": i.items,
            "discount": i.discount, "tax": i.tax, "total": i.total, "paid": i.paid, "status": inv_status(i), "created_at": i.created_at}


@router.get("", response_model=list[InvoiceOut])
def list_invoices(patient_id: uuid.UUID | None = None, ctx: Ctx = Depends(READ), db: Session = Depends(get_db)):
    stmt = select(Invoice).join(Patient, Patient.id == Invoice.patient_id).where(
        Invoice.clinic_id == ctx.clinic.id, Invoice.deleted_at.is_(None), Patient.deleted_at.is_(None))
    if patient_id:
        stmt = stmt.where(Invoice.patient_id == patient_id)
    return [inv_out(i) for i in db.scalars(stmt.order_by(Invoice.number.desc()).limit(300)).all()]


@router.post("", response_model=InvoiceOut, status_code=201)
def create_invoice(body: InvoiceIn, ctx: Ctx = Depends(WRITE), db: Session = Depends(get_db)):
    scoped(db, Patient, body.patient_id, ctx)
    subtotal = sum(i.qty * i.price for i in body.items)
    if body.discount > subtotal:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The discount can't be more than the invoice subtotal.")
    for _ in range(3):  # retry if two invoices race for the same number
        nxt = (db.scalar(select(func.max(Invoice.number)).where(Invoice.clinic_id == ctx.clinic.id)) or 0) + 1
        inv = Invoice(clinic_id=ctx.clinic.id, patient_id=body.patient_id, number=nxt, items=[i.model_dump() for i in body.items],
                      discount=body.discount, tax=body.tax, total=subtotal - body.discount + body.tax)
        db.add(inv)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(status.HTTP_409_CONFLICT, "Could not allocate an invoice number. Try again.")
    audit(db, ctx, "invoice.created", "invoice", inv.id)
    pat = db.get(Patient, inv.patient_id)
    nt = Notifier(db, ctx)
    if pat.user_id:
        nt.add("New invoice", f"Invoice #{inv.number} · PKR {inv.total}", "invoices", "/portal?tab=invoices", user_ids=[pat.user_id])
    db.commit()
    changed(ctx, "invoices", "notifications")
    nt.push()
    return inv_out(inv)


@router.post("/{iid}/payments", response_model=InvoiceOut)
def add_payment(iid: uuid.UUID, body: PaymentIn, ctx: Ctx = Depends(WRITE), db: Session = Depends(get_db)):
    inv = scoped(db, Invoice, iid, ctx)
    if inv.refunded:
        raise HTTPException(status.HTTP_409_CONFLICT, "This invoice was refunded.")
    if body.amount > inv.total - inv.paid:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"The amount is more than the balance due ({inv.total - inv.paid}).")
    db.add(Payment(clinic_id=ctx.clinic.id, invoice_id=inv.id, amount=body.amount, method=body.method))
    inv.paid += body.amount
    nt = Notifier(db, ctx)
    if inv.paid == inv.total:
        nt.add(f"Invoice #{inv.number} paid", f"{inv.patient.full_name} paid in full.", "billing", "/billing", roles=(Role.OWNER,))
    if inv.patient.user_id:
        nt.add("Payment received", f"PKR {body.amount} for invoice #{inv.number}", "invoices", "/portal?tab=invoices", user_ids=[inv.patient.user_id])
    audit(db, ctx, "invoice.payment", "invoice", inv.id)
    db.commit()
    changed(ctx, "invoices", "notifications")
    nt.push()
    messaging.notify_patient(ctx.clinic.id, inv.patient_id, "Payment receipt", f"We received PKR {body.amount} for invoice #{inv.number} at {ctx.clinic.name}. Balance: PKR {inv.total - inv.paid}.")
    return inv_out(inv)


@router.post("/{iid}/refund", response_model=InvoiceOut)
def refund(iid: uuid.UUID, ctx: Ctx = Depends(WRITE), db: Session = Depends(get_db)):
    inv = scoped(db, Invoice, iid, ctx)
    if inv.refunded or inv.paid <= 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "There is nothing to refund on this invoice.")
    db.add(Payment(clinic_id=ctx.clinic.id, invoice_id=inv.id, amount=-inv.paid))
    inv.paid, inv.refunded = 0, True
    audit(db, ctx, "invoice.refunded", "invoice", inv.id)
    db.commit()
    changed(ctx, "invoices")
    return inv_out(inv)


@router.delete("/{iid}", status_code=204)
def delete_invoice(iid: uuid.UUID, ctx: Ctx = Depends(WRITE), db: Session = Depends(get_db)):
    inv = scoped(db, Invoice, iid, ctx)
    inv.deleted_at, inv.deleted_by = utcnow(), ctx.user.id
    audit(db, ctx, "invoice.deleted", "invoice", inv.id)
    db.commit()
    changed(ctx, "invoices", "trash")


@router.get("/{iid}/receipt.pdf")
def receipt(iid: uuid.UUID, ctx: Ctx = Depends(READ), db: Session = Depends(get_db)):
    inv = scoped(db, Invoice, iid, ctx)
    return Response(receipt_pdf(ctx.clinic.name, inv, inv_status(inv)), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="invoice-{inv.number}.pdf"'})
