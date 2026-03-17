
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URI")

async def fix_db():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        print("Restoring alembic_version to 07390fbae0fd...")
        await conn.execute(text("DELETE FROM alembic_version;"))
        await conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('07390fbae0fd');"))
        print("Done.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_db())
