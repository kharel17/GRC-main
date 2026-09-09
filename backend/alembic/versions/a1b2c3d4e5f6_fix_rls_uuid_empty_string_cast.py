"""fix_rls_uuid_empty_string_cast

Revision ID: a1b2c3d4e5f6
Revises: 0fb1bca489dd
Create Date: 2026-09-09 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0fb1bca489dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create helper function current_org_id() to safely parse app.org_id
    op.execute("""
        CREATE OR REPLACE FUNCTION current_org_id() RETURNS uuid AS $$
        BEGIN
            RETURN NULLIF(current_setting('app.org_id', true), '')::uuid;
        EXCEPTION WHEN OTHERS THEN
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql STABLE;
    """)

    # 2. Update core tenant table RLS policies to use current_org_id() / NULLIF
    core_tables = ['risks', 'controls', 'evidence', 'tickets', 'assets', 'control_applicability', 'compliance_items', 'document_analyses']
    for table in core_tables:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = '{table}' AND policyname = 'org_isolation') THEN
                    ALTER POLICY org_isolation ON {table}
                    USING (organization_id = current_org_id());
                END IF;
            END $$;
        """)

    # 3. Update relational policies referencing parent tenant tables
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'risk_control_mappings' AND policyname = 'org_isolation') THEN
                ALTER POLICY org_isolation ON risk_control_mappings
                USING (risk_id IN (SELECT risks.id FROM risks WHERE risks.organization_id = current_org_id()));
            END IF;

            IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'evidence_control_matches' AND policyname = 'org_isolation') THEN
                ALTER POLICY org_isolation ON evidence_control_matches
                USING (evidence_id IN (SELECT evidence.id FROM evidence WHERE evidence.organization_id = current_org_id()));
            END IF;

            IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ticket_comments' AND policyname = 'org_isolation') THEN
                ALTER POLICY org_isolation ON ticket_comments
                USING (ticket_id IN (SELECT tickets.id FROM tickets WHERE tickets.organization_id = current_org_id()));
            END IF;

            IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'ticket_activities' AND policyname = 'org_isolation') THEN
                ALTER POLICY org_isolation ON ticket_activities
                USING (ticket_id IN (SELECT tickets.id FROM tickets WHERE tickets.organization_id = current_org_id()));
            END IF;

            IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'asset_risk_mapping' AND policyname = 'org_isolation') THEN
                ALTER POLICY org_isolation ON asset_risk_mapping
                USING (asset_id IN (SELECT assets.id FROM assets WHERE assets.organization_id = current_org_id()));
            END IF;

            IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'audit_logs' AND policyname = 'org_isolation') THEN
                ALTER POLICY org_isolation ON audit_logs
                USING (user_id IN (SELECT users.id FROM users WHERE users.organization_id = current_org_id()));
            END IF;
        END $$;
    """)


def downgrade() -> None:
    core_tables = ['risks', 'controls', 'evidence', 'tickets', 'assets', 'control_applicability', 'compliance_items', 'document_analyses']
    for table in core_tables:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_policies WHERE tablename = '{table}' AND policyname = 'org_isolation') THEN
                    ALTER POLICY org_isolation ON {table}
                    USING (organization_id = (current_setting('app.org_id'::text, true))::uuid);
                END IF;
            END $$;
        """)
    op.execute("DROP FUNCTION IF EXISTS current_org_id();")
