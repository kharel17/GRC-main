"""Make ticket source_audit_log_id nullable

Revision ID: 69c6398f2f3b
Revises: dc8d7697db36
Create Date: 2026-03-18 04:41:28.506170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69c6398f2f3b'
down_revision: Union[str, Sequence[str], None] = 'dc8d7697db36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('tickets', 'source_audit_log_id',
               existing_type=sa.UUID(),
               nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('tickets', 'source_audit_log_id',
               existing_type=sa.UUID(),
               nullable=False)
