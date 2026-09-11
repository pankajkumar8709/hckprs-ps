"""F3.6 (deep) — content-integrity + malicious-structure scan.

- corrupted PDF (valid %PDF- header, broken body) -> rejected cleanly
- valid-signature PDF carrying /JavaScript + /OpenAction -> rejected
- a clean minimal PDF -> accepted (no false positive)
- corrupted image -> rejected
"""
from __future__ import annotations

import io
import pytest

from app.services.filecheck import deep_verify, sniff_and_verify, FileTypeError


def _clean_pdf(text="Hello lease renewal 2026 rent 2400"):
    esc = text
    content = f"BT /F1 11 Tf 40 760 Td ({esc}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out = io.BytesIO(); out.write(b"%PDF-1.4\n"); offs = []
    for i, b in enumerate(objs, 1):
        offs.append(out.tell()); out.write(b"%d 0 obj\n%s\nendobj\n" % (i, b))
    x = out.tell(); out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for o in offs: out.write(b"%010d 00000 n \n" % o)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, x))
    return out.getvalue()


def test_clean_pdf_accepted():
    data = _clean_pdf()
    assert sniff_and_verify("lease.pdf", data) == "pdf"
    deep_verify("lease.pdf", data)  # must NOT raise


def test_corrupted_pdf_rejected():
    # Valid header, garbage body -> pypdf can't parse it.
    data = b"%PDF-1.4\n" + b"this is not a real pdf body, no xref, no objects" * 5
    with pytest.raises(FileTypeError):
        deep_verify("broken.pdf", data)


def test_pdf_with_javascript_rejected():
    data = _clean_pdf()
    # Inject dangerous active-content tokens into an otherwise valid-looking PDF.
    data = data.replace(b"trailer", b"5 0 obj << /S /JavaScript /JS (app.alert('x')) >> endobj\n/OpenAction 5 0 R\ntrailer")
    with pytest.raises(FileTypeError) as e:
        deep_verify("lease.pdf", data)
    assert "active content" in str(e.value).lower()


def test_corrupted_image_rejected():
    # PNG signature but truncated / garbage body.
    data = b"\x89PNG\r\n\x1a\n" + b"\x00\x01\x02broken" * 4
    assert sniff_and_verify("pic.png", data) == "png"  # signature passes
    with pytest.raises(FileTypeError):
        deep_verify("pic.png", data)                   # deep check catches it
