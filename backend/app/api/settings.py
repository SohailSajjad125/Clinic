import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .. import limits
from ..core.database import get_db
from ..deps import Ctx, require_roles
from ..models import Appointment, ClinicMember, InventoryItem, Location, MedicineTemplate, Role, Service
from ..schemas import AdjustIn, ClinicPatch, InventoryIn, InventoryPatch, LocationIn, PermissionsIn, ServiceIn, TemplateIn
from ..util import Notifier, audit, changed, scoped
from ..models import utcnow

router = APIRouter(tags=["settings"])
ALL = require_roles(*Role.STAFF)
OWNER = require_roles(Role.OWNER)
PRESCRIBERS = require_roles(Role.OWNER, Role.DOCTOR)


@router.get("/clinic")
def get_clinic(ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    c = ctx.clinic
    return {"id": c.id, "name": c.name, "clinic_type": c.clinic_type, "city": c.city, "country": c.country, "working_hours": c.working_hours or {}, "public_listing": c.public_listing, "plan": c.plan, "status": c.status,
            "limits": limits.LIMITS.get(c.plan, {}), "usage": limits.usage(db, c)}


@router.patch("/clinic")
def patch_clinic(body: ClinicPatch, ctx: Ctx = Depends(OWNER), db: Session = Depends(get_db)):
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(ctx.clinic, k, v)
    audit(db, ctx, "clinic.updated", "clinic", ctx.clinic.id)
    db.commit()
    return get_clinic(ctx, db)


def _crud(path, Model, SchemaIn, read_dep, write_dep, fields):
    out = lambda o: {"id": o.id, **{f: getattr(o, f) for f in fields}}

    @router.get(path)
    def lst(ctx: Ctx = Depends(read_dep), db: Session = Depends(get_db)):
        return [out(o) for o in db.scalars(select(Model).where(Model.clinic_id == ctx.clinic.id).order_by(fields[0] and getattr(Model, fields[0])))]

    @router.post(path, status_code=201)
    def add(body: SchemaIn, ctx: Ctx = Depends(write_dep), db: Session = Depends(get_db)):
        o = Model(clinic_id=ctx.clinic.id, **body.model_dump())
        db.add(o)
        db.commit()
        return out(o)

    @router.delete(path + "/{oid}", status_code=204)
    def rm(oid: uuid.UUID, ctx: Ctx = Depends(write_dep), db: Session = Depends(get_db)):
        o = scoped(db, Model, oid, ctx)
        if Model is Location:
            db.execute(update(Appointment).where(Appointment.location_id == o.id).values(location_id=None))
        db.delete(o)
        db.commit()


_crud("/services", Service, ServiceIn, ALL, OWNER, ["name", "price"])
_crud("/medicine-templates", MedicineTemplate, TemplateIn, PRESCRIBERS, PRESCRIBERS, ["medicine", "dose", "frequency", "duration", "instructions"])
_crud("/locations", Location, LocationIn, ALL, OWNER, ["name", "address"])


@router.patch("/staff/{member_id}/permissions")
def permissions(member_id: uuid.UUID, body: PermissionsIn, ctx: Ctx = Depends(OWNER), db: Session = Depends(get_db)):
    m = scoped(db, ClinicMember, member_id, ctx) if False else db.get(ClinicMember, member_id)
    if not m or m.clinic_id != ctx.clinic.id or m.deleted_at is not None or m.role not in (Role.RECEPTIONIST, Role.NURSE):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Team member not found.")
    m.can_view_clinical = body.can_view_clinical
    audit(db, ctx, "staff.permissions", "staff", m.id)
    db.commit()
    changed(ctx, "staff")
    return {"member_id": m.id, "can_view_clinical": m.can_view_clinical}


# ---------- inventory ----------
def inv_out(i: InventoryItem) -> dict:
    return {"id": i.id, "name": i.name, "unit": i.unit, "quantity": i.quantity, "reorder_level": i.reorder_level, "unit_price": i.unit_price, "low": i.quantity <= i.reorder_level}


@router.get("/inventory")
def inv_list(ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    return [inv_out(i) for i in db.scalars(select(InventoryItem).where(InventoryItem.clinic_id == ctx.clinic.id, InventoryItem.deleted_at.is_(None)).order_by(InventoryItem.name))]


inv_writers = require_roles(Role.OWNER, Role.DOCTOR, Role.RECEPTIONIST)


@router.post("/inventory", status_code=201)
def inv_add(body: InventoryIn, ctx: Ctx = Depends(inv_writers), db: Session = Depends(get_db)):
    i = InventoryItem(clinic_id=ctx.clinic.id, **body.model_dump())
    db.add(i)
    db.flush()
    audit(db, ctx, "inventory.created", "inventory", i.id)
    db.commit()
    changed(ctx, "inventory")
    return inv_out(i)


@router.patch("/inventory/{iid}")
def inv_patch(iid: uuid.UUID, body: InventoryPatch, ctx: Ctx = Depends(inv_writers), db: Session = Depends(get_db)):
    i = scoped(db, InventoryItem, iid, ctx)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(i, k, v)
    db.commit()
    changed(ctx, "inventory")
    return inv_out(i)


@router.post("/inventory/{iid}/adjust")
def inv_adjust(iid: uuid.UUID, body: AdjustIn, ctx: Ctx = Depends(inv_writers), db: Session = Depends(get_db)):
    i = scoped(db, InventoryItem, iid, ctx)
    if i.quantity + body.delta < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Only {i.quantity} {i.unit} in stock.")
    was_low = i.quantity <= i.reorder_level
    i.quantity += body.delta
    audit(db, ctx, f"inventory.adjust:{body.delta:+d}", "inventory", i.id)
    nt = Notifier(db, ctx)
    if i.quantity <= i.reorder_level and not was_low:
        nt.add("Low stock", f"{i.name}: {i.quantity} {i.unit} left (reorder at {i.reorder_level}).", "inventory", "/inventory", roles=(Role.OWNER,))
    db.commit()
    changed(ctx, "inventory", "notifications")
    nt.push()
    return inv_out(i)


@router.delete("/inventory/{iid}", status_code=204)
def inv_delete(iid: uuid.UUID, ctx: Ctx = Depends(inv_writers), db: Session = Depends(get_db)):
    i = scoped(db, InventoryItem, iid, ctx)
    i.deleted_at, i.deleted_by = utcnow(), ctx.user.id
    audit(db, ctx, "inventory.deleted", "inventory", i.id)
    db.commit()
    changed(ctx, "inventory", "trash")
