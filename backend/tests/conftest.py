import sys
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.db.session import SessionLocal


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db() -> Generator:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def applicant_token(client: TestClient) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "applicant@demo.gov.in", "password": "Demo@12345"},
    )
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@demo.gov.in", "password": "Demo@12345"},
    )
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def officer_token(client: TestClient) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "officer@demo.gov.in", "password": "Demo@12345"},
    )
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def committee_token(client: TestClient) -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "committee@demo.gov.in", "password": "Demo@12345"},
    )
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]

