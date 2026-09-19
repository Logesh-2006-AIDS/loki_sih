import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import (
    get_db,
    get_current_user,
    require_roles,
    check_officer_application_scope,
)
from app.core.enums import UserRole, ApplicationStatus
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
)
from app.services.application_service import ApplicationService

router = APIRouter()


@router.get(
    "/",
    response_model=List[ApplicationResponse],
    summary="List applications (filtered for applicants, full queue for officers/committee/admins)",
)
def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT:
        return service.list_by_applicant(current_user.id)
    else:
        return service.list_all(skip=skip, limit=limit)


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new draft application",
)
def create_draft_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    return service.create_draft(current_user.id, data)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get application details by ID",
)
def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot access application belonging to another user")

    if user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, current_user.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    return app


@router.put(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Update an application draft",
)
def update_application_draft(
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT:
        if app.applicant_id != current_user.id:
            raise ForbiddenException("Cannot modify application belonging to another user")
        if data.status is not None and data.status != app.status:
            raise ForbiddenException("Applicants cannot directly modify application workflow status")
        if app.status != ApplicationStatus.DRAFT:
            raise ForbiddenException("Cannot modify submitted application")
    elif user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, current_user.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    return service.update_application(
        application_id=application_id,
        data=data,
        actor_id=current_user.id,
    )


@router.post(
    "/{application_id}/submit",
    response_model=ApplicationResponse,
    summary="Submit a draft application",
)
def submit_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.APPLICANT and app.applicant_id != current_user.id:
        raise ForbiddenException("Cannot submit application belonging to another user")

    return service.submit_application(application_id, current_user.id)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    summary="Update application status (Officer, Committee, or Admin)",
)
def update_application_status(
    application_id: uuid.UUID,
    update_data: ApplicationUpdate,
    db: Session = Depends(get_db),
    staff: User = Depends(
        require_roles([UserRole.OFFICER, UserRole.COMMITTEE, UserRole.ADMIN])
    ),
):
    service = ApplicationService(db)
    app = service.get_application(application_id)

    user_role = staff.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if user_role == UserRole.OFFICER:
        if not check_officer_application_scope(db, staff.id, app.scheme_id, app.form_data or {}):
            raise ForbiddenException("Officer does not have jurisdiction over this application")

    return service.update_application(
        application_id=application_id,
        data=update_data,
        actor_id=staff.id,
    )
