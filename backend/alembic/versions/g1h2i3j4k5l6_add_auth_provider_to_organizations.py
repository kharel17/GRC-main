"""add_auth_provider_to_organizations

Revision ID: g1h2i3j4k5l6
Revises: a1b2c3d4e5f6
Create Date: 2026-09-11 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add auth_provider enum and column to organizations table."""
    # 1. Create the authprovider enum type (idempotent)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'authprovider') THEN
                CREATE TYPE authprovider AS ENUM ('any', 'microsoft', 'google');
            END IF;
        END $$;
    """)

    # 2. Add the column with server default
    op.add_column(
        'organizations',
        sa.Column(
            'auth_provider',
            sa.Enum('any', 'microsoft', 'google', name='authprovider', create_type=False),
            server_default='any',
            nullable=False,
        )
    )


def downgrade() -> None:
    """Remove auth_provider column and enum type."""
    op.drop_column('organizations', 'auth_provider')
    op.execute("DROP TYPE IF EXISTS authprovider")
