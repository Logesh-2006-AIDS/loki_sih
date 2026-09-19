import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.scheme import (
    SchemeCreate,
    SchemeUpdate,
    SchemeResponse,
    SchemeDetailResponse,
    SchemeVersionCreate,
    SchemeVersionUpdate,
    SchemeVersionResponse,
    EligibilityCheckRequest,
    EligibilityCheckResponse,
)
from app.services.scheme_service import SchemeService

router = APIRouter()


# ---------------------------------------------------------------------------
# Public / Applicant Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=List[SchemeResponse],
    summary="List all active scholarship and fellowship schemes",
)
def list_schemes(db: Session = Depends(get_db)):
    """
    Returns all active schemes with active version details,
    forms, rules, and demo disclaimers.
    """
    service = SchemeService(db)
    return service.list_active_schemes()


@router.get(
    "/{scheme_id}",
    response_model=SchemeDetailResponse,
    summary="Get scheme details by ID including active version and versions count",
)
def get_scheme(scheme_id: uuid.UUID, db: Session = Depends(get_db)):
    service = SchemeService(db)
    return service.get_scheme(scheme_id)


@router.get(
    "/{scheme_id}/versions",
    response_model=List[SchemeVersionResponse],
    summary="List all historical and active versions of a scheme",
)
def list_scheme_versions(scheme_id: uuid.UUID, db: Session = Depends(get_db)):
    service = SchemeService(db)
    return service.get_scheme_versions(scheme_id)


@router.get(
    "/{scheme_id}/versions/{version_id}",
    response_model=SchemeVersionResponse,
    summary="Get specific scheme version details",
)
def get_scheme_version(
    scheme_id: uuid.UUID, version_id: uuid.UUID, db: Session = Depends(get_db)
):
    service = SchemeService(db)
    return service.get_scheme_version(version_id)


@router.post(
    "/{scheme_id}/check-eligibility",
    response_model=EligibilityCheckResponse,
    summary="Evaluate self-eligibility against active or specified scheme version",
)
def check_self_eligibility(
    scheme_id: uuid.UUID,
    data: EligibilityCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluates applicant inputs deterministically against configured rules.
    Indicative only — does not create or alter any application records.
    """
    service = SchemeService(db)
    return service.check_eligibility(
        scheme_id=scheme_id,
        answers=data.answers,
        scheme_version_id=data.scheme_version_id,
    )


@router.post(
    "/versions/{version_id}/check-eligibility",
    response_model=EligibilityCheckResponse,
    summary="Evaluate self-eligibility directly against a specific scheme version",
)
def check_version_eligibility(
    version_id: uuid.UUID,
    data: EligibilityCheckRequest,
    db: Session = Depends(get_db),
):
    service = SchemeService(db)
    v = service.get_scheme_version(version_id)
    return service.check_eligibility(
        scheme_id=v.scheme_id,
        answers=data.answers,
        scheme_version_id=version_id,
    )


# ---------------------------------------------------------------------------
# Admin Endpoints (Requires UserRole.ADMIN)
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=SchemeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new scheme (Admin only)",
)
def create_scheme(
    data: SchemeCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = SchemeService(db)
    return service.create_scheme(data, actor_id=admin.id)


@router.put(
    "/{scheme_id}",
    response_model=SchemeResponse,
    summary="Update scheme catalog metadata (Admin only)",
)
def update_scheme(
    scheme_id: uuid.UUID,
    data: SchemeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = SchemeService(db)
    return service.update_scheme(scheme_id, data, actor_id=admin.id)


@router.post(
    "/{scheme_id}/versions",
    response_model=SchemeVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new version for a scheme (Admin only)",
)
def create_scheme_version(
    scheme_id: uuid.UUID,
    data: SchemeVersionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = SchemeService(db)
    return service.create_scheme_version(scheme_id, data, actor_id=admin.id)


@router.put(
    "/versions/{version_id}",
    response_model=SchemeVersionResponse,
    summary="Update an unlocked scheme version (Admin only)",
)
def update_scheme_version(
    version_id: uuid.UUID,
    data: SchemeVersionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Updates rules, forms, documents, or weights on an unlocked version.
    Fails with 400 if the version is locked.
    """
    service = SchemeService(db)
    return service.update_scheme_version(version_id, data, actor_id=admin.id)


@router.post(
    "/versions/{version_id}/lock",
    response_model=SchemeVersionResponse,
    summary="Permanently lock a scheme version (Admin only)",
)
def lock_scheme_version(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = SchemeService(db)
    return service.lock_scheme_version(version_id, actor_id=admin.id)


@router.post(
    "/versions/{version_id}/activate",
    response_model=SchemeVersionResponse,
    summary="Activate scheme version with single active version transactional enforcement (Admin only)",
)
def activate_scheme_version(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = SchemeService(db)
    return service.activate_scheme_version(version_id, actor_id=admin.id)
