import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class PublicDeficiencyItem(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    cycle: int = 1
    document_id: Optional[uuid.UUID] = None
    document_type: str
    document_name: str
    reason: str
    applicant_message: str
    applicant_remarks: Optional[str] = None
    status: str
    created_at: datetime
    replacement_document_id: Optional[uuid.UUID] = None
    replacement_uploaded_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PublicDeficiencyListResponse(BaseModel):
    application_id: uuid.UUID
    application_status: str
    total: int
    open_count: int
    replacement_uploaded_count: int
    under_review_count: int
    resolved_count: int
    can_resubmit: bool
    items: List[PublicDeficiencyItem]


class DeficiencyReplacementUploadResponse(BaseModel):
    deficiency_id: uuid.UUID
    status: str
    document_id: uuid.UUID
    version: int
    original_filename: str
    applicant_remarks: Optional[str] = None
    uploaded_at: datetime
    message: str


class ApplicationResubmitRequest(BaseModel):
    declaration_confirmed: bool = Field(..., description="Applicant confirmation that uploaded replacements are genuine")
    remarks: Optional[str] = Field(None, max_length=1000, description="Optional resubmission comments from applicant")


class ApplicationResubmitResponse(BaseModel):
    application_id: uuid.UUID
    reference_id: str
    status: str
    resubmission_count: int
    resubmitted_at: datetime
    message: str
