"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from alembic import op
import sqlalchemy as sa
${imports if imports}

revision = '${up_revision}'
down_revision = ${down_revision | repr}
branch_labels = ${branch_labels | repr}
depends_on = ${depends_on | repr}


def upgrade():
    ${upgrades if upgrades}


def downgrade():
    ${downgrades if downgrades}


