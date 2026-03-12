"""add manager_id and is_acting_admin to users

Revision ID: d0a2bfcbefb8
Revises: 3a7c58921e5b
Create Date: 2026-03-12 15:03:17.998558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0a2bfcbefb8'
down_revision: Union[str, Sequence[str], None] = '3a7c58921e5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_acting_admin', sa.Integer(), server_default='0', nullable=True))
    op.add_column('users', sa.Column('manager_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_user_manager', 'users', 'users', ['manager_id'], ['id'])
    op.create_index('ix_users_manager_id', 'users', ['manager_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_users_manager_id', table_name='users')
    op.drop_constraint('fk_user_manager', 'users', type_='foreignkey')
    op.drop_column('users', 'manager_id')
    op.drop_column('users', 'is_acting_admin')
