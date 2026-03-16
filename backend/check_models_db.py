import asyncio
import sys
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add the current directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app import models

async def verify_models():
    print("Testing SQLAlchemy models...")
    async with SessionLocal() as db:
        try:
            # Test User
            print("Checking User model...")
            await db.execute(select(models.User).limit(1))
            
            # Test Organization
            print("Checking Organization model...")
            await db.execute(select(models.Organization).limit(1))
            
            # Test Risk
            print("Checking Risk model...")
            await db.execute(select(models.Risk).limit(1))
            
            # Test Control
            print("Checking Control model...")
            await db.execute(select(models.Control).limit(1))
            
            # Test Ticket
            print("Checking Ticket model...")
            await db.execute(select(models.Ticket).limit(1))
            
            # Test Notification
            print("Checking Notification model...")
            await db.execute(select(models.Notification).limit(1))
            
            print("\nSUCCESS: All critical models are queryable.")
            return True
        except Exception as e:
            print(f"\nFAILURE: Model check failed with error: {e}")
            return False

if __name__ == "__main__":
    if asyncio.run(verify_models()):
        sys.exit(0)
    else:
        sys.exit(1)
