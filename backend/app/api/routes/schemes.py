import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.core.enums import UserRole
from app.models.user import User
from app.schemas.scheme import SchemeCreate, SchemeUpdate, SchemeResponse
from app.services.scheme_service import SchemeService

router = APIRouter()


@router.get(
    "/",
    response_model=List[SchemeResponse],
    summary="List all active scholarship and fellowship schemes",
)
def list_schemes(db: Session = Depends(get_db)):
    service = SchemeService(db)
    return service.list_active_schemes()


@router.get(
    "/{scheme_id}",
    response_model=SchemeResponse,
    summary="Get scheme details by ID",
)
def get_scheme(scheme_id: uuid.UUID, db: Session = Depends(get_db)):
    service = SchemeService(db)
    return service.get_scheme(scheme_id)


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
    summary="Update scheme details (Admin only)",
)
def update_scheme(
    scheme_id: uuid.UUID,
    data: SchemeUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    service = SchemeService(db)
    return service.update_scheme(scheme_id, data, actor_id=admin.id)
