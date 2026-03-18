import asyncio
from app.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT * FROM organizations LIMIT 0"))
        print(f"Organizations columns: {list(res.keys())}")
        
        res = await conn.execute(text("SELECT * FROM tickets LIMIT 0"))
        print(f"Tickets columns: {list(res.keys())}")

if __name__ == "__main__":
    asyncio.run(check())
