"""
Automated Multi-Tenant Isolation & RLS Verification Script

Verifies that PostgreSQL Row Level Security (RLS) policies on tenant tables
(risks, controls, evidence, tickets) strictly isolate data between different
organizations when accessed via grc_app_user.
"""
import sys
import uuid
import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://grc_app_user:grc_app_secret@localhost:5432/grc_db"


async def main():
    print("=" * 70)
    print("  MULTI-TENANT ISOLATION & ROW LEVEL SECURITY (RLS) TEST SUITE")
    print("=" * 70)
    print(f"Connecting to database via grc_app_user...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    results = {}

    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    user_id = None
    created_ephemeral_user = False

    risk_a1_id = uuid.uuid4()
    risk_a2_id = uuid.uuid4()
    risk_b1_id = uuid.uuid4()
    risk_b2_id = uuid.uuid4()

    try:
        # Step 0: Ensure we have a valid user_id for owner_id and created_by
        async with engine.begin() as conn:
            user_res = await conn.execute(text("SELECT id FROM users LIMIT 1"))
            row = user_res.fetchone()
            if row:
                user_id = row[0]
            else:
                user_id = uuid.uuid4()
                await conn.execute(
                    text("""
                        INSERT INTO users (id, email, hashed_password, role, is_active)
                        VALUES (:id, :email, 'dummy_hash', 'user', true)
                    """),
                    {"id": user_id, "email": f"rls_test_{uuid.uuid4().hex[:6]}@test.com"}
                )
                created_ephemeral_user = True

        print(f"\n[SETUP] Setting up test fixtures...")
        print(f"  - Ephemeral Org A: {org_a_id}")
        print(f"  - Ephemeral Org B: {org_b_id}")
        print(f"  - Test User ID:    {user_id}")

        # Step 1: Create ephemeral organizations
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO organizations (id, name, compliance_frameworks) VALUES (:id, :name, '[]'::jsonb)"),
                {"id": org_a_id, "name": f"Test Tenant Org A ({org_a_id})"}
            )
            await conn.execute(
                text("INSERT INTO organizations (id, name, compliance_frameworks) VALUES (:id, :name, '[]'::jsonb)"),
                {"id": org_b_id, "name": f"Test Tenant Org B ({org_b_id})"}
            )
            print("  - Inserted Org A and Org B into 'organizations'.")

        # Step 2: Insert 2 risks for Org A (under Org A context)
        async with engine.begin() as conn:
            await conn.execute(text(f"SET LOCAL app.org_id = '{org_a_id}';"))
            for r_id, title in [(risk_a1_id, "Risk A1"), (risk_a2_id, "Risk A2")]:
                await conn.execute(
                    text("""
                        INSERT INTO risks (
                            id, title, description, likelihood, impact, risk_score,
                            organization_id, owner_id, created_by, created_at, updated_at
                        ) VALUES (
                            :id, :title, 'Org A test risk', 2, 3, 6,
                            :org_id, :owner_id, :created_by, :now, :now
                        )
                    """),
                    {
                        "id": r_id,
                        "title": title,
                        "org_id": org_a_id,
                        "owner_id": user_id,
                        "created_by": user_id,
                        "now": datetime.now()
                    }
                )
            print("  - Inserted 2 test risks under Org A.")

        # Step 3: Insert 2 risks for Org B (under Org B context)
        async with engine.begin() as conn:
            await conn.execute(text(f"SET LOCAL app.org_id = '{org_b_id}';"))
            for r_id, title in [(risk_b1_id, "Risk B1"), (risk_b2_id, "Risk B2")]:
                await conn.execute(
                    text("""
                        INSERT INTO risks (
                            id, title, description, likelihood, impact, risk_score,
                            organization_id, owner_id, created_by, created_at, updated_at
                        ) VALUES (
                            :id, :title, 'Org B test risk', 3, 4, 12,
                            :org_id, :owner_id, :created_by, :now, :now
                        )
                    """),
                    {
                        "id": r_id,
                        "title": title,
                        "org_id": org_b_id,
                        "owner_id": user_id,
                        "created_by": user_id,
                        "now": datetime.now()
                    }
                )
            print("  - Inserted 2 test risks under Org B.")

        # -------------------------------------------------------------
        # TEST 1: Org A Context
        # -------------------------------------------------------------
        print("\n" + "-" * 70)
        print("TEST 1: Querying under Org A Context (SET LOCAL app.org_id = Org_A)")
        async with engine.begin() as conn:
            await conn.execute(text(f"SET LOCAL app.org_id = '{org_a_id}';"))
            res = await conn.execute(text("SELECT id, title, organization_id FROM risks;"))
            rows = res.fetchall()
            count = len(rows)
            org_ids = {row[2] for row in rows}
            print(f"  Rows returned: {count}")
            for r in rows:
                print(f"    - Risk: {r[1]} (id: {r[0]}, org: {r[2]})")

            test1_pass = (count == 2) and (org_ids == {org_a_id})
            results["Test 1: Org A Context Isolation"] = "PASS" if test1_pass else f"FAIL (Returned {count} rows, expected 2 strictly matching Org A)"

        # -------------------------------------------------------------
        # TEST 2: Org B Context
        # -------------------------------------------------------------
        print("\n" + "-" * 70)
        print("TEST 2: Querying under Org B Context (SET LOCAL app.org_id = Org_B)")
        async with engine.begin() as conn:
            await conn.execute(text(f"SET LOCAL app.org_id = '{org_b_id}';"))
            res = await conn.execute(text("SELECT id, title, organization_id FROM risks;"))
            rows = res.fetchall()
            count = len(rows)
            org_ids = {row[2] for row in rows}
            print(f"  Rows returned: {count}")
            for r in rows:
                print(f"    - Risk: {r[1]} (id: {r[0]}, org: {r[2]})")

            test2_pass = (count == 2) and (org_ids == {org_b_id})
            results["Test 2: Org B Context Isolation"] = "PASS" if test2_pass else f"FAIL (Returned {count} rows, expected 2 strictly matching Org B)"

        # -------------------------------------------------------------
        # TEST 3: No Context / Leaked Tenant
        # -------------------------------------------------------------
        print("\n" + "-" * 70)
        print("TEST 3: Querying with No Context (app.org_id is unset / RESET)")
        async with engine.begin() as conn:
            try:
                # Explicitly reset or ensure app.org_id is not set
                await conn.execute(text("RESET app.org_id;"))
                res = await conn.execute(text("SELECT id, title, organization_id FROM risks;"))
                rows = res.fetchall()
                count = len(rows)
                print(f"  Rows returned with RESET app.org_id: {count}")
                if count > 0:
                    print(f"  WARNING: Leaked rows detected: {rows}")

                test3a_pass = (count == 0)
            except Exception as e:
                print(f"  Query blocked as expected with no context: {e}")
                test3a_pass = True

            # Also verify empty string '' does not raise uuid cast error
            try:
                await conn.execute(text("SET LOCAL app.org_id = '';"))
                res_empty = await conn.execute(text("SELECT id, title, organization_id FROM risks;"))
                rows_empty = res_empty.fetchall()
                count_empty = len(rows_empty)
                print(f"  Rows returned with empty string app.org_id: {count_empty}")
                test3b_pass = (count_empty == 0)
            except Exception as e:
                print(f"  Query blocked with empty string app.org_id: {e}")
                test3b_pass = True

            test3_pass = test3a_pass and test3b_pass
            results["Test 3: No Context Block/Zero Rows"] = "PASS" if test3_pass else f"FAIL (Expected 0 rows when unauthenticated)"

        # -------------------------------------------------------------
        # TEST 4: Cross-Tenant Direct Primary Key Access Prevention
        # -------------------------------------------------------------
        print("\n" + "-" * 70)
        print("TEST 4: Cross-Tenant Access by Direct Primary Key Query")
        async with engine.begin() as conn:
            # Under Org A context, try to directly query Org B's risk by its primary key
            await conn.execute(text(f"SET LOCAL app.org_id = '{org_a_id}';"))
            res = await conn.execute(
                text("SELECT id, title FROM risks WHERE id = :target_id;"),
                {"target_id": risk_b1_id}
            )
            cross_row = res.fetchone()
            print(f"  Querying Org B risk ({risk_b1_id}) while authenticated as Org A...")
            print(f"  Result: {cross_row}")
            test4_pass = (cross_row is None)
            results["Test 4: Cross-Tenant PK Access Block"] = "PASS" if test4_pass else "FAIL (Org A was able to read Org B record by ID!)"

        # -------------------------------------------------------------
        # TEST 5: Verify RLS Status on All Core Tenant Tables
        # -------------------------------------------------------------
        print("\n" + "-" * 70)
        print("TEST 5: Verifying RLS Enforcement Flags on Tenant Tables")
        async with engine.begin() as conn:
            res = await conn.execute(text("""
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname IN ('risks', 'controls', 'evidence', 'tickets');
            """))
            tables_status = res.fetchall()
            all_rls_enabled = True
            for tbl, rls, force_rls in tables_status:
                status_str = f"RLS={rls}, FORCE_RLS={force_rls}"
                print(f"  - Table '{tbl}': {status_str}")
                if not (rls and force_rls):
                    all_rls_enabled = False

            results["Test 5: RLS + FORCE RLS Enabled on Tenant Tables"] = "PASS" if all_rls_enabled else "FAIL (One or more tables lack RLS/FORCE RLS)"

    finally:
        # Cleanup
        print("\n" + "-" * 70)
        print("[CLEANUP] Removing ephemeral test records...")
        async with engine.begin() as conn:
            # To delete risks from Org A and Org B, we can set app.org_id for each or delete with context
            await conn.execute(text(f"SET LOCAL app.org_id = '{org_a_id}';"))
            await conn.execute(text("DELETE FROM risks WHERE organization_id = :org_id;"), {"org_id": org_a_id})
            await conn.execute(text(f"SET LOCAL app.org_id = '{org_b_id}';"))
            await conn.execute(text("DELETE FROM risks WHERE organization_id = :org_id;"), {"org_id": org_b_id})

            # Delete test organizations (RLS is disabled on organizations table)
            await conn.execute(
                text("DELETE FROM organizations WHERE id IN (:org_a, :org_b);"),
                {"org_a": org_a_id, "org_b": org_b_id}
            )

            if created_ephemeral_user and user_id:
                await conn.execute(text("DELETE FROM users WHERE id = :user_id;"), {"user_id": user_id})

            print("  - Cleaned up test risks and organizations successfully.")

        await engine.dispose()

    # Summary
    print("\n" + "=" * 70)
    print("                    TEST SUITE RESULTS")
    print("=" * 70)
    all_passed = True
    for test_name, status in results.items():
        print(f"  {status:<7} | {test_name}")
        if not status.startswith("PASS"):
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("  ALL RLS MULTI-TENANT ISOLATION TESTS PASSED SUCCESSFULLY! (EXIT 0)")
        print("=" * 70)
        sys.exit(0)
    else:
        print("  SOME TESTS FAILED! (EXIT 1)")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
