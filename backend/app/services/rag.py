"""F2.4 — RAG indexing + retrieval over pgvector, user-scoped at the SQL level.

Indexing: on extraction success, chunk ocr_text, embed locally, store rows tagged
with user_id + document_id. Retrieval: embed the query, cosine-distance search
FILTERED BY user_id in the WHERE clause (the isolation guarantee — not a prompt
hint). Returns chunks + the documents they came from for citations.

Degrades gracefully: if embeddings are unavailable, indexing is a no-op and
search returns [], so the caller falls back to whole-text grounding.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk
from app.services import embeddings


def index_document(
    db: Session, user_id: uuid.UUID, document_id: uuid.UUID, ocr_text: str
) -> int:
    """Chunk + embed + store. Returns number of chunks indexed (0 if unavailable)."""
    if not embeddings.available():
        return 0
    chunks = embeddings.chunk_text(ocr_text)
    if not chunks:
        return 0
    vecs = embeddings.embed_texts(chunks)
    if not vecs:
        return 0
    # Clear any prior chunks for this doc (re-index safe).
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id,
        DocumentChunk.user_id == user_id,  # RULE 4
    ).delete()
    for i, (content, vec) in enumerate(zip(chunks, vecs)):
        db.add(
            DocumentChunk(
                user_id=user_id,
                document_id=document_id,
                chunk_index=i,
                content=content,
                embedding=vec,
            )
        )
    db.commit()
    return len(chunks)


def search(
    db: Session, user_id: uuid.UUID, query: str, k: int = 5
) -> tuple[str, list[dict]]:
    """User-scoped similarity search. Returns (context_text, citations).

    citations: [{"document_id","filename"}] deduped, in relevance order.
    Empty context => caller should say "no relevant documents".
    """
    qvec = embeddings.embed_query(query)
    if qvec is None:
        return "", []
    rows = (
        db.query(DocumentChunk, Document.filename)
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(DocumentChunk.user_id == user_id)  # RULE 4 — SQL-level isolation
        .order_by(DocumentChunk.embedding.cosine_distance(qvec))
        .limit(k)
        .all()
    )
    if not rows:
        return "", []
    parts: list[str] = []
    citations: list[dict] = []
    seen: set[uuid.UUID] = set()
    for chunk, filename in rows:
        parts.append(f"[from {filename}]\n{chunk.content}")
        if chunk.document_id not in seen:
            seen.add(chunk.document_id)
            citations.append(
                {"document_id": str(chunk.document_id), "filename": filename}
            )
    return "\n\n".join(parts), citations
