
import asyncio
import sys
import os
import uuid
sys.path.append(os.getcwd())

async def seed():
    try:
        from app import models
        from app.database import SessionLocal
        from sqlalchemy import select
    except ImportError as e:
        print(f"Import error: {e}")
        return

    categories = [
        {"id": "00000000-0000-0000-0000-000000000001", "name": "Operational", "description": "Day-to-day operational risks", "color": "#3b82f6"},
        {"id": "00000000-0000-0000-0000-000000000002", "name": "Financial", "description": "Financial stability risks", "color": "#10b981"},
        {"id": "00000000-0000-0000-0000-000000000003", "name": "Compliance", "description": "Regulatory compliance risks", "color": "#f59e0b"},
        {"id": "00000000-0000-0000-0000-000000000004", "name": "Strategic", "description": "Long-term strategy risks", "color": "#8b5cf6"},
        {"id": "00000000-0000-0000-0000-000000000005", "name": "Reputational", "description": "Brand and reputation risks", "color": "#ef4444"},
        {"id": "00000000-0000-0000-0000-000000000006", "name": "Technology", "description": "IT and cybersecurity risks", "color": "#06b6d4"},
    ]
    
    async with SessionLocal() as db:
        for cat_data in categories:
            cat_id = uuid.UUID(cat_data["id"])
            stmt = select(models.RiskCategory).where(models.RiskCategory.name == cat_data["name"])
            res = await db.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                cat = models.RiskCategory(
                    id=cat_id,
                    name=cat_data["name"],
                    description=cat_data["description"],
                    color=cat_data["color"]
                )
                db.add(cat)
                print(f"Added category: {cat_data['name']}")
            else:
                if existing.id != cat_id:
                    print(f"ID mismatch for {cat_data['name']}, but leaving it to avoid constraint errors if linked.")
        
        await db.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed())
