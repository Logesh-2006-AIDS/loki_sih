import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import check_committee_scheme_scope, get_db, require_roles
from app.core.enums import UserRole
from app.core.exceptions import ForbiddenException
from app.models.officer_assignment import OfficerAssignment
from app.models.user import User
from app.schemas.analytics import (
    ApplicationFunnelResponse,
    AuditLogReportResponse,
    OfficerThroughputResponse,
    SchemeBreakdownsResponse,
    SystemOverviewMetrics,
    VelocityTrendsResponse,
    VerificationDecisionMetrics,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter()


def _verify_staff_scheme_access(
    db: Session, current_user: User, scheme_id: Optional[uuid.UUID]
) -> None:
    """
    Enforces scoped access for staff (OFFICER, COMMITTEE).
    ADMIN has global unrestricted access.
    Staff members MUST specify a scheme_id to which they are actively assigned.
    """
    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)
    if user_role == UserRole.ADMIN:
        return

    if not scheme_id:
        raise ForbiddenException(
            "Staff role requires specifying a scoped 'scheme_id' parameter."
        )

    if user_role == UserRole.OFFICER:
        assignments = (
            db.query(OfficerAssignment)
            .filter(
                OfficerAssignment.officer_id == current_user.id,
                OfficerAssignment.is_active == True,
            )
            .all()
        )
        if not assignments:
            raise ForbiddenException("Officer has no active assignments.")
        for a in assignments:
            if a.scheme_id is None or a.scheme_id == scheme_id:
                return
        raise ForbiddenException("Officer is not assigned to this scheme.")

    if user_role == UserRole.COMMITTEE:
        if not check_committee_scheme_scope(db, current_user.id, scheme_id):
            raise ForbiddenException("Committee member is not assigned to this scheme.")
        return

    raise ForbiddenException("Access denied.")


# -----------------------------------------------------------------------------
# 1. System Overview (Admin Only)
# -----------------------------------------------------------------------------
@router.get(
    "/overview",
    response_model=SystemOverviewMetrics,
    summary="Get platform-wide operational KPIs and current-state distribution",
)
def get_overview(
    scheme_id: Optional[uuid.UUID] = Query(None, description="Optional scheme filter"),
    start_date: Optional[datetime] = Query(None, description="Filter intake from start date"),
    end_date: Optional[datetime] = Query(None, description="Filter intake up to end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> SystemOverviewMetrics:
    service = AnalyticsService(db)
    return service.get_system_overview(
        scheme_id=scheme_id, start_date=start_date, end_date=end_date
    )


# -----------------------------------------------------------------------------
# 2. Application Funnel (Scoped Staff & Admin)
# -----------------------------------------------------------------------------
@router.get(
    "/funnel",
    response_model=ApplicationFunnelResponse,
    summary="Get cumulative lifecycle milestone conversion funnel",
)
def get_funnel(
    scheme_id: Optional[uuid.UUID] = Query(None, description="Optional scheme filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.OFFICER, UserRole.COMMITTEE])
    ),
) -> ApplicationFunnelResponse:
    _verify_staff_scheme_access(db, current_user, scheme_id)
    service = AnalyticsService(db)
    return service.get_application_funnel(scheme_id=scheme_id)


# -----------------------------------------------------------------------------
# 3. Velocity Trends (Scoped Staff & Admin)
# -----------------------------------------------------------------------------
@router.get(
    "/trends",
    response_model=VelocityTrendsResponse,
    summary="Get daily intake, scrutiny, and selection velocity timeline",
)
def get_trends(
    scheme_id: Optional[uuid.UUID] = Query(None, description="Optional scheme filter"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    granularity: str = Query("day", description="Granularity: day, week, month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.OFFICER, UserRole.COMMITTEE])
    ),
) -> VelocityTrendsResponse:
    _verify_staff_scheme_access(db, current_user, scheme_id)
    service = AnalyticsService(db)
    return service.get_velocity_trends(
        scheme_id=scheme_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )


# -----------------------------------------------------------------------------
# 4. Scheme & Version Performance (Scoped Staff & Admin)
# -----------------------------------------------------------------------------
@router.get(
    "/schemes",
    response_model=SchemeBreakdownsResponse,
    summary="Get scheme and version-bound quota performance summaries",
)
def get_schemes(
    scheme_id: Optional[uuid.UUID] = Query(None, description="Optional scheme filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles([UserRole.ADMIN, UserRole.OFFICER, UserRole.COMMITTEE])
    ),
) -> SchemeBreakdownsResponse:
    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    service = AnalyticsService(db)
    all_schemes_resp = service.get_scheme_breakdowns(scheme_id=scheme_id)

    if user_role == UserRole.ADMIN:
        return all_schemes_resp

    # Filter schemes to only those the staff user is authorized for
    authorized_summaries = []
    for s in all_schemes_resp.schemes:
        try:
            _verify_staff_scheme_access(db, current_user, s.scheme_id)
            authorized_summaries.append(s)
        except ForbiddenException:
            continue

    return SchemeBreakdownsResponse(schemes=authorized_summaries)


# -----------------------------------------------------------------------------
# 5. Staff Throughput & Workload (Admin Only)
# -----------------------------------------------------------------------------
@router.get(
    "/officers",
    response_model=OfficerThroughputResponse,
    summary="Get officer verification throughput and workload (Admin only, no applicant PII)",
)
def get_officer_throughput(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> OfficerThroughputResponse:
    service = AnalyticsService(db)
    return service.get_officer_throughput(start_date=start_date, end_date=end_date)


# -----------------------------------------------------------------------------
# 6. Verification Decisions & AI-Human Agreement (Admin Only)
# -----------------------------------------------------------------------------
@router.get(
    "/decisions",
    response_model=VerificationDecisionMetrics,
    summary="Get AI-human agreement, override rates, and breakdown (Admin only)",
)
def get_decision_metrics(
    scheme_id: Optional[uuid.UUID] = Query(None, description="Optional scheme filter"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> VerificationDecisionMetrics:
    service = AnalyticsService(db)
    return service.get_decision_metrics(
        scheme_id=scheme_id, start_date=start_date, end_date=end_date
    )


# -----------------------------------------------------------------------------
# 7. Searchable System Audit Logs (Admin Only)
# -----------------------------------------------------------------------------
@router.get(
    "/audit-logs",
    response_model=AuditLogReportResponse,
    summary="Search and filter platform audit logs (Admin only, scrubbed credentials)",
)
def get_audit_logs(
    action: Optional[str] = Query(None, description="Action filter"),
    entity_type: Optional[str] = Query(None, description="Entity type filter"),
    actor_id: Optional[uuid.UUID] = Query(None, description="Actor user ID"),
    application_id: Optional[uuid.UUID] = Query(None, description="Application ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> AuditLogReportResponse:
    service = AnalyticsService(db)
    return service.get_audit_logs_report(
        action=action,
        entity_type=entity_type,
        actor_id=actor_id,
        application_id=application_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        limit=limit,
    )


# -----------------------------------------------------------------------------
# 8. Streaming CSV Exports (Admin Only, Server Cap 10,000)
# -----------------------------------------------------------------------------
@router.get(
    "/export/applications",
    summary="Export non-sensitive application administrative data as streaming CSV (Admin only, 10k cap)",
)
def export_applications(
    scheme_id: Optional[uuid.UUID] = Query(None, description="Scheme filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: Optional[int] = Query(10000, ge=1, description="Max rows (clamped to 10,000)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> StreamingResponse:
    service = AnalyticsService(db)
    generator = service.export_applications_stream(
        scheme_id=scheme_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"mta_applications_export_{ts}.csv"
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get(
    "/export/audit-logs",
    summary="Export platform audit logs as streaming CSV (Admin only, 10k cap)",
)
def export_audit_logs(
    action: Optional[str] = Query(None, description="Action filter"),
    entity_type: Optional[str] = Query(None, description="Entity type filter"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    limit: Optional[int] = Query(10000, ge=1, description="Max rows (clamped to 10,000)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> StreamingResponse:
    service = AnalyticsService(db)
    generator = service.export_audit_logs_stream(
        action=action,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"mta_audit_logs_export_{ts}.csv"
    return StreamingResponse(
        generator,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )
