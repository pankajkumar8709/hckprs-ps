"""Text extraction with OCR fallback — Phase 1 F1.2.

Strategy (per the plan): try the PDF's embedded text layer first (pypdf). If that
yields little/no text — a scanned or image-only PDF — fall back to OCR
(pdf2image -> pytesseract). Image uploads (jpg/png) go straight to OCR.

OCR requires two EXTERNAL binaries that pip cannot install:
  - Tesseract-OCR  (https://github.com/UB-Mannheim/tesseract/wiki)
  - Poppler        (pdf2image needs `pdftoppm`; https://github.com/oschwartz10612/poppler-windows)
When they are absent the OCR path degrades gracefully: text-layer PDFs still work,
and scanned PDFs / images return "" (with a reason logged) instead of crashing.
Set POPPLER_PATH in the environment if poppler isn't on PATH.
"""
from __future__ import annotations

import io
import logging
import os

logger = logging.getLogger(__name__)

# Below this many characters we treat a PDF as having no usable text layer.
_MIN_TEXT_LEN = 20


class ExtractionError(Exception):
    """Raised when text cannot be extracted from the given bytes."""


def extract_text(filename: str, data: bytes) -> str:
    """Return best-effort plain text for a supported upload.

    - .pdf  -> pypdf text layer first, OCR fallback if empty/scanned
    - .txt/.md -> decoded directly
    - .jpg/.jpeg/.png -> OCR
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        text = _extract_pdf_text(data)
        if len(text.strip()) >= _MIN_TEXT_LEN:
            return text
        # No usable text layer -> scanned PDF; try OCR.
        ocr = _ocr_pdf(data)
        return ocr if ocr.strip() else text
    if lower.endswith((".txt", ".md")):
        return data.decode("utf-8", errors="replace")
    if lower.endswith((".jpg", ".jpeg", ".png")):
        return _ocr_image(data)
    return ""


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ExtractionError("pypdf not installed") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        parts = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise ExtractionError(f"failed to read PDF: {exc}") from exc
    return "\n".join(parts).strip()


def _ocr_pdf(data: bytes) -> str:
    """Render PDF pages to images (pdf2image/poppler) then OCR (pytesseract)."""
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        logger.warning("OCR fallback unavailable: pdf2image not installed")
        return ""
    kwargs = {}
    poppler = os.environ.get("POPPLER_PATH")
    if poppler:
        kwargs["poppler_path"] = poppler
    try:
        images = convert_from_bytes(data, dpi=200, **kwargs)
    except Exception as exc:
        # Most commonly: poppler binary not found on PATH.
        logger.warning("OCR fallback unavailable (poppler): %s", exc)
        return ""
    out = []
    for img in images:
        out.append(_ocr_pil_image(img))
    return "\n".join(p for p in out if p).strip()


def _ocr_image(data: bytes) -> str:
    try:
        from PIL import Image
    except ImportError:
        logger.warning("OCR unavailable: Pillow not installed")
        return ""
    try:
        img = Image.open(io.BytesIO(data))
    except Exception as exc:
        logger.warning("could not open image for OCR: %s", exc)
        return ""
    return _ocr_pil_image(img)


def _ocr_pil_image(img) -> str:
    try:
        import pytesseract
    except ImportError:
        logger.warning("OCR unavailable: pytesseract not installed")
        return ""
    tess = os.environ.get("TESSERACT_PATH")
    if tess:
        pytesseract.pytesseract.tesseract_cmd = tess
    try:
        return (pytesseract.image_to_string(img) or "").strip()
    except Exception as exc:
        # Most commonly: tesseract binary not found on PATH.
        logger.warning("OCR unavailable (tesseract): %s", exc)
        return ""
