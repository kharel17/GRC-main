"""Merge migration heads

Revision ID: f1d97b9f00cb
Revises: 43996b42d3f6, f77beaea7328
Create Date: 2026-03-18 04:28:50.109452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1d97b9f00cb'
down_revision: Union[str, Sequence[str], None] = ('43996b42d3f6', 'f77beaea7328')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
