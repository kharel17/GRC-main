"""
End-to-end verification script for document ingestion pipeline.
"""
import asyncio
import os
import uuid
from fpdf import FPDF

from app.database import SessionLocal
from app import models
from app.ingestion.pipeline import process_document_job
from app.ingestion.job_queue import get_job_status, init_job_record
from app.ingestion.extractor import extract_pages_from_bytes
from app.ingestion.chunker import chunk_document, estimate_tokens

def generate_sample_pdf() -> bytes:
    """Generate a 15-page sample compliance PDF with sections and control references."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    sections = [
        ("Information Security Policy", "5.1 Policies for Information Security", "The organization shall define and approve information security policies. All personnel must comply with access guidelines, asset management rules, and password security standard operating procedures."),
        ("Human Resource Security", "6.1 Screening and Terms of Employment", "Background verification checks on all candidates for employment shall be carried out in accordance with relevant laws, regulations, and ethics. Confidentiality agreements must be signed prior to system access."),
        ("Asset Management", "5.9 Inventory of Assets and Acceptable Use", "Identified assets associated with information and information processing facilities shall be identified, inventoried, and maintained in an accurate inventory list with assigned ownership."),
        ("Access Control", "5.15 Access Control and Privilege Management", "Access to information and application system functions shall be restricted in accordance with the Access Control Policy. Multi-factor authentication (MFA) is required for all administrative access."),
        ("Cryptography", "8.24 Use of Cryptography and Key Management", "Rules for the effective use of cryptography, including cryptographic key management, shall be defined and implemented. AES-256 encryption is required for data at rest and TLS 1.3 for data in transit."),
        ("Physical Security", "7.1 Physical Security Perimeter", "Security perimeters shall be defined and used to protect areas that contain either information or other associated assets. Entry points must be monitored via CCTV and badge readers."),
        ("Operations Security", "8.15 Logging and Monitoring", "Event logs recording user activities, exceptions, faults, and information security events shall be produced, kept, and regularly reviewed to prevent unauthorized access."),
        ("Communications Security", "8.20 Network Security and Segmentation", "Networks shall be managed and controlled to protect information in systems and applications. Firewalls and VLAN segmentation must be implemented."),
        ("System Acquisition", "8.25 Secure Development Lifecycle", "Rules for secure development of software and systems shall be established and applied. Static and dynamic security analysis (SAST/DAST) must occur prior to deployment."),
        ("Supplier Relationships", "5.19 Information Security in Supplier Relationships", "Requirements for mitigating information security risks associated with the use of supplier products or services shall be agreed upon and documented in binding contracts."),
        ("Information Security Incident Management", "5.24 Information Security Incident Management Planning", "The organization shall plan and prepare for managing information security incidents by defining, establishing, and communicating processes, roles, and responsibilities."),
        ("Business Continuity", "5.29 Information Security During Disruption", "The organization shall plan how to maintain information security at an acceptable level during adverse situations, including disaster recovery drills."),
        ("Compliance", "5.36 Compliance with Policies and Standards", "Compliance with the organization's information security policies, rules, and standards shall be regularly reviewed through internal audits and third-party assessments."),
        ("Threat Intelligence", "5.7 Threat Intelligence Collection", "Information relating to information security threats shall be collected and analyzed to produce threat intelligence that feeds into vulnerability management."),
        ("Data Leakage Prevention", "8.12 Data Leakage Prevention (DLP)", "Data leakage prevention measures shall be applied to systems, networks, and end-user devices that process, store, or transmit sensitive information.")
    ]

    for title, heading, body in sections:
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=16)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 8, heading, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        # Repeat body text to create realistic page volume
        full_body = (body + " ") * 10
        pdf.multi_cell(0, 6, full_body)

    return bytes(pdf.output())

from sqlalchemy import select

async def run_test():
    print("--- STEP 1: Generating 15-page sample compliance PDF ---")
    pdf_bytes = generate_sample_pdf()
    print(f"Generated PDF size: {len(pdf_bytes)} bytes")

    print("\n--- STEP 2: Testing Extractor & Token Chunker ---")
    pages = extract_pages_from_bytes(pdf_bytes, "sample_isms_policy.pdf")
    print(f"Extracted pages: {len(pages)}")
    for p in pages[:3]:
        print(f"  Page {p.page_number}: {len(p.raw_text)} chars, OCR={p.was_ocr_applied}")

    chunks = chunk_document(pages, document_id="test-doc-123", org_id="test-org-456", target_token_size=400)
    print(f"Total chunks created: {len(chunks)}")
    for c in chunks[:3]:
        print(f"  Chunk #{c.chunk_index} (Page {c.page_number}, Heading: '{c.section_heading}'): {c.token_count} tokens")
        print(f"    Sample text snippet: {c.text[:80]}...")

    print("\n--- STEP 3: Testing Database Job State & Async Pipeline ---")
    async with SessionLocal() as db:
        # Find test org or first org
        result = await db.execute(select(models.Organization))
        org = result.scalars().first()
        if not org:
            print("No org found in DB, skipping DB job record creation")
            return
        
        # Find test user
        user_res = await db.execute(select(models.User).where(models.User.organization_id == org.id))
        user = user_res.scalars().first()
        if not user:
            print("No user found in DB, skipping DB test")
            return

        doc_analysis = models.DocumentAnalysis(
            organization_id=org.id,
            file_name="sample_isms_policy.pdf",
            file_size=len(pdf_bytes),
            file_type="pdf",
            uploaded_by=user.id,
            status=models.DocumentAnalysisStatus.processing,
        )
        db.add(doc_analysis)
        await db.flush()
        
        await init_job_record(db, doc_analysis)
        await db.commit()
        analysis_id = doc_analysis.id
        print(f"Created DocumentAnalysis record ID: {analysis_id}")

        # Check initial status
        status_before = await get_job_status(db, analysis_id)
        print(f"Initial job status: step={status_before.step}, progress={status_before.progress}%")

    print("\n--- STEP 4: Executing process_document_job pipeline ---")
    await process_document_job(
        analysis_id=analysis_id,
        file_bytes=pdf_bytes,
        filename="sample_isms_policy.pdf",
        organization_id=org.id
    )

    print("\n--- STEP 5: Verifying final job status in DB ---")
    async with SessionLocal() as db:
        status_after = await get_job_status(db, analysis_id)
        print(f"Final job status: status={status_after.status}, step={status_after.step}, progress={status_after.progress}%, chunk_count={status_after.chunk_count}")
        print("Success! Ingestion pipeline completed end-to-end.")

if __name__ == "__main__":
    asyncio.run(run_test())
