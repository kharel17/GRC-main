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
            res = await conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'userrole'"))
            labels = [v[0] for v in res.fetchall()]
            print(f"UserRole Enum labels: {labels}")
        except Exception as e:
            print(f"Error: {e}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
