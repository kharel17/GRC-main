from app.config import settings
from app.database import engine
from sqlalchemy import select
from app.models.user import User
from app.utils.security import verify_password
import asyncio

async def main():
    async with engine.connect() as conn:
        res = await conn.execute(select(User).where(User.email == 'alice@company.com'))
        row = res.first()
        print('row', row)
        hashed_password = row[3]
        print('hashed', hashed_password)
        print('verify', verify_password('demo', hashed_password))

asyncio.run(main())
