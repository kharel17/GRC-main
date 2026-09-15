"""multi_framework_and_hitl_provenance

Revision ID: h1i2j3k4l5m6
Revises: g1h2i3j4k5l6
Create Date: 2026-09-15 20:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, Sequence[str], None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Multi-Tenant Framework Scoping
    op.add_column(
        'frameworks',
        sa.Column('is_system', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'frameworks',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    )
    
    # Drop global unique constraint on name
    op.drop_constraint('frameworks_name_key', 'frameworks', type_='unique')
    
    # Add composite unique constraint across (name, organization_id)
    op.create_unique_constraint('uq_framework_name_org', 'frameworks', ['name', 'organization_id'])
    
    # Add partial unique index for system frameworks where organization_id IS NULL
    op.create_index(
        'uq_framework_system_name',
        'frameworks',
        ['name'],
        unique=True,
        postgresql_where=sa.text('organization_id IS NULL')
    )

    # Update RLS policy on frameworks
    op.execute("DROP POLICY IF EXISTS read_all ON frameworks;")
    op.execute("DROP POLICY IF EXISTS framework_read_policy ON frameworks;")
    op.execute("""
        CREATE POLICY framework_read_policy ON frameworks
            FOR SELECT USING (organization_id IS NULL OR organization_id = current_org_id());
    """)

    # 2. Controls - Audit Provenance, Assessment Flags & Relational Framework FKs
    op.add_column(
        'controls',
        sa.Column('source', sa.String(), server_default='manual', nullable=True)
    )
    op.add_column(
        'controls',
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_analyses.id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column(
        'controls',
        sa.Column('assessment_status', sa.String(), server_default='human_verified', nullable=False)
    )
    op.add_column(
        'controls',
        sa.Column('framework_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('frameworks.id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column(
        'controls',
        sa.Column('framework_control_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('framework_controls.id', ondelete='SET NULL'), nullable=True)
    )
    op.create_index('ix_controls_org_framework_ctrl', 'controls', ['organization_id', 'framework_control_id'])

    # 3. Risks - Audit Provenance & Assessment Flags
    op.add_column(
        'risks',
        sa.Column('source', sa.String(), server_default='manual', nullable=True)
    )
    op.add_column(
        'risks',
        sa.Column('source_document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('document_analyses.id', ondelete='SET NULL'), nullable=True)
    )
    op.add_column(
        'risks',
        sa.Column('assessment_status', sa.String(), server_default='human_verified', nullable=False)
    )
    op.create_index('ix_risks_org_source_doc', 'risks', ['organization_id', 'source_document_id'])


def downgrade() -> None:
    # 3. Revert Risks
    op.drop_index('ix_risks_org_source_doc', table_name='risks')
    op.drop_column('risks', 'assessment_status')
    op.drop_column('risks', 'source_document_id')
    op.drop_column('risks', 'source')

    # 2. Revert Controls
    op.drop_index('ix_controls_org_framework_ctrl', table_name='controls')
    op.drop_constraint('controls_framework_control_id_fkey', 'controls', type_='foreignkey')
    op.drop_constraint('controls_framework_id_fkey', 'controls', type_='foreignkey')
    op.drop_column('controls', 'framework_control_id')
    op.drop_column('controls', 'framework_id')
    op.drop_column('controls', 'assessment_status')
    op.drop_column('controls', 'source_document_id')
    op.drop_column('controls', 'source')

    # 1. Revert Frameworks
    op.execute("DROP POLICY IF EXISTS framework_read_policy ON frameworks;")
    op.execute("CREATE POLICY read_all ON frameworks FOR SELECT USING (true);")
    op.drop_index('uq_framework_system_name', table_name='frameworks')
    op.drop_constraint('uq_framework_name_org', 'frameworks', type_='unique')
    op.create_unique_constraint('frameworks_name_key', 'frameworks', ['name'])
    op.drop_constraint('frameworks_organization_id_fkey', 'frameworks', type_='foreignkey')
    op.drop_column('frameworks', 'organization_id')
    op.drop_column('frameworks', 'is_system')
