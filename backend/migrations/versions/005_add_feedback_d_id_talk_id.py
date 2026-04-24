"""add d_id_talk_id to feedback for async D-ID polling

Revision ID: 005_feedback_talk
Revises: 004_cascade_fks
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_feedback_talk"
down_revision: Union[str, Sequence[str], None] = "004_cascade_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("feedback", sa.Column("d_id_talk_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("feedback", "d_id_talk_id")
