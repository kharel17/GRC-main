
import asyncio
import os
import asyncpg

async def main():
    db_url = "postgresql://postgres:postgres@localhost:5432/postgres"
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.startswith("SQLALCHEMY_DATABASE_URI="):
                    db_url = line.split("=", 1)[1].strip().strip('"').strip("'").replace("postgresql+asyncpg://", "postgresql://")
                    break

    with open("db_results_final.txt", "w") as f_out:
        try:
            # DISABLE statement cache for pgbouncer compatibility
            conn = await asyncpg.connect(db_url, statement_cache_size=0)
            f_out.write(f"Connected to {db_url}\n")
            
            # Find the org with risks
            rows = await conn.fetch("SELECT organization_id, count(*) as c FROM risks GROUP BY organization_id ORDER BY c DESC")
            f_out.write(f"Risk counts by Org: {rows}\n")
            
            for row in rows:
                org_id = row['organization_id']
                if not org_id: continue
                
                org_name = await conn.fetchval("SELECT name FROM organizations WHERE id = $1", org_id)
                f_out.write(f"Org Candidate: {org_name} ({org_id})\n")
                
                if org_name and org_name != "Platform Team":
                    f_out.write(f"UPDATING USER bcolorc17@gmail.com to {org_name}\n")
                    # Use a direct query without a prepared statement name if possible (asyncpg handle this with statement_cache_size=0)
                    await conn.execute("UPDATE users SET organization_id = $1, organization_name = $2 WHERE email = 'bcolorc17@gmail.com'", org_id, org_name)
                    f_out.write("USER UPDATED SUCCESSFULLY\n")
                    
                    # Also fix invitation status
                    await conn.execute("UPDATE users SET invitation_status = 'active' WHERE email = 'bcolorc17@gmail.com'")
                    break
            
            await conn.close()
            f_out.write("DONE\n")
        except Exception as e:
            f_out.write(f"ERROR: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
