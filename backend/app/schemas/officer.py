import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OfficerQueueItem(BaseModel):
    """
    Officer queue item with minimized PII.
    Applicant email and phone are deliberately excluded.
    """
    id: uuid.UUID
    reference_id: str
    scheme_id: uuid.UUID
    scheme_code: str
    scheme_name: str
    applicant_name: str
    state: Optional[str] = None
    status: str
    submitted_at: Optional[datetime] = None
    total_documents: int = 0
    ai_flagged_count: int = 0
    ai_status: str = "PENDING"
    overall_confidence: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class OfficerQueueCounts(BaseModel):
    pending_review: int = 0
    verified: int = 0
    deficient: int = 0
    rejected: int = 0
    all: int = 0


class OfficerQueueResponse(BaseModel):
    total: int
    skip: int
    limit: int
    counts: OfficerQueueCounts
    items: List[OfficerQueueItem]


class OfficerDocumentScrutinyItem(BaseModel):
    id: uuid.UUID
    document_type: str
    original_filename: str
    mime_type: str
    file_size: int
    status: str
    uploaded_at: datetime

    # Phase 3 OCR / AI Verification Evidence
    ocr_text: Optional[str] = None
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    field_confidences: Dict[str, Any] = Field(default_factory=dict)
    comparison_results: Dict[str, Any] = Field(default_factory=dict)
    overall_confidence: Optional[float] = None
    flags: List[Dict[str, Any]] = Field(default_factory=list)

    # Phase 4 Human Scrutiny Metadata
    officer_decision: Optional[str] = None
    officer_remarks: Optional[str] = None
    ai_override: bool = False
    override_reason: Optional[str] = None
    verified_by: Optional[uuid.UUID] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OfficerApplicationScrutinyResponse(BaseModel):
    id: uuid.UUID
    reference_id: str
    status: str
    submitted_at: Optional[datetime] = None

    # Applicant details for scrutiny screen
    applicant_id: uuid.UUID
    applicant_name: str
    applicant_email: str
    applicant_phone: Optional[str] = None

    # Scheme metadata
    scheme_id: uuid.UUID
    scheme_code: str
    scheme_name: str
    scheme_version: Optional[str] = None
    eligibility_rules: Optional[Dict[str, Any]] = None
    form_schema: Optional[Dict[str, Any]] = None
    required_documents_config: Optional[List[Dict[str, Any]]] = None

    # Application form payload
    form_data: Dict[str, Any] = Field(default_factory=dict)

    # Scrutiny documents & history
    documents: List[OfficerDocumentScrutinyItem] = Field(default_factory=list)
    scrutiny_remarks: Optional[str] = None
    scrutiny_officer_id: Optional[uuid.UUID] = None
    scrutiny_officer_name: Optional[str] = None
    scrutiny_completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OfficerDocumentDecisionRequest(BaseModel):
    decision: str = Field(..., description="VERIFIED, RESUBMISSION_REQUIRED, or REJECTED")
    remarks: Optional[str] = None
    ai_override: bool = False
    override_reason: Optional[str] = None


class DeficiencyItemCreate(BaseModel):
    document_id: Optional[uuid.UUID] = None
    reason: str
    applicant_message: str


class OfficerApplicationDecisionRequest(BaseModel):
    decision: str = Field(..., description="VERIFIED, DEFICIENT, or REJECTED")
    remarks: str = Field(..., min_length=1, description="Officer scrutiny overall remarks")
    deficiencies: Optional[List[DeficiencyItemCreate]] = None


class OfficerStatsResponse(BaseModel):
    pending_review_count: int
    verified_count: int
    deficient_count: int
    rejected_count: int
    total_assigned_count: int
