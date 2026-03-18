import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    uri = os.getenv("SQLALCHEMY_DATABASE_URI")
    engine = create_async_engine(uri)
    async with engine.connect() as conn:
        try:
            res = await conn.execute(text("SELECT * FROM organizations LIMIT 0"))
            print(f"Organizations: {list(res.keys())}")
            
            res = await conn.execute(text("SELECT * FROM tickets LIMIT 0"))
            print(f"Tickets: {list(res.keys())}")
            
            res = await conn.execute(text("SELECT * FROM risks LIMIT 0"))
            print(f"Risks: {list(res.keys())}")
        except Exception as e:
            print(f"Error: {e}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
