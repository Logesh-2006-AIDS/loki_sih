import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.application import Application
from app.core.enums import ApplicationStatus
from app.services.rules_engine import RulesEngine


# ---------------------------------------------------------------------------
# Autouse fixture to clean up all isolated TEST_% schemes after each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def cleanup_test_schemes(db: Session):
    yield
    # Delete any test schemes created during the test run
    test_schemes = db.query(Scheme).filter(Scheme.scheme_code.like("TEST_%")).all()
    for s in test_schemes:
        db.delete(s)
    db.commit()


# ---------------------------------------------------------------------------
# Test Helper to create an isolated Scheme for tests
# ---------------------------------------------------------------------------

def create_isolated_scheme(client: TestClient, admin_token: str, rules=None) -> dict:
    code = f"TEST_{uuid.uuid4().hex[:6].upper()}"
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "scheme_code": code,
        "name": f"Automated Test Scheme ({code})",
        "description": "Isolated scheme for automated testing",
        "scheme_version": "1.0",
        "is_demo": True,
        "eligibility_rules": rules or {
            "rules": [
                {
                    "field": "community",
                    "operator": "equals",
                    "value": "ST",
                    "label": "Community",
                    "pass_message": "Community verified: ST.",
                    "fail_message": "Must belong to ST.",
                },
                {
                    "field": "min_qualifying_percentage",
                    "operator": "greater_than_or_equal",
                    "value": 55.0,
                    "label": "Qualifying Marks",
                    "pass_message": "Marks >= 55%.",
                    "fail_message": "Marks must be at least 55%.",
                },
            ]
        },
        "form_schema": {},
        "required_documents": {},
        "scoring_weights": {},
    }
    res = client.post("/api/v1/schemes/", headers=headers, json=payload)
    assert res.status_code == 201, res.text
    return res.json()


# ---------------------------------------------------------------------------
# Test 1 & 2: Public Scheme Discovery & Details
# ---------------------------------------------------------------------------

def test_list_active_schemes_phase1(client: TestClient):
    res = client.get("/api/v1/schemes/")
    assert res.status_code == 200
    schemes = res.json()
    assert len(schemes) >= 2
    for s in schemes:
        assert "scheme_code" in s
        assert "scheme_version" in s
        assert "active_version_id" in s
        assert s["active_version_id"] is not None
        assert s["is_demo"] is True


def test_get_scheme_detail_with_active_version(client: TestClient):
    list_res = client.get("/api/v1/schemes/")
    nfst = next(s for s in list_res.json() if s["scheme_code"] == "NFST")
    scheme_id = nfst["id"]

    res = client.get(f"/api/v1/schemes/{scheme_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == scheme_id
    assert "active_version" in data
    assert data["active_version"]["scheme_version"] == "1.0"
    assert data["versions_count"] >= 1
    assert "eligibility_rules" in data["active_version"]
    assert "required_documents" in data["active_version"]


# ---------------------------------------------------------------------------
# Test 3 & 4: Multiple Versions & Uniqueness Constraint
# ---------------------------------------------------------------------------

def test_multiple_scheme_versions_coexist(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    scheme = create_isolated_scheme(client, admin_token)
    scheme_id = scheme["id"]

    # Create version 1.1
    create_res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={
            "scheme_version": "1.1",
            "name": f"{scheme['name']} v1.1",
            "description": "Updated prototype version for coexistence test",
            "is_demo": True,
            "eligibility_rules": {"min_qualifying_percentage": 50.0},
        },
    )
    assert create_res.status_code == 201, create_res.text
    v1_1 = create_res.json()
    assert v1_1["scheme_version"] == "1.1"

    # List versions of this scheme
    versions_res = client.get(f"/api/v1/schemes/{scheme_id}/versions")
    assert versions_res.status_code == 200
    versions = versions_res.json()
    version_numbers = [v["scheme_version"] for v in versions]
    assert "1.0" in version_numbers
    assert "1.1" in version_numbers


def test_scheme_version_uniqueness(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    scheme = create_isolated_scheme(client, admin_token)
    scheme_id = scheme["id"]

    # Attempt to create duplicate version 1.0
    res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={
            "scheme_version": "1.0",
            "name": "Duplicate 1.0",
        },
    )
    assert res.status_code == 409  # Conflict / Duplicate


# ---------------------------------------------------------------------------
# Test 5: Locked Scheme Version Immutability
# ---------------------------------------------------------------------------

def test_locked_scheme_version_cannot_be_modified(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    scheme = create_isolated_scheme(client, admin_token)
    scheme_id = scheme["id"]

    # Create a version to lock
    v_res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={
            "scheme_version": "2.0",
            "name": "Lockable Version",
            "eligibility_rules": {"minimum_marks": 60},
        },
    )
    assert v_res.status_code == 201
    v_id = v_res.json()["id"]

    # Lock the version
    lock_res = client.post(f"/api/v1/schemes/versions/{v_id}/lock", headers=headers)
    assert lock_res.status_code == 200
    assert lock_res.json()["is_locked"] is True

    # Attempt to modify locked version -> must fail with 400
    edit_res = client.put(
        f"/api/v1/schemes/versions/{v_id}",
        headers=headers,
        json={"name": "Modified After Lock"},
    )
    assert edit_res.status_code == 400
    assert "locked" in edit_res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 6, 7 & 8: RBAC Permissions for Scheme Configuration
# ---------------------------------------------------------------------------

def test_applicant_cannot_modify_scheme(client: TestClient, applicant_token: str):
    headers = {"Authorization": f"Bearer {applicant_token}"}
    list_res = client.get("/api/v1/schemes/")
    scheme_id = list_res.json()[0]["id"]

    # Try to create a version as applicant
    res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={"scheme_version": "9.9-hack"},
    )
    assert res.status_code == 403


def test_officer_cannot_modify_scheme(client: TestClient, officer_token: str):
    headers = {"Authorization": f"Bearer {officer_token}"}
    list_res = client.get("/api/v1/schemes/")
    scheme_id = list_res.json()[0]["id"]

    # Try to create a version as officer
    res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={"scheme_version": "9.9-officer-hack"},
    )
    assert res.status_code == 403


def test_admin_can_manage_scheme_versions(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    scheme = create_isolated_scheme(client, admin_token)
    scheme_id = scheme["id"]

    # Admin creates version
    res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={
            "scheme_version": "3.0",
            "name": "Admin Managed Version",
            "eligibility_rules": {"min_qualifying_percentage": 58.0},
        },
    )
    assert res.status_code == 201
    v_id = res.json()["id"]

    # Admin updates unlocked version
    update_res = client.put(
        f"/api/v1/schemes/versions/{v_id}",
        headers=headers,
        json={"name": "Admin Managed Version Renamed"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Admin Managed Version Renamed"


# ---------------------------------------------------------------------------
# Test 9 & 10: Deterministic Rules Engine Operators & Failure Explanations
# ---------------------------------------------------------------------------

def test_rules_engine_all_operators():
    rules = {
        "rules": [
            {"field": "cat", "operator": "equals", "value": "ST"},
            {"field": "status", "operator": "not_equals", "value": "BANNED"},
            {"field": "score", "operator": "greater_than", "value": 50},
            {"field": "min_pct", "operator": "greater_than_or_equal", "value": 55.0},
            {"field": "fine", "operator": "less_than", "value": 100},
            {"field": "income", "operator": "less_than_or_equal", "value": 600000},
            {"field": "degree", "operator": "in", "value": ["M.Phil", "Ph.D."]},
            {"field": "pan", "operator": "required", "value": None},
        ]
    }

    # All pass
    passing_answers = {
        "cat": "ST",
        "status": "ACTIVE",
        "score": 51,
        "min_pct": 55.0,
        "fine": 0,
        "income": 500000,
        "degree": "Ph.D.",
        "pan": "ABCDE1234F",
    }
    result = RulesEngine.evaluate(rules, passing_answers)
    assert result.eligible is True
    assert len(result.checks) == 8
    assert all(c.passed for c in result.checks)
    assert "appear to meet" in result.summary_message

    # One fails (income)
    failing_answers = dict(passing_answers)
    failing_answers["income"] = 700000
    result_fail = RulesEngine.evaluate(rules, failing_answers)
    assert result_fail.eligible is False
    income_check = next(c for c in result_fail.checks if c.rule == "income")
    assert income_check.passed is False
    assert "exceeds" in income_check.message or "<=" in income_check.operator
    assert "may not meet" in result_fail.summary_message


def test_self_eligibility_failure_reasons(client: TestClient):
    list_res = client.get("/api/v1/schemes/")
    scheme_nfst = next(s for s in list_res.json() if s["scheme_code"] == "NFST")

    # Evaluate with non-ST and income exceeding ceiling
    res = client.post(
        f"/api/v1/schemes/{scheme_nfst['id']}/check-eligibility",
        json={
            "answers": {
                "community": "GENERAL",
                "min_qualifying_percentage": 50.0,
                "max_annual_family_income": 900000,
                "course_type": "Diploma",
            }
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["eligible"] is False
    assert "may not meet" in data["summary_message"]
    assert "indicative only" in data["disclaimer"].lower()

    # Check reason messages
    checks = {c["rule"]: c for c in data["checks"]}
    assert checks["community"]["passed"] is False
    assert checks["min_qualifying_percentage"]["passed"] is False
    assert checks["max_annual_family_income"]["passed"] is False


# ---------------------------------------------------------------------------
# Test 11: Self-Check Does Not Modify Application Data
# ---------------------------------------------------------------------------

def test_self_check_does_not_modify_application_data(client: TestClient, db: Session):
    apps_before = db.query(Application).count()

    list_res = client.get("/api/v1/schemes/")
    scheme_id = list_res.json()[0]["id"]

    # Run check
    res = client.post(
        f"/api/v1/schemes/{scheme_id}/check-eligibility",
        json={"answers": {"community": "ST", "min_qualifying_percentage": 65.0}},
    )
    assert res.status_code == 200

    # Ensure application count is unchanged
    apps_after = db.query(Application).count()
    assert apps_before == apps_after


# ---------------------------------------------------------------------------
# Test 12: Invalid Rule Configuration Handled Safely
# ---------------------------------------------------------------------------

def test_invalid_rule_configuration_handled_safely():
    malformed_rules = {
        "rules": [
            {"field": "score", "operator": "unsupported_op", "value": 100},
            {"field": "age", "operator": "greater_than", "value": "non-numeric"},
            "not-even-a-dict",
        ]
    }
    # Should not throw uncaught exception
    result = RulesEngine.evaluate(malformed_rules, {"score": 50, "age": "abc"})
    assert result.eligible is False
    assert len(result.checks) == 3
    assert all(not c.passed for c in result.checks)


# ---------------------------------------------------------------------------
# Test 13 & 14: Application Version Binding & Frozen Rules Snapshot
# ---------------------------------------------------------------------------

def test_application_version_binding_and_frozen_snapshot(
    client: TestClient, db: Session, applicant_token: str, admin_token: str
):
    applicant_headers = {"Authorization": f"Bearer {applicant_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create an isolated scheme
    scheme = create_isolated_scheme(client, admin_token)
    scheme_id = scheme["id"]
    initial_version_id = scheme["active_version_id"]

    # 2. Applicant creates a draft application -> binds active version
    draft_res = client.post(
        "/api/v1/applications/",
        headers=applicant_headers,
        json={
            "scheme_id": scheme_id,
            "form_data": {"personal": {"name": "Test Scholar"}},
        },
    )
    assert draft_res.status_code == 201
    app_id = draft_res.json()["id"]

    # 3. Applicant submits application -> freezes snapshot of active version
    submit_res = client.post(
        f"/api/v1/applications/{app_id}/submit",
        headers=applicant_headers,
    )
    assert submit_res.status_code == 200
    app_data = submit_res.json()
    assert app_data["scheme_version_id"] == initial_version_id
    assert app_data["frozen_rules_snapshot"] is not None

    # 4. Admin creates and activates Version 1.9 with different rules
    new_v_res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=admin_headers,
        json={
            "scheme_version": "1.9",
            "name": "Future Active Version",
            "eligibility_rules": {"min_qualifying_percentage": 75.0},
        },
    )
    assert new_v_res.status_code == 201
    new_v_id = new_v_res.json()["id"]

    # Activate version 1.9
    act_res = client.post(
        f"/api/v1/schemes/versions/{new_v_id}/activate", headers=admin_headers
    )
    assert act_res.status_code == 200

    # 5. Verify that previously submitted application is STILL bound to initial_version_id!
    persisted_app = db.query(Application).filter(Application.id == uuid.UUID(app_id)).first()
    assert str(persisted_app.scheme_version_id) == str(initial_version_id)
    assert persisted_app.scheme_version_id != uuid.UUID(new_v_id)
    assert persisted_app.frozen_rules_snapshot != {"min_qualifying_percentage": 75.0}


# ---------------------------------------------------------------------------
# Test 15: Single Active Version Transactional Enforcement
# ---------------------------------------------------------------------------

def test_single_active_version_enforcement(
    client: TestClient, db: Session, admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}
    scheme = create_isolated_scheme(client, admin_token)
    scheme_id = scheme["id"]

    # Create version A and activate
    va_res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={"scheme_version": "4.0A", "name": "Version A"},
    )
    va_id = va_res.json()["id"]
    client.post(f"/api/v1/schemes/versions/{va_id}/activate", headers=headers)

    # Create version B and activate
    vb_res = client.post(
        f"/api/v1/schemes/{scheme_id}/versions",
        headers=headers,
        json={"scheme_version": "4.0B", "name": "Version B"},
    )
    vb_id = vb_res.json()["id"]
    client.post(f"/api/v1/schemes/versions/{vb_id}/activate", headers=headers)

    # Query DB directly to verify Version A is now inactive and Version B is active
    va = db.query(SchemeVersion).filter(SchemeVersion.id == uuid.UUID(va_id)).first()
    vb = db.query(SchemeVersion).filter(SchemeVersion.id == uuid.UUID(vb_id)).first()
    assert va.is_active is False
    assert vb.is_active is True

    # Count active versions for this scheme in DB -> must be exactly 1!
    active_count = (
        db.query(SchemeVersion)
        .filter(
            SchemeVersion.scheme_id == uuid.UUID(scheme_id),
            SchemeVersion.is_active.is_(True),
        )
        .count()
    )
    assert active_count == 1
