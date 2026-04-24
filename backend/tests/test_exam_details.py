"""Tests for GET /api/exams/{id} (owner scoping and payload shape)."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import _sync_database_url
from models import GeneratedExam, PersonaEnum, User
from routers import auth as auth_module


@pytest.fixture
def db_teacher_with_exam():
    engine = create_engine(_sync_database_url(), pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(
        google_id="pytest-exam-details-teacher",
        email="pytest_exam_details@example.com",
        name="Teacher",
        persona=PersonaEnum.teacher,
        generations_number=0,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    exam = GeneratedExam(
        user_id=user.id,
        topic="Crops",
        level="ordinary",
        questions=json.dumps(["Q1"]),
    )
    session.add(exam)
    session.commit()
    session.refresh(exam)
    yield user, exam
    session.delete(exam)
    session.delete(user)
    session.commit()
    session.close()


def test_get_exam_details_returns_exam_properties(client, db_teacher_with_exam):
    user, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(user.id), user.persona.value)
    r = client.get(f"/api/exams/{exam.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == exam.id
    assert body["topic"] == "Crops"
    assert body["level"] == "ordinary"
    assert body["questions"] == ["Q1"]
    assert "created_at" in body


def test_get_exam_details_not_found_is_404(client, db_teacher_with_exam):
    user, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(user.id), user.persona.value)
    r = client.get(
        f"/api/exams/{exam.id + 99999}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json().get("detail") == "Exam not found"
