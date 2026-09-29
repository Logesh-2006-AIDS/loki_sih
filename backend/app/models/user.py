import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum, func
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import UserRole, UserAccountStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), default=UserRole.APPLICANT, nullable=False
    )
    account_status: Mapped[UserAccountStatus] = mapped_column(
        Enum(UserAccountStatus, native_enum=False),
        default=UserAccountStatus.ACTIVE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mocked_ekyc_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    applications = relationship(
        "Application",
        foreign_keys="[Application.applicant_id]",
        back_populates="applicant",
        cascade="all, delete-orphan",
    )
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    assignments = relationship("OfficerAssignment", back_populates="officer", cascade="all, delete-orphan")
    committee_assignments = relationship("CommitteeAssignment", back_populates="user", cascade="all, delete-orphan")
    staff_request = relationship(
        "StaffRegistrationRequest",
        foreign_keys="[StaffRegistrationRequest.user_id]",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
