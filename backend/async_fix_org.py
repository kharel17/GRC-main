
import asyncio
import os
import asyncpg

async def main():
    # Try to find the DB URL from .env
    db_url = "postgresql://postgres:postgres@localhost:5432/postgres"
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("SQLALCHEMY_DATABASE_URI="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    # Convert to asyncpg style if needed
                    val = val.replace("postgresql+asyncpg://", "postgresql://")
                    if val:
                        db_url = val
                    break

    try:
        conn = await asyncpg.connect(db_url)
        print(f"Connected to {db_url}")
        
        # 1. Find orgs with risks
        rows = await conn.fetch("SELECT organization_id, count(*) FROM risks GROUP BY organization_id")
        print("Risk counts by Org ID:")
        for row in rows:
            org_id = row['organization_id']
            count = row['count']
            org_name = await conn.fetchval("SELECT name FROM organizations WHERE id = $1", org_id)
            print(f"- {org_name} ({org_id}): {count} risks")
            
            if org_name and org_name != "Platform Team":
                print(f"RECOMMENDATION: Move user back to {org_name}")
                # Update the user
                await conn.execute("UPDATE users SET organization_id = $1, organization_name = $2 WHERE email = 'bcolorc17@gmail.com'", org_id, org_name)
                print(f"SUCCESS: User bcolorc17@gmail.com moved back to {org_name}")
        
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
