import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class DocumentVerificationResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    verification_status: str
    ocr_text: Optional[str] = None
    extracted_fields: Dict[str, Any] = {}
    field_confidences: Dict[str, Any] = {}
    comparison_results: Dict[str, Any] = {}
    overall_confidence: Optional[float] = None
    flags: List[Dict[str, Any]] = []
    processed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationVerificationSummaryResponse(BaseModel):
    application_id: uuid.UUID
    application_status: str
    total_documents: int
    verified_count: int
    flagged_count: int
    document_verifications: List[DocumentVerificationResponse]

    model_config = ConfigDict(from_attributes=True)
