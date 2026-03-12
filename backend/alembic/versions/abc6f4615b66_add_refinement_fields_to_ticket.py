"""add refinement fields to ticket

Revision ID: abc6f4615b66
Revises: 0cf1bb2b5ea7
Create Date: 2026-03-12 16:49:57.605007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'abc6f4615b66'
down_revision: Union[str, Sequence[str], None] = '0cf1bb2b5ea7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: Create the ENUM type if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE evidencestatus AS ENUM (
                'submitted',
                'under_review',
                'verified',
                'rejected',
                'expired'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Step 2: Add a new temporary column with ENUM type
    op.execute("""
        ALTER TABLE evidence 
        ADD COLUMN status_new evidencestatus;
    """)
    
    # Step 3: Copy existing data with safe casting
    op.execute("""
        UPDATE evidence 
        SET status_new = CASE 
            WHEN status IN (
                'submitted', 
                'under_review', 
                'verified', 
                'rejected', 
                'expired'
            ) 
            THEN status::evidencestatus
            ELSE 'submitted'::evidencestatus
        END;
    """)
    
    # Step 4: Drop old column and rename new one
    op.execute("ALTER TABLE evidence DROP COLUMN status;")
    op.execute("""
        ALTER TABLE evidence 
        RENAME COLUMN status_new TO status;
    """)

    # Step 5: Add the remaining ticket and evidence fields
    op.drop_column('evidence', 'ai_summary')
    op.drop_column('evidence', 'ai_confidence_score')
    op.add_column('tickets', sa.Column('is_repeat_finding', sa.Boolean(), nullable=True))
    op.add_column('tickets', sa.Column('iso_clause', sa.String(), nullable=True))
    op.add_column('tickets', sa.Column('risk_score', sa.Integer(), nullable=True))
    op.add_column('tickets', sa.Column('previous_ticket_id', sa.UUID(), nullable=True))
    op.add_column('tickets', sa.Column('status_updated_at', sa.DateTime(), nullable=True))
    op.alter_column('tickets', 'is_auto_escalation_enabled',
               existing_type=sa.INTEGER(),
               type_=sa.Boolean(),
               existing_nullable=True)
    op.create_foreign_key(None, 'tickets', 'tickets', ['previous_ticket_id'], ['id'])
    op.drop_index(op.f('ix_users_manager_id'), table_name='users')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        ALTER TABLE evidence 
        ALTER COLUMN status TYPE VARCHAR 
        USING status::VARCHAR;
    """)
    op.execute("DROP TYPE IF EXISTS evidencestatus;")

    # Revert other changes
    op.create_index(op.f('ix_users_manager_id'), 'users', ['manager_id'], unique=False)
    op.drop_constraint(None, 'tickets', type_='foreignkey')
    op.alter_column('tickets', 'is_auto_escalation_enabled',
               existing_type=sa.Boolean(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.drop_column('tickets', 'status_updated_at')
    op.drop_column('tickets', 'previous_ticket_id')
    op.drop_column('tickets', 'risk_score')
    op.drop_column('tickets', 'iso_clause')
    op.drop_column('tickets', 'is_repeat_finding')
    op.add_column('evidence', sa.Column('ai_confidence_score', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('evidence', sa.Column('ai_summary', sa.TEXT(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
