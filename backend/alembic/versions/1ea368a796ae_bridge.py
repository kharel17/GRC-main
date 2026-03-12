"""bridge missing render revision

Revision ID: 1ea368a796ae
Revises: f1f4459c2ba3
Create Date: 2026-03-13 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1ea368a796ae'
down_revision: Union[str, Sequence[str], None] = 'f1f4459c2ba3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op upgrade to bridge the missing revision."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
