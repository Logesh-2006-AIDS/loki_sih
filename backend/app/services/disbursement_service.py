import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.enums import (
    UserRole,
    FellowshipStatus,
    DisbursementStatus,
    AuditEntityType,
)
from app.core.status_transitions import can_transition_disbursement
from app.models.fellowship import FellowshipRecord, DisbursementInstallment
from app.models.user import User
from app.models.audit_log import AuditLog
from app.adapters.pfms_adapter import pfms_adapter, PFMSPaymentResult
from app.schemas.fellowship import (
    DisbursementInstallmentResponse,
    DisbursementExecuteResponse,
)

logger = logging.getLogger(__name__)

MAX_PAYMENT_RETRIES = 3


class FinancialImmutabilityException(HTTPException):
    def __init__(self, detail: str = "Financial amounts cannot be altered once approved or processed"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class DisbursementService:
    def __init__(self, db: Session):
        self.db = db

    def get_fellowship_installments(
        self, fellowship_id: uuid.UUID, actor: User
    ) -> List[DisbursementInstallmentResponse]:
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
                detail="Not authorized to view disbursements for this fellowship",
            )

        installments = (
            self.db.query(DisbursementInstallment)
            .filter(DisbursementInstallment.fellowship_id == fellowship_id)
            .order_by(DisbursementInstallment.installment_number.asc())
            .all()
        )

        results = []
        for inst in installments:
            results.append(
                DisbursementInstallmentResponse(
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
            )
        return results

    def list_all_installments(
        self, actor: User, status_filter: Optional[str] = None
    ) -> List[DisbursementInstallmentResponse]:
        query = self.db.query(DisbursementInstallment)
        if status_filter:
            query = query.filter(DisbursementInstallment.payment_status == status_filter)
        installments = query.order_by(DisbursementInstallment.created_at.desc()).limit(100).all()

        results = []
        for inst in installments:
            results.append(
                DisbursementInstallmentResponse(
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
            )
        return results

    def approve_installment(
        self, installment_id: uuid.UUID, actor: User, remarks: Optional[str] = None
    ) -> DisbursementInstallment:
        if actor.role not in [UserRole.ADMIN, UserRole.OFFICER]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only ADMIN or OFFICER can approve disbursements",
            )

        inst = (
            self.db.query(DisbursementInstallment)
            .filter(DisbursementInstallment.id == installment_id)
            .with_for_update()
            .first()
        )
        if not inst:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Installment not found"
            )

        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == inst.fellowship_id)
            .first()
        )

        if fellowship.status != FellowshipStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot approve installment: Fellowship is in '{fellowship.status}' status",
            )

        if inst.payment_status == DisbursementStatus.APPROVED_FOR_PAYMENT.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Installment has already been approved for payment",
            )

        if inst.payment_status in [
            DisbursementStatus.PROCESSING.value,
            DisbursementStatus.SUCCESS.value,
            DisbursementStatus.CANCELLED.value,
            DisbursementStatus.RETRY_EXHAUSTED.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot approve installment: Current status is '{inst.payment_status}'",
            )

        current_status = DisbursementStatus(inst.payment_status)
        target_status = DisbursementStatus.APPROVED_FOR_PAYMENT

        if not can_transition_disbursement(current_status, target_status):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Illegal installment transition from '{current_status}' to '{target_status}'",
            )

        inst.payment_status = target_status.value
        inst.approved_by = actor.id
        inst.approved_at = datetime.now(timezone.utc)

        audit = AuditLog(
            application_id=fellowship.application_id,
            entity_type=AuditEntityType.DISBURSEMENT.value,
            entity_id=str(inst.id),
            actor_id=actor.id,
            action="DISBURSEMENT_APPROVED_FOR_PAYMENT",
            previous_status=current_status.value,
            new_status=target_status.value,
            details={
                "installment_number": inst.installment_number,
                "amount": float(inst.total_amount),
                "remarks": remarks,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(inst)
        return inst

    def execute_installment(
        self, installment_id: uuid.UUID, actor: User, test_account_override: Optional[str] = None
    ) -> DisbursementExecuteResponse:
        """
        Executes an approved installment via the simulated PFMS gateway adapter.
        Guarantees row-locking, idempotency, and financial immutability.
        """
        if actor.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Disbursement execution strictly requires ADMIN authority",
            )

        inst = (
            self.db.query(DisbursementInstallment)
            .filter(DisbursementInstallment.id == installment_id)
            .with_for_update()
            .first()
        )
        if not inst:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Installment not found"
            )

        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == inst.fellowship_id)
            .first()
        )

        if fellowship.status == FellowshipStatus.SUSPENDED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot execute installment: Fellowship is currently suspended",
            )

        if inst.payment_status == DisbursementStatus.SUCCESS.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Installment has already been successfully disbursed",
            )

        if inst.payment_status not in [
            DisbursementStatus.APPROVED_FOR_PAYMENT.value,
            DisbursementStatus.PROCESSING.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Installment must be in 'APPROVED_FOR_PAYMENT' to execute, currently '{inst.payment_status}'",
            )

        # Atomic transition to PROCESSING
        inst.payment_status = DisbursementStatus.PROCESSING.value
        self.db.flush()

        # Resolve beneficiary details
        beneficiary_name = (
            fellowship.applicant.full_name
            if fellowship.applicant
            else "Fellowship Scholar"
        )
        scheme_code = fellowship.scheme.scheme_code if fellowship.scheme else "MTA-FEL"
        sanction_number = fellowship.sanction_order_number or "DEMO-SANCTION"

        # Dispatch to statutory adapter
        # Test accounts ending in 9999 or 8888 can be passed in test fixture simulation
        dispatch_account = test_account_override or f"00000000{inst.account_number_last4}"

        result: PFMSPaymentResult = pfms_adapter.dispatch_payment(
            payment_request_id=inst.payment_request_id,
            installment_id=inst.id,
            beneficiary_name=beneficiary_name,
            account_number=dispatch_account,
            ifsc_code=inst.ifsc_code,
            amount=float(inst.total_amount),
            scheme_code=scheme_code,
            sanction_number=sanction_number,
        )

        if result.is_success:
            inst.payment_status = DisbursementStatus.SUCCESS.value
            inst.pfms_reference_id = result.pfms_reference_id
            inst.bank_reference_utr = result.bank_reference_utr
            inst.processed_at = datetime.now(timezone.utc)
            inst.failure_reason = None
            action_name = "DISBURSEMENT_PAYMENT_SUCCESS"
        else:
            inst.payment_status = DisbursementStatus.FAILED.value
            inst.failure_reason = result.failure_reason
            inst.last_attempt_at = datetime.now(timezone.utc)
            inst.retry_count += 1
            action_name = "DISBURSEMENT_PAYMENT_FAILED"

        audit = AuditLog(
            application_id=fellowship.application_id,
            entity_type=AuditEntityType.DISBURSEMENT.value,
            entity_id=str(inst.id),
            actor_id=actor.id,
            action=action_name,
            previous_status=DisbursementStatus.APPROVED_FOR_PAYMENT.value,
            new_status=inst.payment_status,
            details={
                "amount": float(inst.total_amount),
                "bank_account": f"XXXXXX{inst.account_number_last4}",
                "utr": inst.bank_reference_utr,
                "failure_reason": inst.failure_reason,
            },
        )
        self.db.add(audit)
        self.db.commit()
        self.db.refresh(inst)

        return DisbursementExecuteResponse(
            installment_id=inst.id,
            payment_status=inst.payment_status,
            is_success=result.is_success,
            pfms_reference_id=inst.pfms_reference_id,
            bank_reference_utr=inst.bank_reference_utr,
            failure_reason=inst.failure_reason,
            processed_at=result.processed_at,
            demo_disclaimer=result.demo_disclaimer,
        )

    def retry_failed_installment(
        self, installment_id: uuid.UUID, actor: User, test_account_override: Optional[str] = None
    ) -> DisbursementExecuteResponse:
        if actor.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Disbursement retry strictly requires ADMIN authority",
            )

        inst = (
            self.db.query(DisbursementInstallment)
            .filter(DisbursementInstallment.id == installment_id)
            .with_for_update()
            .first()
        )
        if not inst:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Installment not found"
            )

        fellowship = (
            self.db.query(FellowshipRecord)
            .filter(FellowshipRecord.id == inst.fellowship_id)
            .first()
        )

        if fellowship.status == FellowshipStatus.SUSPENDED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot retry payment while fellowship is suspended",
            )

        if inst.payment_status != DisbursementStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Only FAILED installments can be retried, current status is '{inst.payment_status}'",
            )

        if inst.retry_count >= MAX_PAYMENT_RETRIES:
            inst.payment_status = DisbursementStatus.RETRY_EXHAUSTED.value
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment retry limit exhausted ({MAX_PAYMENT_RETRIES}/{MAX_PAYMENT_RETRIES}). Transitioned to RETRY_EXHAUSTED.",
            )

        # Fresh payment request id minted for retry idempotency
        inst.payment_request_id = uuid.uuid4()
        inst.payment_status = DisbursementStatus.APPROVED_FOR_PAYMENT.value
        self.db.commit()

        # Re-execute
        return self.execute_installment(
            installment_id=inst.id, actor=actor, test_account_override=test_account_override
        )
