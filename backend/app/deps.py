import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session as DBSession

from .core.database import get_db
from .core.security import decode_token
from .models import Clinic, ClinicMember, Session, User

bearer = HTTPBearer(auto_error=False)


@dataclass
class Ctx:
    user: User
    member: ClinicMember
    clinic: Clinic
    session: Session


@dataclass
class Actor:
    user: User
    session: Session


def _unauth(msg="Your session is invalid or has expired. Sign in again."):
    return HTTPException(status.HTTP_401_UNAUTHORIZED, msg, headers={"WWW-Authenticate": "Bearer"})


def actor_from_payload(db: DBSession, payload: dict) -> Actor:
    """The session is re-checked in the database on every request, so logging out or revoking a device takes effect at once."""
    try:
        sess = db.get(Session, uuid.UUID(payload["sid"]))
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise _unauth()
    if not sess or sess.revoked_at is not None or sess.user_id != user_id:
        raise _unauth()
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise _unauth()
    return Actor(user, sess)


def member_from_payload(db: DBSession, payload: dict) -> Ctx:
    actor = actor_from_payload(db, payload)
    try:
        member = db.get(ClinicMember, uuid.UUID(payload["mid"]))
    except (KeyError, ValueError):
        raise _unauth()
    if not member or member.user_id != actor.user.id or member.deleted_at is not None or actor.session.member_id != member.id:
        raise _unauth()
    if member.clinic.deleted_at is not None:
        raise _unauth()
    if member.clinic.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This clinic's account is suspended. Please contact support.")
    return Ctx(user=actor.user, member=member, clinic=member.clinic, session=actor.session)


def ctx_from_payload(db: DBSession, payload: dict) -> Ctx:
    ctx = member_from_payload(db, payload)
    if ctx.user.must_change_password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You must change your temporary password before continuing.")
    return ctx


def _payload(creds):
    if creds is None:
        raise _unauth("Sign in to continue.")
    try:
        return decode_token(creds.credentials, "access")
    except jwt.PyJWTError:
        raise _unauth()


def get_ctx(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: DBSession = Depends(get_db)) -> Ctx:
    return ctx_from_payload(db, _payload(creds))


def get_actor(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: DBSession = Depends(get_db)) -> Actor:
    return actor_from_payload(db, _payload(creds))


def get_admin(actor: Actor = Depends(get_actor)) -> Actor:
    if not actor.user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform administrators only.")
    return actor


def require_roles(*roles: str):
    def dep(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        if ctx.member.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have permission to do this.")
        return ctx

    return dep
