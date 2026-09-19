import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role, get_current_user
from app.core.enums import UserRole
from app.core.exceptions import EntityNotFoundException, ForbiddenException
from app.models.user import User
from app.schemas.user import UserResponse
from app.repositories.user_repo import UserRepository

router = APIRouter()


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List all users (Admin only)",
)
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role(UserRole.ADMIN)),
):
    repo = UserRepository(db)
    if role:
        users = repo.get_by_role(role)
    else:
        users = repo.get_all(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user details by ID (Self or Admin)",
)
def get_user_by_id(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_role = current_user.role
    if isinstance(user_role, str):
        user_role = UserRole(user_role)

    if current_user.id != user_id and user_role != UserRole.ADMIN:
        raise ForbiddenException("Cannot view profile of another user")

    repo = UserRepository(db)
    user = repo.get_by_id(user_id)
    if not user:
        raise EntityNotFoundException("User", user_id)
    return UserResponse.model_validate(user)
