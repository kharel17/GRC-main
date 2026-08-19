from fpdf import FPDF
from typing import List, Dict, Any
import datetime

class PDFReport(FPDF):
    def __init__(self, title: str, generated_by: str):
        super().__init__()
        self.report_title = title
        self.generated_by = generated_by
        self.generated_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Header banner
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 41, 59) # Slate 800
        self.cell(0, 10, self.report_title, ln=False, align="L")
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(59, 130, 246) # Blue 500
        self.cell(0, 10, "GRC Platform", ln=True, align="R")
        
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 5, f"Generated: {self.generated_date} | By: {self.generated_by}", ln=True, align="L")
        self.set_draw_color(226, 232, 240)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}} — GRC Platform Confidential Report", align="C")

def build_pdf_response(title: str, generated_by: str, headers: List[str], rows: List[List[Any]], col_widths: List[int] = None) -> bytes:
    pdf = PDFReport(title, generated_by)
    pdf.alias_nb_pages()
    pdf.add_page()
    
    if not col_widths:
        usable_w = 190
        col_widths = [usable_w // len(headers)] * len(headers)

    # Table Header
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(71, 85, 105)
    pdf.set_font("Helvetica", "B", 9)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, str(h).upper(), border=1, fill=True, align="C")
    pdf.ln()

    # Table Rows
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(51, 65, 85)
    
    fill = False
    for row in rows:
        pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
        for i, val in enumerate(row):
            # Truncate text if too long for cell
            val_str = str(val) if val is not None else "—"
            if len(val_str) > 35:
                val_str = val_str[:32] + "..."
            pdf.cell(col_widths[i], 7, val_str, border=1, fill=fill, align="L")
        pdf.ln()
        fill = not fill

    return bytes(pdf.output())
