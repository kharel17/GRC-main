"""add linked_risk_id to controls manual

Revision ID: 43996b42d3f6
Revises: f995e18518e8
Create Date: 2026-03-17 21:26:35.368013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43996b42d3f6'
down_revision: Union[str, Sequence[str], None] = 'f995e18518e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('controls', sa.Column('linked_risk_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_control_linked_risk', 'controls', 'risks', ['linked_risk_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_control_linked_risk', 'controls', type_='foreignkey')
    op.drop_column('controls', 'linked_risk_id')
