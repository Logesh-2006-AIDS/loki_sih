import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from app.models.staff_request import StaffRegistrationRequest
from app.core.enums import StaffRequestStatus, UserRole
from app.repositories.base_repo import BaseRepository


class StaffRequestRepository(BaseRepository[StaffRegistrationRequest]):
    def __init__(self, db: Session):
        super().__init__(StaffRegistrationRequest, db)

    def get_by_id(self, request_id: uuid.UUID) -> Optional[StaffRegistrationRequest]:
        query = (
            select(StaffRegistrationRequest)
            .options(
                joinedload(StaffRegistrationRequest.user),
                joinedload(StaffRegistrationRequest.reviewer),
            )
            .where(StaffRegistrationRequest.id == request_id)
        )
        return self.db.execute(query).scalar_one_or_none()

    def get_by_user_id(self, user_id: uuid.UUID) -> Optional[StaffRegistrationRequest]:
        query = (
            select(StaffRegistrationRequest)
            .options(
                joinedload(StaffRegistrationRequest.user),
                joinedload(StaffRegistrationRequest.reviewer),
            )
            .where(StaffRegistrationRequest.user_id == user_id)
            .order_by(StaffRegistrationRequest.submitted_at.desc())
        )
        return self.db.execute(query).scalars().first()

    def list_requests(
        self,
        status: Optional[StaffRequestStatus] = None,
        role: Optional[UserRole] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[StaffRegistrationRequest], int]:
        query = select(StaffRegistrationRequest).options(
            joinedload(StaffRegistrationRequest.user),
            joinedload(StaffRegistrationRequest.reviewer),
        )

        if status:
            query = query.where(StaffRegistrationRequest.status == status)
        if role:
            query = query.where(StaffRegistrationRequest.requested_role == role)

        # Count total matching query before pagination
        count_query = select(func.count(StaffRegistrationRequest.id))
        if status:
            count_query = count_query.where(StaffRegistrationRequest.status == status)
        if role:
            count_query = count_query.where(StaffRegistrationRequest.requested_role == role)

        total = self.db.execute(count_query).scalar_one()

        query = (
            query.order_by(StaffRegistrationRequest.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        results = list(self.db.execute(query).scalars().all())
        return results, total

    def count_by_status(self, status: StaffRequestStatus) -> int:
        query = select(func.count(StaffRegistrationRequest.id)).where(
            StaffRegistrationRequest.status == status
        )
        return self.db.execute(query).scalar_one()
