import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class MeritScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    scheme_version_id: Optional[uuid.UUID] = None
    batch_id: Optional[uuid.UUID] = None
    total_score: float
    rank: Optional[int] = None
    tie_break_level: Optional[str] = None
    is_current: bool = True
    formula_version: str = "1.0"
    score_breakdown: Dict[str, Any] = {}
    calculated_at: datetime
    calculated_by: Optional[uuid.UUID] = None


class MeritRankItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    application_id: uuid.UUID
    reference_id: str
    applicant_name: str
    total_score: float
    rank: int
    tie_break_level: Optional[str] = None
    status: str
    score_breakdown: Dict[str, Any] = {}


class MeritCalculationBatchResponse(BaseModel):
    batch_id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_version_id: uuid.UUID
    scored_count: int
    status: str
    calculation_timestamp: datetime
    boundary_tie_flag: bool = False
    tied_candidate_ids: List[uuid.UUID] = []
