import asyncio
import httpx
from sqlalchemy import text
from app.database import SessionLocal
import uuid

async def setup_test_data():
    async with SessionLocal() as db:
        # Create Org A and Org B
        org_a_id = str(uuid.uuid4())
        org_b_id = str(uuid.uuid4())
        user_a_id = str(uuid.uuid4())
        risk_b_id = str(uuid.uuid4())
        
        await db.execute(
            text("INSERT INTO organizations (id, name, compliance_frameworks) VALUES (:id_a, 'Org A', '{}')"),
            {"id_a": org_a_id}
        )
        await db.execute(
            text("INSERT INTO organizations (id, name, compliance_frameworks) VALUES (:id_b, 'Org B', '{}')"),
            {"id_b": org_b_id}
        )
        
        # User A in Org A
        from app.utils.security import get_password_hash
        pwd = get_password_hash("password")
        await db.execute(
            text("INSERT INTO users (id, email, full_name, hashed_password, organization_id, is_active, invitation_status, role) VALUES (:uid, 'usera@orga.com', 'User A', :pwd, :oid, true, 'active', 'admin')"),
            {"uid": user_a_id, "pwd": pwd, "oid": org_a_id}
        )
        
        # Risk B in Org B
        await db.execute(
            text("INSERT INTO risks (id, title, description, organization_id, likelihood, impact, score, status) VALUES (:rid, 'Risk B', 'Belongs to Org B', :oid, 1, 1, 1, 'open')"),
            {"rid": risk_b_id, "oid": org_b_id}
        )
        
        await db.commit()
        return org_a_id, org_b_id, risk_b_id, user_a_id

async def cleanup_test_data(org_a, org_b, user_a, risk_b):
    async with SessionLocal() as db:
        await db.execute(text("DELETE FROM risks WHERE id = :rid"), {"rid": risk_b})
        await db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_a})
        await db.execute(text("DELETE FROM organizations WHERE id IN (:oid_a, :oid_b)"), {"oid_a": org_a, "oid_b": org_b})
        await db.commit()

async def main():
    print("Setting up test data...")
    org_a, org_b, risk_b, user_a = await setup_test_data()
    
    try:
        async with httpx.AsyncClient() as client:
            print("[*] Logging in as usera@orga.com...")
            resp = await client.post("http://127.0.0.1:8000/api/v1/auth/login", data={"username": "usera@orga.com", "password": "password"})
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print(f"[*] Successfully logged in. Got token.")
            
            print(f"\n[*] Attempting to fetch Risk B ({risk_b}) belonging to Org B...")
            risk_resp = await client.get(f"http://127.0.0.1:8000/api/v1/risks/{risk_b}", headers=headers)
            print(f"Status: {risk_resp.status_code}")
            print(f"Response: {risk_resp.text}")
    finally:
        print("\nCleaning up test data...")
        await cleanup_test_data(org_a, org_b, user_a, risk_b)

if __name__ == "__main__":
    asyncio.run(main())
