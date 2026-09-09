"""
PDF / Document Text Extraction.

Extracted from ai_service.py – provides a unified extractor with
OCR fallback, PyPDF2 fallback, docx fallback, and raw text decode.
"""

import logging
from io import BytesIO

logger = logging.getLogger("grc.ai")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text content from a PDF/document file's bytes using unified extractor with OCR fallback."""
    # 1. Try unified extractor (PyMuPDF + Tesseract OCR + DOCX + plain text)
    try:
        from app.ingestion.extractor import extract_text_from_bytes
        text = extract_text_from_bytes(file_bytes, "document.pdf")
        if text.strip():
            return text.strip()
    except Exception as e:
        logger.warning(f"Unified extractor failed ({e}), trying fallback handlers")

    # 2. Fallback: PyPDF2 / pypdf with strict=False
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(BytesIO(file_bytes), strict=False)
        pages_text: list[str] = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t.strip())
        extracted = "\n\n".join(pages_text)
        if extracted.strip():
            return extracted
    except Exception as e:
        logger.warning(f"PyPDF2 fallback extraction failed: {e}")

    # 3. Fallback: docx format parser
    try:
        import docx  # type: ignore
        doc = docx.Document(BytesIO(file_bytes))
        full_text = [p.text for p in doc.paragraphs if p.text.strip()]
        if full_text:
            return "\n\n".join(full_text)
    except Exception:
        pass

    # 4. Fallback: UTF-8 / Latin-1 text decode for plain text / markdown / logs
    try:
        decoded = file_bytes.decode('utf-8', errors='ignore')
        # Check if file has readable text characters
        printable_ratio = sum(1 for c in decoded if c.isprintable() or c in '\n\r\t') / max(len(decoded), 1)
        if printable_ratio > 0.85 and len(decoded.strip()) > 10:
            return decoded.strip()
    except Exception:
        pass

    return ""
