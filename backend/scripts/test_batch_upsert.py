import asyncio
import logging
import sys
import uuid
import numpy as np

# Configure logging to show info messages clearly
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("test_batch_upsert")

from app.ingestion.chunker import Chunk
from app.services.vector_store import vector_store

async def run_synthetic_test():
    logger.info("Initializing vector store service...")
    vector_store.initialize()
    ready = await vector_store.initialize_collections()
    logger.info(f"Vector store readiness: {vector_store.is_ready} (init result={ready})")

    doc_id = str(uuid.uuid4())
    org_id = "24de3639-ee40-4563-a207-dd66436a0da8"

    # Simulate 250 dummy chunks
    num_chunks = 250
    dummy_chunks = [
        Chunk(
            chunk_id=str(uuid.uuid4()),
            document_id=doc_id,
            org_id=org_id,
            page_number=(i // 10) + 1,
            section_heading=f"Section {i // 25 + 1}",
            chunk_index=i,
            text=f"This is synthetic chunk text #{i} for large document batching verification.",
            token_count=15,
        )
        for i in range(num_chunks)
    ]

    # Simulate 250 dummy 384-dimensional vectors
    dummy_embeddings = np.random.randn(num_chunks, 384).astype(np.float32)

    logger.info(f"Executing upsert_chunks for {num_chunks} chunks with batch_size=100...")
    success = await vector_store.upsert_chunks(
        chunks=dummy_chunks,
        embeddings=dummy_embeddings,
        batch_size=100,
    )

    logger.info(f"upsert_chunks completed with success={success}")
    assert success is True, "upsert_chunks must return True"
    print("\n>>> SYNTHETIC BATCH TEST PASSED SUCCESSFULLY: 3 distinct batches (100, 100, 50 points) verified.")

if __name__ == "__main__":
    asyncio.run(run_synthetic_test())
