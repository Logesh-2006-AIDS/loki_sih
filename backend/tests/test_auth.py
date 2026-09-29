import uuid
from fastapi.testclient import TestClient


def test_auth_login_all_seeded_roles(client: TestClient):
    roles_credentials = [
        ("applicant@demo.gov.in", "Demo@12345", "APPLICANT"),
        ("officer@demo.gov.in", "Demo@12345", "OFFICER"),
        ("committee@demo.gov.in", "Demo@12345", "COMMITTEE"),
        ("loki@gmail.com", "loki@06", "ADMIN"),
    ]
    for email, password, expected_role in roles_credentials:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, f"Failed for {email}: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert data["user"]["role"] == expected_role


def test_auth_login_case_insensitive_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "Applicant@DEMO.gov.in", "password": "Demo@12345"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "applicant@demo.gov.in"
    assert data["user"]["role"] == "APPLICANT"


def test_auth_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost.user@demo.gov.in", "password": "Demo@12345"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["error"]


def test_auth_login_invalid_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "applicant@demo.gov.in", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["error"]


def test_auth_get_me(client: TestClient, applicant_token: str):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {applicant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "applicant@demo.gov.in"
    assert data["role"] == "APPLICANT"
    assert data["is_active"] is True


def test_auth_register_and_login_new_user(client: TestClient):
    unique_email = f"test_{uuid.uuid4().hex[:8]}@demo.gov.in"
    reg_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "New Test Applicant",
            "email": unique_email,
            "phone": "+91 9999900000",
            "password": "TestPassword@123",
            "role": "APPLICANT",
        },
    )
    assert reg_response.status_code == 201
    user_data = reg_response.json()
    assert user_data["email"] == unique_email

    # Now login with the newly registered user
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "TestPassword@123"},
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
