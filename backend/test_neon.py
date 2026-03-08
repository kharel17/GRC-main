import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def test_connection():
    print(f"Testing connection to: {settings.POSTGRES_SERVER}")
    print(f"Port: {settings.POSTGRES_PORT}")
    print(f"Database: {settings.POSTGRES_DB}")
    print(f"User: {settings.POSTGRES_USER}")
    print(f"Full URI: {settings.SQLALCHEMY_DATABASE_URI[:50]}...")
    
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    try:
        async with engine.connect() as conn:
            print("[OK] Successfully connected to Supabase database!")
            await conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())
