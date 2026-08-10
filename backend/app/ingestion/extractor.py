"""
Document Extractor — Robust PDF/DOCX/text extraction with page tracking and OCR fallback.
"""
from dataclasses import dataclass
from io import BytesIO
import logging
from typing import List, Optional

logger = logging.getLogger("grc.ingestion.extractor")

@dataclass
class PageContent:
    page_number: int       # 1-indexed
    raw_text: str
    was_ocr_applied: bool = False

def extract_pages_from_bytes(file_bytes: bytes, filename: str) -> List[PageContent]:
    """
    Extract text page by page from raw file bytes.
    Supports PDF (via PyMuPDF + pytesseract OCR fallback), DOCX, and plain text.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf" or _is_pdf_header(file_bytes):
        return _extract_pdf_pages(file_bytes)
    elif ext in ("docx", "doc"):
        return _extract_docx_pages(file_bytes)
    else:
        return _extract_plaintext_pages(file_bytes)

def _is_pdf_header(file_bytes: bytes) -> bool:
    return file_bytes.startswith(b"%PDF-")

def _extract_pdf_pages(file_bytes: bytes) -> List[PageContent]:
    """
    Extract text page-by-page from PDF using PyMuPDF (fitz).
    If a page produces less than 20 characters of readable text, attempt OCR via Tesseract.
    """
    pages: List[PageContent] = []

    # 1. Primary: PyMuPDF (fitz)
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)
            text = page.get_text("text").strip()
            was_ocr = False

            # Check if page is image-only / scanned (less than 20 chars)
            if len(text) < 20:
                ocr_text = _ocr_pdf_page(page)
                if ocr_text and len(ocr_text) > len(text):
                    text = ocr_text
                    was_ocr = True

            if text:
                pages.append(PageContent(page_number=page_num, raw_text=text, was_ocr_applied=was_ocr))

        if pages:
            return pages
    except Exception as e:
        logger.warning(f"PyMuPDF extraction failed ({e}), attempting PyPDF2 fallback")

    # 2. Fallback: PyPDF2 / pypdf
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(BytesIO(file_bytes), strict=False)
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(PageContent(page_number=idx + 1, raw_text=text.strip(), was_ocr_applied=False))
        if pages:
            return pages
    except Exception as e:
        logger.warning(f"PyPDF2 fallback failed: {e}")

    # 3. Plaintext fallback if PDF headers contained plain text
    return _extract_plaintext_pages(file_bytes)

def _ocr_pdf_page(fitz_page) -> Optional[str]:
    """Perform OCR on a single PyMuPDF page using pytesseract if installed."""
    try:
        import pytesseract
        from PIL import Image

        # Render page to pixmap image (dpi 200)
        pix = fitz_page.get_pixmap(dpi=200)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr_text = pytesseract.image_to_string(img)
        return ocr_text.strip()
    except Exception as e:
        logger.debug(f"OCR skipped for page ({e})")
        return None

def _extract_docx_pages(file_bytes: bytes) -> List[PageContent]:
    """Extract paragraphs from DOCX into a single page or sectioned pages."""
    try:
        import docx
        doc = docx.Document(BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            return []
        
        # Group into pseudo-pages (~500 words per page)
        pages: List[PageContent] = []
        current_page_lines: List[str] = []
        current_word_count = 0
        page_num = 1

        for para in paragraphs:
            words = len(para.split())
            current_page_lines.append(para)
            current_word_count += words
            if current_word_count >= 400:
                pages.append(PageContent(page_number=page_num, raw_text="\n\n".join(current_page_lines)))
                page_num += 1
                current_page_lines = []
                current_word_count = 0

        if current_page_lines:
            pages.append(PageContent(page_number=page_num, raw_text="\n\n".join(current_page_lines)))

        return pages
    except Exception as e:
        logger.warning(f"DOCX extraction failed ({e}), falling back to text decode")
        return _extract_plaintext_pages(file_bytes)

def _extract_plaintext_pages(file_bytes: bytes) -> List[PageContent]:
    """Decode plain text bytes and group into pages of ~2000 chars."""
    try:
        text = file_bytes.decode("utf-8", errors="ignore").strip()
    except Exception:
        text = ""

    if not text:
        return []

    lines = text.splitlines()
    pages: List[PageContent] = []
    current_chunk: List[str] = []
    current_len = 0
    page_num = 1

    for line in lines:
        current_chunk.append(line)
        current_len += len(line)
        if current_len >= 2000:
            pages.append(PageContent(page_number=page_num, raw_text="\n".join(current_chunk)))
            page_num += 1
            current_chunk = []
            current_len = 0

    if current_chunk:
        pages.append(PageContent(page_number=page_num, raw_text="\n".join(current_chunk)))

    return pages
