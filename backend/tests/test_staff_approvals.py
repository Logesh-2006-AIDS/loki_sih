import uuid
from fastapi.testclient import TestClient


def test_applicant_self_registration_creates_active_user(client: TestClient):
    unique_email = f"applicant_{uuid.uuid4().hex[:8]}@example.gov.in"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ramesh Tribal Scholar",
            "email": unique_email,
            "phone": "+91 9876543210",
            "password": "Password@12345",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == unique_email
    assert data["role"] == "APPLICANT"
    assert data["account_status"] == "ACTIVE"
    assert data["is_active"] is True


def test_applicant_can_login_after_registration(client: TestClient):
    unique_email = f"applicant_{uuid.uuid4().hex[:8]}@example.gov.in"
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Ramesh Tribal Scholar",
            "email": unique_email,
            "password": "Password@12345",
        },
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "Password@12345"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["user"]["role"] == "APPLICANT"
    assert token_data["user"]["account_status"] == "ACTIVE"


def test_officer_registration_creates_pending_account(client: TestClient):
    unique_email = f"officer_{uuid.uuid4().hex[:8]}@mota.gov.in"
    response = client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Sunil Kumar Verification Officer",
            "email": unique_email,
            "phone": "+91 9876543211",
            "password": "Officer@12345",
            "requested_role": "OFFICER",
            "employee_id": "MOTA-VO-8891",
            "department": "Tribal Welfare Department",
            "designation": "Assistant Scrutiny Officer",
            "jurisdiction": "Jharkhand",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["email"] == unique_email
    assert data["role"] == "OFFICER"
    assert data["account_status"] == "PENDING_APPROVAL"
    assert data["is_active"] is False


def test_pending_officer_cannot_login_to_portal(client: TestClient):
    unique_email = f"officer_{uuid.uuid4().hex[:8]}@mota.gov.in"
    client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Pending Officer",
            "email": unique_email,
            "password": "Officer@12345",
            "requested_role": "OFFICER",
            "employee_id": "VO-9999",
            "department": "Tribal Affairs",
            "designation": "Desk Officer",
            "jurisdiction": "Odisha",
        },
    )

    # Attempt login while pending
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "Officer@12345"},
    )
    assert login_res.status_code == 403
    assert "pending administrator approval" in login_res.json()["error"].lower()


def test_admin_can_approve_officer_and_login_succeeds(
    client: TestClient, admin_token: str
):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    unique_email = f"officer_{uuid.uuid4().hex[:8]}@mota.gov.in"
    client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Approving Officer",
            "email": unique_email,
            "password": "Officer@12345",
            "requested_role": "OFFICER",
            "employee_id": "VO-4411",
            "department": "MoTA Delhi",
            "designation": "Senior Verification Officer",
            "jurisdiction": "National",
        },
    )

    # Admin lists pending requests
    list_res = client.get(
        "/api/v1/admin/user-approvals?status=PENDING", headers=admin_headers
    )
    assert list_res.status_code == 200
    requests = list_res.json()
    matching = [r for r in requests if r["user_email"] == unique_email]
    assert len(matching) == 1
    req_id = matching[0]["id"]

    # Admin approves the request
    approve_res = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/approve", headers=admin_headers
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # Officer now logs in successfully
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "Officer@12345"},
    )
    assert login_res.status_code == 200
    officer_token = login_res.json()["access_token"]

    # Officer can access officer API
    queue_res = client.get(
        "/api/v1/officer/queue",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert queue_res.status_code == 200


def test_committee_shinchan_rejection_and_reason_display_flow(
    client: TestClient, admin_token: str
):
    """
    Requirements:
    1. Committee Shinchan registers.
    2. Admin rejects Shinchan with:
       "Official institutional identification details could not be verified."
    3. Shinchan attempts login.
    4. Login returns HTTP 403.
    5. No JWT is returned.
    6. Response contains the rejection reason.
    8. Another user cannot retrieve Shinchan's rejection reason.
    """
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    shinchan_email = f"shinchan_{uuid.uuid4().hex[:8]}@univ.edu.in"
    reg_res = client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Shinchan Nohara",
            "email": shinchan_email,
            "phone": "+91 9876543210",
            "password": "Password@12345",
            "requested_role": "COMMITTEE",
            "employee_id": "COMM-SHIN-007",
            "department": "Department of Sociology",
            "designation": "Associate Professor",
            "jurisdiction": "Kanto Region",
        },
    )
    assert reg_res.status_code == 201
    assert reg_res.json()["account_status"] == "PENDING_APPROVAL"

    # Find Shinchan's pending request
    list_res = client.get(
        "/api/v1/admin/user-approvals?status=PENDING", headers=admin_headers
    )
    assert list_res.status_code == 200
    req_id = [r for r in list_res.json() if r["user_email"] == shinchan_email][0]["id"]

    # Admin rejects Shinchan with exact required reason
    admin_reason = "Official institutional identification details could not be verified."
    reject_res = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/reject",
        headers=admin_headers,
        json={"reason": admin_reason},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"
    assert reject_res.json()["rejection_reason"] == admin_reason

    # Shinchan attempts login with correct credentials
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": shinchan_email, "password": "Password@12345"},
    )
    # 4. Login returns HTTP 403
    assert login_res.status_code == 403
    data = login_res.json()

    # 5. No JWT is returned
    assert "access_token" not in data
    assert "token" not in data

    # 6. Response contains the rejection reason and generic message
    assert data["error"] == "Your registration request was not approved."
    assert data["reason"] == admin_reason
    assert data["status_code"] == 403

    # 8. Another user cannot retrieve Shinchan's rejection reason
    # Attempting to login as Shinchan with wrong password:
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": shinchan_email, "password": "WrongPassword@123"},
    )
    assert bad_login.status_code == 401
    assert "reason" not in bad_login.json()
    assert admin_reason not in bad_login.text

    # Another applicant logging in cannot see Shinchan's reason
    other_email = f"other_{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other Student",
            "email": other_email,
            "password": "Password@12345",
        },
    )
    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": other_email, "password": "Password@12345"},
    )
    assert other_login.status_code == 200
    other_token = other_login.json()["access_token"]
    unauth_approval_call = client.get(
        "/api/v1/admin/user-approvals",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert unauth_approval_call.status_code == 403
    assert admin_reason not in unauth_approval_call.text


def test_admin_rejection_reason_validation_rules(
    client: TestClient, admin_token: str
):
    """
    Requirements:
    11. Admin cannot reject without providing a reason.
    12. Empty rejection reason is rejected.
    13. Very long rejection reason is rejected.
    14. Rejection reason is displayed as plain text and cannot execute HTML/script.
    """
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    staff_email = f"staff_val_{uuid.uuid4().hex[:8]}@mota.gov.in"
    client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Validation Staff",
            "email": staff_email,
            "password": "Staff@12345",
            "requested_role": "OFFICER",
            "employee_id": "VAL-1234",
            "department": "Welfare Dept",
            "designation": "Inspector",
            "jurisdiction": "Central",
        },
    )

    list_res = client.get(
        "/api/v1/admin/user-approvals?status=PENDING", headers=admin_headers
    )
    req_id = [r for r in list_res.json() if r["user_email"] == staff_email][0]["id"]

    # 11. Missing reason field
    res_missing = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/reject",
        headers=admin_headers,
        json={},
    )
    assert res_missing.status_code == 422

    # 12. Empty rejection reason
    res_empty = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/reject",
        headers=admin_headers,
        json={"reason": "   "},
    )
    assert res_empty.status_code == 422
    assert "Please provide a reason" in res_empty.text

    # Too short (< 10 chars)
    res_short = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/reject",
        headers=admin_headers,
        json={"reason": "Short"},
    )
    assert res_short.status_code == 422
    assert "at least 10 characters" in res_short.text

    # 13. Very long rejection reason (> 1000 chars)
    res_long = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/reject",
        headers=admin_headers,
        json={"reason": "X" * 1001},
    )
    assert res_long.status_code == 422
    assert "cannot exceed 1000 characters" in res_long.text

    # 14. HTML or script content is rejected
    res_html = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/reject",
        headers=admin_headers,
        json={"reason": "<script>alert('pwned')</script> Invalid credentials"},
    )
    assert res_html.status_code == 422
    assert "cannot contain HTML or script" in res_html.text

    res_tags = client.post(
        f"/api/v1/admin/user-approvals/{req_id}/reject",
        headers=admin_headers,
        json={"reason": "<b>Invalid identification credentials</b>"},
    )
    assert res_tags.status_code == 422
    assert "cannot contain HTML or script" in res_tags.text


def test_committee_member_registration_and_approval_workflow(
    client: TestClient, admin_token: str
):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    unique_email = f"committee_{uuid.uuid4().hex[:8]}@univ.edu.in"
    reg_res = client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Prof. Anita Murmu",
            "email": unique_email,
            "phone": "+91 9123456780",
            "password": "Committee@12345",
            "requested_role": "COMMITTEE",
            "employee_id": "COMM-EXP-772",
            "department": "Anthropology & Tribal Studies",
            "designation": "Professor & Selection Member",
            "jurisdiction": "Central University",
        },
    )
    assert reg_res.status_code == 201
    assert reg_res.json()["account_status"] == "PENDING_APPROVAL"

    # Pending login is blocked
    assert client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "Committee@12345"},
    ).status_code == 403

    # Admin approves
    list_res = client.get(
        "/api/v1/admin/user-approvals?status=PENDING", headers=admin_headers
    )
    req_id = [r for r in list_res.json() if r["user_email"] == unique_email][0]["id"]
    client.post(f"/api/v1/admin/user-approvals/{req_id}/approve", headers=admin_headers)

    # Committee logs in
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "Committee@12345"},
    )
    assert login_res.status_code == 200
    comm_token = login_res.json()["access_token"]

    # Access committee schemes
    comm_res = client.get(
        "/api/v1/committee/schemes",
        headers={"Authorization": f"Bearer {comm_token}"},
    )
    assert comm_res.status_code == 200


def test_registration_security_cannot_create_admin(client: TestClient):
    # Attempting to register as ADMIN via register-staff must be rejected
    res1 = client.post(
        "/api/v1/auth/register-staff",
        json={
            "full_name": "Hacker Trying Admin",
            "email": f"hacker_{uuid.uuid4().hex[:6]}@exploit.com",
            "password": "Password@123",
            "requested_role": "ADMIN",
            "employee_id": "X",
            "department": "X",
            "designation": "X",
            "jurisdiction": "X",
        },
    )
    assert res1.status_code in [400, 422]

    # Attempting to send role=ADMIN via generic /register must be rejected
    res2 = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Hacker Trying Admin",
            "email": f"hacker_{uuid.uuid4().hex[:6]}@exploit.com",
            "password": "Password@123",
            "role": "ADMIN",
        },
    )
    assert res2.status_code == 400
    assert "prohibited" in res2.json()["error"].lower()


def test_non_admin_cannot_access_or_action_approvals(
    client: TestClient, applicant_token: str, officer_token: str
):
    # Applicant gets 403
    app_headers = {"Authorization": f"Bearer {applicant_token}"}
    res_app = client.get("/api/v1/admin/user-approvals", headers=app_headers)
    assert res_app.status_code == 403

    # Officer gets 403
    off_headers = {"Authorization": f"Bearer {officer_token}"}
    res_off = client.get("/api/v1/admin/user-approvals", headers=off_headers)
    assert res_off.status_code == 403


def test_duplicate_email_registration_rejected(client: TestClient):
    duplicate_email = f"dup_{uuid.uuid4().hex[:6]}@example.gov.in"
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "First User",
            "email": duplicate_email,
            "password": "Password@123",
        },
    )

    # Second registration with exact same email
    res2 = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Second User",
            "email": duplicate_email,
            "password": "Password@123",
        },
    )
    assert res2.status_code == 409
    assert "already exists" in res2.json()["error"].lower()


def test_registration_validation_rules(client: TestClient):
    # 1. Weak password (no special char)
    res_weak = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Password123",
        },
    )
    assert res_weak.status_code in [400, 422]

    # 2. Short password (< 8 chars)
    res_short = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Pass@1",
        },
    )
    assert res_short.status_code in [400, 422]

    # 3. Invalid Indian mobile number
    res_phone = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "phone": "12345",
            "password": "Password@123",
        },
    )
    assert res_phone.status_code in [400, 422]

    # 4. Invalid full name with numbers/symbols
    res_name = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "User123<>",
            "email": f"test_{uuid.uuid4().hex[:6]}@example.com",
            "password": "Password@123",
        },
    )
    assert res_name.status_code in [400, 422]


def test_public_registration_never_trusts_role(client: TestClient):
    # Even if an attacker passes role=OFFICER to /register, an APPLICANT is created
    attacker_email = f"attacker_{uuid.uuid4().hex[:6]}@example.com"
    res = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Attacker Trying Officer",
            "email": attacker_email,
            "password": "Password@123",
            "role": "OFFICER",
        },
    )
    assert res.status_code == 201
    assert res.json()["role"] == "APPLICANT"
    assert res.json()["account_status"] == "ACTIVE"

