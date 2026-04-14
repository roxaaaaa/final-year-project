import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import _sync_database_url
from models import PersonaEnum, User
from routers import auth as auth_module


@pytest.fixture
def db_student():
    engine = create_engine(_sync_database_url(), pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    user = User(
        google_id="pytest-google-id",
        email="pytest_user@example.com",
        name="Pytest User",
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


def test_user_me_requires_auth(client):
    r = client.get("/api/user/me")
    assert r.status_code == 401


def test_user_me_with_valid_token(client, db_student):
    token = auth_module.create_jwt_token(str(db_student.id), db_student.persona.value)
    r = client.get("/api/user/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "pytest_user@example.com"
    assert body["persona"] == "student"
    assert body["id"] == str(db_student.id)
