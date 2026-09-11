"""Documents endpoints (Section 0.4): upload, list, detail, delete.

Upload flow (Phase 1 MVP): save file -> extract text (pypdf) -> single-shot LLM
extraction (Gemini) -> store ExtractedField rows -> mark done.

RULE 4: every query filters by current_user.id. No exceptions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Document, ExtractedField, ShareGrant, User
from app.schemas import (
    DocumentDetailResponse,
    DocumentResponse,
    ShareGrantResponse,
    ShareRequest,
)
from app.services import llm, rag, storage
from app.services.pdf_ocr import ExtractionError, extract_text
from app.services.reminders import create_reminders_for_document
from app.services.insights import regenerate_insights
from app.services.scoped import scoped_get, scoped_query
from app.services.filecheck import sniff_and_verify as verify_file_type, FileTypeError, deep_verify
from app.services import audit

router = APIRouter(prefix="/documents", tags=["documents"])

# MVP allowlist (Section F3.12 will harden MIME sniffing; extension check for now).
_ALLOWED_EXT = (".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png")
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_FREE_TIER_DOC_LIMIT = 10  # F2.9 — free plan cap


@router.post("/upload", response_model=DocumentDetailResponse, status_code=201)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    _ip = request.client.host if request.client else None
    filename = file.filename or "upload"
    if not filename.lower().endswith(_ALLOWED_EXT):
        audit.log_audit(db, current_user.id, audit.SECURITY_UPLOAD_BLOCKED,
                        resource_type="upload.bad_extension", ip_address=_ip)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(_ALLOWED_EXT)}",
        )

    # F2.9 — enforce free-tier document cap before doing any work.
    if current_user.plan_tier == "free":
        doc_count = (
            db.query(Document)
            .filter(Document.user_id == current_user.id)  # RULE 4
            .count()
        )
        if doc_count >= _FREE_TIER_DOC_LIMIT:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Free plan is limited to {_FREE_TIER_DOC_LIMIT} documents. "
                    "Upgrade to premium for unlimited uploads."
                ),
            )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > _MAX_BYTES:
        audit.log_audit(db, current_user.id, audit.SECURITY_UPLOAD_BLOCKED,
                        resource_type="upload.oversized", ip_address=_ip)
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    # F3.6 — verify the file's actual bytes match its claimed type (reject a
    # renamed .exe/archive/script masquerading as a document).
    try:
        verify_file_type(filename, data)
    except FileTypeError as exc:
        audit.log_audit(db, current_user.id, audit.SECURITY_UPLOAD_BLOCKED,
                        resource_type="upload.type_mismatch", ip_address=_ip)
        raise HTTPException(status_code=400, detail=str(exc))

    # F3.6 (deep) — content integrity + malicious-structure scan: reject a
    # corrupted file or a valid-signature PDF carrying scripts/auto-run actions.
    try:
        deep_verify(filename, data)
    except FileTypeError as exc:
        audit.log_audit(db, current_user.id, audit.SECURITY_UPLOAD_BLOCKED,
                        resource_type="upload.content_unsafe", ip_address=_ip)
        raise HTTPException(status_code=400, detail=str(exc))

    storage_path = storage.save_file(current_user.id, filename, data)
    doc = Document(
        user_id=current_user.id,
        filename=filename,
        storage_path=storage_path,
        upload_status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        ocr_text = extract_text(filename, data)
        doc.ocr_text = ocr_text

        # F2.1 + F2.2 — Classification -> Extraction -> Validation pipeline.
        result = llm.ingest_document(ocr_text)
        doc.doc_type = result["doc_type"]
        doc.agent_trace_json = {"steps": result["agent_trace"]}
        for f in result["fields"]:  # only validator-accepted fields
            db.add(
                ExtractedField(
                    document_id=doc.id,
                    user_id=current_user.id,
                    field_name=f["field_name"],
                    field_value=f.get("field_value"),
                    field_type=f["field_type"],
                    confidence=f.get("confidence"),
                )
            )
        # F2.2 — validator may fail the doc (all hard facts unverifiable).
        doc.upload_status = result["status"]
        db.commit()
        db.refresh(doc)

        # F2.3 — auto-create reminders from extracted dates.
        create_reminders_for_document(db, current_user.id, doc.id)
        # F2.7 — refresh cross-document insights.
        regenerate_insights(db, current_user.id)
        # F2.4 — index chunks for RAG (no-op if embeddings unavailable).
        try:
            rag.index_document(db, current_user.id, doc.id, ocr_text)
        except Exception:
            db.rollback()  # RAG indexing must never fail the upload
    except ExtractionError as exc:
        doc.upload_status = "failed"
        db.commit()
        raise HTTPException(status_code=422, detail=f"Extraction failed: {exc}")

    audit.log_audit(db, current_user.id, audit.DOC_UPLOAD,
                    resource_type="document", resource_id=doc.id)
    return _detail(db, doc, current_user.id)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)  # RULE 4
        .order_by(Document.created_at.desc())
        .all()
    )


# F2.8 — MUST be declared before /{doc_id} so it isn't parsed as a UUID.
@router.get("/shared-with-me", response_model=list[DocumentResponse])
def shared_with_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Document]:
    now = datetime.now(timezone.utc)
    rows = (
        db.query(Document)
        .join(ShareGrant, ShareGrant.document_id == Document.id)
        .filter(
            ShareGrant.shared_with_user_id == current_user.id,  # RULE 4
            (ShareGrant.expires_at.is_(None)) | (ShareGrant.expires_at > now),
        )
        .order_by(Document.created_at.desc())
        .all()
    )
    return rows


@router.post("/{doc_id}/share", response_model=ShareGrantResponse, status_code=201)
def share_document(
    doc_id: uuid.UUID,
    body: ShareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ShareGrant:
    # Only the OWNER may share (F3.2 scoped fetch — 404 if not owner).
    doc = scoped_get(db, Document, doc_id, current_user.id,
                     not_found_detail="Document not found")
    target = db.query(User).filter(User.email == body.shared_with_email).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Recipient user not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot share with yourself")
    grant = ShareGrant(
        document_id=doc.id,
        owner_user_id=current_user.id,
        shared_with_user_id=target.id,
        permission=body.permission,
        expires_at=body.expires_at,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    audit.log_audit(db, current_user.id, audit.SHARE_CREATE,
                    resource_type="document", resource_id=doc.id)
    return grant


def _accessible_document(db: Session, doc_id: uuid.UUID, user: User) -> Document | None:
    """F2.8 — return the doc if the user OWNS it OR has a valid non-expired grant.

    Owner path goes through the scoped helper (F3.2); the share-grant path is the
    deliberate, audited widening of access beyond owner-scope. Returns None if
    neither applies.
    """
    # Owner path — user-scoped fetch (returns None instead of raising here).
    doc = scoped_query(db, Document, user.id).filter(Document.id == doc_id).first()
    if doc is not None:
        return doc
    # Shared path: a valid non-expired grant to this user.
    now = datetime.now(timezone.utc)
    grant = (
        db.query(ShareGrant)
        .filter(
            ShareGrant.document_id == doc_id,
            ShareGrant.shared_with_user_id == user.id,
            (ShareGrant.expires_at.is_(None)) | (ShareGrant.expires_at > now),
        )
        .first()
    )
    if grant is None:
        return None
    return db.query(Document).filter(Document.id == doc_id).first()


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    doc = _accessible_document(db, doc_id, current_user)  # owner OR valid grant
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    audit.log_audit(db, current_user.id, audit.DOC_ACCESS,
                    resource_type="document", resource_id=doc.id)
    # Fields belong to the OWNER; read them by document owner id, not requester.
    return _detail(db, doc, doc.user_id)


@router.get("/{doc_id}/download-url")
def get_download_url(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """F3.3 — mint a short-lived signed URL for the file. Auth + access checked
    here; the file route itself is opened only by the token."""
    doc = _accessible_document(db, doc_id, current_user)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    token = storage.sign_download(doc.id, current_user.id)
    return {"url": f"/documents/{doc.id}/file?uid={current_user.id}&token={token}",
            "expires_in": 300}


@router.get("/{doc_id}/file")
def download_file(
    doc_id: uuid.UUID,
    uid: uuid.UUID,
    token: str,
    db: Session = Depends(get_db),
) -> Response:
    """F3.3 — serve decrypted bytes ONLY with a valid, non-expired signed token.
    No bearer auth here: the signed token IS the capability (and it is bound to
    uid + doc + expiry). An invalid/expired token → 403."""
    if not storage.verify_download(doc_id, uid, token):
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    # Confirm the doc is actually accessible to that uid (owner or valid grant).
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None or doc.storage_path is None:
        raise HTTPException(status_code=404, detail="Document not found")
    now = datetime.now(timezone.utc)
    is_owner = doc.user_id == uid
    has_grant = db.query(ShareGrant).filter(
        ShareGrant.document_id == doc_id,
        ShareGrant.shared_with_user_id == uid,
        (ShareGrant.expires_at.is_(None)) | (ShareGrant.expires_at > now),
    ).first() is not None
    if not (is_owner or has_grant):
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    try:
        data = storage.read_file(doc.storage_path)
    except Exception:
        raise HTTPException(status_code=404, detail="File unavailable")
    return Response(content=data, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'})


@router.delete("/{doc_id}", status_code=204, response_class=Response)
def delete_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    doc = scoped_get(db, Document, doc_id, current_user.id,
                     not_found_detail="Document not found")
    audit.log_audit(db, current_user.id, audit.DOC_DELETE,
                    resource_type="document", resource_id=doc.id)
    db.delete(doc)  # ExtractedField rows cascade via FK ondelete=CASCADE
    db.commit()
    return Response(status_code=204)


def _detail(db: Session, doc: Document, user_id: uuid.UUID) -> DocumentDetailResponse:
    fields = (
        db.query(ExtractedField)
        .filter(
            ExtractedField.document_id == doc.id,
            ExtractedField.user_id == user_id,  # RULE 4
        )
        .all()
    )
    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        upload_status=doc.upload_status,
        created_at=doc.created_at,
        ocr_text=doc.ocr_text,
        extracted_fields=fields,
        agent_trace=(doc.agent_trace_json or {}).get("steps", []),
    )
