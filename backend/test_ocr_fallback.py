import unittest
from unittest.mock import MagicMock, patch
from app.ingestion.extractor import _ocr_pdf_page, _extract_pdf_pages

class TestOCRFallback(unittest.TestCase):
    @patch('pytesseract.image_to_string')
    def test_ocr_pdf_page_success(self, mock_image_to_string):
        # Set up mock pytesseract return value
        mock_image_to_string.return_value = "Sample OCR Extracted Compliance Policy Text"

        # Create a mock fitz page
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b'\xff' * 30000 # Dummy RGB pixels
        mock_page.get_pixmap.return_value = mock_pixmap

        # Run the function
        result = _ocr_pdf_page(mock_page)

        # Assertions
        self.assertEqual(result, "Sample OCR Extracted Compliance Policy Text")
        mock_image_to_string.assert_called_once()

    @patch('app.ingestion.extractor._ocr_pdf_page')
    @patch('fitz.open')
    def test_extract_pdf_pages_triggers_ocr(self, mock_fitz_open, mock_ocr_pdf_page):
        # Set up fitz document mock
        mock_doc = MagicMock()
        mock_page = MagicMock()
        
        # Scenario: page.get_text returns almost nothing (triggering OCR)
        mock_page.get_text.return_value = "Short"
        mock_doc.__len__.return_value = 1
        mock_doc.load_page.return_value = mock_page
        mock_fitz_open.return_value = mock_doc

        # Set up OCR mock
        mock_ocr_pdf_page.return_value = "This is a full page of text extracted using OCR fallback."

        # Run extraction
        pages = _extract_pdf_pages(b"%PDF-1.4 dummy bytes")

        # Verify
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].page_number, 1)
        self.assertEqual(pages[0].raw_text, "This is a full page of text extracted using OCR fallback.")
        self.assertTrue(pages[0].was_ocr_applied)
        mock_ocr_pdf_page.assert_called_once_with(mock_page)

if __name__ == "__main__":
    unittest.main()
