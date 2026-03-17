
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import sys
import os

sys.path.append(os.getcwd())
from app.config import settings

async def find_orgs():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as db:
        # Use raw SQL to avoid model mapping issues for this quick check
        result = await db.execute(text("SELECT organization_id, count(*) FROM risks GROUP BY organization_id"))
        rows = result.all()
        print("Risk counts by Org ID:")
        for row in rows:
            print(f"- Org ID: {row[0]}, Count: {row[1]}")
            
            if row[0]:
                org_name_res = await db.execute(text("SELECT name FROM organizations WHERE id = :id"), {"id": row[0]})
                name = org_name_res.scalar()
                print(f"  Org Name: {name}")
                
        # Also list all orgs
        all_orgs = await db.execute(text("SELECT id, name FROM organizations"))
        print("\nAll Organizations:")
        for o in all_orgs.all():
            print(f"- {o[1]} ({o[0]})")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(find_orgs())
