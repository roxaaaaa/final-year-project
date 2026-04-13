"""foreign keys ON DELETE CASCADE for dev-friendly deletes

Revision ID: 004_cascade_fks
Revises: 003_fix_level
Create Date: 2026-04-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_cascade_fks"
down_revision: Union[str, Sequence[str], None] = "003_fix_level"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL default constraint names from SQLAlchemy / Alembic
    op.execute(
        sa.text(
            """
            ALTER TABLE generated_exams DROP CONSTRAINT IF EXISTS generated_exams_user_id_fkey;
            ALTER TABLE generated_exams ADD CONSTRAINT generated_exams_user_id_fkey
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

            ALTER TABLE practice_attempts DROP CONSTRAINT IF EXISTS practice_attempts_user_id_fkey;
            ALTER TABLE practice_attempts ADD CONSTRAINT practice_attempts_user_id_fkey
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

            ALTER TABLE practice_attempts DROP CONSTRAINT IF EXISTS practice_attempts_generated_exam_id_fkey;
            ALTER TABLE practice_attempts ADD CONSTRAINT practice_attempts_generated_exam_id_fkey
              FOREIGN KEY (generated_exam_id) REFERENCES generated_exams(id) ON DELETE CASCADE;

            ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_practice_attempt_id_fkey;
            ALTER TABLE feedback ADD CONSTRAINT feedback_practice_attempt_id_fkey
              FOREIGN KEY (practice_attempt_id) REFERENCES practice_attempts(id) ON DELETE CASCADE;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE feedback DROP CONSTRAINT IF EXISTS feedback_practice_attempt_id_fkey;
            ALTER TABLE feedback ADD CONSTRAINT feedback_practice_attempt_id_fkey
              FOREIGN KEY (practice_attempt_id) REFERENCES practice_attempts(id);

            ALTER TABLE practice_attempts DROP CONSTRAINT IF EXISTS practice_attempts_generated_exam_id_fkey;
            ALTER TABLE practice_attempts ADD CONSTRAINT practice_attempts_generated_exam_id_fkey
              FOREIGN KEY (generated_exam_id) REFERENCES generated_exams(id);

            ALTER TABLE practice_attempts DROP CONSTRAINT IF EXISTS practice_attempts_user_id_fkey;
            ALTER TABLE practice_attempts ADD CONSTRAINT practice_attempts_user_id_fkey
              FOREIGN KEY (user_id) REFERENCES users(id);

            ALTER TABLE generated_exams DROP CONSTRAINT IF EXISTS generated_exams_user_id_fkey;
            ALTER TABLE generated_exams ADD CONSTRAINT generated_exams_user_id_fkey
              FOREIGN KEY (user_id) REFERENCES users(id);
            """
        )
    )
