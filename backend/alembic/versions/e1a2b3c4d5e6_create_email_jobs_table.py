"""create_email_jobs_table

Revision ID: e1a2b3c4d5e6
Revises: b6c79cc3e5ac
Create Date: 2026-09-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'b6c79cc3e5ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'emailjobstatus') THEN 
                CREATE TYPE emailjobstatus AS ENUM ('pending', 'processing', 'sent', 'failed', 'dead'); 
            END IF; 
        END $$;
    """)

    op.create_table(
        'email_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('recipient', sa.String(), nullable=False),
        sa.Column('template_name', sa.String(), nullable=False),
        sa.Column('template_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('pending', 'processing', 'sent', 'failed', 'dead', name='emailjobstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_email_jobs_recipient'), 'email_jobs', ['recipient'], unique=False)
    op.create_index(op.f('ix_email_jobs_status'), 'email_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_email_jobs_next_retry_at'), 'email_jobs', ['next_retry_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_jobs_next_retry_at'), table_name='email_jobs')
    op.drop_index(op.f('ix_email_jobs_status'), table_name='email_jobs')
    op.drop_index(op.f('ix_email_jobs_recipient'), table_name='email_jobs')
    op.drop_table('email_jobs')
    op.execute('DROP TYPE IF EXISTS emailjobstatus')
