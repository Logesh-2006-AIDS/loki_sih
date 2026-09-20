import uuid
from typing import Generator, Optional, Sequence
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.enums import UserRole
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    if not token:
        raise UnauthorizedException("Authentication token missing")

    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedException("Invalid or expired authentication token")

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Token payload missing subject")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise UnauthorizedException("Invalid user ID format in token")

    user = db.get(User, user_uuid)
    if not user:
        raise UnauthorizedException("User account not found")

    if not user.is_active:
        raise ForbiddenException("User account is inactive")

    return user


def require_role(role: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role
        if isinstance(user_role, str):
            user_role = UserRole(user_role)
        if user_role != role:
            raise ForbiddenException(f"Operation requires {role.value} role")
        return current_user

    return role_checker


def require_roles(roles: Sequence[UserRole]):
    def roles_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role
        if isinstance(user_role, str):
            user_role = UserRole(user_role)
        if user_role not in roles:
            allowed_roles = [r.value for r in roles]
            raise ForbiddenException(
                f"Operation requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return roles_checker


def check_officer_application_scope(
    db: Session,
    officer_id: uuid.UUID,
    app_scheme_id: uuid.UUID,
    app_form_data: dict,
) -> bool:
    """
    Validates whether an officer has jurisdiction over an application.
    Security Invariant:
      - ADMIN users have system-wide access.
      - Officers with NO active assignments are DENIED access (no implicit unrestricted access).
      - Explicit global scope is represented by an assignment with both scheme_id=None and state=None.
      - Scoped assignments require matching scheme and/or state.
    """
    user = db.get(User, officer_id)
    if user:
        role = user.role
        if isinstance(role, str):
            role = UserRole(role)
        if role == UserRole.ADMIN:
            return True

    from app.models.officer_assignment import OfficerAssignment
    assignments = (
        db.query(OfficerAssignment)
        .filter(
            OfficerAssignment.officer_id == officer_id,
            OfficerAssignment.is_active == True,
        )
        .all()
    )
    if not assignments:
        return False

    for assign in assignments:
        # Explicit global scope assignment: both scheme_id and state are None
        if assign.scheme_id is None and assign.state is None:
            return True

        scheme_match = (assign.scheme_id is None) or (assign.scheme_id == app_scheme_id)
        state_match = True
        if assign.state:
            app_state = (
                app_form_data.get("personal", {}).get("state")
                or app_form_data.get("state")
            )
            state_match = (app_state == assign.state)
        if scheme_match and state_match:
            return True
    return False

