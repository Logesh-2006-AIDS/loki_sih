import io
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.scheme import Scheme
from app.models.application import Application
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.models.officer_assignment import OfficerAssignment
from app.models.deficiency import Deficiency
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.core.enums import UserRole, ApplicationStatus, DocumentStatus
from app.core.security import get_password_hash


def _get_token(client: TestClient, email: str, password: str = "Demo@12345") -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def _setup_test_environment(client: TestClient, db: Session):
    """Sets up an applicant, an application, and test documents in UNDER_MANUAL_REVIEW."""
    # Ensure active NFST scheme (test documents match NFST requirements)
    scheme = db.query(Scheme).filter(Scheme.scheme_code == "NFST").first()
    assert scheme is not None, "NFST scheme must exist"

    # Ensure applicant
    applicant = db.query(User).filter(User.email == "applicant@demo.gov.in").first()
    assert applicant is not None

    # Ensure global officer
    officer = db.query(User).filter(User.email == "officer@demo.gov.in").first()
    assert officer is not None

    # Global assignment for demo officer
    existing_assign = db.query(OfficerAssignment).filter(OfficerAssignment.officer_id == officer.id).first()
    if not existing_assign:
        assign = OfficerAssignment(officer_id=officer.id, state=None, scheme_id=None, is_active=True)
        db.add(assign)
        db.commit()

    # Create application in UNDER_MANUAL_REVIEW
    app_ref = f"MTA-TEST-{uuid.uuid4().hex[:6].upper()}"
    app = Application(
        reference_id=app_ref,
        applicant_id=applicant.id,
        scheme_id=scheme.id,
        status=ApplicationStatus.UNDER_MANUAL_REVIEW,
        form_data={
            "personal": {"name": "Test Tribal Applicant", "state": "Rajasthan"},
            "state": "Rajasthan",
        },
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    # Create all four required scheme documents
    doc1 = Document(
        application_id=app.id,
        document_type="CASTE_CERTIFICATE",
        original_filename="st_cert.pdf",
        storage_path=f"applications/{app.id}/st_cert.pdf",
        mime_type="application/pdf",
        file_size=1024,
        status=DocumentStatus.VERIFIED,
    )
    doc2 = Document(
        application_id=app.id,
        document_type="INCOME_CERTIFICATE",
        original_filename="income_cert.pdf",
        storage_path=f"applications/{app.id}/income_cert.pdf",
        mime_type="application/pdf",
        file_size=2048,
        status=DocumentStatus.FLAGGED,
    )
    doc3 = Document(
        application_id=app.id,
        document_type="PG_MARKSHEET",
        original_filename="pg_marksheet.pdf",
        storage_path=f"applications/{app.id}/pg_marksheet.pdf",
        mime_type="application/pdf",
        file_size=3072,
        status=DocumentStatus.VERIFIED,
    )
    doc4 = Document(
        application_id=app.id,
        document_type="ADMISSION_LETTER",
        original_filename="admission_letter.pdf",
        storage_path=f"applications/{app.id}/admission_letter.pdf",
        mime_type="application/pdf",
        file_size=4096,
        status=DocumentStatus.VERIFIED,
    )
    db.add_all([doc1, doc2, doc3, doc4])
    db.commit()
    db.refresh(doc1)
    db.refresh(doc2)
    db.refresh(doc3)
    db.refresh(doc4)

    # Create Phase 3 verification records (AI verification state)
    v1 = DocumentVerification(
        document_id=doc1.id,
        verification_status="VERIFIED",
        extracted_fields={"category": {"value": "ST", "confidence": 0.95}},
        flags=[],
        overall_confidence=0.95,
        verification_source="AI",
    )
    v2 = DocumentVerification(
        document_id=doc2.id,
        verification_status="FLAGGED",
        extracted_fields={"annual_income": {"value": "450000", "confidence": 0.85}},
        flags=[{"field": "annual_income", "reason": "Declared 300000, document shows 450000", "severity": "HIGH"}],
        overall_confidence=0.85,
        verification_source="AI",
    )
    v3 = DocumentVerification(
        document_id=doc3.id,
        verification_status="VERIFIED",
        extracted_fields={"percentage_marks": {"value": "68.5", "confidence": 0.92}},
        flags=[],
        overall_confidence=0.92,
        verification_source="AI",
    )
    v4 = DocumentVerification(
        document_id=doc4.id,
        verification_status="VERIFIED",
        extracted_fields={"university_name": {"value": "Delhi University", "confidence": 0.90}},
        flags=[],
        overall_confidence=0.90,
        verification_source="AI",
    )
    db.add_all([v1, v2, v3, v4])
    db.commit()
    db.refresh(v1)
    db.refresh(v2)
    db.refresh(v3)
    db.refresh(v4)

    return {
        "scheme": scheme,
        "applicant": applicant,
        "officer": officer,
        "app": app,
        "doc1": doc1,
        "doc2": doc2,
        "doc3": doc3,
        "doc4": doc4,
        "v1": v1,
        "v2": v2,
        "v3": v3,
        "v4": v4,
    }


# ---------------------------------------------------------------------------
# Test 1: Document Rejection Does NOT Automatically Reject Application
# ---------------------------------------------------------------------------
def test_rejected_document_does_not_automatically_reject_application(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")

    doc_id = env["doc1"].id
    app_id = env["app"].id

    # Officer marks document 1 as REJECTED
    res = client.post(
        f"/api/v1/officer/documents/{doc_id}/decision",
        json={
            "decision": "REJECTED",
            "remarks": "Fake revenue authority seal detected upon visual scrutiny",
        },
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "REJECTED"
    assert data["officer_decision"] == "REJECTED"
    assert data["officer_remarks"] == "Fake revenue authority seal detected upon visual scrutiny"

    # Verify parent application is STILL in UNDER_MANUAL_REVIEW
    db.expire_all()
    app = db.get(Application, app_id)
    assert app.status == ApplicationStatus.UNDER_MANUAL_REVIEW, (
        "Document rejection must NOT automatically change the application status."
    )


# ---------------------------------------------------------------------------
# Test 2: Rejected Document Blocks Application Approval
# ---------------------------------------------------------------------------
def test_rejected_document_blocks_application_approval(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")
    app_id = env["app"].id

    # Mark document 1 as REJECTED
    client.post(
        f"/api/v1/officer/documents/{env['doc1'].id}/decision",
        json={"decision": "REJECTED", "remarks": "Document rejected"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # Attempt to approve application -> MUST be rejected by validation guard
    res = client.post(
        f"/api/v1/officer/applications/{app_id}/decision",
        json={"decision": "VERIFIED", "remarks": "Approving application"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res.status_code == 400
    assert "RESUBMISSION_REQUIRED or REJECTED" in res.json()["error"]


# ---------------------------------------------------------------------------
# Test 3: AI Verified vs Human Verified Semantic Distinction
# ---------------------------------------------------------------------------
def test_ai_verified_vs_human_verified_distinction(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")

    doc1 = env["doc1"]
    v1 = env["v1"]

    # Before human scrutiny: Document.status is VERIFIED from AI, but officer_decision is None
    assert doc1.status == DocumentStatus.VERIFIED
    assert v1.officer_decision is None
    assert v1.verified_by is None

    # Officer performs human verification
    res = client.post(
        f"/api/v1/officer/documents/{doc1.id}/decision",
        json={"decision": "VERIFIED", "remarks": "Verified by officer"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res.status_code == 200

    # After human scrutiny: officer_decision is VERIFIED and verified_by is officer ID
    db.expire_all()
    v1_updated = db.get(DocumentVerification, v1.id)
    assert v1_updated.officer_decision == "VERIFIED"
    assert v1_updated.verified_by == env["officer"].id
    assert v1_updated.verified_at is not None


# ---------------------------------------------------------------------------
# Test 4: AI Flag Override Workflow
# ---------------------------------------------------------------------------
def test_officer_ai_override_workflow(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")
    doc2_id = env["doc2"].id  # doc2 has AI flags

    # 1. Attempting to mark VERIFIED without ai_override/reason fails
    res_fail = client.post(
        f"/api/v1/officer/documents/{doc2_id}/decision",
        json={"decision": "VERIFIED", "remarks": "Approving"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_fail.status_code == 400
    assert "override_reason" in res_fail.json()["error"].lower()

    # 2. Providing ai_override and non-empty override_reason succeeds
    res_success = client.post(
        f"/api/v1/officer/documents/{doc2_id}/decision",
        json={
            "decision": "VERIFIED",
            "remarks": "Manual verification passed",
            "ai_override": True,
            "override_reason": "Applicant provided supplementary clarification on agriculture income exclusion.",
        },
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_success.status_code == 200
    data = res_success.json()
    assert data["ai_override"] is True
    assert "supplementary clarification" in data["override_reason"]

    # 3. Check high-visibility audit event logged
    audit = (
        db.query(AuditLog)
        .filter(AuditLog.action == "OFFICER_AI_FLAG_OVERRIDDEN", AuditLog.entity_id == str(doc2_id))
        .first()
    )
    assert audit is not None
    assert audit.details["human_decision"] == "VERIFIED"


# ---------------------------------------------------------------------------
# Test 5: Partial Document Decisions are Durable and Multi-Officer Visible
# ---------------------------------------------------------------------------
def test_partial_document_decisions_durability_and_visibility(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")
    app_id = env["app"].id
    doc1_id = env["doc1"].id

    # Officer A verifies document 1
    res_doc = client.post(
        f"/api/v1/officer/documents/{doc1_id}/decision",
        json={"decision": "VERIFIED", "remarks": "Officer A verified ST cert"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_doc.status_code == 200

    # Ensure second officer exists
    email_b = "officer_b@demo.gov.in"
    officer_b = db.query(User).filter(User.email == email_b).first()
    if not officer_b:
        officer_b = User(
            full_name="Officer B (State Nodal)",
            email=email_b,
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.OFFICER,
            is_active=True,
        )
        db.add(officer_b)
        db.commit()
    # Explicit global scope for Officer B
    if not db.query(OfficerAssignment).filter(OfficerAssignment.officer_id == officer_b.id).first():
        db.add(OfficerAssignment(officer_id=officer_b.id, is_active=True))
        db.commit()

    token_b = _get_token(client, email_b)

    # Officer B loads scrutiny details
    res_scrutiny = client.get(
        f"/api/v1/officer/applications/{app_id}/scrutiny",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_scrutiny.status_code == 200
    scrutiny_data = res_scrutiny.json()

    # Verify Officer B sees Officer A's decision on document 1
    doc1_item = next(d for d in scrutiny_data["documents"] if d["id"] == str(doc1_id))
    assert doc1_item["officer_decision"] == "VERIFIED"
    assert doc1_item["officer_remarks"] == "Officer A verified ST cert"
    assert doc1_item["verified_by_name"] == env["officer"].full_name

    # Document 2 is still pending human decision
    doc2_item = next(d for d in scrutiny_data["documents"] if d["id"] == str(env["doc2"].id))
    assert doc2_item["officer_decision"] is None


# ---------------------------------------------------------------------------
# Test 6: Unassigned Officer Denied Access (Strict Scope Security)
# ---------------------------------------------------------------------------
def test_unassigned_officer_denied_access(client: TestClient, db: Session):
    unassigned_email = "unassigned_officer@demo.gov.in"
    unassigned = db.query(User).filter(User.email == unassigned_email).first()
    if not unassigned:
        unassigned = User(
            full_name="Unassigned Officer",
            email=unassigned_email,
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.OFFICER,
            is_active=True,
        )
        db.add(unassigned)
        db.commit()

    # Ensure NO assignments exist
    db.query(OfficerAssignment).filter(OfficerAssignment.officer_id == unassigned.id).delete()
    db.commit()

    token = _get_token(client, unassigned_email)

    # 1. Queue returns 0 items
    res_queue = client.get("/api/v1/officer/queue", headers={"Authorization": f"Bearer {token}"})
    assert res_queue.status_code == 200
    assert res_queue.json()["total"] == 0

    # 2. Direct scrutiny access returns 403 Forbidden
    env = _setup_test_environment(client, db)
    res_scrutiny = client.get(
        f"/api/v1/officer/applications/{env['app'].id}/scrutiny",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_scrutiny.status_code == 403
    assert "jurisdiction" in res_scrutiny.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 7: Scoped Officer Restricted to Jurisdiction
# ---------------------------------------------------------------------------
def test_scoped_officer_restricted_to_jurisdiction(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)  # application has state: "Rajasthan"
    app_id = env["app"].id

    odisha_email = "odisha_officer@demo.gov.in"
    odisha_officer = db.query(User).filter(User.email == odisha_email).first()
    if not odisha_officer:
        odisha_officer = User(
            full_name="Odisha State Officer",
            email=odisha_email,
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.OFFICER,
            is_active=True,
        )
        db.add(odisha_officer)
        db.commit()

    # Clear and assign specifically to "Odisha"
    db.query(OfficerAssignment).filter(OfficerAssignment.officer_id == odisha_officer.id).delete()
    db.add(OfficerAssignment(officer_id=odisha_officer.id, state="Odisha", is_active=True))
    db.commit()

    odisha_token = _get_token(client, odisha_email)

    # Odisha officer tries to access Rajasthan application -> 403 Forbidden
    res = client.get(
        f"/api/v1/officer/applications/{app_id}/scrutiny",
        headers={"Authorization": f"Bearer {odisha_token}"},
    )
    assert res.status_code == 403
    assert "jurisdiction" in res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 8: Deficient Handoff Creates Open Deficiency WITHOUT Applicant Notification
# ---------------------------------------------------------------------------
def test_deficient_handoff_creates_open_deficiency_without_notification(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")
    app_id = env["app"].id
    doc2_id = env["doc2"].id

    # Mark doc 2 as RESUBMISSION_REQUIRED
    client.post(
        f"/api/v1/officer/documents/{doc2_id}/decision",
        json={
            "decision": "RESUBMISSION_REQUIRED",
            "remarks": "Income certificate expired in FY 2023. Current FY 2025-26 required.",
        },
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # Check notification count prior to decision
    notif_count_before = (
        db.query(Notification)
        .filter(Notification.user_id == env["applicant"].id)
        .count()
    )

    # Finalize application decision as DEFICIENT
    res_app = client.post(
        f"/api/v1/officer/applications/{app_id}/decision",
        json={
            "decision": "DEFICIENT",
            "remarks": "Income certificate expired. ST caste certificate verified successfully.",
            "deficiencies": [
                {
                    "document_id": str(doc2_id),
                    "reason": "EXPIRED_INCOME_CERTIFICATE",
                    "applicant_message": "Please re-upload valid Income Certificate for FY 2025-26.",
                }
            ],
        },
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "DEFICIENT"

    # 1. Verify deficiency record created in OPEN status
    deficiency = (
        db.query(Deficiency)
        .filter(Deficiency.application_id == app_id, Deficiency.document_id == doc2_id)
        .first()
    )
    assert deficiency is not None
    assert deficiency.status == "OPEN"
    assert deficiency.reason == "EXPIRED_INCOME_CERTIFICATE"

    # 2. Verify ZERO applicant notifications sent (Phase 5 boundary strictly maintained!)
    notif_count_after = (
        db.query(Notification)
        .filter(Notification.user_id == env["applicant"].id)
        .count()
    )
    assert notif_count_after == notif_count_before, (
        "Phase 4 must NOT dispatch applicant deficiency notifications; Phase 5 owns that workflow."
    )


# ---------------------------------------------------------------------------
# Test 9: Queue Response Excludes Applicant Contact PII
# ---------------------------------------------------------------------------
def test_queue_response_excludes_applicant_contact_pii(client: TestClient, db: Session):
    _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")

    res = client.get("/api/v1/officer/queue", headers={"Authorization": f"Bearer {officer_token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) > 0
    item = data["items"][0]

    # Required queue operational fields
    assert "reference_id" in item
    assert "applicant_name" in item
    assert "scheme_code" in item
    assert "status" in item

    # PII minimization check: email and phone MUST NOT be present in queue item
    assert "applicant_email" not in item
    assert "applicant_phone" not in item
    assert "email" not in item
    assert "phone" not in item


# ---------------------------------------------------------------------------
# Test 10: Application Verified Guard Requires Explicit Human Verification
# ---------------------------------------------------------------------------
def test_application_verified_guard_requires_all_docs_human_verified(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")
    app_id = env["app"].id

    # Doc 1 has AI verification, but NOT human officer verification
    # Try to verify application directly
    res_fail = client.post(
        f"/api/v1/officer/applications/{app_id}/decision",
        json={"decision": "VERIFIED", "remarks": "Approving"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_fail.status_code == 400
    assert "requires explicit human verification" in res_fail.json()["error"].lower()

    # Now officer human-verifies doc 1
    client.post(
        f"/api/v1/officer/documents/{env['doc1'].id}/decision",
        json={"decision": "VERIFIED", "remarks": "Officer checked stamp and roll"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # Officer human-verifies doc 2 with AI override
    client.post(
        f"/api/v1/officer/documents/{env['doc2'].id}/decision",
        json={
            "decision": "VERIFIED",
            "remarks": "Manual verification complete",
            "ai_override": True,
            "override_reason": "Correct income format verified against state tehsildar portal.",
        },
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # Officer human-verifies doc 3
    client.post(
        f"/api/v1/officer/documents/{env['doc3'].id}/decision",
        json={"decision": "VERIFIED", "remarks": "Officer checked postgraduate marksheet"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # Officer human-verifies doc 4
    client.post(
        f"/api/v1/officer/documents/{env['doc4'].id}/decision",
        json={"decision": "VERIFIED", "remarks": "Officer checked university doctoral admission letter"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # Now application verification succeeds because all mandatory documents have human verification
    res_ok = client.post(
        f"/api/v1/officer/applications/{app_id}/decision",
        json={"decision": "VERIFIED", "remarks": "All documents verified by desk officer."},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "VERIFIED"


# ---------------------------------------------------------------------------
# Test 11: Applicant Cannot Access Officer Endpoints (RBAC)
# ---------------------------------------------------------------------------
def test_applicant_cannot_access_officer_endpoints(client: TestClient, db: Session):
    env = _setup_test_environment(client, db)
    applicant_token = _get_token(client, "applicant@demo.gov.in")

    res_queue = client.get("/api/v1/officer/queue", headers={"Authorization": f"Bearer {applicant_token}"})
    assert res_queue.status_code == 403

    res_stats = client.get("/api/v1/officer/stats", headers={"Authorization": f"Bearer {applicant_token}"})
    assert res_stats.status_code == 403

    res_scrutiny = client.get(
        f"/api/v1/officer/applications/{env['app'].id}/scrutiny",
        headers={"Authorization": f"Bearer {applicant_token}"},
    )
    assert res_scrutiny.status_code == 403


# ---------------------------------------------------------------------------
# Test 12: Officer Cannot Directly Finalize a SUBMITTED Application as VERIFIED
# ---------------------------------------------------------------------------
def test_officer_cannot_finalize_submitted_application_as_verified(client: TestClient, db: Session):
    """
    Regression Test:
    Proves an officer cannot directly finalize an application in SUBMITTED status.
    The strict lifecycle must be:
      SUBMITTED -> UNDER_AI_VERIFICATION -> UNDER_MANUAL_REVIEW -> VERIFIED / DEFICIENT / REJECTED
    Any attempt to decision an application that is not in UNDER_MANUAL_REVIEW must be rejected with 409 Conflict.
    Furthermore, status_transitions engine must disallow SUBMITTED -> VERIFIED and UNDER_AI_VERIFICATION -> VERIFIED.
    """
    from app.core.status_transitions import can_transition_application

    # Invariant 1: Core state machine disallows direct transitions to VERIFIED from SUBMITTED or UNDER_AI_VERIFICATION
    assert not can_transition_application(ApplicationStatus.SUBMITTED, ApplicationStatus.VERIFIED)
    assert not can_transition_application(ApplicationStatus.UNDER_AI_VERIFICATION, ApplicationStatus.VERIFIED)
    assert can_transition_application(ApplicationStatus.UNDER_MANUAL_REVIEW, ApplicationStatus.VERIFIED)

    env = _setup_test_environment(client, db)
    officer_token = _get_token(client, "officer@demo.gov.in")

    # Put application in SUBMITTED status (bypassing AI verification and manual review stage)
    app = env["app"]
    app.status = ApplicationStatus.SUBMITTED
    db.commit()
    db.refresh(app)

    # Officer attempts to record application decision directly on SUBMITTED application
    res_decision = client.post(
        f"/api/v1/officer/applications/{app.id}/decision",
        json={"decision": "VERIFIED", "remarks": "Attempting to verify submitted application directly"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # Invariant 2: Endpoint rejects with 409 Conflict because status != UNDER_MANUAL_REVIEW
    assert res_decision.status_code == 409
    error_msg = res_decision.json()["error"]
    assert "UNDER_MANUAL_REVIEW" in error_msg
    assert "SUBMITTED" in error_msg

    # Invariant 3: DB record status remains strictly untouched as SUBMITTED
    db.refresh(app)
    assert app.status == ApplicationStatus.SUBMITTED

