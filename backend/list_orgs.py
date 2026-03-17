
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
import os

sys.path.append(os.getcwd())
from app import models
from app.config import settings

async def list_orgs():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        result = await db.execute(select(models.Organization))
        orgs = result.scalars().all()
        print("Organizations in DB:")
        for o in orgs:
            print(f"- {o.name} ({o.id})")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(list_orgs())
