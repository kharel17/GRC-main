import asyncio
from app.services.vector_store import vector_store
from app.config import settings

async def main():
    await vector_store.initialize_collections()
    # Query PostgreSQL document_analyses
    from app.database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as db:
        res = await db.execute(text("SELECT id, file_name, status, organization_id FROM document_analyses"))
        print("Document analyses in DB:")
        for row in res.all():
            print(f"- ID: {row[0]}, Name: {row[1]}, Status: {row[2]}, Org: {row[3]}")

        
    c = await vector_store._client.count(settings.QDRANT_COLLECTION_ISO_CONTROLS)
    print("Count in ISO controls:", c)

if __name__ == "__main__":
    asyncio.run(main())
