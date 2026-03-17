
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("SQLALCHEMY_DATABASE_URI="):
                DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

async def check():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        print("Tables in database:")
        for row in res.all():
            print(f"- {row[0]}")
            
        # Check risks count directly
        try:
            res = await conn.execute(text("SELECT count(*) FROM risks"))
            print(f"Risks count: {res.scalar()}")
        except Exception as e:
            print(f"Error checking risks: {e}")
            
        # Check organizations
        try:
            res = await conn.execute(text("SELECT id, name FROM organizations"))
            print("Organizations:")
            for row in res.all():
                print(f"- {row[1]} ({row[0]})")
        except Exception as e:
            print(f"Error checking organizations: {e}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
