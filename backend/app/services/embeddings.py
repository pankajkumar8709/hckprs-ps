"""Local embeddings — F2.4 vector RAG (Groq-only stack has no embeddings API).

Uses sentence-transformers `all-MiniLM-L6-v2` (384-dim). The model is loaded
LAZILY on first use and cached process-wide, so importing this module is cheap
and a server that never does RAG never pays the model-load memory cost.

Degrades gracefully: if sentence-transformers isn't installed or the model can't
load, embed_texts returns [] and the caller falls back to whole-text grounding.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

EMBED_DIM = 384
_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
_load_failed = False


def _get_model():
    global _model, _load_failed
    if _model is not None:
        return _model
    if _load_failed:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(_MODEL_NAME)
        logger.info("Loaded embedding model %s", _MODEL_NAME)
        return _model
    except Exception as exc:  # ImportError or model download/load failure
        logger.warning("Embeddings unavailable (%s): %s", _MODEL_NAME, exc)
        _load_failed = True
        return None


def available() -> bool:
    return _get_model() is not None


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns [] if the model is unavailable."""
    if not texts:
        return []
    model = _get_model()
    if model is None:
        return []
    try:
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [v.tolist() for v in vecs]
    except Exception as exc:
        logger.warning("Embedding failed: %s", exc)
        return []


def embed_query(text: str) -> list[float] | None:
    out = embed_texts([text])
    return out[0] if out else None


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """Split text into overlapping character-window chunks for embedding."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0:
            start = 0
    return chunks
