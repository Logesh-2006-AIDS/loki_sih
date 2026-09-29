from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.schemas.staff_request import StaffRegisterRequest, ApplicantRegisterRequest
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new applicant account",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.register(user_in)


@router.post(
    "/register-staff",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new staff registration request (Officer or Committee Member)",
)
def register_staff(staff_in: StaffRegisterRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.register_staff(staff_in)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate with email & password to retrieve JWT token",
)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.authenticate(login_data)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get profile details of the current authenticated user",
)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
