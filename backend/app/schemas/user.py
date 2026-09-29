import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from app.core.enums import UserRole, UserAccountStatus
from app.schemas.staff_request import (
    validate_name_field,
    validate_phone_field,
    validate_password_field,
)


class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.APPLICANT
    account_status: UserAccountStatus = UserAccountStatus.ACTIVE

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        return validate_name_field(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_field(v)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        return validate_password_field(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    account_status: Optional[UserAccountStatus] = None


class UserResponse(UserBase):
    id: uuid.UUID
    role: UserRole
    account_status: UserAccountStatus = UserAccountStatus.ACTIVE
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
