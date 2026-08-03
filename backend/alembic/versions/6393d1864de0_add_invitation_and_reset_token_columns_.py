"""add_invitation_and_reset_token_columns_to_users

Revision ID: 6393d1864de0
Revises: 36acc6ed0d23
Create Date: 2026-08-03 07:58:43.100724

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6393d1864de0'
down_revision: Union[str, Sequence[str], None] = '36acc6ed0d23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS invitation_token_hash VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS invitation_expires_at TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_hash VARCHAR")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP WITHOUT TIME ZONE")
    
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_invitation_token_hash ON users (invitation_token_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_reset_token_hash ON users (reset_token_hash)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_users_reset_token_hash")
    op.execute("DROP INDEX IF EXISTS ix_users_invitation_token_hash")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS reset_token_expires_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS reset_token_hash")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS invitation_expires_at")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS invitation_token_hash")
