
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Try to find the DB URL
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("SQLALCHEMY_DATABASE_URI="):
                DATABASE_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # 1. Find the Org with the risks
        res = await conn.execute(text("SELECT organization_id, count(*) as count FROM risks GROUP BY organization_id ORDER BY count DESC LIMIT 1"))
        row = res.fetchone()
        
        if not row or not row[0]:
            print("No organization found with risks.")
            # Fallback to finding any org that isn't Platform Team
            res = await conn.execute(text("SELECT id, name FROM organizations WHERE name != 'Platform Team' LIMIT 1"))
            row = res.fetchone()
            if not row:
                print("No non-platform organizations found.")
                return
            target_org_id = row[0]
            target_org_name = row[1]
        else:
            target_org_id = row[0]
            res = await conn.execute(text("SELECT name FROM organizations WHERE id = :id"), {"id": target_org_id})
            target_org_name = res.scalar() or "Unknown"

        print(f"Target Org: {target_org_name} ({target_org_id})")
        
        # 2. Update the user bcolorc17@gmail.com
        update_res = await conn.execute(
            text("UPDATE users SET organization_id = :org_id, organization_name = :org_name WHERE email = 'bcolorc17@gmail.com'"),
            {"org_id": target_org_id, "org_name": target_org_name}
        )
        await conn.commit()
        print(f"Updated user bcolorc17@gmail.com to organization {target_org_name}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
