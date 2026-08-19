"""merge_heads

Revision ID: b6c79cc3e5ac
Revises: 43996b42d3f6, f77beaea7328
Create Date: 2026-06-08 01:59:09.700260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c79cc3e5ac'
down_revision: Union[str, Sequence[str], None] = ('43996b42d3f6', 'f77beaea7328')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
