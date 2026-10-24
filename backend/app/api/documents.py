import re
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import messaging
from ..core import storage
from ..core.database import get_db
from ..deps import Ctx, require_roles
from ..models import Document, Patient, Role, utcnow
from ..schemas import DocumentPatch
from ..util import Notifier, audit, changed, rate_limit_user, scoped

router = APIRouter(tags=["documents"])
ALL = require_roles(*Role.STAFF)
MAX = 10 * 1024 * 1024
TYPES = {"pdf": ("application/pdf", b"%PDF"), "png": ("image/png", b"\x89PNG"), "jpg": ("image/jpeg", b"\xff\xd8\xff"), "jpeg": ("image/jpeg", b"\xff\xd8\xff"), "webp": ("image/webp", b"RIFF"), "txt": ("text/plain", b"")}


def doc_out(d: Document) -> dict:
    return {"id": d.id, "patient_id": d.patient_id, "filename": d.filename, "content_type": d.content_type, "size": d.size, "category": d.category,
            "shared_with_patient": d.shared_with_patient, "created_at": d.created_at}


def serve(d: Document) -> Response:
    name = re.sub(r'[^A-Za-z0-9._ -]', "_", d.filename)
    return Response(storage.read(d.storage_key), media_type=d.content_type, headers={"Content-Disposition": f'attachment; filename="{name}"', "X-Content-Type-Options": "nosniff"})


@router.post("/patients/{pid}/documents", status_code=201)
def upload(pid: uuid.UUID, file: UploadFile = File(...), category: str = Form("other"), shared: bool = Form(False), ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    rate_limit_user(ctx, "upload", 30, 600)
    p = scoped(db, Patient, pid, ctx)
    if category not in ("report", "scan", "lab", "other"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown document category.")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a PDF, image (PNG, JPG, WebP) or text file.")
    data = file.file.read(MAX + 1)
    if len(data) > MAX:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Files can be at most 10 MB.")
    ctype, magic = TYPES[ext]
    if not data or not data.startswith(magic):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "The file's contents don't match its type.")
    d = Document(clinic_id=ctx.clinic.id, patient_id=p.id, filename=(file.filename or "file")[:200], content_type=ctype, size=len(data), storage_key=storage.save(data),
                 category=category, shared_with_patient=shared, uploaded_by=ctx.user.id)
    db.add(d)
    db.flush()
    audit(db, ctx, "document.uploaded", "document", d.id)
    db.commit()
    changed(ctx, "documents")
    if shared and p.user_id:
        nt = Notifier(db, ctx).add("New document", f"A {category} was shared with you", "documents", "/portal?tab=documents", user_ids=[p.user_id])
        db.commit()
        nt.push()
    if shared:
        messaging.notify_patient(ctx.clinic.id, p.id, "New document available", f"A new {category} from {ctx.clinic.name} is available in your patient portal.")
    return doc_out(d)


@router.get("/documents")
def list_documents(patient_id: uuid.UUID, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    scoped(db, Patient, patient_id, ctx)
    rows = db.scalars(select(Document).where(Document.clinic_id == ctx.clinic.id, Document.patient_id == patient_id, Document.deleted_at.is_(None)).order_by(Document.created_at.desc())).all()
    return [doc_out(d) for d in rows]


@router.get("/documents/{did}/download")
def download(did: uuid.UUID, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    return serve(scoped(db, Document, did, ctx))


@router.patch("/documents/{did}")
def update(did: uuid.UUID, body: DocumentPatch, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    d = scoped(db, Document, did, ctx)
    for k, v in body.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(d, k, v)
    db.commit()
    changed(ctx, "documents")
    return doc_out(d)


@router.delete("/documents/{did}", status_code=204)
def delete(did: uuid.UUID, ctx: Ctx = Depends(ALL), db: Session = Depends(get_db)):
    d = scoped(db, Document, did, ctx)
    d.deleted_at, d.deleted_by = utcnow(), ctx.user.id
    audit(db, ctx, "document.deleted", "document", d.id)
    db.commit()
    changed(ctx, "documents", "trash")
