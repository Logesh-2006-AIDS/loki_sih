import uuid
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.fellowship import (
    DisbursementInstallmentResponse,
    DisbursementApproveRequest,
    DisbursementExecuteResponse,
)
from app.services.disbursement_service import DisbursementService

router = APIRouter()


class ExecutionRequest(BaseModel):
    test_account_override: Optional[str] = None


@router.get("", response_model=List[DisbursementInstallmentResponse])
def list_disbursements(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.OFFICER])),
):
    """
    List disbursements across fellowships (capped at 100 recent).
    """
    service = DisbursementService(db)
    return service.list_all_installments(current_user, status_filter=status)


@router.post("/{id}/approve", response_model=DisbursementInstallmentResponse)
def approve_installment(
    id: uuid.UUID,
    request: Optional[DisbursementApproveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.OFFICER])),
):
    """
    Approve an installment for payment dispatch.
    Financial amounts become strictly immutable once approved.
    """
    service = DisbursementService(db)
    inst = service.approve_installment(
        id, current_user, remarks=request.remarks if request else None
    )
    return DisbursementInstallmentResponse(
        id=inst.id,
        fellowship_id=inst.fellowship_id,
        installment_number=inst.installment_number,
        academic_year=inst.academic_year,
        period_start=inst.period_start,
        period_end=inst.period_end,
        stipend_amount=float(inst.stipend_amount),
        contingency_amount=float(inst.contingency_amount),
        hra_amount=float(inst.hra_amount),
        total_amount=float(inst.total_amount),
        payment_status=inst.payment_status,
        integration_mode=inst.integration_mode,
        payment_request_id=inst.payment_request_id,
        pfms_reference_id=inst.pfms_reference_id,
        bank_reference_utr=inst.bank_reference_utr,
        account_number_masked=f"XXXXXX{inst.account_number_last4}",
        ifsc_code=inst.ifsc_code,
        retry_count=inst.retry_count,
        last_attempt_at=inst.last_attempt_at,
        processed_at=inst.processed_at,
        failure_reason=inst.failure_reason,
        approved_by=inst.approved_by,
        approved_at=inst.approved_at,
    )


@router.post("/{id}/execute", response_model=DisbursementExecuteResponse)
def execute_installment(
    id: uuid.UUID,
    body: Optional[ExecutionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Dispatch an approved installment to the statutory PFMS simulation adapter.
    Protected by row locks and idempotency keys. Restricted to ADMIN.
    """
    service = DisbursementService(db)
    test_override = body.test_account_override if body else None
    return service.execute_installment(id, current_user, test_account_override=test_override)


@router.post("/{id}/retry", response_model=DisbursementExecuteResponse)
def retry_failed_installment(
    id: uuid.UUID,
    body: Optional[ExecutionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Retry a FAILED installment dispatch.
    Enforces maximum 3 retries, generates a new payment request ID, and preserves failure history.
    """
    service = DisbursementService(db)
    test_override = body.test_account_override if body else None
    return service.retry_failed_installment(
        id, current_user, test_account_override=test_override
    )
