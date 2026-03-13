import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_columns():
    uri = "postgresql+asyncpg://postgres.htgojajcceunavgchrgc:VVGHSBUjYyvYWuhF@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?ssl=require"
    engine = create_async_engine(uri)
    try:
        async with engine.connect() as conn:
            res_users = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"))
            cols_users = [row[0] for row in res_users]
            
            res_orgs = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'organizations'"))
            cols_orgs = [row[0] for row in res_orgs]
            
            with open("tmp/cols.txt", "w") as f:
                f.write(f"USERS_COLS:{','.join(cols_users)}\n")
                f.write(f"ORGS_COLS:{','.join(cols_orgs)}\n")
        print("Done writing to tmp/cols.txt")
    except Exception as e:
        print(f"ERROR:{e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_columns())
