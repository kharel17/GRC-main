import asyncio
from app.database import engine
from sqlalchemy import text

ORG_A = "24de3639-ee40-4563-a207-dd66436a0da8"
ORG_B = "629d3a0a-62a1-4eb1-b233-e7107f33211b"

async def run_test():
    async with engine.connect() as conn:
        print("=== Cross-Tenant RLS Leakage Verification ===")
        user_res = await conn.execute(text("SELECT current_user;"))
        print(f"Authenticated Role: {user_res.scalar()}")

        # 1. Unscoped session (no org context set)
        print("\n--- 1. Context: Unscoped (No Org ID Set) ---")
        unscoped_ctrl = (await conn.execute(text("SELECT count(*) FROM controls;"))).scalar()
        unscoped_risk = (await conn.execute(text("SELECT count(*) FROM risks;"))).scalar()
        unscoped_orgs = (await conn.execute(text("SELECT count(*) FROM organizations;"))).scalar()
        print(f"Unscoped visible controls:      {unscoped_ctrl}")
        print(f"Unscoped visible risks:         {unscoped_risk}")
        print(f"Unscoped visible organizations: {unscoped_orgs}")

        # 2. Org A Context
        print(f"\n--- 2. Context: Scoped to Org A ({ORG_A}) ---")
        await conn.execute(text("SELECT set_config('app.org_id', :org, false);"), {"org": ORG_A})
        await conn.execute(text("SELECT set_config('app.current_org_id', :org, false);"), {"org": ORG_A})
        ctrl_a = (await conn.execute(text("SELECT count(*) FROM controls;"))).scalar()
        risk_a = (await conn.execute(text("SELECT count(*) FROM risks;"))).scalar()
        orgs_a = (await conn.execute(text("SELECT count(*) FROM organizations;"))).scalar()
        print(f"Org A visible controls:      {ctrl_a}")
        print(f"Org A visible risks:         {risk_a}")
        print(f"Org A visible organizations: {orgs_a}")

        # 3. Org B Context (testing cross-tenant isolation)
        print(f"\n--- 3. Context: Scoped to Org B ({ORG_B}) ---")
        await conn.execute(text("SELECT set_config('app.org_id', :org, false);"), {"org": ORG_B})
        await conn.execute(text("SELECT set_config('app.current_org_id', :org, false);"), {"org": ORG_B})
        ctrl_b = (await conn.execute(text("SELECT count(*) FROM controls;"))).scalar()
        risk_b = (await conn.execute(text("SELECT count(*) FROM risks;"))).scalar()
        orgs_b = (await conn.execute(text("SELECT count(*) FROM organizations;"))).scalar()
        # Direct attempt to select Org A's controls while scoped as Org B:
        leakage_query = await conn.execute(
            text("SELECT count(*) FROM controls WHERE organization_id = :org_a;"),
            {"org_a": ORG_A}
        )
        leakage_count = leakage_query.scalar()
        print(f"Org B visible controls:           {ctrl_b}")
        print(f"Org B visible risks:              {risk_b}")
        print(f"Org B visible organizations:      {orgs_b}")
        print(f"Direct query for Org A data by B: {leakage_count} (Must be 0)")

        # Assertions
        assert unscoped_ctrl == 0, f"Expected 0 unscoped controls, got {unscoped_ctrl}"
        assert unscoped_risk == 0, f"Expected 0 unscoped risks, got {unscoped_risk}"
        assert ctrl_a == 7, f"Expected 7 controls for Org A, got {ctrl_a}"
        assert risk_a == 2, f"Expected 2 risks for Org A, got {risk_a}"
        assert orgs_a == 1, f"Expected 1 organization for Org A, got {orgs_a}"
        assert ctrl_b == 0, f"Expected 0 controls for Org B, got {ctrl_b}"
        assert risk_b == 0, f"Expected 0 risks for Org B, got {risk_b}"
        assert orgs_b == 1, f"Expected 1 organization for Org B, got {orgs_b}"
        assert leakage_count == 0, f"LEAKAGE DETECTED: Org B saw {leakage_count} rows from Org A!"

        print("\n>>> RESULT: STRICT PASS - Zero cross-tenant leakage confirmed under grc_app_user.")

if __name__ == "__main__":
    asyncio.run(run_test())
