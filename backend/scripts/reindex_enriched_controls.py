import asyncio, json, logging, pathlib, sys
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reindex")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.services.ai_service import ai_service
from app.services.vector_store import vector_store
async def main():
    if not ai_service.is_ready:
        ai_service.initialize()
    vector_store.initialize()
    ok = await vector_store.initialize_collections()
    if not ok:
        log.error("Qdrant unreachable")
        sys.exit(1)
    with open("data/iso27001-controls-enriched.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    controls = data["controls"]
    log.info(f"Embedding {len(controls)} controls...")
    embeddings = ai_service._embed_texts([c["text"] for c in controls])
    log.info("Upserting into grc_iso_controls...")
    await vector_store.upsert_iso_controls(controls, embeddings)
    log.info("Re-index complete!")
if __name__ == "__main__":
    asyncio.run(main())
