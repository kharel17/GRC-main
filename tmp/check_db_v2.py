import asyncio
import traceback
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_columns():
    uri = "postgresql+asyncpg://postgres.htgojajcceunavgchrgc:VVGHSBUjYyvYWuhF@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?ssl=require"
    engine = create_async_engine(uri)
    try:
        async with engine.connect() as conn:
            print("Checking users table...")
            result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"))
            columns = [row[0] for row in result]
            print(f"Users columns: {columns}")
            
            print("Checking organizations table...")
            result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'organizations'"))
            columns = [row[0] for row in result]
            print(f"Organizations columns: {columns}")
    except Exception:
        print("Detailed error:")
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_columns())
