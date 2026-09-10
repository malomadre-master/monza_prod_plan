import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.security import hash_password
from app.seed import seed_work_centers

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture
def db_session():
    Base.metadata.create_all(engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    db_session.add(
        User(
            username="admin",
            display_name="Админ",
            password_hash=hash_password("admin"),
            role=UserRole.admin,
            is_active=True,
        )
    )
    db_session.add(
        User(
            username="worker1",
            display_name="Станочник",
            password_hash=hash_password("pass"),
            role=UserRole.worker,
            is_active=True,
        )
    )
    db_session.add(
        User(
            username="designer1",
            display_name="Конструктор Один",
            password_hash=hash_password("pass"),
            role=UserRole.designer,
            is_active=True,
        )
    )
    db_session.add(
        User(
            username="designer2",
            display_name="Конструктор Два",
            password_hash=hash_password("pass"),
            role=UserRole.designer,
            is_active=True,
        )
    )
    db_session.commit()
    seed_work_centers(db_session)

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, username: str = "admin", password: str = "admin") -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]
