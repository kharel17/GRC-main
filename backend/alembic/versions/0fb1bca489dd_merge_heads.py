"""merge_heads

Revision ID: 0fb1bca489dd
Revises: 6393d1864de0, f1a2b3c4d5e7
Create Date: 2026-09-09 17:49:09.683111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0fb1bca489dd'
down_revision: Union[str, Sequence[str], None] = ('6393d1864de0', 'f1a2b3c4d5e7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
