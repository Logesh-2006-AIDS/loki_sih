import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommitteeAssignmentCreate(BaseModel):
    user_id: uuid.UUID
    scheme_id: Optional[uuid.UUID] = None
    role_in_committee: str = "MEMBER"


class CommitteeAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    scheme_id: Optional[uuid.UUID] = None
    role_in_committee: str
    is_active: bool
    assigned_at: datetime


class CommitteeBatchCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    application_ids: List[uuid.UUID] = Field(..., min_length=1)


class BatchAddApplicationRequest(BaseModel):
    application_id: uuid.UUID



class CommitteeBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    status: str
    is_locked: bool
    locked_at: Optional[datetime] = None
    locked_by: Optional[uuid.UUID] = None
    application_count: int
    reviews_completed_count: int
    created_at: datetime


class CommitteeReviewRequest(BaseModel):
    scores: Dict[str, float] = Field(..., description="Map of qualitative component code to numerical score")
    remarks: Optional[str] = Field(None, max_length=2000, description="Confidential committee deliberation notes")
    recommendation: str = Field("RECOMMEND", description="RECOMMEND, WAITLIST, REJECT, or NEEDS_DISCUSSION")


class CommitteeReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    committee_member_id: uuid.UUID
    committee_member_name: Optional[str] = None
    batch_id: uuid.UUID
    scores: Dict[str, Any]
    remarks: Optional[str] = None
    recommendation: str
    is_locked: bool
    created_at: datetime
    updated_at: datetime


class CommitteeDossierResponse(BaseModel):
    application_id: uuid.UUID
    reference_id: str
    batch_id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_name: str
    scheme_version_id: uuid.UUID
    scheme_version: str
    applicant_name: str
    category: Optional[str] = None
    state: Optional[str] = None
    academic_summary: Dict[str, Any] = {}
    proposal_summary: Dict[str, Any] = {}
    verified_documents: List[Dict[str, Any]] = []
    my_review: Optional[CommitteeReviewResponse] = None
    is_batch_locked: bool = False
    required_quorum: int = 1
    completed_reviews_count: int = 0


class BatchFinalizeRequest(BaseModel):
    committee_minutes: str = Field(..., min_length=20, description="Official minutes of the Selection Committee meeting")
    meeting_date: datetime
    resolution_reference: str = Field(..., min_length=3, max_length=128, description="Gazette / Committee Resolution Reference Order")


class TieResolutionRequest(BaseModel):
    preferred_candidate_id: uuid.UUID
    secondary_candidate_id: uuid.UUID
    statutory_justification: str = Field(..., min_length=20, description="Statutory or committee rationale for boundary tie resolution")
    authority_order_reference: str = Field(..., min_length=3, max_length=128)


class SelectionOverrideRequest(BaseModel):
    application_id: uuid.UUID
    target_status: str = Field(..., description="SELECTED or REJECTED")
    override_reason: str = Field(..., min_length=20, description="Detailed statutory / administrative justification")
    authority_reference: str = Field(..., min_length=3, max_length=128, description="Ministry order / court directive reference")
    selection_round: int = Field(2, ge=2)


class SelectionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    result: str
    rank: Optional[int] = None
    quota_category: str
    reason: Optional[str] = None
    committee_minutes: Optional[str] = None
    authority_reference: Optional[str] = None
    selection_round: int
    is_override: bool
    override_reason: Optional[str] = None
    override_by: Optional[uuid.UUID] = None
    finalized_by: Optional[uuid.UUID] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime


class ApplicantSelectionResultResponse(BaseModel):
    application_reference_id: str
    result: str
    rank: Optional[int] = None
    selection_round: int = 1
    finalized_at: Optional[datetime] = None
