
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
import sys
import os

# Set up path to import app
sys.path.append(os.getcwd())

from app import models
from app.config import settings

async def check_data():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Find the user
        email = "bcolorc17@gmail.com"
        result = await db.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User {email} not found")
            return
            
        print(f"User: {user.email}, Role: {user.role}, Org: {user.organization_name} ({user.organization_id})")
        
        org_id = user.organization_id
        
        # 2. Check counts for this org
        risk_count = await db.execute(select(func.count()).filter(models.Risk.organization_id == org_id))
        control_count = await db.execute(select(func.count()).filter(models.ControlApplicability.organization_id == org_id))
        
        print(f"Risks for Org: {risk_count.scalar()}")
        print(f"Control Applicabilities for Org: {control_count.scalar()}")
        
        # 3. Check if there are ANY risks in the DB (to see if they are in another org)
        all_risks = await db.execute(select(func.count()).select_from(models.Risk))
        print(f"Total Risks in DB (Any Org): {all_risks.scalar()}")
        
        if all_risks.scalar() > 0:
            sample_risk_res = await db.execute(select(models.Risk).limit(1))
            r = sample_risk_res.scalar()
            print(f"Sample Risk Org ID: {r.organization_id}")
            
            # Find the org name
            if r.organization_id:
                org_res = await db.execute(select(models.Organization).where(models.Organization.id == r.organization_id))
                org = org_res.scalar_one_or_none()
                if org:
                    print(f"Organization with data: {org.name} ({org.id})")
                else:
                    print(f"Organization ID {r.organization_id} found in risks but not in Organization table!")
            else:
                print("Risks found with NULL organization_id")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_data())
