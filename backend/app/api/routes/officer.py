import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.officer import (
    OfficerQueueResponse,
    OfficerStatsResponse,
    OfficerApplicationScrutinyResponse,
    OfficerDocumentScrutinyItem,
    OfficerDocumentDecisionRequest,
    OfficerApplicationDecisionRequest,
)
from app.schemas.application import ApplicationResponse
from app.services.officer_service import OfficerService

router = APIRouter()


@router.get(
    "/queue",
    response_model=OfficerQueueResponse,
    summary="Get assigned application queue for desk officer (PII-minimized)",
)
def get_officer_queue(
    status_filter: Optional[str] = Query(None, description="Filter by status (e.g. UNDER_MANUAL_REVIEW, VERIFIED, ALL)"),
    scheme_id: Optional[uuid.UUID] = Query(None, description="Filter by scheme UUID"),
    state: Optional[str] = Query(None, description="Filter by applicant domicile state"),
    search: Optional[str] = Query(None, description="Search by reference ID or applicant name"),
    has_ai_flags: Optional[bool] = Query(None, description="Filter applications with AI flags"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    officer: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    service = OfficerService(db)
    return service.get_queue(
        officer=officer,
        status_filter=status_filter,
        scheme_id=scheme_id,
        state=state,
        search=search,
        has_ai_flags=has_ai_flags,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/stats",
    response_model=OfficerStatsResponse,
    summary="Get officer dashboard workload counters within jurisdiction",
)
def get_officer_stats(
    db: Session = Depends(get_db),
    officer: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    service = OfficerService(db)
    return service.get_stats(officer=officer)


@router.get(
    "/applications/{application_id}/scrutiny",
    response_model=OfficerApplicationScrutinyResponse,
    summary="Get comprehensive scrutiny package for an application",
)
def get_application_scrutiny(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    officer: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    service = OfficerService(db)
    return service.get_scrutiny_details(officer=officer, application_id=application_id)


@router.post(
    "/documents/{document_id}/decision",
    response_model=OfficerDocumentScrutinyItem,
    summary="Record durable human scrutiny decision on an individual document",
)
def record_document_decision(
    document_id: uuid.UUID,
    decision_data: OfficerDocumentDecisionRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    service = OfficerService(db)
    return service.record_document_decision(
        officer=officer,
        document_id=document_id,
        data=decision_data,
    )


@router.post(
    "/applications/{application_id}/decision",
    response_model=ApplicationResponse,
    summary="Submit final human scrutiny determination for the application",
)
def record_application_decision(
    application_id: uuid.UUID,
    decision_data: OfficerApplicationDecisionRequest,
    db: Session = Depends(get_db),
    officer: User = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    service = OfficerService(db)
    updated_app = service.record_application_decision(
        officer=officer,
        application_id=application_id,
        data=decision_data,
    )
    return ApplicationResponse.model_validate(updated_app)
