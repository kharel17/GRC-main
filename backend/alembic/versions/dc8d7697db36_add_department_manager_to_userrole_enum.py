"""Add department_manager to userrole enum

Revision ID: dc8d7697db36
Revises: cd926c3afef8
Create Date: 2026-03-18 04:40:01.241752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc8d7697db36'
down_revision: Union[str, Sequence[str], None] = 'cd926c3afef8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enums cannot be added in a transaction in some Postgres setups, 
    # but Alembic handles this or we can use op.execute.
    # We use a loop for clarity.
    new_roles = [
        'superadmin', 'control_owner', 'risk_owner', 
        'compliance_officer', 'department_manager', 
        'executive', 'auditor'
    ]
    for role in new_roles:
        # We wrap in try-except or check existence if we want it to be idempotent, 
        # but for a migration specifically adding them, a direct execute is standard.
        # Note: ALTER TYPE ... ADD VALUE cannot be rolled back easily in Postgres < 12.
        op.execute(f"ALTER TYPE userrole ADD VALUE '{role}'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
