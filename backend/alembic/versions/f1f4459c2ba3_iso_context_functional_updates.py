"""iso_context_functional_updates

Revision ID: f1f4459c2ba3
Revises: abc6f4615b66
Create Date: 2026-03-13 02:21:31.221395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1f4459c2ba3'
down_revision: Union[str, Sequence[str], None] = 'abc6f4615b66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Ensure Enums exist
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'organizationsize') THEN
                CREATE TYPE organizationsize AS ENUM ('small', 'medium', 'large', 'enterprise');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assettype') THEN
                CREATE TYPE assettype AS ENUM ('data', 'software', 'hardware', 'service', 'personnel', 'physical');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assetclassification') THEN
                CREATE TYPE assetclassification AS ENUM ('public', 'internal', 'confidential', 'restricted');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assetcriticality') THEN
                CREATE TYPE assetcriticality AS ENUM ('low', 'medium', 'high', 'critical');
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assetstatus') THEN
                CREATE TYPE assetstatus AS ENUM ('active', 'decommissioned', 'under_review');
            END IF;
        END $$;
    """)

    # 2. Ensure Organizations table exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id UUID PRIMARY KEY,
            name VARCHAR NOT NULL,
            industry VARCHAR,
            size organizationsize,
            description TEXT,
            website VARCHAR,
            country VARCHAR,
            compliance_frameworks JSONB NOT NULL DEFAULT '[]'::jsonb,
            primary_contact_id UUID REFERENCES users(id),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """)

    # 3. Ensure Assets table exists
    op.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id UUID PRIMARY KEY,
            organization_id UUID NOT NULL REFERENCES organizations(id),
            name VARCHAR NOT NULL,
            description TEXT,
            asset_type assettype NOT NULL,
            classification assetclassification DEFAULT 'internal',
            criticality assetcriticality DEFAULT 'medium',
            location VARCHAR,
            status assetstatus DEFAULT 'active',
            owner_id UUID NOT NULL REFERENCES users(id),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
    """)

    # 4. Add new columns to organizations
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS employee_count INTEGER")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS risk_appetite JSONB")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS compliance_target_date TIMESTAMP WITHOUT TIME ZONE")

    # 5. Expand AssetType enum
    op.execute("""
        DO $$ BEGIN
            ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'server';
            ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'db';
            ALTER TYPE assettype ADD VALUE IF NOT EXISTS 'app';
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # 6. Create many-to-many mapping table
    op.execute("""
        CREATE TABLE IF NOT EXISTS asset_risk_mapping (
            asset_id UUID NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
            risk_id UUID NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
            PRIMARY KEY (asset_id, risk_id)
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organizations', 'compliance_target_date')
    op.drop_column('organizations', 'risk_appetite')
    op.drop_column('organizations', 'employee_count')
    op.drop_table('asset_risk_mapping')
