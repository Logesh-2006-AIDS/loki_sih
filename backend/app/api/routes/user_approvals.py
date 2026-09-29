import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.core.enums import UserRole, StaffRequestStatus
from app.models.user import User
from app.schemas.staff_request import (
    StaffRequestResponse,
    StaffRequestStatsResponse,
    StaffRequestRejectAction,
)
from app.services.user_approval_service import UserApprovalService

router = APIRouter()


@router.get(
    "/stats",
    response_model=StaffRequestStatsResponse,
    summary="Get overall counts and metrics for staff account approvals (Admin only)",
)
def get_approval_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = UserApprovalService(db)
    return service.get_stats()


@router.get("", response_model=List[StaffRequestResponse], include_in_schema=False)
@router.get(
    "/",
    response_model=List[StaffRequestResponse],
    summary="List all staff registration requests with filtering (Admin only)",
)
def list_staff_requests(
    status: Optional[StaffRequestStatus] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    role: Optional[UserRole] = Query(None, description="Filter by requested role (OFFICER, COMMITTEE)"),
    search: Optional[str] = Query(None, description="Search by name, email, or department"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = UserApprovalService(db)
    requests, _ = service.list_requests(
        status=status, role=role, search=search, skip=skip, limit=limit
    )
    return requests


@router.get(
    "/{request_id}",
    response_model=StaffRequestResponse,
    summary="Get detailed information for a single staff registration request (Admin only)",
)
def get_staff_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = UserApprovalService(db)
    return service.get_request(request_id)


@router.post(
    "/{request_id}/approve",
    response_model=StaffRequestResponse,
    summary="Approve a pending staff registration request and activate user (Admin only)",
)
def approve_staff_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = UserApprovalService(db)
    return service.approve_request(request_id=request_id, admin_id=admin.id)


@router.post(
    "/{request_id}/reject",
    response_model=StaffRequestResponse,
    summary="Reject a staff registration request (Admin only)",
)
def reject_staff_request(
    request_id: uuid.UUID,
    action: StaffRequestRejectAction,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = UserApprovalService(db)
    return service.reject_request(
        request_id=request_id, admin_id=admin.id, reason=action.reason
    )
