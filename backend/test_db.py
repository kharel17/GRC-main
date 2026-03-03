import asyncio
import asyncpg
import sys
import os

# Load .env file manually for standalone script
from dotenv import load_dotenv
load_dotenv()

async def run():
    try:
        conn = await asyncpg.connect(
            user=os.getenv('POSTGRES_USER', 'grc_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'grc_secret'),
            database=os.getenv('POSTGRES_DB', 'grc_db'),
            host=os.getenv('POSTGRES_SERVER', '127.0.0.1'),
            port=int(os.getenv('POSTGRES_PORT', '5432'))
        )
        print("[OK] Successfully connected to the database!")
        
        # Quick sanity check: list tables
        tables = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
        print(f"[INFO] Found {len(tables)} tables:")
        for t in tables:
            print(f"   - {t['tablename']}")
        
        await conn.close()
    except Exception as e:
        print(f"[ERROR] Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run())
