"""create notifications table

Revision ID: 0cf1bb2b5ea7
Revises: 87949b88fb9a
Create Date: 2026-03-12 16:08:39.360013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cf1bb2b5ea7'
down_revision: Union[str, Sequence[str], None] = '87949b88fb9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('notifications',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('ticket_id', sa.UUID(), nullable=True),
    sa.Column('message', sa.String(), nullable=False),
    sa.Column('type', sa.String(), nullable=False),
    sa.Column('is_read', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_notifications_user_id_is_read', 'notifications', ['user_id', 'is_read'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_notifications_user_id_is_read', table_name='notifications')
    op.drop_table('notifications')
