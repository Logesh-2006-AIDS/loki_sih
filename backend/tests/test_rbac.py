from fastapi.testclient import TestClient


def test_rbac_unauthenticated_request_rejected(client: TestClient):
    response = client.get("/api/v1/users/")
    assert response.status_code == 401
    assert "token missing" in response.json()["error"].lower()


def test_rbac_applicant_forbidden_from_admin_users(
    client: TestClient, applicant_token: str
):
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {applicant_token}"},
    )
    assert response.status_code == 403
    assert "requires admin role" in response.json()["error"].lower()


def test_rbac_admin_allowed_access_to_users(client: TestClient, admin_token: str):
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 4
