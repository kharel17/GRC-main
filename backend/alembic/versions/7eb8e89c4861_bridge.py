"""bridge missing render revisions

Revision IDs: 1ea368a796ae, 446d7a089740, 7eb8e89c4861
Revises: f1f4459c2ba3
Create Date: 2026-03-13 04:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# We create a chain: f1f4459c2ba3 -> 1ea368a796ae -> 446d7a089740 -> 7eb8e89c4861
# In this file, we register 7eb8e89c4861 as the head of these orphan branches.
revision: str = '7eb8e89c4861'
down_revision: Union[str, Sequence[str], None] = '446d7a089740'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op upgrade to bridge the chain of missing revisions."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
