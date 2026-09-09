import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test_conn(url: str, label: str):
    print(f"Testing {label}...")
    try:
        engine = create_async_engine(url, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT current_user, current_database()"))
            row = res.fetchone()
            print(f"SUCCESS {label}: User={row[0]}, DB={row[1]}")
            return True
    except Exception as exc:
        print(f"FAILED {label}: {exc}")
        return False

async def main():
    # 1. Test Direct Connection (port 5432)
    url_direct = "postgresql+asyncpg://postgres:VVGHSBUjYyvYWuhF@db.htgojajcceunavgchrgc.supabase.co:5432/postgres?ssl=require"
    # 2. Test Transaction Pooler (port 6543)
    url_pooler = "postgresql+asyncpg://postgres.htgojajcceunavgchrgc:VVGHSBUjYyvYWuhF@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?ssl=require"
    # 3. Test Session Pooler (port 5432)
    url_session = "postgresql+asyncpg://postgres.htgojajcceunavgchrgc:VVGHSBUjYyvYWuhF@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres?ssl=require"

    await test_conn(url_direct, "Direct 5432")
    await test_conn(url_pooler, "Pooler 6543")
    await test_conn(url_session, "Pooler 5432")

if __name__ == "__main__":
    asyncio.run(main())
