import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field


class AwardAcceptanceRequest(BaseModel):
    application_id: uuid.UUID
    joining_date: date
    institution_name: str
    department: Optional[str] = None
    guide_name: Optional[str] = None
    research_topic: Optional[str] = None
    bank_account_number: str = Field(..., min_length=9, max_length=18)
    ifsc_code: str = Field(..., min_length=11, max_length=11)


class AwardAcceptanceResponse(BaseModel):
    application_id: uuid.UUID
    status: str
    acceptance_recorded: bool
    message: str


class FellowshipActivationRequest(BaseModel):
    application_id: uuid.UUID
    start_date: Optional[date] = None
    tenure_years: Optional[int] = 5
    sanction_order_number: Optional[str] = None


class FellowshipRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    fellowship_number: str
    sanction_order_number: Optional[str] = None
    sanction_mode: str
    sanction_date: Optional[date] = None
    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    applicant_id: uuid.UUID
    assigned_officer_id: Optional[uuid.UUID] = None
    status: str
    current_year: int
    tenure_years: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    institution_name: Optional[str] = None
    department: Optional[str] = None
    guide_name: Optional[str] = None
    research_topic: Optional[str] = None
    award_letter_url: Optional[str] = None
    disbursement_status: str
    created_at: datetime
    updated_at: datetime


class RenewalSubmitRequest(BaseModel):
    academic_year: int
    annual_progress_summary: Optional[str] = None
    marks_percentage: Optional[float] = None
    continuation_certificate_path: Optional[str] = None
    marksheet_document_path: Optional[str] = None
    documents: Optional[Dict[str, Any]] = None


class RenewalReviewRequest(BaseModel):
    decision: str  # APPROVED, REJECTED, DEFICIENT
    remarks: Optional[str] = None
    deficiency_reason: Optional[str] = None
    deficiency_message: Optional[str] = None
    deficient_document_id: Optional[uuid.UUID] = None


class RenewalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fellowship_id: uuid.UUID
    renewal_number: int
    academic_year: int
    status: str
    annual_progress_summary: Optional[str] = None
    marks_percentage: Optional[float] = None
    continuation_certificate_path: Optional[str] = None
    marksheet_document_path: Optional[str] = None
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_decision: Optional[str] = None
    reviewer_remarks: Optional[str] = None
    deficiency_id: Optional[uuid.UUID] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None


class ProgressReportSubmitRequest(BaseModel):
    academic_year: int
    report_period_start: Optional[date] = None
    report_period_end: Optional[date] = None
    file_path: str
    description: Optional[str] = None
    publications_count: int = 0
    presentations_count: int = 0
    patents_count: int = 0
    supervisor_remarks: Optional[str] = None
    supervisor_approved: bool = False


class ProgressReportReviewRequest(BaseModel):
    decision: str  # APPROVED, REJECTED, DEFICIENT
    remarks: Optional[str] = None
    deficiency_reason: Optional[str] = None
    deficiency_message: Optional[str] = None
    deficient_document_id: Optional[uuid.UUID] = None


class ProgressReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fellowship_id: uuid.UUID
    academic_year: int
    report_period_start: Optional[date] = None
    report_period_end: Optional[date] = None
    file_path: str
    description: Optional[str] = None
    publications_count: int
    presentations_count: int
    patents_count: int
    supervisor_remarks: Optional[str] = None
    supervisor_approved: bool
    status: str
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_decision: Optional[str] = None
    reviewer_remarks: Optional[str] = None
    deficiency_id: Optional[uuid.UUID] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None


class DisbursementInstallmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fellowship_id: uuid.UUID
    installment_number: int
    academic_year: int
    period_start: date
    period_end: date
    stipend_amount: float
    contingency_amount: float
    hra_amount: float
    total_amount: float
    payment_status: str
    integration_mode: str
    payment_request_id: uuid.UUID
    pfms_reference_id: Optional[str] = None
    bank_reference_utr: Optional[str] = None
    account_number_masked: str
    ifsc_code: str
    retry_count: int
    last_attempt_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    approved_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None


class DisbursementApproveRequest(BaseModel):
    remarks: Optional[str] = None


class DisbursementExecuteResponse(BaseModel):
    installment_id: uuid.UUID
    payment_status: str
    is_success: bool
    pfms_reference_id: Optional[str] = None
    bank_reference_utr: Optional[str] = None
    failure_reason: Optional[str] = None
    processed_at: str
    demo_disclaimer: str = "SIMULATED ENVIRONMENT: No actual government funds were transferred."


class FellowshipStatusUpdateRequest(BaseModel):
    status: str  # ACTIVE, SUSPENDED, TERMINATED, COMPLETED
    reason: str
    statutory_order_number: Optional[str] = None
