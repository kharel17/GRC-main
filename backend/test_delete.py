import asyncio
import json
from fastapi.testclient import TestClient
from app.main import app
from app.api import deps
from app.database import SessionLocal
import traceback
import logging

# Capture all logs
logging.basicConfig(level=logging.INFO)

async def run():
    from app.models.user import User, UserRole
    from app.models.risk import Risk
    from sqlalchemy import select
    
    # 1. Identify a risk to delete
    async with SessionLocal() as db:
        res = await db.execute(select(Risk).order_by(Risk.created_at.desc()).limit(10))
        all_risks = res.scalars().all()
        target_risk = None
        for r in all_risks:
            if r.title in ["DAAAAAA", "Final test", "Commit Fix DB Test", "test"]:
                target_risk = r
                break
        
        if not target_risk:
            print("No suitable test risk found to delete.")
            return

        print(f"Targeting risk: {target_risk.title} ({target_risk.id})")
        
        # We need the user who owns it or an admin
        user = await db.get(User, target_risk.created_by)
        if not user:
             user = User(id=target_risk.created_by, role=UserRole.admin, email='auth@example.com', organization_id=target_risk.organization_id)

    # 2. Setup mock auth
    app.dependency_overrides[deps.get_current_active_user] = lambda: user
    app.dependency_overrides[deps.get_current_user] = lambda: user
    # Note: RoleChecker is a class, we need to override the dependency call
    # But for now let's just use the client
    
    client = TestClient(app)
    
    print(f"Attempting to delete risk {target_risk.id} as user {user.email}...")
    try:
        response = client.delete(f"/api/v1/risks/{target_risk.id}")
        print(f"STATUS: {response.status_code}")
        if response.status_code != 204:
            print("DELETE FAILED")
            print(f"RESPONSE: {response.text}")
        else:
            print("DELETE SUCCESSFUL")
    except Exception:
        print("EXCEPTION DURING REQUEST:")
        traceback.print_exc()

try:
    asyncio.run(run())
except Exception:
    traceback.print_exc()
finally:
    app.dependency_overrides.clear()
