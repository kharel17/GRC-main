
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import sys
import os

sys.path.append(os.getcwd())
from app.config import settings

async def check_user():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        res = await db.execute(text("SELECT id, email, organization_id, organization_name, role FROM users WHERE email = 'bcolorc17@gmail.com'"))
        user = res.one_or_none()
        if user:
            print(f"User in DB: {user}")
        else:
            print("User not found in DB")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_user())
