import uuid
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel


class PFMSPaymentResult(BaseModel):
    is_success: bool
    integration_mode: str = "SIMULATED_MOCK"
    payment_request_id: uuid.UUID
    pfms_reference_id: str
    bank_reference_utr: Optional[str] = None
    failure_reason: Optional[str] = None
    processed_at: str
    demo_disclaimer: str = "SIMULATED ENVIRONMENT: No actual government funds were transferred."


class IPFMSAdapter(ABC):
    @abstractmethod
    def dispatch_payment(
        self,
        payment_request_id: uuid.UUID,
        installment_id: uuid.UUID,
        beneficiary_name: str,
        account_number: str,
        ifsc_code: str,
        amount: float,
        scheme_code: str,
        sanction_number: str,
    ) -> PFMSPaymentResult:
        """Dispatches an installment to the payment gateway."""
        pass


class MockPFMSAdapter(IPFMSAdapter):
    """
    Statutory mock implementation for simulated PFMS integration.
    Guarantees deterministic mock outcomes, test account simulations, and idempotent replays.
    NOTE: In prototype/demo mode, raw account numbers are accepted only as transient in-memory
    test fixture inputs for dispatch simulation and are NEVER persisted or logged.
    """

    def __init__(self):
        self._processed_requests: Dict[uuid.UUID, PFMSPaymentResult] = {}
        self._lock = threading.Lock()

    def dispatch_payment(
        self,
        payment_request_id: uuid.UUID,
        installment_id: uuid.UUID,
        beneficiary_name: str,
        account_number: str,
        ifsc_code: str,
        amount: float,
        scheme_code: str,
        sanction_number: str,
    ) -> PFMSPaymentResult:
        with self._lock:
            # Idempotency check: if payment_request_id was already processed, return stored result
            if payment_request_id in self._processed_requests:
                return self._processed_requests[payment_request_id]

            now_iso = datetime.now(timezone.utc).isoformat()

            # Deterministic test simulation triggers based on account number suffix
            if account_number and account_number.endswith("9999"):
                result = PFMSPaymentResult(
                    is_success=False,
                    payment_request_id=payment_request_id,
                    pfms_reference_id=f"PFMS-SIM-ERR-{uuid.uuid4().hex[:8].upper()}",
                    bank_reference_utr=None,
                    failure_reason="BENEFICIARY_NAME_MISMATCH_AT_DESTINATION_BANK",
                    processed_at=now_iso,
                )
            elif account_number and account_number.endswith("8888"):
                result = PFMSPaymentResult(
                    is_success=False,
                    payment_request_id=payment_request_id,
                    pfms_reference_id=f"PFMS-SIM-ERR-{uuid.uuid4().hex[:8].upper()}",
                    bank_reference_utr=None,
                    failure_reason="INVALID_BANK_IFSC_CODE_OR_BRANCH_CLOSED",
                    processed_at=now_iso,
                )
            else:
                sim_utr = f"UTR-SIM-{int(datetime.now(timezone.utc).timestamp())}-{uuid.uuid4().hex[:6].upper()}"
                result = PFMSPaymentResult(
                    is_success=True,
                    payment_request_id=payment_request_id,
                    pfms_reference_id=f"PFMS-SIM-2026-{uuid.uuid4().hex[:8].upper()}",
                    bank_reference_utr=sim_utr,
                    failure_reason=None,
                    processed_at=now_iso,
                )

            self._processed_requests[payment_request_id] = result
            return result


# Singleton instance for system usage
pfms_adapter: IPFMSAdapter = MockPFMSAdapter()
