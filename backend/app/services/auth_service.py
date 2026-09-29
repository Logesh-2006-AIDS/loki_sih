from sqlalchemy.orm import Session
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.enums import UserRole, UserAccountStatus, StaffRequestStatus
from app.core.exceptions import AppException, UnauthorizedException, DuplicateEntityException
from app.models.user import User
from app.models.staff_request import StaffRegistrationRequest
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, Token
from app.schemas.staff_request import ApplicantRegisterRequest, StaffRegisterRequest
from app.repositories.user_repo import UserRepository
from app.repositories.staff_request_repo import StaffRequestRepository
from app.repositories.audit_repo import AuditRepository


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.staff_repo = StaffRequestRepository(db)
        self.audit_repo = AuditRepository(db)

    def register(self, user_in: UserCreate) -> UserResponse:
        # Public applicant registration endpoint:
        # Explicitly reject attempts to register as ADMIN
        if user_in.role == UserRole.ADMIN:
            raise AppException("Admin self-registration is prohibited.", status_code=400)

        clean_email = user_in.email.lower().strip()
        existing = self.user_repo.get_by_email(clean_email)
        if existing:
            raise DuplicateEntityException("An account with this email address already exists.")

        # Never trust the role sent by a public applicant registration request.
        # Applicant registration always creates APPLICANT with ACTIVE status.
        user = User(
            full_name=user_in.full_name.strip(),
            email=clean_email,
            phone=user_in.phone.strip() if user_in.phone else None,
            password_hash=get_password_hash(user_in.password),
            role=UserRole.APPLICANT,
            account_status=UserAccountStatus.ACTIVE,
            is_active=True,
        )
        created_user = self.user_repo.create(user)

        self.audit_repo.log_event(
            entity_type="USER",
            entity_id=str(created_user.id),
            actor_id=created_user.id,
            action="USER_REGISTERED",
            details={"email": created_user.email, "role": str(created_user.role)},
        )

        return UserResponse.model_validate(created_user)

    def register_applicant(self, req: ApplicantRegisterRequest) -> UserResponse:
        clean_email = req.email.lower().strip()
        existing = self.user_repo.get_by_email(clean_email)
        if existing:
            raise DuplicateEntityException("An account with this email address already exists.")

        user = User(
            full_name=req.full_name.strip(),
            email=clean_email,
            phone=req.phone,
            password_hash=get_password_hash(req.password),
            role=UserRole.APPLICANT,
            account_status=UserAccountStatus.ACTIVE,
            is_active=True,
        )
        created_user = self.user_repo.create(user)

        self.audit_repo.log_event(
            entity_type="USER",
            entity_id=str(created_user.id),
            actor_id=created_user.id,
            action="USER_REGISTERED",
            details={"email": created_user.email, "role": str(created_user.role)},
        )

        return UserResponse.model_validate(created_user)

    def register_staff(self, req: StaffRegisterRequest) -> UserResponse:
        if req.requested_role not in [UserRole.OFFICER, UserRole.COMMITTEE]:
            raise AppException("Requested role must be either OFFICER or COMMITTEE.", status_code=400)

        clean_email = req.email.lower().strip()
        existing = self.user_repo.get_by_email(clean_email)
        if existing:
            raise DuplicateEntityException("An account with this email address already exists.")

        # Staff user starts inactive and pending administrator approval
        user = User(
            full_name=req.full_name.strip(),
            email=clean_email,
            phone=req.phone,
            password_hash=get_password_hash(req.password),
            role=req.requested_role,
            account_status=UserAccountStatus.PENDING_APPROVAL,
            is_active=False,
        )
        created_user = self.user_repo.create(user)

        # Create staff registration request record
        staff_req = StaffRegistrationRequest(
            user_id=created_user.id,
            requested_role=req.requested_role,
            employee_id=req.employee_id.strip(),
            department=req.department.strip(),
            designation=req.designation.strip(),
            jurisdiction=req.jurisdiction.strip(),
            status=StaffRequestStatus.PENDING,
        )
        self.staff_repo.create(staff_req)

        self.audit_repo.log_event(
            entity_type="USER",
            entity_id=str(created_user.id),
            actor_id=created_user.id,
            action="STAFF_APPROVAL_SUBMITTED",
            details={
                "email": created_user.email,
                "requested_role": str(req.requested_role),
                "employee_id": req.employee_id,
                "department": req.department,
            },
        )

        return UserResponse.model_validate(created_user)

    def authenticate(self, login_data: LoginRequest) -> Token:
        clean_email = login_data.email.lower().strip()
        user = self.user_repo.get_by_email(clean_email)
        if not user:
            self.audit_repo.log_event(
                entity_type="USER",
                entity_id="UNKNOWN",
                actor_id=None,
                action="USER_LOGIN_FAILED",
                details={"email": clean_email, "reason": "user_not_found"},
            )
            raise UnauthorizedException("Invalid email or password")

        if not verify_password(login_data.password, user.password_hash):
            self.audit_repo.log_event(
                entity_type="USER",
                entity_id=str(user.id),
                actor_id=user.id,
                action="USER_LOGIN_FAILED",
                details={"email": clean_email, "reason": "invalid_password"},
            )
            raise UnauthorizedException("Invalid email or password")

        # Explicit Account Lifecycle Checks
        if user.account_status == UserAccountStatus.PENDING_APPROVAL:
            raise AppException(
                "Your account is pending administrator approval. You will be able to access the portal after your account has been approved.",
                status_code=403,
            )

        if user.account_status == UserAccountStatus.REJECTED:
            staff_req = self.staff_repo.get_by_user_id(user.id)
            rejection_reason = (
                staff_req.rejection_reason
                if staff_req and staff_req.rejection_reason
                else "Official institutional identification details could not be verified."
            )
            raise AppException(
                "Your registration request was not approved.",
                status_code=403,
                reason=rejection_reason,
            )

        if not user.is_active or user.account_status != UserAccountStatus.ACTIVE:
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
