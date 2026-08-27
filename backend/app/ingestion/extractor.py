"""
Document Extractor — Robust PDF/DOCX/Image/Text extraction with fine-tuned OCR and multimodal fallback.
"""
from dataclasses import dataclass
from io import BytesIO
import logging
import os
import re
import shutil
from typing import List, Optional

from PIL import Image, ImageOps, ImageFilter
from app.config import settings

logger = logging.getLogger("grc.ingestion.extractor")

_TESSERACT_INITIALIZED = False
_TESSERACT_AVAILABLE = False

IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "tiff", "tif", "webp", "bmp"}

# Common image MIME types
MIME_BY_EXT = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "bmp": "image/bmp",
}

@dataclass
class PageContent:
    page_number: int       # 1-indexed
    raw_text: str
    was_ocr_applied: bool = False


def _init_tesseract() -> bool:
    """
    Discover and configure pytesseract executable path automatically across platforms.
    Checks:
    1. os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
    2. shutil.which("tesseract")
    3. Standard Windows directories (Program Files, LocalAppData, Chocolatey, Scoop)
    """
    global _TESSERACT_INITIALIZED, _TESSERACT_AVAILABLE
    if _TESSERACT_INITIALIZED:
        return _TESSERACT_AVAILABLE

    _TESSERACT_INITIALIZED = True
    try:
        import pytesseract

        # 1. Check explicit env var
        env_cmd = os.environ.get("TESSERACT_CMD") or os.environ.get("TESSERACT_PATH")
        if env_cmd and os.path.isfile(env_cmd):
            pytesseract.pytesseract.tesseract_cmd = env_cmd
            _TESSERACT_AVAILABLE = True
            logger.info(f"Tesseract configured from TESSERACT_CMD: {env_cmd}")
            return True

        # 2. Check system PATH
        which_tesseract = shutil.which("tesseract")
        if which_tesseract:
            pytesseract.pytesseract.tesseract_cmd = which_tesseract
            _TESSERACT_AVAILABLE = True
            return True

        # 3. Check standard Windows paths
        standard_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            r"C:\tools\tesseract\tesseract.exe",
            r"C:\ProgramData\chocolatey\bin\tesseract.exe",
        ]
        for p in standard_paths:
            if os.path.isfile(p):
                pytesseract.pytesseract.tesseract_cmd = p
                tessdata = os.path.join(os.path.dirname(p), "tessdata")
                if os.path.isdir(tessdata) and not os.environ.get("TESSDATA_PREFIX"):
                    os.environ["TESSDATA_PREFIX"] = tessdata
                _TESSERACT_AVAILABLE = True
                logger.info(f"Tesseract auto-discovered at: {p}")
                return True

        _TESSERACT_AVAILABLE = False
        logger.debug("Tesseract binary not found on system PATH or default directories.")
        return False
    except Exception as e:
        logger.debug(f"Failed to initialize pytesseract: {e}")
        _TESSERACT_AVAILABLE = False
        return False


def _preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """
    Fine-tuned image preprocessing pipeline to maximize OCR character recognition:
    1. Upscale low-resolution images so character heights are optimal for LSTM.
    2. Convert to grayscale to remove background color noise.
    3. Auto-contrast normalization to make faint or shaded text distinct.
    4. Edge sharpening to clarify character contours.
    """
    try:
        # 1. Convert to RGB if palette/RGBA
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # 2. Rescale low-resolution images (< 1200px in width or height)
        w, h = img.size
        if w < 1200 or h < 1200:
            scale_factor = max(1.5, min(2.5, 1800 / max(w, h, 1)))
            new_w, new_h = int(w * scale_factor), int(h * scale_factor)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 3. Grayscale conversion
        gray = ImageOps.grayscale(img)

        # 4. Auto-contrast normalization (clip 2% of darkest/lightest pixels)
        contrast = ImageOps.autocontrast(gray, cutoff=2)

        # 5. Sharpening filter
        sharpened = contrast.filter(ImageFilter.SHARPEN)

        return sharpened
    except Exception as e:
        logger.debug(f"Image preprocessing fallback to original ({e})")
        return img


def _clean_ocr_text(text: str) -> str:
    """Clean and normalize raw OCR output."""
    if not text:
        return ""

    # Fix broken hyphenated words across line breaks (e.g. "compli-\nance" -> "compliance")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)

    # Normalize excessive blank lines (more than 2 -> 2)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Strip non-printable control characters except standard whitespace
    text = "".join(ch for ch in text if ch.isprintable() or ch in '\n\r\t')

    return text.strip()


def _run_tesseract_ocr(img: Image.Image) -> Optional[str]:
    """
    Execute multi-pass fine-tuned Tesseract OCR:
    - Pass 1: --oem 1 --psm 3 (Fully automatic page segmentation)
    - Pass 2 (fallback): --oem 1 --psm 6 (Uniform text block, ideal for certificates/forms)
    """
    if not _init_tesseract():
        return None

    try:
        import pytesseract

        # Preprocess image
        processed_img = _preprocess_image_for_ocr(img)

        # Pass 1: Automatic page segmentation (best for multi-column policy layouts)
        config_p1 = r'--oem 1 --psm 3'
        text_p1 = pytesseract.image_to_string(processed_img, config=config_p1)
        text_p1 = _clean_ocr_text(text_p1)

        # If Pass 1 produced solid text (> 40 chars), return it
        if len(text_p1) >= 40:
            return text_p1

        # Pass 2: Single uniform block (best for certificates, evidence scans, single forms)
        config_p2 = r'--oem 1 --psm 6'
        text_p2 = pytesseract.image_to_string(processed_img, config=config_p2)
        text_p2 = _clean_ocr_text(text_p2)

        # Pick whichever pass yielded more readable text
        best_text = text_p2 if len(text_p2) > len(text_p1) else text_p1
        return best_text if best_text else None
    except Exception as e:
        logger.debug(f"Tesseract OCR pass failed: {e}")
        return None


def _gemini_vision_ocr(image_bytes: bytes, mime_type: str = "image/png") -> Optional[str]:
    """
    Multimodal Vision OCR fallback via Gemini 1.5 Flash.

    Data Residency & Sovereignty Gate:
      - STRICTLY disabled if DATA_RESIDENCY_MODE == 'strict'
      - STRICTLY disabled if LLM_MODE != 'cloud' (e.g. in 'local-only' or 'self-hosted' mode)
      - Requires valid GEMINI_API_KEY
    """
    # 1. Hard Gate: Data residency enforcement (no outbound data in strict mode)
    if getattr(settings, "DATA_RESIDENCY_MODE", "off") == "strict":
        logger.debug("Gemini Vision OCR blocked: DATA_RESIDENCY_MODE is 'strict'")
        return None

    # 2. Hard Gate: LLM mode enforcement (cloud calls only allowed if LLM_MODE='cloud')
    if getattr(settings, "LLM_MODE", "local-only") != "cloud":
        logger.debug(
            "Gemini Vision OCR blocked: LLM_MODE is '%s' (cloud OCR prohibited in local/self-hosted modes)",
            getattr(settings, "LLM_MODE", "local-only")
        )
        return None

    # 3. API key check
    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        logger.debug("Gemini Vision OCR skipped: GEMINI_API_KEY is not configured")
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = (
            "Transcribe all text from this scanned document page or image accurately. "
            "Preserve section headers, numbered clauses, policy requirements, bullet points, and tables. "
            "Return ONLY the verbatim extracted text. Do not include markdown preamble, summary, or conversational commentary."
        )

        response = client.models.generate_content(
            model=settings.LLM_CLOUD_MODEL or "gemini-1.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ]
        )

        if response and response.text:
            cleaned = _clean_ocr_text(response.text)
            if cleaned:
                logger.info("Gemini Vision OCR successfully extracted page text")
                return cleaned
        return None
    except Exception as e:
        logger.debug(f"Gemini Vision OCR fallback skipped ({e})")
        return None


def extract_pages_from_bytes(file_bytes: bytes, filename: str) -> List[PageContent]:
    """
    Extract text page by page from raw file bytes.
    Supports PDF (via PyMuPDF + fine-tuned Tesseract + Gemini Vision fallback), DOCX, Standalone Images, and plain text.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf" or _is_pdf_header(file_bytes):
        return _extract_pdf_pages(file_bytes)
    elif ext in ("docx", "doc"):
        return _extract_docx_pages(file_bytes)
    elif ext in IMAGE_EXTENSIONS:
        return _extract_image_pages(file_bytes, ext)
    else:
        return _extract_plaintext_pages(file_bytes)


def extract_text_from_bytes(file_bytes: bytes, filename: str = "") -> str:
    """Extract full text as a single string across all extracted pages."""
    pages = extract_pages_from_bytes(file_bytes, filename)
    return "\n\n".join(p.raw_text for p in pages if p.raw_text.strip()).strip()


def _is_pdf_header(file_bytes: bytes) -> bool:
    return file_bytes.startswith(b"%PDF-")


def _extract_pdf_pages(file_bytes: bytes) -> List[PageContent]:
    """
    Extract text page-by-page from PDF using PyMuPDF.
    If a page is scanned, image-only, or sparse (<80 chars / <15 words with images), attempt fine-tuned OCR.
    """
    pages: List[PageContent] = []

    # 1. Primary: PyMuPDF (fitz)
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc.load_page(page_idx)
            text = page.get_text("text").strip()
            was_ocr = False

            # Check if page is image-only, scanned, or sparse text with embedded images
            words = text.split()
            images = page.get_images() if hasattr(page, "get_images") else []
            has_images = len(images) > 0

            # Trigger OCR if text is minimal or if text is sparse on a page with images
            should_ocr = len(text) < 30 or (len(text) < 80 and has_images) or (len(words) < 15 and has_images)

            if should_ocr:
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

    return []


def _ocr_pdf_page(fitz_page) -> Optional[str]:
    """
    Perform fine-tuned OCR on a single PyMuPDF page:
    1. Render at 300 DPI for high-detail character edges.
    2. Try multi-pass Tesseract OCR.
    3. Fallback to Gemini Vision if Tesseract is missing/insufficient.
    """
    try:
        # Render page at 300 DPI
        pix = fitz_page.get_pixmap(dpi=300)
        try:
            png_bytes = pix.tobytes("png")
            img = Image.open(BytesIO(png_bytes))
        except Exception:
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            buf = BytesIO()
            img.save(buf, format="PNG")
            png_bytes = buf.getvalue()

        # Step 1: Run fine-tuned Tesseract
        ocr_text = _run_tesseract_ocr(img)
        if ocr_text and len(ocr_text) >= 20:
            return ocr_text

        # Step 2: Fallback to Gemini Vision if available
        vision_text = _gemini_vision_ocr(png_bytes, "image/png")
        if vision_text and len(vision_text) > len(ocr_text or ""):
            return vision_text

        return ocr_text
    except Exception as e:
        logger.debug(f"OCR skipped for page ({e})")
        return None


def _extract_image_pages(file_bytes: bytes, ext: str = "png") -> List[PageContent]:
    """
    Direct OCR on standalone image bytes (PNG, JPG, TIFF, WebP, etc.):
    1. Runs fine-tuned Tesseract OCR with preprocessing.
    2. Falls back to Gemini Vision if Tesseract is unavailable or insufficient.
    """
    try:
        img = Image.open(BytesIO(file_bytes))
        mime_type = MIME_BY_EXT.get(ext, "image/png")

        # Step 1: Try fine-tuned Tesseract
        ocr_text = _run_tesseract_ocr(img)
        if ocr_text and len(ocr_text) >= 20:
            return [PageContent(page_number=1, raw_text=ocr_text, was_ocr_applied=True)]

        # Step 2: Try Gemini Vision fallback
        vision_text = _gemini_vision_ocr(file_bytes, mime_type)
        best_text = vision_text if (vision_text and len(vision_text) > len(ocr_text or "")) else ocr_text

        if best_text:
            return [PageContent(page_number=1, raw_text=best_text, was_ocr_applied=True)]
        return []
    except Exception as e:
        logger.warning(f"Image OCR extraction failed: {e}")
        return []


def _extract_docx_pages(file_bytes: bytes) -> List[PageContent]:
    """Extract paragraphs from DOCX into a single page or sectioned pages."""
    try:
        import docx
        doc = docx.Document(BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            return []
        
        # Group into pseudo-pages (~400 words per page)
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


