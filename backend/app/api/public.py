"""Public (unauthenticated) endpoints used by the marketing website."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import Clinic, ContactMessage, NewsletterSubscriber
from ..schemas import ContactIn, NewsletterIn
from ..util import _hits, notify_admins, rate_limit  # noqa: F401

router = APIRouter(prefix="/public", tags=["public"])


def _limit(request, bucket, limit, window=600):
    rate_limit(request, bucket, limit, window)


@router.post("/contact", status_code=201)
def contact(body: ContactIn, request: Request, db: Session = Depends(get_db)):
    _limit(request, "contact", 5)
    if body.website:  # bot: pretend success, store nothing
        return {"ok": True}
    db.add(ContactMessage(
        name=body.name.strip(), email=body.email.lower(), clinic_name=(body.clinic_name or "").strip() or None,
        phone=(body.phone or "").strip() or None, topic=body.topic, message=body.message.strip(),
    ))
    push = notify_admins(db, "New support message", f"{body.name.strip()} · {body.topic}", "admin_support", "/admin?tab=support")
    db.commit()
    push()
    return {"ok": True}


@router.get("/clinics")
def find_clinics(request: Request, q: str = Query(min_length=2, max_length=60), db: Session = Depends(get_db)):
    """Lets a new patient find their clinic. Only clinics that opted in are listed, and a search term is required so the list can't be scraped in one call."""
    rate_limit(request, "clinic_search", 60, 600)
    rows = db.scalars(select(Clinic).where(Clinic.deleted_at.is_(None), Clinic.status == "active", Clinic.public_listing.is_(True),
                                          Clinic.name.icontains(q.strip(), autoescape=True) | Clinic.city.icontains(q.strip(), autoescape=True)).order_by(Clinic.name).limit(15)).all()
    return [{"id": c.id, "name": c.name, "city": c.city, "country": c.country, "clinic_type": c.clinic_type} for c in rows]


@router.post("/newsletter", status_code=201)
def newsletter(body: NewsletterIn, request: Request, db: Session = Depends(get_db)):
    _limit(request, "newsletter", 10)
    email = body.email.lower()
    if body.website or db.scalar(select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)):
        return {"ok": True}  # idempotent; never reveals whether an address is already subscribed
    db.add(NewsletterSubscriber(email=email))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"ok": True}
