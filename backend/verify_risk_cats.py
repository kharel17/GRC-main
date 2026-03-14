
import asyncio
import sys
import os
sys.path.append(os.getcwd())

async def check():
    from app import models
    from app.database import SessionLocal
    from sqlalchemy import select
    
    async with SessionLocal() as db:
        res = await db.execute(select(models.RiskCategory))
        cats = res.scalars().all()
        print(f"CATEGORIES_IN_DB: {[{\"id\": str(c.id), \"name\": c.name} for c in cats]}")

if __name__ == "__main__":
    asyncio.run(check())
