import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .deps import Ctx
from .models import AuditLog, ClinicMember, Notification
import time
from collections import defaultdict, deque

from .realtime import publish

STAFF_ROLES = ("owner", "doctor", "receptionist", "nurse")
_hits: dict = defaultdict(deque)  # in-process limiter; use Redis when running several servers


def rate_limit(request, bucket: str, limit: int, window: int = 600) -> None:
    ip = request.client.host if request.client else "unknown"
    now, q = time.monotonic(), _hits[(bucket, ip)]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests. Please try again in a few minutes.")
    q.append(now)


def utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def changed(ctx: Ctx, *entities: str):
    """Tell every connected client of this clinic to refresh these lists."""
    for e in entities:
        publish(ctx.clinic.id, {"type": "data", "entity": e}, roles=STAFF_ROLES)


def audit(db: Session, ctx: Ctx, action: str, entity: str, entity_id: uuid.UUID | None):
    db.add(AuditLog(clinic_id=ctx.clinic.id, actor_id=ctx.user.id, action=action, entity_type=entity, entity_id=entity_id))


def scoped(db: Session, model, obj_id: uuid.UUID, ctx: Ctx, include_deleted: bool = False):
    obj = db.get(model, obj_id)
    if not obj or obj.clinic_id != ctx.clinic.id or (not include_deleted and getattr(obj, "deleted_at", None) is not None):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    return obj


ADMIN_ROOM = uuid.UUID(int=0)


class Notifier:
    """Collects who should hear about an event, writes their notification rows, and after the commit pushes them live.
    Only people the event is relevant to are notified; everyone else just gets a silent list refresh (via changed())."""

    def __init__(self, db: Session, ctx: Ctx | None, clinic_id=None):
        self.db, self.ctx, self.clinic_id = db, ctx, clinic_id or (ctx.clinic.id if ctx else None)
        self.sent: list = []

    def add(self, title: str, body: str = "", category: str = "general", link: str | None = None, roles: tuple = (), user_ids=()):
        ids = set(user_ids)
        if roles:
            q = select(ClinicMember.user_id).where(ClinicMember.clinic_id == self.clinic_id, ClinicMember.deleted_at.is_(None), ClinicMember.role.in_(roles))
            ids |= set(self.db.scalars(q).all())
        if self.ctx:
            ids.discard(self.ctx.user.id)  # never notify people about their own actions
        for uid in ids:
            self.db.add(Notification(clinic_id=self.clinic_id, user_id=uid, title=title, body=body, category=category, link=link))
        if ids:
            self.sent.append((list(ids), title, body, category, link))
        return self

    def doctor_user(self, member_id):
        m = self.db.get(ClinicMember, member_id) if member_id else None
        return [m.user_id] if m and m.deleted_at is None else []

    def push(self):
        for ids, title, body, category, link in self.sent:
            publish(self.clinic_id, {"type": "notification", "title": title, "body": body, "category": category, "link": link}, user_ids=ids)


def notify_admins(db: Session, title: str, body: str = "", category: str = "admin_support", link: str | None = None):
    from .models import User

    ids = db.scalars(select(User.id).where(User.is_superadmin.is_(True), User.is_active.is_(True))).all()
    for uid in ids:
        db.add(Notification(clinic_id=None, user_id=uid, title=title, body=body, category=category, link=link))
    return lambda: publish(ADMIN_ROOM, {"type": "notification", "title": title, "body": body, "category": category, "link": link}, user_ids=ids)


def rate_limit_user(ctx, bucket: str, limit: int, window: int = 600) -> None:
    """Per signed-in user (not per IP), for expensive or abusable actions."""
    now, q = time.monotonic(), _hits[(bucket, str(ctx.user.id))]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "You're doing that too often. Please wait a moment.")
    q.append(now)


def cleared_at(db: Session, user_id, scope: str):
    from .models import ChatClear

    row = db.scalar(select(ChatClear).where(ChatClear.user_id == user_id, ChatClear.scope == scope))
    return utc(row.cleared_at) if row else None


def cleared_map(db: Session, user_id, prefix: str) -> dict:
    from .models import ChatClear

    return {r.scope.split(":", 1)[1]: utc(r.cleared_at) for r in db.scalars(select(ChatClear).where(ChatClear.user_id == user_id, ChatClear.scope.like(prefix + ":%")))}


def clear_chat(db: Session, user_id, clinic_id, scope: str):
    from .models import ChatClear, utcnow

    row = db.scalar(select(ChatClear).where(ChatClear.user_id == user_id, ChatClear.scope == scope)) or ChatClear(user_id=user_id, clinic_id=clinic_id, scope=scope)
    row.cleared_at = utcnow()
    db.add(row)
