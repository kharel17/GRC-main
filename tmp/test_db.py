import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_conn():
    uri = "postgresql+asyncpg://postgres.htgojajcceunavgchrgc:VVGHSBUjYyvYWuhF@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?ssl=require"
    engine = create_async_engine(uri)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("Connection successful!")
    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_conn())
