import io
import uuid
import threading
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import ApplicationStatus, DocumentStatus, UserRole
from app.core.security import get_password_hash
from app.models.user import User
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.application import Application
from app.models.document import Document
from app.models.document_verification import DocumentVerification
from app.models.deficiency import Deficiency
from app.models.officer_assignment import OfficerAssignment
from app.models.notification import Notification
from app.models.audit_log import AuditLog
from app.services.officer_service import OfficerService
from app.schemas.officer import OfficerApplicationDecisionRequest, OfficerDocumentDecisionRequest


def _get_token(client: TestClient, email: str, password: str = "Demo@12345") -> str:
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return res.json()["access_token"]


def _setup_environment(client: TestClient, db: Session):
    """Sets up an applicant, officer, scheme, and an application in DEFICIENT state with an OPEN deficiency."""
    # 1. Scheme & Version
    scheme = db.query(Scheme).filter(Scheme.scheme_code == "NFST").first()
    if not scheme:
        scheme = Scheme(
            scheme_code="NFST",
            name="National Fellowship for ST Students",
            description="Fellowship support for M.Phil and Ph.D. ST scholars",
            funding_type="CENTRAL_SECTOR",
            target_group={"categories": ["ST"]},
            is_active=True,
        )
        db.add(scheme)
        db.commit()

    sv = db.query(SchemeVersion).filter(SchemeVersion.scheme_id == scheme.id).first()
    if not sv:
        sv = SchemeVersion(
            scheme_id=scheme.id,
            scheme_version="1.0",
            form_schema={"sections": [{"id": "personal", "fields": []}]},
            eligibility_rules={"category": "ST"},
            required_documents={
                "documents": [
                    {"code": "INCOME_CERTIFICATE", "name": "Income Certificate", "required": True, "allowed_extensions": ["pdf"]},
                    {"code": "CASTE_CERTIFICATE", "name": "Caste Certificate", "required": True, "allowed_extensions": ["pdf"]},
                ]
            },
            is_active=True,
        )
        db.add(sv)
        db.commit()

    # 2. Users
    applicant = db.query(User).filter(User.email == "applicant@demo.gov.in").first()
    if not applicant:
        applicant = User(
            full_name="Tribal Scholar Applicant",
            email="applicant@demo.gov.in",
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.APPLICANT,
            is_active=True,
        )
        db.add(applicant)
        db.commit()

    officer = db.query(User).filter(User.email == "officer@demo.gov.in").first()
    if not officer:
        officer = User(
            full_name="Senior Scrutiny Officer",
            email="officer@demo.gov.in",
            password_hash=get_password_hash("Demo@12345"),
            role=UserRole.OFFICER,
            is_active=True,
        )
        db.add(officer)
        db.commit()

    # Global scope assignment for officer
    if not db.query(OfficerAssignment).filter(OfficerAssignment.officer_id == officer.id).first():
        db.add(OfficerAssignment(officer_id=officer.id, is_active=True))
        db.commit()

    # 3. Application in DEFICIENT status
    app = Application(
        reference_id=f"MTA-P5-{uuid.uuid4().hex[:6].upper()}",
        applicant_id=applicant.id,
        scheme_id=scheme.id,
        scheme_version_id=sv.id,
        status=ApplicationStatus.DEFICIENT,
        form_data={"personal": {"full_name": applicant.full_name, "state": "Odisha"}},
        resubmission_count=0,
    )
    db.add(app)
    db.commit()
    db.refresh(app)

    # 4. Deficient Document (Income Certificate v1)
    doc = Document(
        application_id=app.id,
        document_type="INCOME_CERTIFICATE",
        original_filename="income_cert_v1.pdf",
        storage_path=f"applications/{app.id}/documents/{uuid.uuid4().hex}.pdf",
        mime_type="application/pdf",
        file_size=10240,
        status=DocumentStatus.RESUBMISSION_REQUIRED,
        version=1,
        is_current=True,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 5. Open Deficiency (Phase 4 handoff state)
    deficiency = Deficiency(
        application_id=app.id,
        document_id=doc.id,
        cycle=1,
        reason="EXPIRED_CERTIFICATE",
        applicant_message="Income certificate is expired. Please upload valid certificate for current fiscal year.",
        status="OPEN",
        notification_dispatched=False,
    )
    db.add(deficiency)
    db.commit()
    db.refresh(deficiency)

    return {
        "scheme": scheme,
        "scheme_version": sv,
        "applicant": applicant,
        "officer": officer,
        "app": app,
        "doc": doc,
        "deficiency": deficiency,
    }


# ---------------------------------------------------------------------------
# Test 1: Replacement Upload Sets REPLACEMENT_UPLOADED, Not RESOLVED
# ---------------------------------------------------------------------------
def test_replacement_upload_sets_replacement_uploaded_not_resolved(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    doc_v1 = env["doc"]
    deficiency = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)

    # Prepare dummy PDF file with valid header
    dummy_pdf = io.BytesIO(b"%PDF-1.4 dummy valid replacement content for test")
    dummy_pdf.name = "income_cert_valid_2024.pdf"

    res = client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("income_cert_valid_2024.pdf", dummy_pdf, "application/pdf")},
        data={"applicant_remarks": "Attached newly issued Tehsildar income certificate for FY 2023-24."},
    )
    assert res.status_code == 201
    res_data = res.json()

    # Invariant 1: Status is REPLACEMENT_UPLOADED, strictly NOT RESOLVED
    assert res_data["status"] == "REPLACEMENT_UPLOADED"
    assert res_data["version"] == 2

    # Invariant 2: Database Deficiency state
    db.refresh(deficiency)
    assert deficiency.status == "REPLACEMENT_UPLOADED"
    assert deficiency.replacement_document_id is not None
    assert deficiency.applicant_remarks == "Attached newly issued Tehsildar income certificate for FY 2023-24."
    assert deficiency.resolved_at is None  # Must NOT be marked resolved yet!

    # Invariant 3: Document lineage
    db.refresh(doc_v1)
    assert doc_v1.is_current is False
    assert doc_v1.superseded_by_id == uuid.UUID(res_data["document_id"])
    assert doc_v1.status == DocumentStatus.RESUBMISSION_REQUIRED  # Historical status untouched

    doc_v2 = db.get(Document, res_data["document_id"])
    assert doc_v2 is not None
    assert doc_v2.is_current is True
    assert doc_v2.version == 2
    assert doc_v2.parent_document_id == doc_v1.id
    assert doc_v2.status == DocumentStatus.PENDING


# ---------------------------------------------------------------------------
# Test 2: Deficiency Becomes RESOLVED Only After Subsequent Human Verification
# ---------------------------------------------------------------------------
def test_deficiency_becomes_resolved_only_after_subsequent_human_verification(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)
    officer_token = _get_token(client, env["officer"].email)

    # 1. Upload replacement
    dummy_pdf = io.BytesIO(b"%PDF-1.4 valid certificate content")
    upload_res = client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("income_cert.pdf", dummy_pdf, "application/pdf")},
    )
    assert upload_res.status_code == 201
    replacement_doc_id = upload_res.json()["document_id"]

    # 2. Resubmit application
    resubmit_res = client.post(
        f"/api/v1/applications/{app.id}/resubmit",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"declaration_confirmed": True, "remarks": "Ready for second scrutiny."},
    )
    assert resubmit_res.status_code == 200
    db.refresh(deficiency)
    assert deficiency.status == "UNDER_REVIEW"

    # 3. Subsequent Officer Scrutiny: Officer verifies the replacement document
    decision_res = client.post(
        f"/api/v1/officer/documents/{replacement_doc_id}/decision",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "decision": "VERIFIED",
            "remarks": "Verified replacement against revenue portal.",
            "ai_override": True,
            "override_reason": "Officer verified replacement against revenue records.",
        },
    )
    assert decision_res.status_code == 200

    # Invariant: Now and ONLY now does the deficiency transition to RESOLVED
    db.refresh(deficiency)
    assert deficiency.status == "RESOLVED"
    assert deficiency.resolved_at is not None

    # Audit event DEFICIENCY_RESOLVED logged
    audit_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == "DEFICIENCY_RESOLVED", AuditLog.application_id == app.id)
        .first()
    )
    assert audit_log is not None


# ---------------------------------------------------------------------------
# Test 3: Multiple Deficiency Cycles Preserved
# ---------------------------------------------------------------------------
def test_multiple_deficiency_cycles_preserved(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency_c1 = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)
    officer_token = _get_token(client, env["officer"].email)

    # 1. Upload replacement for Cycle 1
    dummy_pdf = io.BytesIO(b"%PDF-1.4 replacement v2")
    upload_res = client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency_c1.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("income_cert_v2.pdf", dummy_pdf, "application/pdf")},
    )
    rep_v2_id = upload_res.json()["document_id"]

    # 2. Resubmit
    client.post(
        f"/api/v1/applications/{app.id}/resubmit",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"declaration_confirmed": True},
    )

    # Put application in UNDER_MANUAL_REVIEW to simulate scrutiny
    app.status = ApplicationStatus.UNDER_MANUAL_REVIEW
    db.commit()

    # 3. Officer rejects replacement v2 (Cycle 1 fails)
    rej_doc_res = client.post(
        f"/api/v1/officer/documents/{rep_v2_id}/decision",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"decision": "RESUBMISSION_REQUIRED", "remarks": "Still illegible signature stamp."},
    )
    assert rej_doc_res.status_code == 200

    # Invariant: Cycle 1 deficiency is marked FAILED
    db.refresh(deficiency_c1)
    assert deficiency_c1.status == "FAILED"

    # Officer marks application DEFICIENT again (Cycle 2 begins)
    app_dec_res = client.post(
        f"/api/v1/officer/applications/{app.id}/decision",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "decision": "DEFICIENT",
            "remarks": "Please provide color scan of income certificate with legible tehsildar seal.",
            "deficiencies": [
                {
                    "document_id": rep_v2_id,
                    "reason": "ILLEGIBLE_SEAL",
                    "applicant_message": "Please provide color scan with legible official seal.",
                }
            ],
        },
    )
    assert app_dec_res.status_code == 200

    # Invariant: Cycle 2 deficiency created with cycle=2 and status=OPEN
    all_defs = (
        db.query(Deficiency)
        .filter(Deficiency.application_id == app.id)
        .order_by(Deficiency.cycle.asc())
        .all()
    )
    assert len(all_defs) == 2
    assert all_defs[0].id == deficiency_c1.id
    assert all_defs[0].status == "FAILED"
    assert all_defs[0].cycle == 1

    def_c2 = all_defs[1]
    assert def_c2.cycle == 2
    assert def_c2.status == "OPEN"
    assert def_c2.reason == "ILLEGIBLE_SEAL"


# ---------------------------------------------------------------------------
# Test 4: Explicit Resubmission State Transitions and Audit Events
# ---------------------------------------------------------------------------
def test_explicit_resubmission_state_transitions_and_audit(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)

    # Upload replacement
    dummy_pdf = io.BytesIO(b"%PDF-1.4 content")
    client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("doc.pdf", dummy_pdf, "application/pdf")},
    )

    # Resubmit
    res = client.post(
        f"/api/v1/applications/{app.id}/resubmit",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"declaration_confirmed": True, "remarks": "Submitted all required documents."},
    )
    assert res.status_code == 200

    # Invariant 1: Application transitioned through UNDER_AI_VERIFICATION (and into UNDER_MANUAL_REVIEW via background task)
    db.refresh(app)
    assert app.status in (ApplicationStatus.UNDER_AI_VERIFICATION, ApplicationStatus.UNDER_MANUAL_REVIEW)
    assert app.resubmission_count == 1
    assert app.resubmitted_at is not None

    # Invariant 2: Explicit audit logs exist for both transitions
    audit_resubmitted = (
        db.query(AuditLog)
        .filter(AuditLog.action == "APPLICATION_RESUBMITTED", AuditLog.application_id == app.id)
        .first()
    )
    assert audit_resubmitted is not None
    assert audit_resubmitted.previous_status == "DEFICIENT"
    assert audit_resubmitted.new_status == "RESUBMITTED"

    audit_queued = (
        db.query(AuditLog)
        .filter(AuditLog.action == "APPLICATION_QUEUED_FOR_AI_VERIFICATION", AuditLog.application_id == app.id)
        .first()
    )
    assert audit_queued is not None
    assert audit_queued.previous_status == "RESUBMITTED"
    assert audit_queued.new_status == "UNDER_AI_VERIFICATION"


# ---------------------------------------------------------------------------
# Test 5: Concurrent Resubmission Conflict (HTTP 409)
# ---------------------------------------------------------------------------
def test_concurrent_resubmission_conflict(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)

    dummy_pdf = io.BytesIO(b"%PDF-1.4 content")
    client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("doc.pdf", dummy_pdf, "application/pdf")},
    )

    # First resubmission succeeds
    res1 = client.post(
        f"/api/v1/applications/{app.id}/resubmit",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"declaration_confirmed": True},
    )
    assert res1.status_code == 200

    # Second concurrent/duplicate resubmission fails with 409 Conflict
    res2 = client.post(
        f"/api/v1/applications/{app.id}/resubmit",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"declaration_confirmed": True},
    )
    assert res2.status_code == 409
    assert "DEFICIENT" in res2.json()["error"]


# ---------------------------------------------------------------------------
# Test 6: Phase 4 Remains Notification-Free & Phase 5 Dispatches Independently
# ---------------------------------------------------------------------------
def test_phase4_notification_free_and_phase5_dispatch(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    officer = env["officer"]
    applicant = env["applicant"]

    # Put application in UNDER_MANUAL_REVIEW
    app.status = ApplicationStatus.UNDER_MANUAL_REVIEW
    db.commit()

    # Clear existing notifications
    db.query(Notification).filter(Notification.user_id == applicant.id).delete()
    db.commit()

    # Phase 4 Officer marks application DEFICIENT
    service = OfficerService(db)
    service.record_application_decision(
        officer=officer,
        application_id=app.id,
        data=OfficerApplicationDecisionRequest(
            decision="DEFICIENT",
            remarks="Please upload valid documents.",
            deficiencies=[
                {
                    "document_id": env["doc"].id,
                    "reason": "TEST_DEFICIENCY",
                    "applicant_message": "Needs replacement.",
                }
            ],
        ),
    )

    # Invariant: Phase 4 action created exactly ZERO notifications
    notifs_p4 = db.query(Notification).filter(Notification.user_id == applicant.id).all()
    assert len(notifs_p4) == 0, "Phase 4 must remain strictly notification-free!"

    # Phase 5 notification dispatcher runs independently
    from app.services.deficiency_service import DeficiencyService
    def_service = DeficiencyService(db)
    dispatched = def_service.dispatch_pending_deficiency_notifications(application_id=app.id)
    assert dispatched >= 1

    # Invariant: Notification is now sent by Phase 5
    notifs_p5 = db.query(Notification).filter(Notification.user_id == applicant.id).all()
    assert len(notifs_p5) >= 1
    assert "Deficiencies flagged" in notifs_p5[0].title


# ---------------------------------------------------------------------------
# Test 7: Invalid Replacement Does Not Mutate State
# ---------------------------------------------------------------------------
def test_invalid_replacement_does_not_mutate_state(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency = env["deficiency"]
    doc = env["doc"]
    applicant_token = _get_token(client, env["applicant"].email)

    # Corrupt/executable file pretending to be pdf
    bad_file = io.BytesIO(b"MZ\x90\x00executable bytes not a pdf")
    res = client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("malicious.pdf", bad_file, "application/pdf")},
    )
    assert res.status_code == 400

    # Invariant: Deficiency is still OPEN, document is still is_current=True, no new doc created
    db.refresh(deficiency)
    assert deficiency.status == "OPEN"
    assert deficiency.replacement_document_id is None

    db.refresh(doc)
    assert doc.is_current is True


# ---------------------------------------------------------------------------
# Test 8: Applicant Cannot Alter Unrelated Application Data while DEFICIENT
# ---------------------------------------------------------------------------
def test_applicant_cannot_alter_unrelated_data_while_deficient(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    applicant_token = _get_token(client, env["applicant"].email)

    # Attempt to modify form_data
    res = client.put(
        f"/api/v1/applications/{app.id}",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"form_data": {"personal": {"full_name": "Tampered Name"}}},
    )
    assert res.status_code == 403
    assert "cannot modify submitted application" in res.json()["error"].lower()


# ---------------------------------------------------------------------------
# Test 9: UUID Physical Storage and Lineage
# ---------------------------------------------------------------------------
def test_uuid_physical_storage_and_lineage(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)

    dummy_pdf = io.BytesIO(b"%PDF-1.4 valid test file")
    res = client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("my_personal_tax_file_2024.pdf", dummy_pdf, "application/pdf")},
    )
    assert res.status_code == 201
    doc_id = res.json()["document_id"]

    new_doc = db.get(Document, doc_id)
    assert new_doc is not None

    # Invariant: Storage path does NOT contain original filename or 'v2' in physical storage identity
    assert "my_personal_tax_file_2024" not in new_doc.storage_path
    assert "v2" not in new_doc.storage_path
    # It must contain the document's hex UUID
    assert new_doc.id.hex in new_doc.storage_path


# ---------------------------------------------------------------------------
# Test 10: Resubmission Blocked if Any Deficiency Remains OPEN
# ---------------------------------------------------------------------------
def test_resubmission_blocked_with_open_deficiency(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    applicant_token = _get_token(client, env["applicant"].email)

    # Attempt to resubmit while deficiency is OPEN (no replacement uploaded)
    res = client.post(
        f"/api/v1/applications/{app.id}/resubmit",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"declaration_confirmed": True},
    )
    assert res.status_code == 400
    assert "remain OPEN" in res.json()["error"]


# ---------------------------------------------------------------------------
# Test 11: Exact One is_current = True Document Invariant on Repeated Replacement
# ---------------------------------------------------------------------------
def test_exact_one_is_current_invariant_on_superseded_replacement(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)

    # Upload replacement 1 (v2)
    file1 = io.BytesIO(b"%PDF-1.4 first attempt")
    res1 = client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("doc_attempt1.pdf", file1, "application/pdf")},
    )
    assert res1.status_code == 201
    v2_id = res1.json()["document_id"]

    # Upload replacement 2 (v3, superseding v2 before resubmitting)
    file2 = io.BytesIO(b"%PDF-1.4 second attempt")
    res2 = client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("doc_attempt2.pdf", file2, "application/pdf")},
    )
    assert res2.status_code == 201
    v3_id = res2.json()["document_id"]

    # Invariant check: In the database, for this application and document_type,
    # EXACTLY ONE document has is_current == True
    current_docs = (
        db.query(Document)
        .filter(
            Document.application_id == app.id,
            Document.document_type == "INCOME_CERTIFICATE",
            Document.is_current == True,
        )
        .all()
    )
    assert len(current_docs) == 1
    assert current_docs[0].id == uuid.UUID(v3_id)
    assert current_docs[0].version == 3

    # Check v2 is superseded
    v2_doc = db.get(Document, v2_id)
    assert v2_doc.is_current is False
    assert v2_doc.superseded_by_id == uuid.UUID(v3_id)


# ---------------------------------------------------------------------------
# Test 12: Pipeline Handoff Auto-Transitions to UNDER_MANUAL_REVIEW
# ---------------------------------------------------------------------------
def test_pipeline_handoff_auto_transitions_to_manual_review(client: TestClient, db: Session):
    env = _setup_environment(client, db)
    app = env["app"]
    deficiency = env["deficiency"]
    applicant_token = _get_token(client, env["applicant"].email)

    # Provide all other required scheme documents (already verified)
    caste_doc = Document(
        application_id=app.id,
        document_type="CASTE_CERTIFICATE",
        original_filename="caste.pdf",
        storage_path=f"applications/{app.id}/documents/{uuid.uuid4().hex}.pdf",
        mime_type="application/pdf",
        file_size=5000,
        status=DocumentStatus.VERIFIED,
        version=1,
        is_current=True,
    )
    pg_doc = Document(
        application_id=app.id,
        document_type="PG_MARKSHEET",
        original_filename="pg.pdf",
        storage_path=f"applications/{app.id}/documents/{uuid.uuid4().hex}.pdf",
        mime_type="application/pdf",
        file_size=5000,
        status=DocumentStatus.VERIFIED,
        version=1,
        is_current=True,
    )
    adm_doc = Document(
        application_id=app.id,
        document_type="ADMISSION_LETTER",
        original_filename="adm.pdf",
        storage_path=f"applications/{app.id}/documents/{uuid.uuid4().hex}.pdf",
        mime_type="application/pdf",
        file_size=5000,
        status=DocumentStatus.VERIFIED,
        version=1,
        is_current=True,
    )
    db.add_all([caste_doc, pg_doc, adm_doc])
    db.commit()

    # Upload replacement for income certificate
    dummy_pdf = io.BytesIO(b"%PDF-1.4 replacement")
    client.post(
        f"/api/v1/applications/{app.id}/deficiencies/{deficiency.id}/resolve",
        headers={"Authorization": f"Bearer {applicant_token}"},
        files={"file": ("income.pdf", dummy_pdf, "application/pdf")},
    )

    # Resubmit with sync_verify=True
    res = client.post(
        f"/api/v1/applications/{app.id}/resubmit?sync_verify=true",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"declaration_confirmed": True},
    )
    assert res.status_code == 200

    # Invariant: Pipeline executed and transitioned application to UNDER_MANUAL_REVIEW
    db.refresh(app)
    assert app.status == ApplicationStatus.UNDER_MANUAL_REVIEW
