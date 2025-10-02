"""Add operation_items table

Revision ID: 0003_operation_items
Revises: 0002_engineers_tools
Create Date: 2025-09-30 00:25:00
"""

from alembic import op
import sqlalchemy as sa


revision = '0003_operation_items'
down_revision = '0002_engineers_tools'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'operation_items',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('operation_id', sa.Integer(), sa.ForeignKey('operations.id'), nullable=False),
        sa.Column('tool_id', sa.Integer(), sa.ForeignKey('tools.id'), nullable=True),
        sa.Column('tool_name', sa.String(), nullable=True),
        sa.Column('quantity', sa.Integer(), server_default=sa.text('1'), nullable=False),
    )
    op.create_index('ix_operation_items_operation_id', 'operation_items', ['operation_id'], unique=False)


def downgrade():
    op.drop_index('ix_operation_items_operation_id', table_name='operation_items')
    op.drop_table('operation_items')


