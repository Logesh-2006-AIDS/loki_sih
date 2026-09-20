import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.models.fellowship import FellowshipRecord, RenewalSubmission, ProgressReport
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
    DisbursementInstallmentResponse,
    FellowshipStatusUpdateRequest,
)
from app.services.fellowship_service import FellowshipService
from app.services.disbursement_service import DisbursementService

router = APIRouter()


@router.post("/accept-award", response_model=AwardAcceptanceResponse)
def accept_award(
    request: AwardAcceptanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT)),
):
    """
    Applicant submits Award Acceptance & Joining Undertaking.
    Restricted to the selected applicant.
    """
    service = FellowshipService(db)
    return service.record_award_acceptance(request.application_id, current_user, request)


@router.post("/activate", response_model=FellowshipRecordResponse)
def activate_fellowship(
    request: FellowshipActivationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.OFFICER])),
):
    """
    Authoritative Administrative Sanction and Fellowship Activation.
    Restricted strictly to ADMIN or assigned OFFICER. Applicants receive 403.
    """
    service = FellowshipService(db)
    fellowship = service.activate_fellowship(current_user, request)
    return fellowship


@router.get("/my", response_model=FellowshipRecordResponse)
def get_my_fellowship(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT)),
):
    """
    Get current scholar's active fellowship.
    """
    service = FellowshipService(db)
    return service.get_my_fellowship(current_user)


@router.get("/{id}", response_model=FellowshipRecordResponse)
def get_fellowship_detail(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.APPLICANT, UserRole.OFFICER, UserRole.ADMIN])
    ),
):
    """
    Get fellowship record by ID.
    Applicant: own record only. Officer: assigned scheme. Admin: global.
    """
    service = FellowshipService(db)
    return service.get_fellowship_by_id(id, current_user)


@router.post("/{id}/renewals", response_model=RenewalResponse)
def submit_renewal(
    id: uuid.UUID,
    request: RenewalSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT)),
):
    """
    Submit annual academic renewal.
    Enforces renewal.academic_year == fellowship.current_year + 1.
    """
    service = FellowshipService(db)
    return service.submit_renewal(id, current_user, request)


@router.get("/{id}/renewals", response_model=List[RenewalResponse])
def list_renewals(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.APPLICANT, UserRole.OFFICER, UserRole.ADMIN])
    ),
):
    """
    List renewals for a fellowship record.
    """
    fellowship = (
        db.query(FellowshipRecord).filter(FellowshipRecord.id == id).first()
    )
    if not fellowship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fellowship record not found"
        )
    if current_user.role == UserRole.APPLICANT and fellowship.applicant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    renewals = (
        db.query(RenewalSubmission)
        .filter(RenewalSubmission.fellowship_id == id)
        .order_by(RenewalSubmission.academic_year.asc())
        .all()
    )
    return renewals


@router.post("/renewals/{id}/review", response_model=RenewalResponse)
def review_renewal(
    id: uuid.UUID,
    request: RenewalReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.OFFICER])),
):
    """
    Officer or Admin reviews and approves/flags renewal.
    Approval atomically advances fellowship.current_year.
    """
    service = FellowshipService(db)
    return service.review_renewal(id, current_user, request)


@router.post("/{id}/progress-reports", response_model=ProgressReportResponse)
def submit_progress_report(
    id: uuid.UUID,
    request: ProgressReportSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.APPLICANT)),
):
    """
    Submit periodic research progress report.
    """
    service = FellowshipService(db)
    return service.submit_progress_report(id, current_user, request)


@router.get("/{id}/progress-reports", response_model=List[ProgressReportResponse])
def list_progress_reports(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.APPLICANT, UserRole.OFFICER, UserRole.ADMIN])
    ),
):
    fellowship = (
        db.query(FellowshipRecord).filter(FellowshipRecord.id == id).first()
    )
    if not fellowship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fellowship record not found"
        )
    if current_user.role == UserRole.APPLICANT and fellowship.applicant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    reports = (
        db.query(ProgressReport)
        .filter(ProgressReport.fellowship_id == id)
        .order_by(ProgressReport.academic_year.asc(), ProgressReport.submitted_at.desc())
        .all()
    )
    return reports


@router.post("/progress-reports/{id}/review", response_model=ProgressReportResponse)
def review_progress_report(
    id: uuid.UUID,
    request: ProgressReportReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.OFFICER])),
):
    """
    Officer or Admin reviews progress report.
    Does NOT advance academic year.
    """
    service = FellowshipService(db)
    return service.review_progress_report(id, current_user, request)


@router.get("/{id}/disbursements", response_model=List[DisbursementInstallmentResponse])
def get_fellowship_disbursements(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.APPLICANT, UserRole.OFFICER, UserRole.ADMIN])
    ),
):
    """
    List installment schedule for fellowship. Banking info is masked for all viewers.
    """
    service = DisbursementService(db)
    return service.get_fellowship_installments(id, current_user)


@router.patch("/{id}/status", response_model=FellowshipRecordResponse)
def update_fellowship_status(
    id: uuid.UUID,
    request: FellowshipStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Update fellowship status (SUSPENDED, ACTIVE reinstatement, TERMINATED, COMPLETED).
    Restricted strictly to ADMIN.
    """
    service = FellowshipService(db)
    return service.update_fellowship_status(id, current_user, request)
