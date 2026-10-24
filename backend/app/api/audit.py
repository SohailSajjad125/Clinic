from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..deps import Ctx, require_roles
from ..models import AuditLog, ClinicMember, Role, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def audit_log(limit: int = Query(150, le=500), entity: str | None = Query(None, max_length=40), role: str | None = Query(None, max_length=20), q: str | None = Query(None, max_length=60),
              ctx: Ctx = Depends(require_roles(Role.OWNER)), db: Session = Depends(get_db)):
    """Everything that happened in THIS clinic, by anyone who works in it or is its patient. Other clinics never appear."""
    stmt = (select(AuditLog, ClinicMember.role).outerjoin(ClinicMember, and_(ClinicMember.user_id == AuditLog.actor_id, ClinicMember.clinic_id == AuditLog.clinic_id))
            .where(AuditLog.clinic_id == ctx.clinic.id).order_by(AuditLog.created_at.desc()).limit(limit))
    if entity:
        stmt = stmt.where(AuditLog.entity_type == entity)
    if role:
        stmt = stmt.where(ClinicMember.role == role)
    if q:
        stmt = stmt.where(AuditLog.action.icontains(q.strip(), autoescape=True))
    rows = db.execute(stmt).all()
    ids = {r.actor_id for r, _ in rows if r.actor_id}
    names = {u.id: u.full_name for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    return [{"id": r.id, "action": r.action, "entity": r.entity_type, "entity_id": r.entity_id, "actor": names.get(r.actor_id, "Removed user" if r.actor_id else "System"),
             "actor_role": role_ or ("removed" if r.actor_id else "system"), "at": r.created_at} for r, role_ in rows]
