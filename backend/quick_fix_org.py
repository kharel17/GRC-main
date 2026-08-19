
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Default for local dev if .env is missing
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

# Try to find the DB URL from .env
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("SQLALCHEMY_DATABASE_URI="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    DATABASE_URL = val
                break

async def restore():
    print(f"Connecting to: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # 1. Find the organization that has the risks
        # This is the organization we want to move the user back to
        res = await conn.execute(text("SELECT organization_id, count(*) as c FROM risks GROUP BY organization_id ORDER BY c DESC LIMIT 1"))
        row = res.fetchone()
        
        if not row or not row[0]:
            print("No risk data found in any organization.")
            # Let's see all organizations
            orgs_res = await conn.execute(text("SELECT id, name FROM organizations"))
            print("Available Organizations:")
            for o in orgs_res.all():
                print(f"- {o[1]} ({o[0]})")
            return

        target_org_id = row[0]
        
        # 2. Get the name of that organization
        name_res = await conn.execute(text("SELECT name FROM organizations WHERE id = :id"), {"id": target_org_id})
        target_org_name = name_res.scalar() or "Unknown Org"
        
        print(f"Found target organization: {target_org_name} ({target_org_id}) with {row[1]} risks.")
        
        # 3. Update the user record
        # We need to update bcolorc17@gmail.com
        update_stmt = text("UPDATE users SET organization_id = :org_id, organization_name = :org_name WHERE email = 'bcolorc17@gmail.com'")
        await conn.execute(update_stmt, {"org_id": target_org_id, "org_name": target_org_name})
        
        # 4. ALSO update the organization's onboarding status to True just in case
        await conn.execute(text("UPDATE organizations SET onboarding_completed = TRUE WHERE id = :id"), {"id": target_org_id})
        
        await conn.commit()
        print(f"SUCCESS: User bcolorc17@gmail.com restored to {target_org_name}.")

    await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(restore())
    except Exception as e:
        print(f"Error during restoration: {e}")
