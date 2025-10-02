"""Initial schema: users and operations

Revision ID: 0001_initial
Revises: 
Create Date: 2025-09-30 00:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('badge_id', sa.String(), nullable=True),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('hashed_password', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_superuser', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.create_index('ix_users_badge_id', 'users', ['badge_id'], unique=True)

    op.create_table(
        'operations',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('operation_type', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('status', sa.String(), server_default=sa.text("'in_progress'"), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('engineer_name', sa.String(), nullable=True),
    )
    op.create_index('ix_operations_user_id', 'operations', ['user_id'], unique=False)


def downgrade():
    op.drop_index('ix_operations_user_id', table_name='operations')
    op.drop_table('operations')
    op.drop_index('ix_users_badge_id', table_name='users')
    op.drop_table('users')


