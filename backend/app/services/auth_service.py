from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import AppException, UnauthorizedException, DuplicateEntityException
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, Token
from app.repositories.user_repo import UserRepository
from app.repositories.audit_repo import AuditRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    def register(self, user_in: UserCreate) -> UserResponse:
        existing = self.user_repo.get_by_email(user_in.email)
        if existing:
            raise DuplicateEntityException(f"User with email '{user_in.email}' already exists")

        user = User(
            full_name=user_in.full_name,
            email=user_in.email.lower().strip(),
            phone=user_in.phone,
            password_hash=get_password_hash(user_in.password),
            role=user_in.role,
            is_active=True,
        )
        created_user = self.user_repo.create(user)

        # Audit registration
        self.audit_repo.log_event(
            entity_type="USER",
            entity_id=str(created_user.id),
            actor_id=created_user.id,
            action="USER_REGISTERED",
            details={"email": created_user.email, "role": str(created_user.role)},
        )

        return UserResponse.model_validate(created_user)

    def authenticate(self, login_data: LoginRequest) -> Token:
        user = self.user_repo.get_by_email(login_data.email)
        if not user:
            raise UnauthorizedException("Invalid email or password")

        if not verify_password(login_data.password, user.password_hash):
            raise UnauthorizedException("Invalid email or password")

        if not user.is_active:
            raise AppException("Account is inactive. Please contact administration.", status_code=403)

        access_token = create_access_token(
            subject=str(user.id),
            role=str(user.role.value if hasattr(user.role, "value") else user.role),
        )

        # Audit login event
        self.audit_repo.log_event(
            entity_type="USER",
            entity_id=str(user.id),
            actor_id=user.id,
            action="USER_LOGIN_SUCCESS",
            details={"email": user.email, "role": str(user.role)},
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
