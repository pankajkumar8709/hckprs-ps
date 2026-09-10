"""Documents endpoints (Section 0.4): upload, list, detail, delete.

Upload flow (Phase 1 MVP): save file -> extract text (pypdf) -> single-shot LLM
extraction (Gemini) -> store ExtractedField rows -> mark done.

RULE 4: every query filters by current_user.id. No exceptions.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Document, ExtractedField, User
from app.schemas import DocumentDetailResponse, DocumentResponse
from app.services import llm, storage
from app.services.pdf_ocr import ExtractionError, extract_text

router = APIRouter(prefix="/documents", tags=["documents"])

# MVP allowlist (Section F3.12 will harden MIME sniffing; extension check for now).
_ALLOWED_EXT = (".pdf", ".txt", ".md", ".jpg", ".jpeg", ".png")
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


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
        fields = llm.extract_fields(ocr_text)
        for f in fields:
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
        doc.upload_status = "done"
        db.commit()
        db.refresh(doc)
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


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
def get_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)  # RULE 4
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _detail(db, doc, current_user.id)


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
    )
