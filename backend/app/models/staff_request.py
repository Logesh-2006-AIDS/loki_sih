import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Enum, func, ForeignKey
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import UserRole, StaffRequestStatus


class StaffRegistrationRequest(Base):
    __tablename__ = "staff_registration_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    requested_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), nullable=False
    )
    employee_id: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[StaffRequestStatus] = mapped_column(
        Enum(StaffRequestStatus, native_enum=False),
        default=StaffRequestStatus.PENDING,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="staff_request")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
