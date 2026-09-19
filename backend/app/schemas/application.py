import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict
from app.core.enums import ApplicationStatus


class ApplicationBase(BaseModel):
    scheme_id: uuid.UUID
    form_data: Dict[str, Any] = {}


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    form_data: Optional[Dict[str, Any]] = None
    status: Optional[ApplicationStatus] = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    reference_id: str
    applicant_id: uuid.UUID
    scheme_id: uuid.UUID
    status: ApplicationStatus
    form_data: Dict[str, Any]
    merit_score: Optional[float] = None
    submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
