import asyncio
from app.database import engine
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

async def check():
    async with engine.connect() as conn:
        print("Checking organizations table...")
        try:
            res = await conn.execute(text("SELECT id, name, ticket_settings FROM organizations LIMIT 1"))
            row = res.fetchone()
            print(f"Row data: {row}")
        except ProgrammingError as e:
            print(f"PROG ERROR: {e}")
        except Exception as e:
            print(f"OTHER ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(check())
