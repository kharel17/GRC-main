"""add due_date and escalation fields to tickets

Revision ID: 87949b88fb9a
Revises: be2adc2b8ddf
Create Date: 2026-03-12 16:08:30.052100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87949b88fb9a'
down_revision: Union[str, Sequence[str], None] = 'be2adc2b8ddf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns with nullable=True initially to avoid conflicts
    op.add_column('tickets', sa.Column('is_auto_escalation_enabled', sa.Boolean(), nullable=True, server_default='true'))
    op.add_column('tickets', sa.Column('is_repeat_finding', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('tickets', sa.Column('due_date', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tickets', 'due_date')
    op.drop_column('tickets', 'is_repeat_finding')
    op.drop_column('tickets', 'is_auto_escalation_enabled')
