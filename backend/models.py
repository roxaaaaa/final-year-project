"""ORM tables: users, generated exams, practice attempts, and per-question feedback."""

import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Enum, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import enum

class PersonaEnum(str, enum.Enum):
    """Student or teacher; used for quotas and export rules."""
    student = "student"
    teacher = "teacher"


class User(Base):
    """Google OAuth user row with optional persona and lifetime generation count."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    google_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    persona: Mapped[Optional[PersonaEnum]] = mapped_column(
        Enum(PersonaEnum, native_enum=False, create_constraint=True, validate_strings=True),
        nullable=True,
    )
    generations_number: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now().replace(tzinfo=None))
    last_sign_in_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now().replace(tzinfo=None))

    # Relationships
    generated_exams: Mapped[List["GeneratedExam"]] = relationship("GeneratedExam", back_populates="user")
    practice_attempts: Mapped[List["PracticeAttempt"]] = relationship("PracticeAttempt", back_populates="user")


class GeneratedExam(Base):
    """Stores generated exam question sets for persistence and history"""
    __tablename__ = "generated_exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String, nullable=False)
    # Leaving Cert paper level (ordinary / higher), not user persona
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    questions: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string of questions array
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now().replace(tzinfo=None))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="generated_exams")
    practice_attempts: Mapped[List["PracticeAttempt"]] = relationship("PracticeAttempt", back_populates="generated_exam")


class PracticeAttempt(Base):
    """Stores user practice attempts and answers"""
    __tablename__ = "practice_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    generated_exam_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("generated_exams.id", ondelete="CASCADE"), nullable=False
    )
    answers: Mapped[Optional[str]] = mapped_column(Text)  # JSON string of answers array
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now().replace(tzinfo=None))
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="practice_attempts")
    generated_exam: Mapped["GeneratedExam"] = relationship("GeneratedExam", back_populates="practice_attempts")
    feedback_entries: Mapped[List["Feedback"]] = relationship("Feedback", back_populates="practice_attempt")


class Feedback(Base):
    """Stores generated feedback for user answers"""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    practice_attempt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("practice_attempts.id", ondelete="CASCADE"), nullable=False
    )
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Index of question in the exam
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    video_url: Mapped[Optional[str]] = mapped_column(String)
    video_status: Mapped[Optional[str]] = mapped_column(String, default="pending")  # pending, processing, completed, failed
    d_id_talk_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=lambda: datetime.datetime.now().replace(tzinfo=None))

    # Relationships
    practice_attempt: Mapped["PracticeAttempt"] = relationship("PracticeAttempt", back_populates="feedback_entries")
