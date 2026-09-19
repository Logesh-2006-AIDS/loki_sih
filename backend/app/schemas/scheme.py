import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Scheme Version Schemas (Authoritative Configuration Source)
# ---------------------------------------------------------------------------

class SchemeVersionBase(BaseModel):
    scheme_version: str
    name: str
    description: Optional[str] = None
    is_demo: bool = True
    eligibility_rules: Dict[str, Any] = Field(default_factory=dict)
    form_schema: Dict[str, Any] = Field(default_factory=dict)
    required_documents: Dict[str, Any] = Field(default_factory=dict)
    scoring_weights: Dict[str, Any] = Field(default_factory=dict)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    is_active: bool = False
    is_locked: bool = False


class SchemeVersionCreate(BaseModel):
    scheme_version: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_demo: bool = True
    eligibility_rules: Dict[str, Any] = Field(default_factory=dict)
    form_schema: Dict[str, Any] = Field(default_factory=dict)
    required_documents: Dict[str, Any] = Field(default_factory=dict)
    scoring_weights: Dict[str, Any] = Field(default_factory=dict)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    is_active: bool = False


class SchemeVersionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_demo: Optional[bool] = None
    eligibility_rules: Optional[Dict[str, Any]] = None
    form_schema: Optional[Dict[str, Any]] = None
    required_documents: Optional[Dict[str, Any]] = None
    scoring_weights: Optional[Dict[str, Any]] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    is_active: Optional[bool] = None


class SchemeVersionResponse(BaseModel):
    id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_code: str
    scheme_version: str
    name: str
    description: Optional[str] = None
    is_demo: bool = True
    eligibility_rules: Dict[str, Any]
    form_schema: Dict[str, Any]
    required_documents: Dict[str, Any]
    scoring_weights: Dict[str, Any]
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    is_active: bool
    is_locked: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Scheme Catalog Schemas (Parent Entity)
# ---------------------------------------------------------------------------

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
    deadline: Optional[datetime] = None
    is_active: Optional[bool] = None


class SchemeResponse(SchemeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    active_version_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class SchemeDetailResponse(SchemeResponse):
    active_version: Optional[SchemeVersionResponse] = None
    versions_count: int = 0


# ---------------------------------------------------------------------------
# Self-Eligibility Evaluation Schemas
# ---------------------------------------------------------------------------

from app.services.rules_engine import RuleCheckDetail


class EligibilityCheckRequest(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)
    scheme_version_id: Optional[uuid.UUID] = None


class EligibilityCheckResponse(BaseModel):
    eligible: bool
    summary_message: str
    disclaimer: str = (
        "Self-check is indicative only. Final eligibility is subject to "
        "document verification and official scrutiny."
    )
    is_demo: bool = True
    checks: List[RuleCheckDetail] = Field(default_factory=list)

