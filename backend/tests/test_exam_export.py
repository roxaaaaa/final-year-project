"""Tests for teacher exam export (PDF/DOCX) and auth gating."""

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
        google_id="pytest-teacher-google",
        email="pytest_teacher@example.com",
        name="Pytest Teacher",
        persona=PersonaEnum.teacher,
        generations_number=0,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    exam = GeneratedExam(
        user_id=user.id,
        topic="Soil Science",
        level="higher",
        questions=json.dumps(["First question?", "Second with áéíóú"]),
    )
    session.add(exam)
    session.commit()
    session.refresh(exam)

    yield user, exam

    session.delete(exam)
    session.delete(user)
    session.commit()
    session.close()


@pytest.fixture
def db_student():
    engine = create_engine(_sync_database_url(), pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(
        google_id="pytest-student-export",
        email="pytest_student_export@example.com",
        name="Pytest Student",
        persona=PersonaEnum.student,
        generations_number=0,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    yield user
    session.delete(user)
    session.commit()
    session.close()


def test_export_pdf_teacher_ok(client, db_teacher_with_exam):
    user, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(user.id), user.persona.value)
    r = client.get(
        f"/api/exams/{exam.id}/export?format=pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert "attachment" in r.headers.get("content-disposition", "").lower()
    assert len(r.content) > 100
    assert r.content[:4] == b"%PDF"


def test_export_pdf_twice_font_registration_safe(client, db_teacher_with_exam):
    """Repeated PDF export must not fail if a TTF was registered on the first call."""
    user, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(user.id), user.persona.value)
    url = f"/api/exams/{exam.id}/export?format=pdf"
    headers = {"Authorization": f"Bearer {token}"}
    r1 = client.get(url, headers=headers)
    r2 = client.get(url, headers=headers)
    assert r1.status_code == r2.status_code == 200
    assert r2.content[:4] == b"%PDF"


def test_export_docx_teacher_ok(client, db_teacher_with_exam):
    user, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(user.id), user.persona.value)
    r = client.get(
        f"/api/exams/{exam.id}/export?format=docx",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    ct = r.headers.get("content-type", "")
    assert "wordprocessingml" in ct or "octet-stream" in ct
    assert "attachment" in r.headers.get("content-disposition", "").lower()
    assert len(r.content) > 100
    assert r.content[:2] == b"PK"


def test_export_student_forbidden(client, db_teacher_with_exam, db_student):
    _teacher, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(db_student.id), db_student.persona.value)
    r = client.get(
        f"/api/exams/{exam.id}/export?format=pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_export_not_found(client, db_teacher_with_exam):
    user, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(user.id), user.persona.value)
    r = client.get(
        f"/api/exams/{exam.id + 99999}/export?format=pdf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_export_invalid_format(client, db_teacher_with_exam):
    user, exam = db_teacher_with_exam
    token = auth_module.create_jwt_token(str(user.id), user.persona.value)
    r = client.get(
        f"/api/exams/{exam.id}/export?format=rtf",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
