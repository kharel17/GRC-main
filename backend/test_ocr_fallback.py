import unittest
from unittest.mock import MagicMock, patch
from PIL import Image
from app.ingestion.extractor import (
    _ocr_pdf_page,
    _extract_pdf_pages,
    _extract_image_pages,
    extract_pages_from_bytes,
    extract_text_from_bytes,
    _init_tesseract,
    _preprocess_image_for_ocr,
    _clean_ocr_text,
    _gemini_vision_ocr,
)

class TestOCRFallback(unittest.TestCase):
    @patch('app.ingestion.extractor._init_tesseract', return_value=True)
    @patch('pytesseract.image_to_string')
    def test_ocr_pdf_page_success(self, mock_image_to_string, mock_init_tesseract):
        mock_image_to_string.return_value = "Sample OCR Extracted Compliance Policy Text"

        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b'\xff' * 30000
        mock_page.get_pixmap.return_value = mock_pixmap

        result = _ocr_pdf_page(mock_page)

        self.assertEqual(result, "Sample OCR Extracted Compliance Policy Text")
        mock_image_to_string.assert_called_once()

    @patch('app.ingestion.extractor._ocr_pdf_page')
    @patch('pymupdf.open')
    def test_extract_pdf_pages_triggers_ocr(self, mock_pymupdf_open, mock_ocr_pdf_page):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        
        mock_page.get_text.return_value = "Short"
        mock_page.get_images.return_value = []
        mock_doc.__len__.return_value = 1
        mock_doc.load_page.return_value = mock_page
        mock_pymupdf_open.return_value = mock_doc

        mock_ocr_pdf_page.return_value = "This is a full page of text extracted using OCR fallback."

        pages = _extract_pdf_pages(b"%PDF-1.4 dummy bytes")

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page_number, 1)
        self.assertEqual(pages[0].raw_text, "This is a full page of text extracted using OCR fallback.")
        self.assertTrue(pages[0].was_ocr_applied)
        mock_ocr_pdf_page.assert_called_once_with(mock_page)

    @patch('app.ingestion.extractor._ocr_pdf_page')
    @patch('pymupdf.open')
    def test_extract_pdf_pages_triggers_ocr_on_sparse_image_page(self, mock_pymupdf_open, mock_ocr_pdf_page):
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Confidential Compliance Policy - Page 1 of 10"
        mock_page.get_images.return_value = [(1, 0, 100, 100, 8, 'DeviceRGB', '', 'img1', 'FlateDecode')]
        mock_doc.__len__.return_value = 1
        mock_doc.load_page.return_value = mock_page
        mock_pymupdf_open.return_value = mock_doc

        mock_ocr_pdf_page.return_value = "Confidential Compliance Policy - Page 1 of 10\nFull scanned section A.5 Information Security Policies."

        pages = _extract_pdf_pages(b"%PDF-1.4 dummy bytes")

        self.assertEqual(len(pages), 1)
        self.assertTrue(pages[0].was_ocr_applied)
        self.assertIn("Full scanned section", pages[0].raw_text)

    @patch('app.ingestion.extractor._init_tesseract', return_value=True)
    @patch('pytesseract.image_to_string')
    @patch('PIL.Image.open')
    def test_extract_image_pages(self, mock_pil_open, mock_image_to_string, mock_init_tesseract):
        mock_image_to_string.return_value = "Extracted text from scanned certificate image"
        
        pages = extract_pages_from_bytes(b"dummy image bytes", "scan.png")
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page_number, 1)
        self.assertEqual(pages[0].raw_text, "Extracted text from scanned certificate image")
        self.assertTrue(pages[0].was_ocr_applied)

    def test_preprocess_image_pipeline(self):
        img = Image.new("RGB", (200, 100), color=(230, 230, 230))
        processed = _preprocess_image_for_ocr(img)
        # Verify mode is grayscale (L) and upscaled
        self.assertEqual(processed.mode, "L")
        self.assertGreaterEqual(processed.size[0], 200)

    def test_clean_ocr_text(self):
        raw = "This is a secu-\n rity policy with    extra  \n\n\n\n lines."
        cleaned = _clean_ocr_text(raw)
        self.assertIn("security", cleaned)
        self.assertNotIn("\n\n\n", cleaned)

    @patch('app.ingestion.extractor.settings')
    @patch('google.genai.Client')
    def test_gemini_vision_ocr_fallback(self, mock_client_cls, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-api-key"
        mock_settings.DATA_RESIDENCY_MODE = "off"
        mock_settings.LLM_MODE = "cloud"
        mock_settings.LLM_CLOUD_MODEL = "gemini-1.5-flash"

        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Transcribed text from Gemini Vision OCR"
        mock_instance.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_instance

        text = _gemini_vision_ocr(b"dummy png bytes", "image/png")
        self.assertEqual(text, "Transcribed text from Gemini Vision OCR")

    @patch('app.ingestion.extractor.settings')
    @patch('google.genai.Client')
    def test_gemini_vision_ocr_blocked_in_strict_mode(self, mock_client_cls, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-api-key"
        mock_settings.DATA_RESIDENCY_MODE = "strict"
        mock_settings.LLM_MODE = "cloud"

        text = _gemini_vision_ocr(b"dummy png bytes", "image/png")
        self.assertIsNone(text)
        mock_client_cls.assert_not_called()

    @patch('app.ingestion.extractor.settings')
    @patch('google.genai.Client')
    def test_gemini_vision_ocr_blocked_in_local_only_mode(self, mock_client_cls, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-api-key"
        mock_settings.DATA_RESIDENCY_MODE = "off"
        mock_settings.LLM_MODE = "local-only"

        text = _gemini_vision_ocr(b"dummy png bytes", "image/png")
        self.assertIsNone(text)
        mock_client_cls.assert_not_called()

    @patch('app.ingestion.extractor.settings')
    @patch('google.genai.Client')
    def test_gemini_vision_ocr_blocked_in_self_hosted_mode(self, mock_client_cls, mock_settings):
        mock_settings.GEMINI_API_KEY = "test-api-key"
        mock_settings.DATA_RESIDENCY_MODE = "off"
        mock_settings.LLM_MODE = "self-hosted"

        text = _gemini_vision_ocr(b"dummy png bytes", "image/png")
        self.assertIsNone(text)
        mock_client_cls.assert_not_called()

    def test_extract_text_from_bytes_plaintext(self):
        text = extract_text_from_bytes(b"Sample plain text file", "notes.txt")
        self.assertEqual(text, "Sample plain text file")

if __name__ == "__main__":
    unittest.main()
