"""bridge missing render revision 2

Revision ID: 446d7a089740
Revises: 1ea368a796ae
Create Date: 2026-03-13 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '446d7a089740'
down_revision: Union[str, Sequence[str], None] = '1ea368a796ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op upgrade to bridge the second missing revision."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
