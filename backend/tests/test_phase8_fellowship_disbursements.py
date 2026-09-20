import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import (
    UserRole,
    ApplicationStatus,
    FellowshipStatus,
    DisbursementStatus,
    SubmissionStatus,
)
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.fellowship import (
    FellowshipRecord,
    RenewalSubmission,
    ProgressReport,
    DisbursementInstallment,
)
from app.models.deficiency import Deficiency
from app.models.selection_result import SelectionResult
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.user import User
from app.models.audit_log import AuditLog


@pytest.fixture(autouse=True)
def cleanup_phase8_test_schemes(db: Session):
    yield
    test_schemes = db.query(Scheme).filter(Scheme.scheme_code.like("SCHEME-%")).all()
    scheme_ids = [s.id for s in test_schemes]
    if scheme_ids:
        # 1. Installments
        db.query(DisbursementInstallment).filter(
            DisbursementInstallment.fellowship_id.in_(
                db.query(FellowshipRecord.id).filter(FellowshipRecord.scheme_id.in_(scheme_ids))
            )
        ).delete(synchronize_session=False)

        # 2. Renewals
        db.query(RenewalSubmission).filter(
            RenewalSubmission.fellowship_id.in_(
                db.query(FellowshipRecord.id).filter(FellowshipRecord.scheme_id.in_(scheme_ids))
            )
        ).delete(synchronize_session=False)

        # 3. Progress reports
        db.query(ProgressReport).filter(
            ProgressReport.fellowship_id.in_(
                db.query(FellowshipRecord.id).filter(FellowshipRecord.scheme_id.in_(scheme_ids))
            )
        ).delete(synchronize_session=False)

        # 4. Fellowships
        db.query(FellowshipRecord).filter(FellowshipRecord.scheme_id.in_(scheme_ids)).delete(synchronize_session=False)

        # 5. Deficiencies
        db.query(Deficiency).filter(
            Deficiency.application_id.in_(
                db.query(Application.id).filter(Application.scheme_id.in_(scheme_ids))
            )
        ).delete(synchronize_session=False)

        # 6. Selection results
        db.query(SelectionResult).filter(
            SelectionResult.application_id.in_(
                db.query(Application.id).filter(Application.scheme_id.in_(scheme_ids))
            )
        ).delete(synchronize_session=False)

        # 7. Audit logs
        db.query(AuditLog).filter(
            AuditLog.application_id.in_(
                db.query(Application.id).filter(Application.scheme_id.in_(scheme_ids))
            )
        ).delete(synchronize_session=False)

        # 8. Applications
        db.query(Application).filter(Application.scheme_id.in_(scheme_ids)).delete(synchronize_session=False)

        # 9. Scheme versions
        db.query(SchemeVersion).filter(SchemeVersion.scheme_id.in_(scheme_ids)).delete(synchronize_session=False)

        # 10. Schemes
        db.query(Scheme).filter(Scheme.id.in_(scheme_ids)).delete(synchronize_session=False)
        db.commit()


def create_selected_app(db: Session, stipend_monthly: float = 31000.0, contingency_annual: float = 10000.0) -> Application:
    """Helper to create a cleanly isolated selected application for testing."""
    applicant = db.query(User).filter(User.email == "applicant@demo.gov.in").first()
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()

    scheme = Scheme(
        scheme_code=f"SCHEME-{uuid.uuid4().hex[:6].upper()}",
        name="National Fellowship Test Scheme",
        description="[DEMO PROTOTYPE] Scheme for Phase 8 testing",
        is_active=True,
    )
    db.add(scheme)
    db.flush()

    rules = {
        "financial_rules": {
            "monthly_stipend": stipend_monthly,
            "annual_contingency": contingency_annual,
            "annual_hra": 0.0,
        },
        "quota_config": {"total_slots": 20},
    }

    version = SchemeVersion(
        scheme_id=scheme.id,
        scheme_code=scheme.scheme_code,
        scheme_version="1.0",
        name=f"{scheme.name} v1.0",
        form_schema={},
        eligibility_rules={},
        required_documents={},
        scoring_weights=rules,
        is_active=True,
    )
    db.add(version)
    db.flush()

    app = Application(
        reference_id=f"APP-2026-{uuid.uuid4().hex[:8].upper()}",
        applicant_id=applicant.id,
        scheme_id=scheme.id,
        scheme_version_id=version.id,
        status=ApplicationStatus.SELECTED,
        form_data={
            "personal": {"name": "Test Scholar", "state": "Odisha"},
            "education": {"institution": "IIT Delhi", "degree": "Ph.D."},
            "award_acceptance": {
                "acceptance_recorded": True,
                "joining_date": "2026-08-01",
                "institution_name": "IIT Delhi",
                "department": "Computer Science",
                "guide_name": "Dr. Sharma",
                "research_topic": "AI in Tribal Welfare",
                "account_number_last4": "1234",
                "ifsc_code": "SBIN0001234",
            },
        },
        frozen_rules_snapshot=rules,
    )
    db.add(app)
    db.flush()

    sel = SelectionResult(
        application_id=app.id,
        result="SELECTED",
        rank=1,
        finalized_by=admin.id,
        finalized_at=datetime.now(timezone.utc),
    )
    db.add(sel)
    db.commit()
    db.refresh(app)
    return app


# -----------------------------------------------------------------------------
# 1. Fellowship Activation Authority
# -----------------------------------------------------------------------------
def test_fellowship_activation_by_admin_from_selected_application(client: TestClient, db: Session, admin_token: str):
    app = create_selected_app(db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.post(
        "/api/v1/fellowships/activate",
        headers=headers,
        json={"application_id": str(app.id), "tenure_years": 5},
    )
    assert res.status_code == 200, f"Activation failed: {res.text}"
    data = res.json()

    assert data["fellowship_number"].startswith("MTA-FEL-2026-")
    assert data["sanction_order_number"].startswith("DEMO-SANCTION-MTA-2026-")
    assert data["sanction_mode"] == "DEMO_SIMULATED"
    assert data["status"] == "ACTIVE"
    assert data["current_year"] == 1
    assert data["tenure_years"] == 5

    # Verify Application moved to FELLOWSHIP_ACTIVE
    db.refresh(app)
    assert app.status == ApplicationStatus.FELLOWSHIP_ACTIVE

    # Verify 5 scheduled installments generated
    insts = (
        db.query(DisbursementInstallment)
        .filter(DisbursementInstallment.fellowship_id == data["id"])
        .all()
    )
    assert len(insts) == 5
    for inst in insts:
        assert inst.payment_status == DisbursementStatus.SCHEDULED.value


# -----------------------------------------------------------------------------
# 2. Applicant Cannot Directly Activate Fellowship
# -----------------------------------------------------------------------------
def test_applicant_cannot_directly_activate_fellowship(client: TestClient, db: Session, applicant_token: str):
    app = create_selected_app(db)
    headers = {"Authorization": f"Bearer {applicant_token}"}

    # Calling /activate directly must be 403 Forbidden
    res = client.post(
        "/api/v1/fellowships/activate",
        headers=headers,
        json={"application_id": str(app.id)},
    )
    assert res.status_code == 403, f"Expected 403, got: {res.status_code}"

    # Calling /accept-award succeeds
    res_accept = client.post(
        "/api/v1/fellowships/accept-award",
        headers=headers,
        json={
            "application_id": str(app.id),
            "joining_date": "2026-08-01",
            "institution_name": "IIT Bombay",
            "bank_account_number": "123456789012",
            "ifsc_code": "SBIN0001234",
        },
    )
    assert res_accept.status_code == 200
    assert res_accept.json()["acceptance_recorded"] is True


# -----------------------------------------------------------------------------
# 3. Activation Blocked for Non-Selected Applications
# -----------------------------------------------------------------------------
def test_activation_blocked_for_non_selected_applications(client: TestClient, db: Session, admin_token: str):
    app = create_selected_app(db)
    app.status = ApplicationStatus.VERIFIED
    db.commit()

    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.post(
        "/api/v1/fellowships/activate",
        headers=headers,
        json={"application_id": str(app.id)},
    )
    assert res.status_code == 409
    assert "must be 'SELECTED'" in res.json()["detail"]


# -----------------------------------------------------------------------------
# 4. Initial Disbursement Schedule Bound to Frozen Rules
# -----------------------------------------------------------------------------
def test_initial_disbursement_schedule_bound_to_frozen_rules(client: TestClient, db: Session, admin_token: str):
    app = create_selected_app(db, stipend_monthly=45000.0, contingency_annual=20000.0)
    headers = {"Authorization": f"Bearer {admin_token}"}

    res = client.post(
        "/api/v1/fellowships/activate",
        headers=headers,
        json={"application_id": str(app.id)},
    )
    assert res.status_code == 200
    fel_id = res.json()["id"]

    insts = (
        db.query(DisbursementInstallment)
        .filter(DisbursementInstallment.fellowship_id == fel_id)
        .order_by(DisbursementInstallment.installment_number.asc())
        .all()
    )
    assert len(insts) == 5
    first_inst = insts[0]
    assert float(first_inst.stipend_amount) == 45000.0 * 12
    assert float(first_inst.contingency_amount) == 20000.0
    assert float(first_inst.total_amount) == (45000.0 * 12) + 20000.0


# -----------------------------------------------------------------------------
# 5. Annual Renewal Year Sequencing Invariant
# -----------------------------------------------------------------------------
def test_annual_renewal_year_sequencing_invariant(client: TestClient, db: Session, admin_token: str, applicant_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    headers = {"Authorization": f"Bearer {applicant_token}"}

    # Year 1 fellow attempts Year 3 renewal -> 400 Bad Request
    res_invalid = client.post(
        f"/api/v1/fellowships/{fellowship.id}/renewals",
        headers=headers,
        json={"academic_year": 3, "annual_progress_summary": "Skipped year"},
    )
    assert res_invalid.status_code == 400
    assert "sequence violation" in res_invalid.json()["detail"].lower()

    # Year 1 fellow submits Year 2 renewal -> 200 OK
    res_valid = client.post(
        f"/api/v1/fellowships/{fellowship.id}/renewals",
        headers=headers,
        json={"academic_year": 2, "annual_progress_summary": "Year 1 completed successfully", "marks_percentage": 82.5},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["academic_year"] == 2

    # Duplicate submission for Year 2 -> 409 Conflict
    res_dup = client.post(
        f"/api/v1/fellowships/{fellowship.id}/renewals",
        headers=headers,
        json={"academic_year": 2, "annual_progress_summary": "Duplicate submission"},
    )
    assert res_dup.status_code == 409


# -----------------------------------------------------------------------------
# 6. Renewal Officer Approval and Year Advancement
# -----------------------------------------------------------------------------
def test_renewal_officer_approval_and_year_advancement(client: TestClient, db: Session, admin_token: str, officer_token: str, applicant_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    # Submit renewal for year 2
    res_sub = client.post(
        f"/api/v1/fellowships/{fellowship.id}/renewals",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"academic_year": 2, "annual_progress_summary": "Completed Year 1 coursework"},
    )
    renewal_id = res_sub.json()["id"]

    # Officer approves renewal
    res_appr = client.post(
        f"/api/v1/fellowships/renewals/{renewal_id}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"decision": "APPROVED", "remarks": "Satisfactory coursework and guide recommendation"},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "APPROVED"

    # Verify atomic advancement of fellowship current_year
    db.refresh(fellowship)
    assert fellowship.current_year == 2
    assert fellowship.status == "ACTIVE"


# -----------------------------------------------------------------------------
# 7. Renewal Deficiency and Phase 5 Resubmission Integration
# -----------------------------------------------------------------------------
def test_renewal_deficiency_and_phase5_resubmission_integration(client: TestClient, db: Session, admin_token: str, officer_token: str, applicant_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    res_sub = client.post(
        f"/api/v1/fellowships/{fellowship.id}/renewals",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"academic_year": 2, "annual_progress_summary": "Year 1 progress"},
    )
    renewal_id = res_sub.json()["id"]

    # Officer flags deficiency
    res_flag = client.post(
        f"/api/v1/fellowships/renewals/{renewal_id}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "decision": "DEFICIENT",
            "deficiency_reason": "MISSING_SUPERVISOR_SEAL",
            "deficiency_message": "Please re-upload continuation certificate with registrar seal.",
        },
    )
    assert res_flag.status_code == 200
    data = res_flag.json()
    assert data["status"] == "DEFICIENT"
    assert data["deficiency_id"] is not None

    # Verify Phase 5 Deficiency model record created
    def_record = db.query(Deficiency).filter(Deficiency.id == data["deficiency_id"]).first()
    assert def_record is not None
    assert def_record.application_id == app.id
    assert def_record.status == "OPEN"


# -----------------------------------------------------------------------------
# 8. Progress Reports Do Not Advance Fellowship Year
# -----------------------------------------------------------------------------
def test_progress_report_does_not_advance_fellowship_year(client: TestClient, db: Session, admin_token: str, officer_token: str, applicant_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()
    assert fellowship.current_year == 1

    # Submit progress report
    res_rep = client.post(
        f"/api/v1/fellowships/{fellowship.id}/progress-reports",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={
            "academic_year": 1,
            "file_path": "/reports/progress_q1.pdf",
            "description": "Published 1 conference paper",
            "publications_count": 1,
            "presentations_count": 2,
        },
    )
    assert res_rep.status_code == 200
    report_id = res_rep.json()["id"]

    # Officer approves progress report
    res_rev = client.post(
        f"/api/v1/fellowships/progress-reports/{report_id}/review",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={"decision": "APPROVED", "remarks": "Commendable research milestone"},
    )
    assert res_rev.status_code == 200

    # Current year must remain 1
    db.refresh(fellowship)
    assert fellowship.current_year == 1


# -----------------------------------------------------------------------------
# 9. Disbursement Approval and PFMS Simulation
# -----------------------------------------------------------------------------
def test_disbursement_approval_and_pfms_simulation(client: TestClient, db: Session, admin_token: str, officer_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    inst = (
        db.query(DisbursementInstallment)
        .filter(DisbursementInstallment.fellowship_id == fellowship.id)
        .order_by(DisbursementInstallment.installment_number.asc())
        .first()
    )
    assert inst.payment_status == "SCHEDULED"

    # Officer approves installment
    res_appr = client.post(
        f"/api/v1/disbursements/{inst.id}/approve",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["payment_status"] == "APPROVED_FOR_PAYMENT"

    # Admin executes disbursement
    res_exec = client.post(
        f"/api/v1/disbursements/{inst.id}/execute",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_exec.status_code == 200
    data = res_exec.json()
    assert data["payment_status"] == "SUCCESS"
    assert data["is_success"] is True
    assert data["bank_reference_utr"].startswith("UTR-SIM-")
    assert "SIMULATED ENVIRONMENT" in data["demo_disclaimer"]


# -----------------------------------------------------------------------------
# 10. Financial Amount Immutability After Approval
# -----------------------------------------------------------------------------
def test_financial_amount_immutability_after_approval(client: TestClient, db: Session, admin_token: str, officer_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    inst = (
        db.query(DisbursementInstallment)
        .filter(DisbursementInstallment.fellowship_id == fellowship.id)
        .first()
    )
    # Approve installment
    client.post(f"/api/v1/disbursements/{inst.id}/approve", headers={"Authorization": f"Bearer {officer_token}"})

    db.refresh(inst)
    assert inst.payment_status == DisbursementStatus.APPROVED_FOR_PAYMENT.value
    # Status cannot be modified back to SCHEDULED or mutated
    res_bad = client.post(f"/api/v1/disbursements/{inst.id}/approve", headers={"Authorization": f"Bearer {officer_token}"})
    assert res_bad.status_code == 409


# -----------------------------------------------------------------------------
# 11. PFMS Simulated Failure and Retry Limit (Max 3)
# -----------------------------------------------------------------------------
def test_pfms_simulated_failure_and_retry_limit(client: TestClient, db: Session, admin_token: str, officer_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    inst = (
        db.query(DisbursementInstallment)
        .filter(DisbursementInstallment.fellowship_id == fellowship.id)
        .first()
    )
    client.post(f"/api/v1/disbursements/{inst.id}/approve", headers={"Authorization": f"Bearer {officer_token}"})

    # Execute with failing test account
    res_fail = client.post(
        f"/api/v1/disbursements/{inst.id}/execute",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"test_account_override": "000000009999"},
    )
    assert res_fail.status_code == 200
    assert res_fail.json()["payment_status"] == "FAILED"
    assert "BENEFICIARY_NAME_MISMATCH" in res_fail.json()["failure_reason"]

    # Retries 1, 2, 3
    for attempt in range(1, 3):
        res_retry = client.post(
            f"/api/v1/disbursements/{inst.id}/retry",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"test_account_override": "000000009999"},
        )
        assert res_retry.status_code == 200
        assert res_retry.json()["payment_status"] == "FAILED"

    # Attempt 4: Exceeds retry limit -> 400 Bad Request and RETRY_EXHAUSTED
    res_exhaust = client.post(
        f"/api/v1/disbursements/{inst.id}/retry",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"test_account_override": "000000009999"},
    )
    assert res_exhaust.status_code == 400
    assert "retry limit exhausted" in res_exhaust.json()["detail"].lower()

    db.refresh(inst)
    assert inst.payment_status == DisbursementStatus.RETRY_EXHAUSTED.value


# -----------------------------------------------------------------------------
# 12. Suspension Cascades Deterministically Across Payment States
# -----------------------------------------------------------------------------
def test_suspension_cascades_across_payment_states(client: TestClient, db: Session, admin_token: str, officer_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    insts = (
        db.query(DisbursementInstallment)
        .filter(DisbursementInstallment.fellowship_id == fellowship.id)
        .order_by(DisbursementInstallment.installment_number.asc())
        .all()
    )
    # Inst 1 -> Execute SUCCESS
    client.post(f"/api/v1/disbursements/{insts[0].id}/approve", headers={"Authorization": f"Bearer {officer_token}"})
    client.post(f"/api/v1/disbursements/{insts[0].id}/execute", headers={"Authorization": f"Bearer {admin_token}"})

    # Inst 2 -> APPROVED_FOR_PAYMENT
    client.post(f"/api/v1/disbursements/{insts[1].id}/approve", headers={"Authorization": f"Bearer {officer_token}"})

    # Suspend fellowship
    res_susp = client.patch(
        f"/api/v1/fellowships/{fellowship.id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "SUSPENDED", "reason": "Academic review audit"},
    )
    assert res_susp.status_code == 200

    # Verify cascades:
    db.refresh(insts[0])
    db.refresh(insts[1])
    db.refresh(insts[2])

    assert insts[0].payment_status == "SUCCESS"  # Untouched
    assert insts[1].payment_status == "CANCELLED"  # Revoked
    assert insts[2].payment_status == "SCHEDULED"  # Frozen


# -----------------------------------------------------------------------------
# 13. Concurrent Activation: Exactly One Fellowship Created
# -----------------------------------------------------------------------------
def test_concurrent_activation_exact_one_fellowship(client: TestClient, db: Session, admin_token: str):
    app = create_selected_app(db)
    results = []

    def try_activate():
        # Dedicated client call in thread
        res = client.post(
            "/api/v1/fellowships/activate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"application_id": str(app.id)},
        )
        results.append(res.status_code)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(try_activate) for _ in range(5)]
        for f in futures:
            f.result()

    success_count = sum(1 for code in results if code == 200)
    conflict_count = sum(1 for code in results if code == 409)

    assert success_count == 1, f"Expected exactly 1 success, got: {success_count}"
    assert conflict_count == 4, f"Expected 4 conflicts, got: {conflict_count}"

    fel_count = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).count()
    assert fel_count == 1


# -----------------------------------------------------------------------------
# 14. Concurrent Renewal Approval: Exactly One Year Advance
# -----------------------------------------------------------------------------
def test_concurrent_renewal_approval_exact_one_year_advance(client: TestClient, db: Session, admin_token: str, officer_token: str, applicant_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    res_sub = client.post(
        f"/api/v1/fellowships/{fellowship.id}/renewals",
        headers={"Authorization": f"Bearer {applicant_token}"},
        json={"academic_year": 2, "annual_progress_summary": "Year 1 progress"},
    )
    renewal_id = res_sub.json()["id"]

    results = []

    def try_approve():
        res = client.post(
            f"/api/v1/fellowships/renewals/{renewal_id}/review",
            headers={"Authorization": f"Bearer {officer_token}"},
            json={"decision": "APPROVED", "remarks": "Approved concurrently"},
        )
        results.append(res.status_code)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(try_approve) for _ in range(5)]
        for f in futures:
            f.result()

    db.refresh(fellowship)
    assert fellowship.current_year == 2


# -----------------------------------------------------------------------------
# 15. Concurrent Installment Execution: Exactly One Payment Dispatch
# -----------------------------------------------------------------------------
def test_concurrent_installment_execution_exact_one_payment(client: TestClient, db: Session, admin_token: str, officer_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    inst = (
        db.query(DisbursementInstallment)
        .filter(DisbursementInstallment.fellowship_id == fellowship.id)
        .first()
    )
    client.post(f"/api/v1/disbursements/{inst.id}/approve", headers={"Authorization": f"Bearer {officer_token}"})

    results = []

    def try_execute():
        res = client.post(
            f"/api/v1/disbursements/{inst.id}/execute",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        results.append(res.status_code)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(try_execute) for _ in range(5)]
        for f in futures:
            f.result()

    db.refresh(inst)
    assert inst.payment_status == "SUCCESS"
    assert inst.bank_reference_utr is not None


# -----------------------------------------------------------------------------
# 16. RBAC Exclusions and Banking PII Masking
# -----------------------------------------------------------------------------
def test_rbac_and_banking_pii_masking(client: TestClient, db: Session, committee_token: str, applicant_token: str, admin_token: str):
    app = create_selected_app(db)
    client.post("/api/v1/fellowships/activate", headers={"Authorization": f"Bearer {admin_token}"}, json={"application_id": str(app.id)})
    fellowship = db.query(FellowshipRecord).filter(FellowshipRecord.application_id == app.id).first()

    comm_headers = {"Authorization": f"Bearer {committee_token}"}

    # COMMITTEE has zero Phase 8 operational permissions -> 403 Forbidden
    res1 = client.get("/api/v1/fellowships/my", headers=comm_headers)
    assert res1.status_code == 403

    res2 = client.post("/api/v1/fellowships/activate", headers=comm_headers, json={"application_id": str(app.id)})
    assert res2.status_code == 403

    inst = db.query(DisbursementInstallment).filter(DisbursementInstallment.fellowship_id == fellowship.id).first()
    res3 = client.post(f"/api/v1/disbursements/{inst.id}/execute", headers=comm_headers)
    assert res3.status_code == 403

    # Scholar retrieves installment schedule -> verifies masked bank account
    app_headers = {"Authorization": f"Bearer {applicant_token}"}
    res_disb = client.get(f"/api/v1/fellowships/{fellowship.id}/disbursements", headers=app_headers)
    assert res_disb.status_code == 200
    disb_list = res_disb.json()
    assert len(disb_list) > 0
    for item in disb_list:
        assert item["account_number_masked"] == "XXXXXX1234"
        assert "account_number" not in item  # Raw number is never returned
