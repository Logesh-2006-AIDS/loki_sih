from fastapi.testclient import TestClient


def test_rbac_unauthenticated_request_rejected(client: TestClient):
    # Admin endpoint
    res1 = client.get("/api/v1/users/")
    assert res1.status_code == 401
    assert "token missing" in res1.json()["error"].lower()

    # Officer endpoint
    res2 = client.get("/api/v1/officer/queue")
    assert res2.status_code == 401

    # Committee endpoint
    res3 = client.get("/api/v1/committee/schemes")
    assert res3.status_code == 401


def test_rbac_applicant_forbidden_from_admin_and_staff_routes(
    client: TestClient, applicant_token: str
):
    headers = {"Authorization": f"Bearer {applicant_token}"}

    # Applicant cannot access admin-only users
    res_admin = client.get("/api/v1/users/", headers=headers)
    assert res_admin.status_code == 403
    assert "requires admin role" in res_admin.json()["error"].lower()

    # Applicant cannot access officer queue
    res_officer = client.get("/api/v1/officer/queue", headers=headers)
    assert res_officer.status_code == 403

    # Applicant cannot access committee schemes
    res_committee = client.get("/api/v1/committee/schemes", headers=headers)
    assert res_committee.status_code == 403


def test_rbac_officer_restricted_access(
    client: TestClient, officer_token: str
):
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Officer cannot access admin users endpoint
    res_admin = client.get("/api/v1/users/", headers=headers)
    assert res_admin.status_code == 403

    # Officer CAN access officer queue
    res_queue = client.get("/api/v1/officer/queue", headers=headers)
    assert res_queue.status_code == 200


def test_rbac_committee_restricted_access(
    client: TestClient, committee_token: str
):
    headers = {"Authorization": f"Bearer {committee_token}"}

    # Committee cannot access admin users endpoint
    res_admin = client.get("/api/v1/users/", headers=headers)
    assert res_admin.status_code == 403

    # Committee cannot access officer queue
    res_officer = client.get("/api/v1/officer/queue", headers=headers)
    assert res_officer.status_code == 403

    # Committee CAN access committee schemes
    res_schemes = client.get("/api/v1/committee/schemes", headers=headers)
    assert res_schemes.status_code == 200


def test_rbac_admin_full_access(
    client: TestClient, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin accesses users
    res_users = client.get("/api/v1/users/", headers=headers)
    assert res_users.status_code == 200
    assert len(res_users.json()) >= 4

    # Admin accesses officer queue
    res_queue = client.get("/api/v1/officer/queue", headers=headers)
    assert res_queue.status_code == 200

    # Admin accesses committee schemes
    res_schemes = client.get("/api/v1/committee/schemes", headers=headers)
    assert res_schemes.status_code == 200
