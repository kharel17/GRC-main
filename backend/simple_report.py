
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # 1. Risks by Org
        res = await conn.execute(text("SELECT organization_id, count(*) FROM risks GROUP BY organization_id"))
        rows = res.all()
        for row in rows:
            org_id = row[0]
            count = row[1]
            if org_id:
                name_res = await conn.execute(text("SELECT name FROM organizations WHERE id = :id"), {"id": org_id})
                name = name_res.scalar()
                print(f"Org: {name} (ID: {org_id}) - Risks: {count}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
