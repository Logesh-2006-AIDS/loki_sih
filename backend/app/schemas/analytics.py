import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. System Overview Metrics
# ---------------------------------------------------------------------------
class SystemOverviewMetrics(BaseModel):
    total_applications: int = 0
    current_state_distribution: Dict[str, int] = Field(default_factory=dict)
    active_schemes_count: int = 0
    active_schemes_total_quota_slots: int = 0
    active_schemes_quota_utilization_rate: float = 0.0
    total_verified_pool: int = 0
    active_deficiencies_count: int = 0
    resolved_deficiencies_count: int = 0
    total_evaluation_batches: int = 0
    finalized_evaluation_batches: int = 0
    total_selected: int = 0
    total_waitlisted: int = 0
    total_rejected: int = 0
    total_officers: int = 0
    total_committee_members: int = 0


# ---------------------------------------------------------------------------
# 2. Cumulative Milestone Funnel
# ---------------------------------------------------------------------------
class ApplicationMilestone(BaseModel):
    milestone_key: str
    milestone_label: str
    count: int
    conversion_from_start_rate: float
    conversion_from_previous_rate: float


class ApplicationFunnelResponse(BaseModel):
    total_initiated: int
    milestones: List[ApplicationMilestone]


# ---------------------------------------------------------------------------
# 3. Intake & Verification Velocity Trends
# ---------------------------------------------------------------------------
class TimeSeriesPoint(BaseModel):
    date: str  # YYYY-MM-DD
    submissions_count: int = 0
    verifications_count: int = 0
    selections_count: int = 0


class VelocityTrendsResponse(BaseModel):
    start_date: str
    end_date: str
    granularity: str = "day"
    data_points: List[TimeSeriesPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 4. Scheme & Version-Bound Performance
# ---------------------------------------------------------------------------
class SchemePerformanceSummary(BaseModel):
    scheme_id: uuid.UUID
    scheme_code: str
    scheme_name: str
    scheme_version_id: Optional[uuid.UUID] = None
    scheme_version: Optional[str] = None
    is_active: bool = True
    quota_slots: int = 0
    total_applications: int = 0
    verified_count: int = 0
    selected_count: int = 0
    waitlisted_count: int = 0
    rejected_count: int = 0
    quota_exhaustion_rate: float = 0.0


class SchemeBreakdownsResponse(BaseModel):
    schemes: List[SchemePerformanceSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 5. Officer Throughput & Workload
# ---------------------------------------------------------------------------
class OfficerThroughputItem(BaseModel):
    officer_id: uuid.UUID
    officer_name: str
    assigned_applications_count: int = 0
    verified_count: int = 0
    deficiencies_flagged_count: int = 0
    human_overrides_count: int = 0
    avg_verification_duration_hours: float = 0.0


class OfficerThroughputResponse(BaseModel):
    officers: List[OfficerThroughputItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. Verification Integrity & AI-Human Agreement
# ---------------------------------------------------------------------------
class VerificationDecisionMetrics(BaseModel):
    total_documents_evaluated: int = 0
    ai_human_agreements: int = 0
    human_overrides: int = 0
    ai_human_agreement_rate: float = 0.0
    human_override_rate: float = 0.0
    override_breakdown: Dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 7. Searchable Audit Logs
# ---------------------------------------------------------------------------
class AuditLogReportItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogReportResponse(BaseModel):
    total_count: int
    page: int
    limit: int
    logs: List[AuditLogReportItem] = Field(default_factory=list)
