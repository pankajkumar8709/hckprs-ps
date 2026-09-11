"""F3.6 — malicious file handling: content-based type verification.

Verifies an upload's actual bytes match its claimed extension by inspecting
magic-byte signatures, so a renamed executable (MZ / ELF / shell script) cannot
pass as a PDF/image. No external dependency (avoids libmagic's native binary);
signatures are checked directly.

Archives are intentionally NOT accepted (smaller attack surface — no zip-bomb
path). This is stated explicitly in docs/threat-model.md.
"""
from __future__ import annotations

import io

# Allowlisted types → accepted leading signatures.
_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
}

# Known-dangerous signatures we always reject, whatever the extension claims.
_DANGEROUS = [
    b"MZ",              # Windows PE/.exe/.dll
    b"\x7fELF",         # Linux ELF
    b"#!",              # shell / script shebang
    b"PK\x03\x04",      # zip / office / jar (archives — not accepted)
    b"\xca\xfe\xba\xbe",  # Java class / Mach-O fat
    b"\xcf\xfa\xed\xfe",  # Mach-O
]


class FileTypeError(Exception):
    """Raised when file bytes do not match the claimed/allowed type."""


def sniff_and_verify(filename: str, data: bytes) -> str:
    """Return the verified logical type, or raise FileTypeError.

    - Rejects any known-dangerous signature outright.
    - For pdf/jpg/png: the leading bytes MUST match the type's signature.
    - Text (.txt/.md): accepted if the content decodes as UTF-8-ish text and
      shows no dangerous signature (there is no magic number for plain text).
    """
    head = data[:16]
    for sig in _DANGEROUS:
        if data[: len(sig)] == sig:
            raise FileTypeError("file content is an executable/archive, not an allowed document")

    lower = filename.lower()
    ext = lower.rsplit(".", 1)[-1] if "." in lower else ""

    if ext in ("pdf", "jpg", "jpeg", "png"):
        sigs = _SIGNATURES[ext]
        if not any(head.startswith(s) for s in sigs):
            raise FileTypeError(
                f"file does not look like a real .{ext} "
                f"(content signature mismatch — possible renamed/spoofed file)"
            )
        return "pdf" if ext == "pdf" else ("png" if ext == "png" else "jpg")

    if ext in ("txt", "md"):
        # No magic number for plain text; ensure it is decodable and not binary.
        try:
            data[:4096].decode("utf-8")
        except UnicodeDecodeError:
            raise FileTypeError("file claims to be text but contains binary data")
        return "text"

    raise FileTypeError(f"unsupported file type: .{ext}")


# ---- F3.6 (deep) — content integrity + malicious-structure scan ----------
# Dangerous PDF constructs: embedded scripts and auto-run/launch actions that a
# viewer might execute. A file can have a valid %PDF- signature and still carry
# these, so we scan the actual object stream, not just the header.
_PDF_DANGER_TOKENS = [
    b"/JavaScript", b"/JS", b"/OpenAction", b"/AA",
    b"/Launch", b"/EmbeddedFile", b"/RichMedia", b"/XFA",
]
# A PDF asking to run code/launch/embed on open is rejected. (These tokens can
# appear legitimately in rare forms, but personal documents — leases, bills,
# statements — never need auto-executing JavaScript; refusing them is the safe
# default and is documented in docs/threat-model.md.)


def deep_verify(filename: str, data: bytes) -> None:
    """Second-stage check AFTER sniff_and_verify: confirm the file actually
    parses as its claimed type (catches CORRUPTED files) and carries no
    known-MALICIOUS active content (PDF scripts/auto-actions). Raises
    FileTypeError on failure; returns None when the file is safe to store."""
    lower = filename.lower()
    ext = lower.rsplit(".", 1)[-1] if "." in lower else ""

    if ext == "pdf":
        _verify_pdf(data)
    elif ext in ("jpg", "jpeg", "png"):
        _verify_image(data)
    # txt/md already validated as decodable UTF-8 in sniff_and_verify.


def _verify_pdf(data: bytes) -> None:
    # 1) Malicious active content — scan raw bytes for dangerous constructs.
    for tok in _PDF_DANGER_TOKENS:
        if tok in data:
            raise FileTypeError(
                f"PDF contains disallowed active content ({tok.decode('latin1')}); "
                "documents with embedded scripts or auto-run actions are not accepted"
            )
    # 2) Integrity — the PDF must actually parse, or it is corrupted/malformed.
    try:
        from pypdf import PdfReader
    except ImportError:
        return  # cannot deep-check without pypdf; signature check already passed
    try:
        reader = PdfReader(io.BytesIO(data))
        n = len(reader.pages)
        if reader.is_encrypted:
            raise FileTypeError("encrypted PDFs are not supported")
        if n == 0:
            raise FileTypeError("PDF has no readable pages (corrupted or empty)")
        # Touch the first page to force a structural read.
        _ = reader.pages[0]
    except FileTypeError:
        raise
    except Exception as exc:
        raise FileTypeError(f"PDF appears corrupted or malformed: {exc}") from exc


def _verify_image(data: bytes) -> None:
    try:
        from PIL import Image
    except ImportError:
        return  # cannot deep-check without Pillow; signature check already passed
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # detects truncated / corrupted image data
    except Exception as exc:
        raise FileTypeError(f"image appears corrupted or malformed: {exc}") from exc
