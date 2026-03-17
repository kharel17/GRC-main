import asyncio
from app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    print('URI', settings.SQLALCHEMY_DATABASE_URI)
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, connect_args={'statement_cache_size': 0})
    async with engine.connect() as conn:
        from sqlalchemy import text
        result = await conn.execute(text('select 1'))
        print('result', result.scalar())
    await engine.dispose()

asyncio.run(main())
