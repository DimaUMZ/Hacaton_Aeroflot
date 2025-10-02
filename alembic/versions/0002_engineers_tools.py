"""Add engineers and tools tables

Revision ID: 0002_engineers_tools
Revises: 0001_initial
Create Date: 2025-09-30 00:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = '0002_engineers_tools'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'engineers',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('last_name', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(), nullable=False),
        sa.Column('patronymic', sa.String(), nullable=True),
        sa.Column('badge_id', sa.String(), nullable=True),
    )
    op.create_index('ix_engineers_last_name', 'engineers', ['last_name'], unique=False)
    op.create_index('ix_engineers_first_name', 'engineers', ['first_name'], unique=False)
    op.create_index('ix_engineers_badge_id', 'engineers', ['badge_id'], unique=True)

    op.create_table(
        'tools',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
    )
    op.create_index('ix_tools_name', 'tools', ['name'], unique=False)
    op.create_index('ix_tools_sku', 'tools', ['sku'], unique=True)


def downgrade():
    op.drop_index('ix_tools_sku', table_name='tools')
    op.drop_index('ix_tools_name', table_name='tools')
    op.drop_table('tools')
    op.drop_index('ix_engineers_badge_id', table_name='engineers')
    op.drop_index('ix_engineers_first_name', table_name='engineers')
    op.drop_index('ix_engineers_last_name', table_name='engineers')
    op.drop_table('engineers')


