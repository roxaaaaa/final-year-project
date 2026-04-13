"""add google_id to users table

Revision ID: 001
Revises: 
Create Date: 2026-04-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add google_id column if it doesn't exist
    op.add_column('users', sa.Column('google_id', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
    op.create_index('ix_users_google_id', 'users', ['google_id'])
    
    # Add other missing columns
    op.add_column('users', sa.Column('name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('persona', sa.String(), nullable=True))
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('last_sign_in_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_index('ix_users_google_id', table_name='users')
    op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    op.drop_column('users', 'google_id')
    op.drop_column('users', 'last_sign_in_at')
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'persona')
    op.drop_column('users', 'name')
