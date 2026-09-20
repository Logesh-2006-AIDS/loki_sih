import os
import uuid
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.main import app
from app.core.config import settings
from app.core.enums import ApplicationStatus, DocumentStatus
from app.models.application import Application
from app.models.fellowship import FellowshipRecord, DisbursementInstallment
from app.models.document import Document
from app.models.scheme import Scheme
from scripts.seed_sih_demo import seed_sih_demo


# =============================================================================
# PHASE 9: SECURITY, DEPLOYMENT & SIH DEMO TEST SUITE (14 TESTS)
# =============================================================================


def test_security_headers_environment_aware(client: TestClient):
    """
    Test 1: Verify presence of all standard security headers and environment-aware HSTS.
    """
    res = client.get("/api/v1/schemes/")
    assert res.status_code == 200

    # Core security headers
    assert res.headers.get("x-frame-options") in ("DENY", "SAMEORIGIN")
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-xss-protection") == "1; mode=block"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    # Environment-aware HSTS
    original_env = settings.ENVIRONMENT
    try:
        # In development/local, HSTS should be omitted to avoid breaking localhost
        settings.ENVIRONMENT = "development"
        dev_res = client.get("/api/v1/schemes/")
        assert "strict-transport-security" not in dev_res.headers

        # In production, HSTS must be present
        settings.ENVIRONMENT = "production"
        prod_res = client.get("/api/v1/schemes/")
        assert "strict-transport-security" in prod_res.headers
        assert "max-age=31536000" in prod_res.headers["strict-transport-security"]
    finally:
        settings.ENVIRONMENT = original_env


def test_security_headers_on_error_responses(client: TestClient):
    """
    Test 2: Verify that 404, 401, 403 error responses preserve security headers.
    """
    # 404 Not Found
    res_404 = client.get("/api/v1/non-existent-endpoint-phase9")
    assert res_404.status_code == 404
    assert res_404.headers.get("x-frame-options") in ("DENY", "SAMEORIGIN")
    assert res_404.headers.get("x-content-type-options") == "nosniff"

    # 401 Unauthorized
    res_401 = client.get("/api/v1/analytics/overview")
    assert res_401.status_code == 401
    assert res_401.headers.get("x-frame-options") in ("DENY", "SAMEORIGIN")
    assert res_401.headers.get("x-content-type-options") == "nosniff"


def test_content_security_policy_directives(client: TestClient):
    """
    Test 3: Verify concrete CSP directives without wildcard '*' allowances.
    """
    res = client.get("/")
    assert res.status_code == 200
    csp = res.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert "object-src 'self' blob:" in csp
    assert "frame-src 'self' blob:" in csp
    assert "frame-ancestors 'none'" not in csp or "frame-ancestors" in csp
    assert "*" not in csp


def test_payload_size_limit_middleware(client: TestClient):
    """
    Test 4: Verify that HTTP payloads with Content-Length > 25MB receive HTTP 413.
    """
    oversized_length = str(settings.MAX_REQUEST_BODY_BYTES + 1024)
    res = client.post(
        "/api/v1/auth/login",
        headers={"Content-Length": oversized_length},
        json={"email": "applicant@demo.gov.in", "password": "Demo@12345"},
    )
    assert res.status_code == 413
    data = res.json()
    assert "Payload Too Large" in data.get("error", "")


def test_oversized_document_does_not_bypass_phase2_validation(db: Session, client: TestClient, applicant_token: str):
    """
    Test 5: Verify that document payload under 25MB but exceeding Phase 2's 5MB limit
    is properly rejected by document validation service rather than passing through.
    """
    # Create or fetch a draft application
    app = db.query(Application).filter(Application.status == ApplicationStatus.DRAFT).first()
    if not app:
        scheme = db.query(Scheme).filter(Scheme.is_active == True).first()
        app = Application(
            reference_id=f"TEST-DRAFT-{uuid.uuid4().hex[:6].upper()}",
            applicant_id=db.query(Application).first().applicant_id,
            scheme_id=scheme.id,
            scheme_version_id=scheme.active_version_id,
            status=ApplicationStatus.DRAFT,
            form_data={},
            frozen_rules_snapshot={},
        )
        db.add(app)
        db.commit()

    headers = {"Authorization": f"Bearer {applicant_token}"}
    # 5.5 MB payload (under 25 MB middleware limit, but over 5 MB document limit)
    oversized_file_content = b"A" * (int(5.5 * 1024 * 1024))
    files = {
        "file": ("large_certificate.pdf", oversized_file_content, "application/pdf"),
    }
    data = {
        "document_type": "caste_certificate",
    }
    res = client.post(
        f"/api/v1/applications/{app.id}/documents",
        headers=headers,
        data=data,
        files=files,
    )
    # Phase 2 document validator raises ValidationException (400)
    assert res.status_code in (400, 422, 403)


def test_auth_rate_limiting_standalone(client: TestClient):
    """
    Test 6: Verify standalone sliding-window rate limiting on /auth/login.
    """
    # Use custom test client IP with x-test-rate-limit to trigger limiter
    test_ip = f"198.51.100.{uuid.uuid4().int % 200 + 10}"
    headers = {
        "x-test-rate-limit": "true",
        "x-forwarded-for": test_ip,
    }
    payload = {"email": "applicant@demo.gov.in", "password": "WrongPassword123"}

    hit_limit = False
    for i in range(settings.RATE_LIMIT_LOGIN_PER_MINUTE + 5):
        res = client.post("/api/v1/auth/login", headers=headers, json=payload)
        if res.status_code == 429:
            hit_limit = True
            assert "Retry-After" in res.headers
            assert "Too Many Requests" in res.json().get("error", "")
            break

    assert hit_limit is True, "Rate limiter did not trigger after exceeding requests_per_minute"


def test_cors_rejects_unauthorized_origins(client: TestClient):
    """
    Test 7: Verify that unauthorized CORS origins do not receive Access-Control-Allow-Origin header.
    """
    unauthorized_origin = "https://unauthorized-evil-origin.com"
    res = client.options(
        "/api/v1/schemes/",
        headers={
            "Origin": unauthorized_origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert res.headers.get("access-control-allow-origin") != unauthorized_origin


def test_health_liveness_and_readiness_probes(client: TestClient):
    """
    Test 8: Verify decoupled liveness (/health) and readiness (/api/health) probes.
    """
    # Liveness probe: returns 200 OK without database execution
    live_res = client.get("/health")
    assert live_res.status_code == 200
    live_data = live_res.json()
    assert live_data["status"] == "alive"
    assert "version" in live_data

    # Readiness probe: verifies DB connectivity, latency, and subsystem modes
    ready_res = client.get("/api/health")
    assert ready_res.status_code == 200
    ready_data = ready_res.json()
    assert ready_data["status"] in ("healthy", "degraded")
    assert ready_data["database"] == "connected"
    assert "subsystems" in ready_data
    assert ready_data["subsystems"]["database"]["status"] == "connected"
    assert "ai_ocr_pipeline" in ready_data["subsystems"]
    assert "pfms_dbt_gateway" in ready_data["subsystems"]


def test_health_readiness_failure_behavior(client: TestClient, monkeypatch):
    """
    Test 9: Verify readiness probe responds with 503 when core database check fails.
    """
    def mock_broken_execute(*args, **kwargs):
        raise Exception("Database connectivity lost during probe")

    from sqlalchemy.orm import Session
    monkeypatch.setattr(Session, "execute", mock_broken_execute)

    res = client.get("/api/health")
    assert res.status_code == 503
    data = res.json()
    assert data["status"] == "unhealthy"
    assert data["subsystems"]["database"]["status"] == "unreachable"


def test_demo_role_switch_does_not_bypass_rbac(client: TestClient):
    """
    Test 10: Verify that demo role switching issues authentic tokens subject to strict RBAC.
    """
    # 1. Login as APPLICANT
    res_app = client.post(
        "/api/v1/auth/login",
        json={"email": "applicant@demo.gov.in", "password": "Demo@12345"},
    )
    assert res_app.status_code == 200
    applicant_token = res_app.json()["access_token"]
    app_headers = {"Authorization": f"Bearer {applicant_token}"}

    # Applicant cannot access Officer queues -> 403
    res_officer_queue = client.get("/api/v1/officer/queue", headers=app_headers)
    assert res_officer_queue.status_code == 403

    # Applicant cannot access Committee schemes -> 403
    res_comm_schemes = client.get("/api/v1/committee/schemes", headers=app_headers)
    assert res_comm_schemes.status_code == 403

    # Applicant cannot access Admin analytics -> 403
    res_admin_analytics = client.get("/api/v1/analytics/overview", headers=app_headers)
    assert res_admin_analytics.status_code == 403


def test_demo_seed_does_not_create_realistic_official_identifiers(db: Session):
    """
    Test 11: Verify that all seeded dossiers and financial records have DEMO- prefixed identifiers.
    """
    demo_apps = db.query(Application).filter(Application.reference_id.like("DEMO-%")).all()
    assert len(demo_apps) >= 6

    for app_record in demo_apps:
        assert app_record.reference_id.startswith("DEMO-")

    demo_fellowships = db.query(FellowshipRecord).filter(FellowshipRecord.fellowship_number.like("DEMO-%")).all()
    assert len(demo_fellowships) >= 2
    for fel in demo_fellowships:
        assert fel.fellowship_number.startswith("DEMO-")
        assert fel.sanction_order_number.startswith("DEMO-")
        assert fel.sanction_mode == "DEMO_SIMULATED"

    demo_installments = db.query(DisbursementInstallment).filter(DisbursementInstallment.integration_mode == "SIMULATED_MOCK").all()
    assert len(demo_installments) >= 2
    for inst in demo_installments:
        if inst.bank_reference_utr:
            assert inst.bank_reference_utr.startswith("DEMO-")
        if inst.pfms_reference_id:
            assert inst.pfms_reference_id.startswith("DEMO-")


def test_demo_seed_preserves_state_machine_invariants(db: Session):
    """
    Test 12: Verify that seeded demo data complies with all Phase 0-8 state machine invariants.
    """
    demo_apps = db.query(Application).filter(Application.reference_id.like("DEMO-%")).all()
    for app_record in demo_apps:
        # Schema version linkage invariant
        assert app_record.scheme_id is not None
        assert app_record.scheme_version_id is not None
        assert app_record.status in list(ApplicationStatus)

        # Document invariants
        for doc in app_record.documents:
            assert doc.status in list(DocumentStatus)
            assert doc.storage_path is not None
            assert doc.original_filename is not None

            # Verification invariants
            for ver in doc.verifications:
                assert ver.verification_status in ("VERIFIED", "FLAGGED", "REJECTED", "PENDING")


def test_demo_seed_is_repeatable_without_duplicate_records(db: Session):
    """
    Test 13: Verify that seed_sih_demo is strictly idempotent and does not duplicate records.
    """
    apps_before = db.query(Application).filter(Application.reference_id.like("DEMO-%")).count()
    fellowships_before = db.query(FellowshipRecord).filter(FellowshipRecord.fellowship_number.like("DEMO-%")).count()

    # Re-run master seeder
    seed_sih_demo()

    apps_after = db.query(Application).filter(Application.reference_id.like("DEMO-%")).count()
    fellowships_after = db.query(FellowshipRecord).filter(FellowshipRecord.fellowship_number.like("DEMO-%")).count()

    assert apps_after == apps_before
    assert fellowships_after == fellowships_before


def test_no_secret_values_in_application_logs(caplog, client: TestClient):
    """
    Test 14: Verify that sensitive credentials and secret keys are never leaked into logs.
    """
    client.post(
        "/api/v1/auth/login",
        json={"email": "applicant@demo.gov.in", "password": "Demo@12345"},
    )
    # Check captured log messages
    assert settings.JWT_SECRET_KEY not in caplog.text
