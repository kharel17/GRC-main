"""
Diagnostic + cleanup script:
1. Show how many points have empty payloads in grc_doc_chunks
2. Delete all empty-payload points (corrupted / ghosted ingestion artifacts)
3. Show final count
"""
import asyncio
from app.services.vector_store import vector_store
from app.config import settings
from qdrant_client import models as qmodels


async def main():
    await vector_store.initialize_collections()
    client = vector_store._client

    # -- 1. Count total
    total = await client.count(settings.QDRANT_COLLECTION_DOC_CHUNKS)
    print(f"[Before] Total points in grc_doc_chunks: {total.count}")

    # -- 2. Scroll through all points and find those with empty payload or no 'text' field
    empty_ids = []
    offset = None
    while True:
        res, next_offset = await client.scroll(
            collection_name=settings.QDRANT_COLLECTION_DOC_CHUNKS,
            limit=250,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in res:
            payload = point.payload or {}
            if not payload or not payload.get("text"):
                empty_ids.append(point.id)
        if next_offset is None:
            break
        offset = next_offset

    print(f"[Diagnosis] Points with empty/missing text payload: {len(empty_ids)}")

    # -- 3. Delete all empty-payload points
    if empty_ids:
        await client.delete(
            collection_name=settings.QDRANT_COLLECTION_DOC_CHUNKS,
            points_selector=qmodels.PointIdsList(points=empty_ids),
        )
        print(f"[Cleanup] Deleted {len(empty_ids)} corrupted points.")

    # -- 4. Count after cleanup
    total_after = await client.count(settings.QDRANT_COLLECTION_DOC_CHUNKS)
    print(f"[After] Total points in grc_doc_chunks: {total_after.count}")


if __name__ == "__main__":
    asyncio.run(main())
