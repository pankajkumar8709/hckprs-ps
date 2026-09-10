"""Documents endpoints (Section 0.4): upload, list, detail, delete.

Upload flow (Phase 1 MVP): save file -> extract text (pypdf) -> single-shot LLM
extraction (Gemini) -> store ExtractedField rows -> mark done.

RULE 4: every query filters by current_user.id. No exceptions.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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

router = APIRouter(prefix="/documents", tags=["documents"])

# MVP allowlist (Section F3.12 will harden MIME sniffing; extension check for now).
_ALLOWED_EXT = (".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png")
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_FREE_TIER_DOC_LIMIT = 10  # F2.9 — free plan cap


@router.post("/upload", response_model=DocumentDetailResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    filename = file.filename or "upload"
    if not filename.lower().endswith(_ALLOWED_EXT):
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
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

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
    # Only the OWNER may share (Rule 4).
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
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
    return grant


def _accessible_document(db: Session, doc_id: uuid.UUID, user: User) -> Document | None:
    """F2.8 — return the doc if the user OWNS it OR has a valid non-expired grant.

    Enforced server-side, not by trusting the client. Returns None if neither.
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc is None:
        return None
    if doc.user_id == user.id:  # owner path (Rule 4)
        return doc
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
    return doc if grant is not None else None


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    doc = _accessible_document(db, doc_id, current_user)  # owner OR valid grant
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    # Fields belong to the OWNER; read them by document owner id, not requester.
    return _detail(db, doc, doc.user_id)


@router.delete("/{doc_id}", status_code=204, response_class=Response)
def delete_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)  # RULE 4
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
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
