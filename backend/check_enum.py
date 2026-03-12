import asyncio
from sqlalchemy import text
from app.database import engine

async def check_enum():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid WHERE pg_type.typname = 'assettype'"))
        labels = [row[0] for row in result.all()]
        print(f"AssetType labels: {labels}")

if __name__ == "__main__":
    asyncio.run(check_enum())
