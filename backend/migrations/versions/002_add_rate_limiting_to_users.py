"""add rate limiting columns to users table

Revision ID: 002
Revises: 001
Create Date: 2026-04-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add rate limiting column for lifetime generations
    op.add_column('users', sa.Column('generations_number', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'generations_number')
