import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class SchemeBase(BaseModel):
    scheme_code: str
    name: str
    description: Optional[str] = None
    scheme_version: str = "1.0"
    is_demo: bool = True
    eligibility_rules: Dict[str, Any] = {}
    form_schema: Dict[str, Any] = {}
    required_documents: Dict[str, Any] = {}
    scoring_weights: Dict[str, Any] = {}
    deadline: Optional[datetime] = None
    is_active: bool = True


class SchemeCreate(SchemeBase):
    pass


class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scheme_version: Optional[str] = None
    is_demo: Optional[bool] = None
    eligibility_rules: Optional[Dict[str, Any]] = None
    form_schema: Optional[Dict[str, Any]] = None
    required_documents: Optional[Dict[str, Any]] = None
    scoring_weights: Optional[Dict[str, Any]] = None
    deadline: Optional[datetime] = None
    is_active: Optional[bool] = None


class SchemeResponse(SchemeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
