import asyncio
import asyncpg
import sys

async def run():
    try:
        conn = await asyncpg.connect(user='postgres', password='postgres',
                                     database='grc_platform', host='127.0.0.1')
        print("Successfully connected to the database!")
        await conn.close()
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run())
