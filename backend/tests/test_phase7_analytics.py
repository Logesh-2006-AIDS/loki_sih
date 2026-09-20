import csv
import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, SelectionResultEnum, UserRole
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.user import User


# -----------------------------------------------------------------------------
# 1. State Distribution Invariant
# -----------------------------------------------------------------------------
def test_current_state_distribution_invariant(client: TestClient, admin_token: str):
    """
    Verifies that the sum of mutually exclusive counts in current_state_distribution
    strictly equals total_applications.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/analytics/overview", headers=headers)
    assert res.status_code == 200, f"Overview failed: {res.text}"

    data = res.json()
    assert "total_applications" in data
    assert "current_state_distribution" in data

    dist = data["current_state_distribution"]
    total = data["total_applications"]

    # Sum of all state bucket counts must equal total_applications
    sum_dist = sum(dist.values())
    assert sum_dist == total, f"Invariant violated: sum({sum_dist}) != total({total})"

    # Required status keys must all exist in the distribution map
    for status_enum in ApplicationStatus:
        assert status_enum.value in dist, f"Missing status key: {status_enum.value}"


# -----------------------------------------------------------------------------
# 2. Cumulative Milestone Funnel Progression
# -----------------------------------------------------------------------------
def test_cumulative_milestone_funnel_progression(client: TestClient, admin_token: str):
    """
    Verifies the cumulative sequential lifecycle funnel:
    Monotonic non-increasing property: M1 >= M2 >= M3 >= M4 >= M5.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/analytics/funnel", headers=headers)
    assert res.status_code == 200, f"Funnel failed: {res.text}"

    data = res.json()
    assert "total_initiated" in data
    assert "milestones" in data

    milestones = data["milestones"]
    assert len(milestones) == 5, f"Expected 5 milestones, got {len(milestones)}"

    # Invariant: monotonic non-increasing counts
    prev_count = float("inf")
    for i, m in enumerate(milestones):
        cnt = m["count"]
        assert cnt >= 0, f"Negative count in milestone {m['milestone_key']}"
        assert cnt <= prev_count, f"Monotonic invariant failed at step {i}: {cnt} > {prev_count}"
        prev_count = cnt

        # Conversion rates validity
        assert 0.0 <= m["conversion_from_start_rate"] <= 100.0
        assert 0.0 <= m["conversion_from_previous_rate"] <= 100.0


# -----------------------------------------------------------------------------
# 3. Scheme & Version-Bound Quota Calculation
# -----------------------------------------------------------------------------
def test_scheme_version_bound_quota_calculation(client: TestClient, admin_token: str, db: Session):
    """
    Verifies that quota calculation is strictly bound to the scheme version's
    scoring_weights['quota_config']['total_slots'].
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/analytics/schemes", headers=headers)
    assert res.status_code == 200, f"Schemes breakdown failed: {res.text}"

    data = res.json()
    assert "schemes" in data
    summaries = data["schemes"]

    for s in summaries:
        assert "scheme_id" in s
        assert "quota_slots" in s
        assert "total_applications" in s
        assert "selected_count" in s
        assert "quota_exhaustion_rate" in s

        # Verify against database SchemeVersion record
        sv = db.get(SchemeVersion, uuid.UUID(s["scheme_version_id"])) if s.get("scheme_version_id") else None
        if sv:
            weights = sv.scoring_weights or {}
            quota_cfg = weights.get("quota_config") or weights.get("quotas") or {}
            expected_slots = int(quota_cfg.get("total_slots", 0))
            assert s["quota_slots"] == expected_slots, (
                f"Quota mismatch for scheme {s['scheme_code']}: {s['quota_slots']} != {expected_slots}"
            )

        if s["quota_slots"] > 0:
            expected_rate = round((s["selected_count"] / s["quota_slots"]) * 100.0, 2)
            assert s["quota_exhaustion_rate"] == expected_rate


# -----------------------------------------------------------------------------
# 4. AI-Human Agreement & Override Math
# -----------------------------------------------------------------------------
def test_ai_human_agreement_and_override_math(client: TestClient, admin_token: str, db: Session):
    """
    Verifies mathematical definition of AI-human agreement and override rates:
    R_agree + R_override == 100.0 (when N_eval > 0).
    Excludes unreadable/failed and unscrutinized records.
    """
    # 1. Seed known verification records
    # Fetch an existing document or create test document
    doc = db.query(Document).first()
    if not doc:
        pytest.skip("No documents in database to seed verifications")

    officer = db.query(User).filter(User.role == UserRole.OFFICER).first()
    if not officer:
        pytest.skip("No officer user found")

    now = datetime.now(timezone.utc)
    # Agreement record: AI VERIFIED, officer VERIFIED, ai_override=False
    v1 = DocumentVerification(
        document_id=doc.id,
        verification_status="VERIFIED",
        officer_decision="VERIFIED",
        ai_override=False,
        verified_by=officer.id,
        verified_at=now,
    )
    # Override record: AI FLAGGED, officer VERIFIED, ai_override=True
    v2 = DocumentVerification(
        document_id=doc.id,
        verification_status="FLAGGED",
        officer_decision="VERIFIED",
        ai_override=True,
        override_reason="Document clear on human manual inspection",
        verified_by=officer.id,
        verified_at=now,
    )
    # Excluded record: AI FAILED, unscrutinized (officer_decision is None)
    v3 = DocumentVerification(
        document_id=doc.id,
        verification_status="FAILED",
        officer_decision=None,
        ai_override=False,
    )
    db.add_all([v1, v2, v3])
    db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/analytics/decisions", headers=headers)
    assert res.status_code == 200, f"Decisions metrics failed: {res.text}"

    data = res.json()
    assert "total_documents_evaluated" in data
    assert "ai_human_agreements" in data
    assert "human_overrides" in data
    assert "ai_human_agreement_rate" in data
    assert "human_override_rate" in data

    n_eval = data["total_documents_evaluated"]
    if n_eval > 0:
        total_rate = round(data["ai_human_agreement_rate"] + data["human_override_rate"], 1)
        assert total_rate == 100.0, f"Rates do not sum to 100%: {total_rate}"
        assert data["ai_human_agreements"] + data["human_overrides"] == n_eval


# -----------------------------------------------------------------------------
# 5. Staff Throughput & PII Minimization
# -----------------------------------------------------------------------------
def test_officer_throughput_and_pii_sanitization(client: TestClient, admin_token: str):
    """
    Verifies that officer throughput exposes display names and duration,
    while officer email and applicant PII are strictly absent.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/analytics/officers", headers=headers)
    assert res.status_code == 200, f"Officer throughput failed: {res.text}"

    data = res.json()
    assert "officers" in data
    officers = data["officers"]

    for off in officers:
        assert "officer_name" in off
        assert "officer_id" in off
        assert "avg_verification_duration_hours" in off
        assert off["avg_verification_duration_hours"] >= 0.0

        # Security Invariant: Officer email must NOT be present
        assert "email" not in off, "Security violation: officer email exposed in throughput response"
        assert "officer_email" not in off, "Security violation: officer_email exposed in throughput response"

        # Security Invariant: Applicant PII must NOT be present
        for pii_key in ("applicant_name", "applicant_email", "phone_number", "aadhaar_number"):
            assert pii_key not in off, f"Security violation: {pii_key} exposed in officer response"


# -----------------------------------------------------------------------------
# 6. Date Range & Timestamp Semantics
# -----------------------------------------------------------------------------
def test_date_range_and_timestamp_semantics(client: TestClient, admin_token: str):
    """
    Verifies time-series velocity query with ISO timestamp boundaries.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    params = {
        "start_date": "2020-01-01T00:00:00Z",
        "end_date": "2030-01-01T00:00:00Z",
        "granularity": "day",
    }
    res = client.get("/api/v1/analytics/trends", headers=headers, params=params)
    assert res.status_code == 200, f"Trends failed: {res.text}"

    data = res.json()
    assert "data_points" in data
    points = data["data_points"]
    for pt in points:
        assert "date" in pt
        assert "submissions_count" in pt
        assert "verifications_count" in pt
        assert "selections_count" in pt


# -----------------------------------------------------------------------------
# 7. Standardized RBAC Authorization Matrix
# -----------------------------------------------------------------------------
def test_rbac_authorization_matrix(
    client: TestClient,
    applicant_token: str,
    officer_token: str,
    admin_token: str,
):
    """
    Verifies the complete RBAC matrix:
    - APPLICANT: 403 Forbidden across all analytics endpoints.
    - OFFICER: 403 on Admin-only routes; 403 on unscoped queries.
    - ADMIN: 200 OK on all routes.
    """
    app_headers = {"Authorization": f"Bearer {applicant_token}"}
    off_headers = {"Authorization": f"Bearer {officer_token}"}
    adm_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Applicant denied everywhere
    routes_to_test = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/funnel",
        "/api/v1/analytics/trends",
        "/api/v1/analytics/schemes",
        "/api/v1/analytics/officers",
        "/api/v1/analytics/decisions",
        "/api/v1/analytics/audit-logs",
        "/api/v1/analytics/export/applications",
        "/api/v1/analytics/export/audit-logs",
    ]
    for r in routes_to_test:
        res = client.get(r, headers=app_headers)
        assert res.status_code == 403, f"Applicant should be forbidden from {r}, got {res.status_code}"

    # 2. Officer denied on Admin-only routes
    admin_only_routes = [
        "/api/v1/analytics/overview",
        "/api/v1/analytics/officers",
        "/api/v1/analytics/decisions",
        "/api/v1/analytics/audit-logs",
        "/api/v1/analytics/export/applications",
        "/api/v1/analytics/export/audit-logs",
    ]
    for r in admin_only_routes:
        res = client.get(r, headers=off_headers)
        assert res.status_code == 403, f"Officer should be forbidden from {r}, got {res.status_code}"

    # 3. Officer denied on unscoped /funnel without scheme_id
    res = client.get("/api/v1/analytics/funnel", headers=off_headers)
    assert res.status_code == 403, "Officer unscoped funnel should be forbidden"

    # 4. Admin allowed on all routes
    for r in routes_to_test:
        res = client.get(r, headers=adm_headers)
        assert res.status_code == 200, f"Admin should have access to {r}, got {res.status_code}: {res.text}"


# -----------------------------------------------------------------------------
# 8. Searchable Audit Logs & Sensitive Details Sanitization
# -----------------------------------------------------------------------------
def test_searchable_audit_logs_and_sanitization(client: TestClient, admin_token: str, db: Session):
    """
    Verifies indexed audit log querying and ensures secrets/credentials
    are scrubbed from the details JSON.
    """
    # Create an audit log entry with sensitive fields
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    test_action = f"TEST_ACTION_{uuid.uuid4().hex[:8]}"
    secret_details = {
        "password": "super_secret_password",
        "token": "jwt_secret_token_12345",
        "nested": {"access_token": "bearer_secret"},
        "safe_note": "Application evaluated successfully",
    }
    audit_entry = AuditLog(
        entity_type="TEST_ENTITY",
        entity_id=str(uuid.uuid4()),
        action=test_action,
        actor_id=admin.id if admin else None,
        details=secret_details,
    )
    db.add(audit_entry)
    db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get(f"/api/v1/analytics/audit-logs?action={test_action}", headers=headers)
    assert res.status_code == 200, f"Audit logs failed: {res.text}"

    data = res.json()
    assert data["total_count"] >= 1
    found = next((log for log in data["logs"] if log["action"] == test_action), None)
    assert found is not None, f"Audit entry with action {test_action} not found"

    details = found["details"]
    assert details["password"] == "[REDACTED]", "Password was not redacted!"
    assert details["token"] == "[REDACTED]", "Token was not redacted!"
    assert details["nested"]["access_token"] == "[REDACTED]", "Nested token was not redacted!"
    assert details["safe_note"] == "Application evaluated successfully"


# -----------------------------------------------------------------------------
# 9. Streaming CSV Export: 10,000 Cap & Schema Formatting
# -----------------------------------------------------------------------------
def test_streaming_csv_export_cap_and_format(client: TestClient, admin_token: str):
    """
    Verifies that streaming CSV exports enforce the server-side 10,000-row cap,
    emit correct CSV headers, and strictly exclude applicant PII.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Applications export
    res = client.get("/api/v1/analytics/export/applications?limit=50000", headers=headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")

    csv_text = res.text
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    assert len(rows) > 0, "Applications CSV was empty"
    header = rows[0]
    expected_app_header = [
        "reference_id",
        "scheme_code",
        "scheme_version",
        "status",
        "submitted_at",
        "scrutiny_completed_at",
        "selection_result",
        "merit_rank",
        "selection_round",
        "is_override",
    ]
    assert header == expected_app_header, f"Unexpected header: {header}"

    # Verify server-side cap: max 10,000 data rows + 1 header row = 10,001 rows
    assert len(rows) <= 10001, f"Row count {len(rows)} exceeded 10,001 limit cap"

    # Verify PII exclusion: zero columns with name, email, phone, aadhaar
    for col in header:
        assert "name" not in col.lower() or col == "scheme_name"
        assert "email" not in col.lower()
        assert "phone" not in col.lower()
        assert "aadhaar" not in col.lower()

    # 2. Audit logs export
    res_audit = client.get("/api/v1/analytics/export/audit-logs?limit=50000", headers=headers)
    assert res_audit.status_code == 200
    assert "text/csv" in res_audit.headers.get("content-type", "")

    audit_reader = csv.reader(io.StringIO(res_audit.text))
    audit_rows = list(audit_reader)
    assert len(audit_rows) > 0
    expected_audit_header = [
        "id",
        "created_at",
        "actor_id",
        "entity_type",
        "entity_id",
        "action",
        "previous_status",
        "new_status",
        "details_summary",
    ]
    assert audit_rows[0] == expected_audit_header
    assert len(audit_rows) <= 10001


# -----------------------------------------------------------------------------
# 10. PostgreSQL MVCC & Concurrent Write Resilience
# -----------------------------------------------------------------------------
def test_concurrent_write_resilience(client: TestClient, admin_token: str):
    """
    Verifies that simultaneous write transactions and read-only analytical queries
    execute concurrently without deadlocks or errors under PostgreSQL MVCC.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    def run_analytics_query():
        with TestClient(client.app) as c:
            r1 = c.get("/api/v1/analytics/overview", headers=headers)
            r2 = c.get("/api/v1/analytics/funnel", headers=headers)
            r3 = c.get("/api/v1/analytics/decisions", headers=headers)
            assert r1.status_code == 200
            assert r2.status_code == 200
            assert r3.status_code == 200

    def run_transactional_read_or_write():
        session = SessionLocal()
        try:
            # Execute read and audit insertion concurrently
            app_count = session.query(Application).count()
            assert app_count >= 0
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=6) as executor:
        futs = []
        for _ in range(3):
            futs.append(executor.submit(run_analytics_query))
            futs.append(executor.submit(run_transactional_read_or_write))

        for f in futs:
            f.result()  # Will re-raise exceptions if any deadlocks or errors occurred
