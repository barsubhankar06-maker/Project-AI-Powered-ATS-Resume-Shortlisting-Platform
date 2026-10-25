"""Text extraction from PDF and DOCX, with an optional OCR path.

* PDF text layer  -> pypdf
* DOCX            -> python-docx (paragraphs + tables)
* Scanned PDF     -> OCR if OCR_ENABLED and the tesseract binary is present;
                     otherwise we return an explicit "no text layer" signal
                     rather than pretending the resume was read.
"""
from __future__ import annotations

import io
import shutil
from dataclasses import dataclass, field

from ..config import settings


@dataclass
class ExtractResult:
    text: str = ""
    pages: int = 0
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)
    ok: bool = True
    error: str = ""


def _pdf_text(data: bytes) -> ExtractResult:
    from pypdf import PdfReader

    result = ExtractResult()
    try:
        reader = PdfReader(io.BytesIO(data))
        result.pages = len(reader.pages)
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception as exc:  # noqa: BLE001
                result.warnings.append(f"page extraction failed: {exc}")
        result.text = "\n".join(chunks).strip()
    except Exception as exc:  # noqa: BLE001
        return ExtractResult(ok=False, error=f"Could not read PDF: {exc}")

    if len(result.text) < 40:
        # Likely a scanned/image PDF.
        ocr = _try_ocr(data)
        if ocr.ocr_used:
            result.text = ocr.text
            result.ocr_used = True
            result.warnings.extend(ocr.warnings)
        else:
            result.warnings.append(
                "This PDF appears to be scanned or image-based and has no "
                "extractable text layer. " + ocr.error
            )
            result.ok = False
            result.error = "No extractable text (scanned PDF)"
    return result


def _try_ocr(data: bytes) -> ExtractResult:
    if not settings.ocr_enabled:
        return ExtractResult(error="OCR is disabled (set OCR_ENABLED=true and install tesseract).")
    if not shutil.which(settings.tesseract_cmd):
        return ExtractResult(error="The tesseract binary is not installed on this server.")
    try:
        import fitz  # PyMuPDF  # type: ignore
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except ImportError:
        return ExtractResult(error="OCR libraries (PyMuPDF/pytesseract/Pillow) are not installed.")

    try:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        doc = fitz.open(stream=data, filetype="pdf")
        texts = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            texts.append(pytesseract.image_to_string(img))
        return ExtractResult(text="\n".join(texts).strip(), ocr_used=True)
    except Exception as exc:  # noqa: BLE001
        return ExtractResult(error=f"OCR failed: {exc}")


def _docx_text(data: bytes) -> ExtractResult:
    from docx import Document

    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        return ExtractResult(ok=False, error=f"Could not read DOCX: {exc}")
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    text = "\n".join(parts).strip()
    if not text:
        return ExtractResult(ok=False, error="DOCX contained no readable text")
    return ExtractResult(text=text, pages=1)


def extract_text(filename: str, mime: str, data: bytes) -> ExtractResult:
    name = (filename or "").lower()
    if name.endswith(".pdf") or mime == "application/pdf":
        return _pdf_text(data)
    if name.endswith(".docx") or "wordprocessingml" in (mime or ""):
        return _docx_text(data)
    if name.endswith(".txt") or mime.startswith("text/"):
        return ExtractResult(text=data.decode("utf-8", errors="replace"))
    return ExtractResult(ok=False, error="Unsupported file type (only PDF and DOCX are supported)")


ALLOWED_MIME = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}
ALLOWED_EXT = {".pdf", ".docx", ".txt"}


def sniff_kind(filename: str, mime: str, data: bytes) -> tuple[str, str]:
    """Validate a file by extension AND magic bytes. Returns (kind, error)."""
    name = (filename or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_EXT:
        return "", f"Unsupported extension '{ext or 'none'}'. Allowed: .pdf, .docx, .txt"
    head = data[:8]
    if ext == ".pdf" and not head.startswith(b"%PDF"):
        return "", "File does not look like a valid PDF"
    if ext == ".docx" and not head.startswith(b"PK"):
        return "", "File does not look like a valid DOCX (zip) container"
    return ext.lstrip("."), ""
