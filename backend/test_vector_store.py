"""
Phase 2 Verification Script — Qdrant Vector Store.
Tests: collection creation, ISO control upsert, document chunk upsert, dense search.
"""
import asyncio
import sys
import numpy as np
from fpdf import FPDF

# ── Imports ────────────────────────────────────────────────────────────────────
from app.services.ai_service import ai_service
from app.services.vector_store import vector_store
from app.ingestion.extractor import extract_pages_from_bytes
from app.ingestion.chunker import chunk_document


def generate_sample_pdf() -> bytes:
    """Tiny 3-page compliance PDF for testing."""
    pdf = FPDF()
    for title, body in [
        ("Access Control Policy", "5.15 Access control shall restrict access to systems. Multi-factor authentication is required."),
        ("Cryptography Policy",   "8.24 AES-256 encryption required for data at rest. TLS 1.3 for data in transit."),
        ("Incident Management",  "5.24 Security incidents must be reported within 4 hours. An incident response team is activated."),
    ]:
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, (body + " ") * 30)
    return bytes(pdf.output())


async def run():
    errors = []

    print("=" * 60)
    print("Phase 2 Verification — Qdrant Vector Store")
    print("=" * 60)

    # ── Step 1: Connect to Qdrant ──────────────────────────────────────────────
    print("\n[1/5] Initializing Qdrant collections...")
    ok = await vector_store.initialize_collections()
    if not ok:
        print("  FAIL: Could not connect to Qdrant. Is 'docker compose up qdrant' running?")
        sys.exit(1)
    print(f"  OK: is_ready={vector_store.is_ready}")

    # ── Step 2: Load AI model for embeddings ───────────────────────────────────
    print("\n[2/5] Loading AI embedding model...")
    if not ai_service.is_ready:
        ai_service.initialize()
    print(f"  OK: ai_service.is_ready={ai_service.is_ready}")

    # ── Step 3: Upsert ISO controls ────────────────────────────────────────────
    print("\n[3/5] Upserting ISO 27001 controls into grc_iso_controls...")
    if ai_service._controls and ai_service._local_control_embeddings is not None:
        await vector_store.upsert_iso_controls(
            ai_service._controls,
            ai_service._local_control_embeddings
        )
        print(f"  OK: Upserted {len(ai_service._controls)} ISO controls")
    else:
        errors.append("ISO controls or embeddings not available in ai_service")
        print("  SKIP: ISO controls not loaded in ai_service")

    # ── Step 4: Upsert document chunks ─────────────────────────────────────────
    print("\n[4/5] Ingesting sample PDF and upserting chunks into grc_doc_chunks...")
    pdf_bytes = generate_sample_pdf()
    pages = extract_pages_from_bytes(pdf_bytes, "test_policy.pdf")
    chunks = chunk_document(
        pages=pages,
        document_id="test-doc-phase2",
        org_id="test-org-phase2",
        target_token_size=400,
    )
    print(f"  Extracted {len(pages)} pages, created {len(chunks)} chunks")

    chunk_texts = [c.text for c in chunks]
    embeddings = ai_service._embed_texts(chunk_texts)
    await vector_store.upsert_chunks(chunks, embeddings)
    print(f"  OK: Upserted {len(chunks)} chunks into grc_doc_chunks")

    # ── Step 5: Dense search ───────────────────────────────────────────────────
    print("\n[5/5] Running dense search...")

    from app.config import settings

    # Search against doc chunks (org-scoped)
    query_emb = ai_service._embed_texts(["access control multi-factor authentication"])[0]

    doc_hits = await vector_store.dense_search(
        query_vector=query_emb,
        collection_name=settings.QDRANT_COLLECTION_DOC_CHUNKS,
        top_k=3,
        org_id="test-org-phase2",
    )
    print(f"  Doc chunk search returned {len(doc_hits)} hits")
    for h in doc_hits:
        snippet = h["payload"].get("text", "")[:60].replace("\n", " ")
        print(f"    score={h['score']:.4f}  heading='{h['payload'].get('section_heading', '')}' | '{snippet}...'")
    if not doc_hits:
        errors.append("Doc chunk dense search returned 0 results")

    # Search against ISO controls
    ctrl_hits = await vector_store.dense_search(
        query_vector=query_emb,
        collection_name=settings.QDRANT_COLLECTION_ISO_CONTROLS,
        top_k=3,
    )
    print(f"  ISO control search returned {len(ctrl_hits)} hits")
    for h in ctrl_hits:
        print(f"    score={h['score']:.4f}  control='{h['payload'].get('annex', '')}' | '{h['payload'].get('title', '')}'")
    if not ctrl_hits:
        errors.append("ISO control dense search returned 0 results")

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if errors:
        print(f"PHASE 2 VERIFICATION FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("PHASE 2 VERIFICATION PASSED [OK]")
        print("  - Qdrant collections initialized")
        print(f"  - {len(ai_service._controls)} ISO controls indexed")
        print(f"  - {len(chunks)} document chunks indexed (org-scoped)")
        print("  - Dense search returning plausible results on both collections")


if __name__ == "__main__":
    asyncio.run(run())
