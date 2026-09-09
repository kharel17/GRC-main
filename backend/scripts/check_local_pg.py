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
    await test_conn("postgresql+asyncpg://postgres:postgres@localhost:5432/postgres", "Localhost 5432 postgres/postgres")
    await test_conn("postgresql+asyncpg://grc_user:grc_secret@localhost:5432/grc_db", "Localhost 5432 grc_user/grc_db")
    await test_conn("postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/postgres", "127.0.0.1 5432 postgres/postgres")
    await test_conn("postgresql+asyncpg://postgres:password@localhost:5432/postgres", "Localhost 5432 postgres/password")

if __name__ == "__main__":
    asyncio.run(main())
