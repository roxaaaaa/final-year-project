"""fix generated_exams.level to store paper level (ordinary/higher)

Revision ID: 003_fix_level
Revises: ed0d021109c1
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_fix_level"
down_revision: Union[str, Sequence[str], None] = "ed0d021109c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Was incorrectly modeled as persona enum; store Leaving Cert paper level.
    op.execute(
        sa.text(
            """
            ALTER TABLE generated_exams
            ALTER COLUMN level TYPE VARCHAR(16)
            USING CASE level::text
              WHEN 'student' THEN 'ordinary'
              WHEN 'teacher' THEN 'ordinary'
              ELSE level::text
            END
            """
        )
    )


def downgrade() -> None:
    op.alter_column(
        "generated_exams",
        "level",
        existing_type=sa.String(length=16),
        type_=sa.Enum("student", "teacher", name="personaenum", native_enum=False, create_constraint=True),
        postgresql_using="CASE level::text WHEN 'ordinary' THEN 'student' WHEN 'higher' THEN 'teacher' ELSE 'student' END",
        existing_nullable=False,
    )
