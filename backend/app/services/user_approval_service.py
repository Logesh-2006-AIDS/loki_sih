import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.enums import StaffRequestStatus, UserAccountStatus, UserRole
import re
from app.core.exceptions import EntityNotFoundException, AppException, ValidationException
from app.models.user import User
from app.models.staff_request import StaffRegistrationRequest
from app.repositories.staff_request_repo import StaffRequestRepository
from app.repositories.user_repo import UserRepository
from app.repositories.audit_repo import AuditRepository
from app.schemas.staff_request import StaffRequestResponse, StaffRequestStatsResponse


class UserApprovalService:
    def __init__(self, db: Session):
        self.db = db
        self.staff_repo = StaffRequestRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    def _map_to_response(self, req: StaffRegistrationRequest) -> StaffRequestResponse:
        user_name = req.user.full_name if req.user else "Unknown"
        user_email = req.user.email if req.user else "Unknown"
        user_phone = req.user.phone if req.user else None
        reviewer_name = req.reviewer.full_name if req.reviewer else None

        return StaffRequestResponse(
            id=req.id,
            user_id=req.user_id,
            user_name=user_name,
            user_email=user_email,
            user_phone=user_phone,
            requested_role=req.requested_role,
            employee_id=req.employee_id,
            department=req.department,
            designation=req.designation,
            jurisdiction=req.jurisdiction,
            status=req.status,
            rejection_reason=req.rejection_reason,
            submitted_at=req.submitted_at,
            reviewed_at=req.reviewed_at,
            reviewed_by=req.reviewed_by,
            reviewer_name=reviewer_name,
        )

    def list_requests(
        self,
        status: Optional[StaffRequestStatus] = None,
        role: Optional[UserRole] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StaffRequestResponse], int]:
        requests, total = self.staff_repo.list_requests(
            status=status, role=role, search=search, skip=skip, limit=limit
        )
        return [self._map_to_response(r) for r in requests], total

    def get_request(self, request_id: uuid.UUID) -> StaffRequestResponse:
        req = self.staff_repo.get_by_id(request_id)
        if not req:
            raise EntityNotFoundException("StaffRegistrationRequest", request_id)
        return self._map_to_response(req)

    def get_stats(self) -> StaffRequestStatsResponse:
        pending_count = self.db.execute(
            select(func.count(StaffRegistrationRequest.id)).where(
                StaffRegistrationRequest.status == StaffRequestStatus.PENDING
            )
        ).scalar_one()

        rejected_count = self.db.execute(
            select(func.count(StaffRegistrationRequest.id)).where(
                StaffRegistrationRequest.status == StaffRequestStatus.REJECTED
            )
        ).scalar_one()

        total_requests = self.db.execute(
            select(func.count(StaffRegistrationRequest.id))
        ).scalar_one()

        active_officers = self.db.execute(
            select(func.count(User.id)).where(
                User.role == UserRole.OFFICER,
                User.is_active == True,
                User.account_status == UserAccountStatus.ACTIVE,
            )
        ).scalar_one()

        active_committee = self.db.execute(
            select(func.count(User.id)).where(
                User.role == UserRole.COMMITTEE,
                User.is_active == True,
                User.account_status == UserAccountStatus.ACTIVE,
            )
        ).scalar_one()

        return StaffRequestStatsResponse(
            pending_count=pending_count,
            active_officers=active_officers,
            active_committee=active_committee,
            rejected_count=rejected_count,
            total_requests=total_requests,
        )

    def approve_request(
        self, request_id: uuid.UUID, admin_id: uuid.UUID
    ) -> StaffRequestResponse:
        req = self.staff_repo.get_by_id(request_id)
        if not req:
            raise EntityNotFoundException("StaffRegistrationRequest", request_id)

        user = self.user_repo.get_by_id(req.user_id)
        if not user:
            raise EntityNotFoundException("User", req.user_id)

        now = datetime.now(timezone.utc)
        req.status = StaffRequestStatus.APPROVED
        req.reviewed_at = now
        req.reviewed_by = admin_id
        req.rejection_reason = None

        # Activate the user account
        user.account_status = UserAccountStatus.ACTIVE
        user.is_active = True
        user.role = req.requested_role

        self.db.commit()
        self.db.refresh(req)
        self.db.refresh(user)

        self.audit_repo.log_event(
            entity_type="USER",
            entity_id=str(user.id),
            actor_id=admin_id,
            action="STAFF_APPROVED",
            details={
                "request_id": str(req.id),
                "approved_role": str(req.requested_role),
                "email": user.email,
                "employee_id": req.employee_id,
            },
        )

        return self._map_to_response(req)

    def reject_request(
        self, request_id: uuid.UUID, admin_id: uuid.UUID, reason: Optional[str]
    ) -> StaffRequestResponse:
        req = self.staff_repo.get_by_id(request_id)
        if not req:
            raise EntityNotFoundException("StaffRegistrationRequest", request_id)

        user = self.user_repo.get_by_id(req.user_id)
        if not user:
            raise EntityNotFoundException("User", req.user_id)

        if not reason or not reason.strip():
            raise ValidationException("Please provide a reason for rejecting this registration.")
        clean_reason = reason.strip()
        if len(clean_reason) < 10:
            raise ValidationException("Rejection reason must be at least 10 characters.")
        if len(clean_reason) > 1000:
            raise ValidationException("Rejection reason cannot exceed 1000 characters.")
        if re.search(r"<[^>]+>", clean_reason) or "<script" in clean_reason.lower():
            raise ValidationException("Rejection reason cannot contain HTML or script content.")

        now = datetime.now(timezone.utc)

        req.status = StaffRequestStatus.REJECTED
        req.reviewed_at = now
        req.reviewed_by = admin_id
        req.rejection_reason = clean_reason

        # Reject the user account
        user.account_status = UserAccountStatus.REJECTED
        user.is_active = False

        self.db.commit()
        self.db.refresh(req)
        self.db.refresh(user)

        self.audit_repo.log_event(
            entity_type="USER",
            entity_id=str(user.id),
            actor_id=admin_id,
            action="STAFF_REJECTED",
            details={
                "request_id": str(req.id),
                "rejected_role": str(req.requested_role),
                "email": user.email,
                "rejection_reason": clean_reason,
            },
        )

        return self._map_to_response(req)
