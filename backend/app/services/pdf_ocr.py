"""Text extraction — Phase 1 MVP uses pypdf for PDFs (chosen with the user).

The plan calls this step 'OCR'. For the MVP we extract embedded text from PDFs
with pypdf and read text files directly; true image OCR (Tesseract / cloud) is a
later, pluggable swap. Keep the interface (bytes -> str) stable so F2.1 only ever
depends on Document.ocr_text being populated, not on how.
"""
from __future__ import annotations

import io


class ExtractionError(Exception):
    """Raised when text cannot be extracted from the given bytes."""


def extract_text(filename: str, data: bytes) -> str:
    """Return best-effort plain text for a supported upload.

    Supported for MVP: .pdf (pypdf), .txt/.md (utf-8). Images are accepted by the
    upload endpoint's allowlist but produce empty text here until OCR is wired.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(data)
    if lower.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    # Images (jpg/png) — no OCR yet; return empty so downstream marks low signal.
    return ""


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ExtractionError("pypdf not installed") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
        parts = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise ExtractionError(f"failed to read PDF: {exc}") from exc
    return "\n".join(parts).strip()
