import asyncio
import logging
from sqlalchemy import text
from app.database import engine

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

async def check():
    async with engine.connect() as conn:
        print("CHECKING_START")
        try:
            res = await conn.execute(text("SELECT count(*) FROM organizations"))
            count = res.scalar()
            print(f"Organizations count: {count}")
        except Exception as e:
            print(f"Organizations check failed: {e}")
            
        try:
            res = await conn.execute(text("SELECT count(*) FROM assets"))
            count = res.scalar()
            print(f"Assets count: {count}")
        except Exception as e:
            print(f"Assets check failed: {e}")
        print("CHECKING_END")

if __name__ == "__main__":
    asyncio.run(check())
