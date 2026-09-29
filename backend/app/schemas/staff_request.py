import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from app.core.enums import UserRole, StaffRequestStatus


import re

NAME_REGEX = re.compile(r"^[a-zA-Z\s\.\-']+$")
INDIAN_PHONE_REGEX = re.compile(r"^(?:\+91[\-\s]?|91[\-\s]?|0)?[6-9]\d{9}$")


def validate_name_field(v: str) -> str:
    v_clean = v.strip()
    if len(v_clean) < 2 or len(v_clean) > 100:
        raise ValueError("Full Name must be between 2 and 100 characters")
    if not NAME_REGEX.match(v_clean):
        raise ValueError("Full Name can only contain letters, spaces, and valid punctuation (. - ')")
    return v_clean


def validate_phone_field(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v_clean = v.strip()
    if not v_clean or not INDIAN_PHONE_REGEX.match(v_clean):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return v_clean


def validate_password_field(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must contain at least 8 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_/\\+=~`[\]]", v):
        raise ValueError("Password must contain at least one special character")
    return v


class ApplicantRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

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


class StaffRegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    requested_role: UserRole
    employee_id: str
    department: str
    designation: str
    jurisdiction: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        return validate_name_field(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone_field(v)

    @field_validator("requested_role")
    @classmethod
    def validate_requested_role(cls, v: UserRole) -> UserRole:
        if v not in [UserRole.OFFICER, UserRole.COMMITTEE]:
            raise ValueError("Requested role must be either OFFICER or COMMITTEE")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        return validate_password_field(v)

    @field_validator("employee_id", "department", "designation", "jurisdiction")
    @classmethod
    def validate_required_strings(cls, v: str, info) -> str:
        v_clean = v.strip()
        if not v_clean:
            raise ValueError(f"{info.field_name.replace('_', ' ').title()} is required")
        if len(v_clean) > 100:
            raise ValueError(f"{info.field_name.replace('_', ' ').title()} cannot exceed 100 characters")
        return v_clean


class StaffRequestResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    user_phone: Optional[str] = None
    requested_role: UserRole
    employee_id: str
    department: str
    designation: str
    jurisdiction: str
    status: StaffRequestStatus
    rejection_reason: Optional[str] = None
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StaffRequestRejectAction(BaseModel):
    reason: str

    @field_validator("reason")
    @classmethod
    def validate_rejection_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Please provide a reason for rejecting this registration.")
        clean_v = v.strip()
        if len(clean_v) < 10:
            raise ValueError("Rejection reason must be at least 10 characters.")
        if len(clean_v) > 1000:
            raise ValueError("Rejection reason cannot exceed 1000 characters.")
        if re.search(r"<[^>]+>", clean_v) or "<script" in clean_v.lower():
            raise ValueError("Rejection reason cannot contain HTML or script content.")
        return clean_v


class StaffRequestStatsResponse(BaseModel):
    pending_count: int
    active_officers: int
    active_committee: int
    rejected_count: int
    total_requests: int
