import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys

# The user explicitly gave the connection string
URL = "postgresql+asyncpg://postgres.htgojajcceunavgchrgc:VVGHSBUjYyvYWuhF@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?ssl=require"

async def fix_alembic():
    engine = create_async_engine(URL)
    
    async with engine.begin() as conn:
        print("Checking current alembic_version...")
        result = await conn.execute(text("SELECT * FROM alembic_version"))
        rows = result.fetchall()
        print(f"Current rows: {rows}")
        
        print("Updating alembic_version to point to 3a7c58921e5b...")
        await conn.execute(text("UPDATE alembic_version SET version_num = '3a7c58921e5b'"))
        
        print("Verifying update...")
        result = await conn.execute(text("SELECT * FROM alembic_version"))
        new_rows = result.fetchall()
        print(f"New rows: {new_rows}")
        
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_alembic())
