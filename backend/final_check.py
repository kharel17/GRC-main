
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres")

async def main():
    # Try to get URL from .env if not set
    if not os.getenv("DATABASE_URL"):
        try:
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("SQLALCHEMY_DATABASE_URI="):
                        global DATABASE_URL
                        DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except:
            pass

    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # 1. Total Risks
        res = await conn.execute(text("SELECT count(*) FROM risks"))
        print(f"Total Risks in DB: {res.scalar()}")
        
        # 2. Total Orgs
        res = await conn.execute(text("SELECT id, name FROM organizations"))
        print("\nAll Organizations:")
        for row in res.all():
            print(f"- {row[1]} ({row[0]})")
            
        # 3. Risks per Org
        res = await conn.execute(text("SELECT organization_id, count(*) FROM risks GROUP BY organization_id"))
        print("\nRisks by Org ID:")
        for row in res.all():
            print(f"- {row[0]}: {row[1]}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
