import uuid
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from fastapi import HTTPException, status

from app.core.enums import (
    UserRole,
    ApplicationStatus,
    SubmissionStatus,
    FellowshipStatus,
    DisbursementStatus,
    AuditEntityType,
)
from app.core.status_transitions import (
    can_transition_fellowship,
    can_transition_application,
)
from app.models.application import Application
from app.models.fellowship import (
    FellowshipRecord,
    RenewalSubmission,
    ProgressReport,
    DisbursementInstallment,
)
from app.models.deficiency import Deficiency
from app.models.selection_result import SelectionResult
from app.models.user import User
from app.models.scheme import Scheme
from app.models.scheme_version import SchemeVersion
from app.models.audit_log import AuditLog
from app.schemas.fellowship import (
    AwardAcceptanceRequest,
    AwardAcceptanceResponse,
    FellowshipActivationRequest,
    FellowshipRecordResponse,
    RenewalSubmitRequest,
    RenewalReviewRequest,
    RenewalResponse,
    ProgressReportSubmitRequest,
    ProgressReportReviewRequest,
    ProgressReportResponse,
    FellowshipStatusUpdateRequest,
)

logger = logging.getLogger(__name__)


class FellowshipService:
    def __init__(self, db: Session):
        self.db = db

    def record_award_acceptance(
        self, application_id: uuid.UUID, scholar: User, request: AwardAcceptanceRequest
    ) -> AwardAcceptanceResponse:
        """
        Applicant submits Award Acceptance & Joining Undertaking.
        Does NOT create the official sanction or fellowship record.
        """
        app = (
            self.db.query(Application)
            .filter(Application.id == application_id)
            .with_for_update()
            .first()
        )
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
            )

        # Applicant can only accept for their own application
        if scholar.role != UserRole.ADMIN and app.applicant_id != scholar.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to submit acceptance for this application",
            )

        # Application must be SELECTED
        if app.status != ApplicationStatus.SELECTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application is in status '{app.status}', must be 'SELECTED' to accept award",
            )

        # SelectionResult must exist and be SELECTED
        sel_result = (
            self.db.query(SelectionResult)
            .filter(
                SelectionResult.application_id == application_id,
                SelectionResult.result == "SELECTED",
            )
            .first()
        )
        if not sel_result:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No finalized SELECTED selection result found for this application",
            )

        # Extract last4 of account number - full account number is NEVER persisted in DB
        account_last4 = request.bank_account_number[-4:]

        # Update application data
        data = dict(app.form_data or {})
        acceptance_info = {
            "acceptance_recorded": True,
            "acceptance_submitted_at": datetime.now(timezone.utc).isoformat(),
            "joining_date": str(request.joining_date),
            "institution_name": request.institution_name,
            "department": request.department,
            "guide_name": request.guide_name,
            "research_topic": request.research_topic,
            "account_number_last4": account_last4,
            "ifsc_code": request.ifsc_code.upper(),
        }
        data["award_acceptance"] = acceptance_info
        app.form_data = data

        # Audit log with masked account
        audit = AuditLog(
            application_id=app.id,
            entity_type=AuditEntityType.APPLICATION.value,
            entity_id=str(app.id),
            actor_id=scholar.id,
            action="AWARD_ACCEPTANCE_SUBMITTED",
            previous_status=app.status.value,
            new_status=app.status.value,
            details={
                "institution_name": request.institution_name,
                "joining_date": str(request.joining_date),
                "bank_account": f"XXXXXX{account_last4}",
                "ifsc": request.ifsc_code.upper(),
            },
        )
        self.db.add(audit)
        self.db.commit()

        return AwardAcceptanceResponse(
            application_id=app.id,
            status=app.status.value,
            acceptance_recorded=True,
            message="Award acceptance and joining undertaking recorded successfully. Pending administrative sanction and activation.",
        )

    def activate_fellowship(
        self, actor: User, request: FellowshipActivationRequest
    ) -> FellowshipRecord:
        """
        Authoritative activation of fellowship and sanction creation.
        Restricted to ADMIN or assigned OFFICER.
        """
        if actor.role not in [UserRole.ADMIN, UserRole.OFFICER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ADMIN or authorized OFFICER can activate fellowships",
            )

        app = (
            self.db.query(Application)
            .filter(Application.id == request.application_id)
            .with_for_update()
            .first()
        )
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
            )

        # OFFICER scope check
        if actor.role == UserRole.OFFICER:
            from app.services.officer_service import OfficerService

            officer_svc = OfficerService(self.db)
            scope = officer_svc.get_officer_assignment_scope(actor.id)
            if not scope["is_global"]:
                assignments = scope["assignments"]
                assigned_scheme_ids = [
                    a.scheme_id for a in assignments if a.scheme_id is not None
                ]
                if assigned_scheme_ids and app.scheme_id not in assigned_scheme_ids:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Officer is not assigned to the scheme of this application",
                    )

        if app.status != ApplicationStatus.SELECTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot activate fellowship: Application is in status '{app.status}', must be 'SELECTED'",
            )

        # Check existing fellowship
        existing = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.application_id == app.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fellowship record already exists and is active for this application",
            )

        # Binding frozen scheme-version rules
        scheme_ver = app.scheme_version
        fin_rules = (
            app.frozen_rules_snapshot
            or (scheme_ver.scoring_weights if scheme_ver else {})
            or {}
        ).get("financial_rules", {})

        monthly_stipend = float(fin_rules.get("monthly_stipend", 31000.0))
        annual_contingency = float(fin_rules.get("annual_contingency", 10000.0))
        annual_hra = float(fin_rules.get("annual_hra", 0.0))
        tenure_years = request.tenure_years or 5

        # Sanction & Fellowship numbers
        sanction_number = (
            request.sanction_order_number
            or f"DEMO-SANCTION-MTA-2026-{uuid.uuid4().hex[:8].upper()}"
        )
        fellowship_number = f"MTA-FEL-2026-{uuid.uuid4().hex[:8].upper()}"

        start_date = request.start_date or date.today()
        end_date = start_date + timedelta(days=365 * tenure_years)

        # Onboarding metadata
        acceptance_info = (app.form_data or {}).get("award_acceptance", {})
        institution_name = acceptance_info.get(
            "institution_name",
            (app.form_data or {}).get("education", {}).get("institution", "National Institute"),
        )
        department = acceptance_info.get("department")
        guide_name = acceptance_info.get("guide_name")
        research_topic = acceptance_info.get("research_topic")
        account_last4 = acceptance_info.get("account_number_last4", "1234")
        ifsc_code = acceptance_info.get("ifsc_code", "SBIN0001234")

        fellowship = FellowshipRecord(
            application_id=app.id,
            fellowship_number=fellowship_number,
            sanction_order_number=sanction_number,
            sanction_mode="DEMO_SIMULATED",
            sanction_date=date.today(),
            scheme_id=app.scheme_id,
            scheme_version_id=app.scheme_version_id,
            applicant_id=app.applicant_id,
            assigned_officer_id=actor.id if actor.role == UserRole.OFFICER else None,
            status=FellowshipStatus.ACTIVE.value,
            current_year=1,
            tenure_years=tenure_years,
            start_date=start_date,
            end_date=end_date,
            institution_name=institution_name,
            department=department,
            guide_name=guide_name,
            research_topic=research_topic,
            award_letter_url=f"/documents/award_letters/{fellowship_number}.pdf",
            disbursement_status=DisbursementStatus.SCHEDULED,
        )
        self.db.add(fellowship)
        self.db.flush()

        # Generate 5-year scheduled installment schedule
        for year in range(1, tenure_years + 1):
            p_start = start_date + timedelta(days=365 * (year - 1))
            p_end = start_date + timedelta(days=365 * year)
            y_stipend = monthly_stipend * 12
            y_contingency = annual_contingency
            y_hra = annual_hra
            y_total = y_stipend + y_contingency + y_hra

            inst = DisbursementInstallment(
                fellowship_id=fellowship.id,
                installment_number=year,
                academic_year=year,
                period_start=p_start,
                period_end=p_end,
                stipend_amount=y_stipend,
                contingency_amount=y_contingency,
                hra_amount=y_hra,
                total_amount=y_total,
                payment_status=DisbursementStatus.SCHEDULED.value,
                integration_mode="SIMULATED_MOCK",
                payment_request_id=uuid.uuid4(),
                account_number_last4=account_last4,
                ifsc_code=ifsc_code,
                retry_count=0,
            )
            self.db.add(inst)

        # Transition Application to FELLOWSHIP_ACTIVE
        app.status = ApplicationStatus.FELLOWSHIP_ACTIVE

        # Audit log
        audit = AuditLog(
            application_id=app.id,
            entity_type=AuditEntityType.FELLOWSHIP.value,
            entity_id=str(fellowship.id),
            actor_id=actor.id,
            action="FELLOWSHIP_ACTIVATED_BY_ADMIN",
            previous_status=ApplicationStatus.SELECTED.value,
            new_status=ApplicationStatus.FELLOWSHIP_ACTIVE.value,
            details={
                "fellowship_number": fellowship_number,
                "sanction_order_number": sanction_number,
                "tenure_years": tenure_years,
                "stipend_amount_annual": monthly_stipend * 12,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(fellowship)
        return fellowship

    def get_fellowship_by_id(self, fellowship_id: uuid.UUID, actor: User) -> FellowshipRecord:
        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == fellowship_id)
            .first()
        )
        if not fellowship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Fellowship record not found"
            )

        if actor.role == UserRole.APPLICANT and fellowship.applicant_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this fellowship record",
            )
        return fellowship

    def get_my_fellowship(self, scholar: User) -> FellowshipRecord:
        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.applicant_id == scholar.id)
            .order_by(FellowshipRecord.created_at.desc())
            .first()
        )
        if not fellowship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active fellowship found for current scholar",
            )
        return fellowship

    def submit_renewal(
        self, fellowship_id: uuid.UUID, scholar: User, request: RenewalSubmitRequest
    ) -> RenewalSubmission:
        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == fellowship_id)
            .with_for_update()
            .first()
        )
        if not fellowship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Fellowship not found"
            )

        if scholar.role != UserRole.ADMIN and fellowship.applicant_id != scholar.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to submit renewal for this fellowship",
            )

        if fellowship.status in [
            FellowshipStatus.SUSPENDED.value,
            FellowshipStatus.TERMINATED.value,
            FellowshipStatus.COMPLETED.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot submit renewal while fellowship status is '{fellowship.status}'",
            )

        # Strict Year Sequencing Invariant
        expected_year = fellowship.current_year + 1
        if request.academic_year != expected_year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Strict academic year sequence violation: Expected renewal for Year {expected_year}, but received Year {request.academic_year}",
            )

        if request.academic_year > fellowship.tenure_years:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Renewal year {request.academic_year} exceeds fellowship tenure ({fellowship.tenure_years} years)",
            )

        # Uniqueness per year check
        existing_renewal = (
            self.db.query(RenewalSubmission)
            .filter(
                RenewalSubmission.fellowship_id == fellowship.id,
                RenewalSubmission.academic_year == request.academic_year,
            )
            .first()
        )
        if existing_renewal:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Renewal submission already exists for academic year {request.academic_year}",
            )

        renewal = RenewalSubmission(
            fellowship_id=fellowship.id,
            renewal_number=request.academic_year - 1,
            academic_year=request.academic_year,
            status=SubmissionStatus.PENDING,
            annual_progress_summary=request.annual_progress_summary,
            marks_percentage=request.marks_percentage,
            continuation_certificate_path=request.continuation_certificate_path,
            marksheet_document_path=request.marksheet_document_path,
            documents=request.documents or {},
        )
        self.db.add(renewal)

        # Transition fellowship to UNDER_RENEWAL
        fellowship.status = FellowshipStatus.UNDER_RENEWAL.value

        audit = AuditLog(
            application_id=fellowship.application_id,
            entity_type=AuditEntityType.FELLOWSHIP.value,
            entity_id=str(fellowship.id),
            actor_id=scholar.id,
            action="RENEWAL_SUBMITTED",
            previous_status=FellowshipStatus.ACTIVE.value,
            new_status=FellowshipStatus.UNDER_RENEWAL.value,
            details={
                "academic_year": request.academic_year,
                "renewal_number": renewal.renewal_number,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(renewal)
        return renewal

    def review_renewal(
        self, renewal_id: uuid.UUID, actor: User, request: RenewalReviewRequest
    ) -> RenewalSubmission:
        if actor.role not in [UserRole.ADMIN, UserRole.OFFICER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ADMIN or OFFICER can review renewals",
            )

        renewal = (
            self.db.query(RenewalSubmission)
            .filter(RenewalSubmission.id == renewal_id)
            .with_for_update()
            .first()
        )
        if not renewal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Renewal submission not found"
            )

        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == renewal.fellowship_id)
            .with_for_update()
            .first()
        )

        decision = request.decision.upper()
        if decision == "APPROVED":
            renewal.status = SubmissionStatus.APPROVED
            renewal.reviewer_decision = "APPROVED"
            renewal.reviewer_id = actor.id
            renewal.reviewer_remarks = request.remarks
            renewal.reviewed_at = datetime.now(timezone.utc)

            # Atomic Year Advancement
            fellowship.current_year = renewal.academic_year
            fellowship.status = FellowshipStatus.ACTIVE.value

            audit_action = "RENEWAL_APPROVED"

        elif decision == "DEFICIENT":
            # 100% Phase 5 Deficiency Integration
            deficiency = Deficiency(
                application_id=fellowship.application_id,
                document_id=request.deficient_document_id,
                reason=request.deficiency_reason or "RENEWAL_DOCUMENT_DEFICIENT",
                applicant_message=request.deficiency_message
                or "The submitted renewal document has deficiencies. Please upload a replacement.",
                status="OPEN",
            )
            self.db.add(deficiency)
            self.db.flush()

            renewal.deficiency_id = deficiency.id
            renewal.status = SubmissionStatus.DEFICIENT
            renewal.reviewer_decision = "DEFICIENT"
            renewal.reviewer_id = actor.id
            renewal.reviewer_remarks = request.remarks
            renewal.reviewed_at = datetime.now(timezone.utc)

            audit_action = "RENEWAL_FLAGGED_DEFICIENT"

        elif decision == "REJECTED":
            renewal.status = SubmissionStatus.REJECTED
            renewal.reviewer_decision = "REJECTED"
            renewal.reviewer_id = actor.id
            renewal.reviewer_remarks = request.remarks
            renewal.reviewed_at = datetime.now(timezone.utc)

            audit_action = "RENEWAL_REJECTED"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid renewal review decision: '{request.decision}'",
            )

        audit = AuditLog(
            application_id=fellowship.application_id,
            entity_type=AuditEntityType.FELLOWSHIP.value,
            entity_id=str(fellowship.id),
            actor_id=actor.id,
            action=audit_action,
            previous_status=SubmissionStatus.PENDING.value,
            new_status=renewal.status.value,
            details={
                "renewal_id": str(renewal.id),
                "academic_year": renewal.academic_year,
                "current_fellowship_year": fellowship.current_year,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(renewal)
        return renewal

    def submit_progress_report(
        self, fellowship_id: uuid.UUID, scholar: User, request: ProgressReportSubmitRequest
    ) -> ProgressReport:
        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == fellowship_id)
            .first()
        )
        if not fellowship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Fellowship not found"
            )

        if scholar.role != UserRole.ADMIN and fellowship.applicant_id != scholar.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to submit progress report for this fellowship",
            )

        if fellowship.status in [
            FellowshipStatus.SUSPENDED.value,
            FellowshipStatus.TERMINATED.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot submit progress report while fellowship is '{fellowship.status}'",
            )

        report = ProgressReport(
            fellowship_id=fellowship.id,
            academic_year=request.academic_year,
            report_period_start=request.report_period_start,
            report_period_end=request.report_period_end,
            file_path=request.file_path,
            description=request.description,
            publications_count=request.publications_count,
            presentations_count=request.presentations_count,
            patents_count=request.patents_count,
            supervisor_remarks=request.supervisor_remarks,
            supervisor_approved=request.supervisor_approved,
            status=SubmissionStatus.PENDING,
        )
        self.db.add(report)

        audit = AuditLog(
            application_id=fellowship.application_id,
            entity_type=AuditEntityType.FELLOWSHIP.value,
            entity_id=str(fellowship.id),
            actor_id=scholar.id,
            action="PROGRESS_REPORT_SUBMITTED",
            previous_status=None,
            new_status=SubmissionStatus.PENDING.value,
            details={
                "academic_year": request.academic_year,
                "publications_count": request.publications_count,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(report)
        return report

    def review_progress_report(
        self, report_id: uuid.UUID, actor: User, request: ProgressReportReviewRequest
    ) -> ProgressReport:
        if actor.role not in [UserRole.ADMIN, UserRole.OFFICER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ADMIN or OFFICER can review progress reports",
            )

        report = (
            self.db.query(ProgressReport)
            .filter(ProgressReport.id == report_id)
            .with_for_update()
            .first()
        )
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Progress report not found"
            )

        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == report.fellowship_id)
            .first()
        )

        decision = request.decision.upper()
        if decision == "APPROVED":
            report.status = SubmissionStatus.APPROVED
            report.reviewer_decision = "APPROVED"
            report.reviewer_id = actor.id
            report.reviewer_remarks = request.remarks
            report.reviewed_at = datetime.now(timezone.utc)
            # CRITICAL: Progress reports do NOT advance current_year!

        elif decision == "DEFICIENT":
            deficiency = Deficiency(
                application_id=fellowship.application_id,
                document_id=request.deficient_document_id,
                reason=request.deficiency_reason or "PROGRESS_REPORT_DEFICIENT",
                applicant_message=request.deficiency_message
                or "The progress report requires amendments. Please upload a revised report.",
                status="OPEN",
            )
            self.db.add(deficiency)
            self.db.flush()

            report.deficiency_id = deficiency.id
            report.status = SubmissionStatus.DEFICIENT
            report.reviewer_decision = "DEFICIENT"
            report.reviewer_id = actor.id
            report.reviewer_remarks = request.remarks
            report.reviewed_at = datetime.now(timezone.utc)

        elif decision == "REJECTED":
            report.status = SubmissionStatus.REJECTED
            report.reviewer_decision = "REJECTED"
            report.reviewer_id = actor.id
            report.reviewer_remarks = request.remarks
            report.reviewed_at = datetime.now(timezone.utc)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid progress report decision: '{request.decision}'",
            )

        self.db.commit()
        self.db.refresh(report)
        return report

    def update_fellowship_status(
        self, fellowship_id: uuid.UUID, actor: User, request: FellowshipStatusUpdateRequest
    ) -> FellowshipRecord:
        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == fellowship_id)
            .with_for_update()
            .first()
        )
        if not fellowship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Fellowship record not found"
            )

        target_status = FellowshipStatus(request.status.upper())
        current_status = FellowshipStatus(fellowship.status)

        # Validate legal transition
        if not can_transition_fellowship(current_status, target_status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Illegal fellowship transition from '{current_status}' to '{target_status}'",
            )

        # Reinstatement (SUSPENDED -> ACTIVE) requires ADMIN and statutory order
        if current_status == FellowshipStatus.SUSPENDED and target_status == FellowshipStatus.ACTIVE:
            if actor.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Fellowship reinstatement strictly requires ADMIN role",
                )
            if not request.statutory_order_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Reinstatement order requires statutory_order_number",
                )

        # Apply status change
        fellowship.status = target_status.value

        # Cascading effect across payment states when SUSPENDED
        if target_status == FellowshipStatus.SUSPENDED:
            installments = (
                self.db.query(DisbursementInstallment)
                .filter(DisbursementInstallment.fellowship_id == fellowship.id)
                .with_for_update()
                .all()
            )
            for inst in installments:
                if inst.payment_status in [
                    DisbursementStatus.PENDING_APPROVAL.value,
                    DisbursementStatus.APPROVED_FOR_PAYMENT.value,
                ]:
                    inst.payment_status = DisbursementStatus.CANCELLED.value
                    inst.failure_reason = "CANCELLED_DUE_TO_FELLOWSHIP_SUSPENSION"
                # SCHEDULED: remains SCHEDULED (frozen)
                # PROCESSING: allowed to settle (in-flight guarantee)
                # SUCCESS: untouched (permanent ledger)
                # FAILED: retries blocked

        audit = AuditLog(
            application_id=fellowship.application_id,
            entity_type=AuditEntityType.FELLOWSHIP.value,
            entity_id=str(fellowship.id),
            actor_id=actor.id,
            action=f"FELLOWSHIP_STATUS_CHANGED_TO_{target_status.value}",
            previous_status=current_status.value,
            new_status=target_status.value,
            details={
                "reason": request.reason,
                "statutory_order": request.statutory_order_number,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(fellowship)
        return fellowship
