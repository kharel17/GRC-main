"""Sync ticket_settings column

Revision ID: a3d809cd220f
Revises: 69c6398f2f3b
Create Date: 2026-03-18 05:15:50.513717

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3d809cd220f'
down_revision: Union[str, Sequence[str], None] = '69c6398f2f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add ticket_settings column to organizations table
    # Using execute with IF NOT EXISTS to be safe
    op.execute('ALTER TABLE organizations ADD COLUMN IF NOT EXISTS ticket_settings JSONB')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organizations', 'ticket_settings')
