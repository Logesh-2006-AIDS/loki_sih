import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class OfficerAssignment(Base):
    __tablename__ = "officer_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    officer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    scheme_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    officer = relationship("User", back_populates="assignments")
    scheme = relationship("Scheme", back_populates="officer_assignments")
