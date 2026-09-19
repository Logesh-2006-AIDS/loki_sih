import uuid
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_roles
from app.core.enums import UserRole
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.models.user import User
from app.models.application import Application
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get(
    "/entity/{entity_type}/{entity_id}",
    response_model=List[AuditLogResponse],
    summary="Get traceable audit trail by entity type and ID (Staff only)",
)
def get_entity_audit_logs(
    entity_type: str,
    entity_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    staff: User = Depends(
        require_roles([UserRole.OFFICER, UserRole.COMMITTEE, UserRole.ADMIN])
    ),
):
    service = AuditService(db)
    return service.get_logs_for_entity(
        entity_type=entity_type.upper().strip(),
        entity_id=entity_id.strip(),
        skip=skip,
        limit=limit,
    )


@router.get(
    "/application/{application_id}",
    response_model=List[AuditLogResponse],
    summary="Get audit logs for a specific application",
)
def get_application_audit_logs(
    application_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.get(Application, application_id)
    if not app:
        raise EntityNotFoundException("Application", application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot access audit logs for another applicant's application")

    service = AuditService(db)
    return service.get_logs_for_application(
        application_id=application_id, skip=skip, limit=limit
    )
