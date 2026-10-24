import asyncio
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

import jwt

from ..core.database import SessionLocal, get_db
from ..core.security import decode_token
from ..deps import Ctx, actor_from_payload, ctx_from_payload, require_roles
from ..models import Appointment, ChatMessage, ClinicMember, Consultation, Invoice, Notification, Patient, Payment, Role, utcnow
from ..realtime import hub, publish
from ..schemas import ChatIn
from ..util import ADMIN_ROOM, STAFF_ROLES, audit, changed, clear_chat, cleared_at, rate_limit_user, utc

router = APIRouter(tags=["workspace"])


def utc_(d):
    from datetime import timezone as _tz

    return d.replace(tzinfo=_tz.utc) if d.tzinfo is None else d.astimezone(_tz.utc)
ALL = require_roles(*Role.STAFF)

# ---------------- notifications ----------------
from ..deps import Actor, get_actor  # noqa: E402
from ..models import ChatRead  # noqa: E402
from pydantic import BaseModel as _BM  # noqa: E402


def _note(n: Notification) -> dict:
    return {"id": n.id, "title": n.title, "body": n.body, "read": n.read, "category": n.category, "link": n.link, "created_at": n.created_at}


@router.get("/notifications")
def list_notifications(actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == actor.user.id).order_by(Notification.created_at.desc()).limit(100)).all()
    unread = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == actor.user.id, Notification.read.is_(False)))
    return {"items": [_note(n) for n in rows], "unread": unread}


@router.get("/notifications/dots")
def dots(actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    """Red dots: unread notifications per feature, plus unseen team-chat messages."""
    rows = db.execute(select(Notification.category, func.count()).where(Notification.user_id == actor.user.id, Notification.read.is_(False)).group_by(Notification.category)).all()
    out = {c: n for c, n in rows}
    if actor.session.member_id:
        m = db.get(ClinicMember, actor.session.member_id)
        if m and m.role in Role.STAFF:
            seen = db.get(ChatRead, actor.user.id)
            if seen is None:
                db.add(ChatRead(user_id=actor.user.id, clinic_id=m.clinic_id, last_read_at=utcnow()))
                db.commit()
            else:
                n = db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.clinic_id == m.clinic_id, ChatMessage.sender_id != actor.user.id, ChatMessage.created_at > max([x for x in (utc(seen.last_read_at), cleared_at(db, actor.user.id, "team")) if x])))
                if n:
                    out["chat"] = n
    return out


class _Seen(_BM):
    category: str


@router.post("/notifications/seen", status_code=204)
def seen(body: _Seen, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    """The user opened that feature: its red dot goes away."""
    db.execute(update(Notification).where(Notification.user_id == actor.user.id, Notification.category == body.category[:24], Notification.read.is_(False)).values(read=True))
    if body.category == "chat" and actor.session.member_id:
        m = db.get(ClinicMember, actor.session.member_id)
        if m:
            row = db.get(ChatRead, actor.user.id)
            if row:
                row.last_read_at = utcnow()
            else:
                db.add(ChatRead(user_id=actor.user.id, clinic_id=m.clinic_id, last_read_at=utcnow()))
    db.commit()


def _mine(db: Session, actor: Actor, nid: uuid.UUID) -> Notification:
    n = db.get(Notification, nid)
    if not n or n.user_id != actor.user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found.")
    return n


@router.post("/notifications/read-all", status_code=204)
def read_all(actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id == actor.user.id, Notification.read.is_(False)).values(read=True))
    db.commit()


@router.post("/notifications/{nid}/read", status_code=204)
def read_one(nid: uuid.UUID, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    _mine(db, actor, nid).read = True
    db.commit()


@router.delete("/notifications/{nid}", status_code=204)
def delete_notification(nid: uuid.UUID, actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    db.delete(_mine(db, actor, nid))
    db.commit()


@router.delete("/notifications", status_code=204)
def clear_notifications(actor: Actor = Depends(get_actor), db: Session = Depends(get_db)):
    db.execute(delete(Notification).where(Notification.user_id == actor.user.id))
    db.commit()


# ---------------- team chat ----------------


def _msg(m: ChatMessage) -> dict:
    return {"id": m.id, "sender_id": m.sender_id, "sender_name": m.sender_name, "body": m.body, "created_at": m.created_at}


@router.get("/chat")
def chat_history(ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    q = select(ChatMessage).where(ChatMessage.clinic_id == ctx.clinic.id)
    gone = cleared_at(db, ctx.user.id, "team")
    if gone:
        q = q.where(ChatMessage.created_at > gone)                                   # only this person's view is cleared
    rows = db.scalars(q.order_by(ChatMessage.created_at.desc()).limit(100)).all()
    return [_msg(m) for m in reversed(rows)]


@router.post("/chat/clear", status_code=204)
def chat_clear(ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    clear_chat(db, ctx.user.id, ctx.clinic.id, "team")
    seen = db.get(ChatRead, ctx.user.id)
    if seen:
        seen.last_read_at = utcnow()
    audit(db, ctx, "chat.cleared_own_view", "chat", None)
    db.commit()


@router.post("/chat", status_code=201)
def chat_send(body: ChatIn, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    rate_limit_user(ctx, "chat", 60, 60)
    m = ChatMessage(clinic_id=ctx.clinic.id, sender_id=ctx.user.id, sender_name=ctx.user.full_name, body=body.body.strip())
    db.add(m)
    db.commit()
    publish(ctx.clinic.id, {"type": "chat", "message": _msg(m)}, roles=STAFF_ROLES)
    return _msg(m)


@router.delete("/chat/{mid}", status_code=204)
def chat_delete(mid: uuid.UUID, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    m = db.get(ChatMessage, mid)
    if not m or m.clinic_id != ctx.clinic.id or (m.sender_id != ctx.user.id and ctx.member.role != Role.OWNER):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found.")
    db.delete(m)
    db.commit()
    changed(ctx, "chat")


# ---------------- analytics ----------------


@router.get("/analytics/summary")
def analytics(tz_offset_minutes: int = Query(0, ge=-840, le=840), ctx: Ctx = Depends(require_roles(Role.OWNER, Role.DOCTOR)), db: Session = Depends(get_db)):
    off, now = timedelta(minutes=tz_offset_minutes), utcnow()
    local = now + off
    today0 = local.replace(hour=0, minute=0, second=0, microsecond=0) - off  # UTC instant of local midnight
    cid = ctx.clinic.id

    def appts(a, b):
        return select(Appointment).join(Patient, Patient.id == Appointment.patient_id).where(
            Appointment.clinic_id == cid, Appointment.deleted_at.is_(None), Patient.deleted_at.is_(None), Appointment.scheduled_at >= a, Appointment.scheduled_at < b)

    def revenue(a, b):
        return db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).join(Invoice, Invoice.id == Payment.invoice_id).where(
            Payment.clinic_id == cid, Invoice.deleted_at.is_(None), Payment.created_at >= a, Payment.created_at < b)) or 0

    today = db.scalars(appts(today0, today0 + timedelta(days=1))).all()
    month0 = today0 - timedelta(days=local.day - 1)
    last7 = []
    for i in range(6, -1, -1):
        a = today0 - timedelta(days=i)
        last7.append({"date": (a + off).date().isoformat(), "appointments": len(db.scalars(appts(a, a + timedelta(days=1))).all()), "revenue": revenue(a, a + timedelta(days=1))})
    window = db.scalars(appts(now - timedelta(days=30), now)).all()
    counts: dict = {}
    for a in window:
        counts[a.status] = counts.get(a.status, 0) + 1
    due = counts.get("completed", 0) + counts.get("no_show", 0)
    # ---- extended metrics ----
    inv_rows = db.scalars(select(Invoice).join(Patient, Patient.id == Invoice.patient_id).where(Invoice.clinic_id == cid, Invoice.deleted_at.is_(None), Patient.deleted_at.is_(None))).all()
    open_inv = [i for i in inv_rows if not i.refunded and i.paid < i.total]
    by_service: dict = {}
    for i in inv_rows:
        if utc_(i.created_at) >= now - timedelta(days=30) and not i.refunded:
            for it in i.items:
                by_service[it["description"]] = by_service.get(it["description"], 0) + it["qty"] * it["price"]
    done = db.scalars(select(Appointment).join(Patient, Patient.id == Appointment.patient_id).where(
        Appointment.clinic_id == cid, Appointment.deleted_at.is_(None), Patient.deleted_at.is_(None), Appointment.status == "completed")).all()
    mins = lambda a: (utc_(a.completed_at) - utc_(a.started_at)).total_seconds() / 60 if a.started_at and a.completed_at else None
    recent = [a for a in done if utc_(a.scheduled_at) >= now - timedelta(days=30)]
    durations = [m for m in (mins(a) for a in recent) if m is not None and 0 <= m < 600]
    docs: dict = {}
    for a in recent:
        d = docs.setdefault(a.doctor_id, {"visits": 0, "minutes": 0.0})
        d["visits"] += 1
        d["minutes"] += mins(a) if mins(a) is not None and 0 <= mins(a) < 600 else 0
    names = {m.id: m.user.full_name for m in db.scalars(select(ClinicMember).where(ClinicMember.clinic_id == cid))}
    first_visit: dict = {}
    for a in sorted(done, key=lambda x: utc_(x.scheduled_at)):
        first_visit.setdefault(a.patient_id, utc_(a.scheduled_at))
    seen30 = {a.patient_id for a in recent}
    new_p = sum(1 for p in seen30 if first_visit[p] >= now - timedelta(days=30))
    prior = {a.patient_id for a in done if now - timedelta(days=180) <= utc_(a.scheduled_at) < now - timedelta(days=90)}
    back = {a.patient_id for a in done if utc_(a.scheduled_at) >= now - timedelta(days=90)}
    follow = db.scalar(select(func.count()).select_from(Consultation).join(Patient, Patient.id == Consultation.patient_id).where(
        Consultation.clinic_id == cid, Consultation.deleted_at.is_(None), Patient.deleted_at.is_(None), Consultation.follow_up_on >= local.date(), Consultation.follow_up_on <= local.date() + timedelta(days=7))) or 0
    total30 = sum(counts.values())
    return {
        "today": {"appointments": len(today), "waiting": sum(a.status == "arrived" for a in today),
                  "in_consultation": sum(a.status == "in_consultation" for a in today), "completed": sum(a.status == "completed" for a in today)},
        "patients_total": db.scalar(select(func.count()).select_from(Patient).where(Patient.clinic_id == cid, Patient.deleted_at.is_(None))),
        "new_patients_30d": db.scalar(select(func.count()).select_from(Patient).where(Patient.clinic_id == cid, Patient.deleted_at.is_(None), Patient.created_at >= now - timedelta(days=30))),
        "revenue": {"today": revenue(today0, today0 + timedelta(days=1)), "month": revenue(month0, today0 + timedelta(days=1)), "last_30d": revenue(now - timedelta(days=30), now + timedelta(days=1))},
        "last7": last7, "status_counts_30d": counts, "no_show_rate_30d": round(counts.get("no_show", 0) / due, 3) if due else 0,
        "cancellation_rate_30d": round(counts.get("cancelled", 0) / total30, 3) if total30 else 0,
        "pending_invoices": {"count": len(open_inv), "due": sum(i.total - i.paid for i in open_inv)}, "follow_ups_due_7d": follow,
        "avg_consultation_minutes": round(sum(durations) / len(durations), 1) if durations else None,
        "doctor_utilization": [{"doctor": names.get(k, "Unassigned"), "visits": v["visits"], "minutes": round(v["minutes"])} for k, v in sorted(docs.items(), key=lambda x: -x[1]["visits"])],
        "revenue_by_service": [{"service": k, "amount": v} for k, v in sorted(by_service.items(), key=lambda x: -x[1])[:8]],
        "patient_mix_30d": {"new": new_p, "returning": len(seen30) - new_p},
        "retention_90d": round(len(prior & back) / len(prior), 3) if prior else None,
    }


# ---------------- websocket ----------------


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """Client sends {"token": <access token>} as its first message (keeps tokens out of URLs and logs)."""
    await ws.accept()
    try:
        first = await asyncio.wait_for(ws.receive_json(), timeout=10)
        payload = decode_token(str(first.get("token", "")), "access")

        def check():
            with SessionLocal() as db:
                if payload.get("mid") == "":  # platform admin session (no clinic)
                    a = actor_from_payload(db, payload)
                    if not a.user.is_superadmin:
                        raise PermissionError
                    return ADMIN_ROOM, a.user.id, "superadmin"
                c = ctx_from_payload(db, payload)
                return c.clinic.id, c.user.id, c.member.role

        clinic_id, user_id, role = await run_in_threadpool(check)
    except (Exception, jwt.PyJWTError):
        await ws.close(code=4401)
        return
    await ws.send_json({"type": "ready"})
    hub.add(clinic_id, user_id, role, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(clinic_id, ws)
