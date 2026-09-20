import uuid
from datetime import datetime
from typing import Any, List
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CommitteeEvaluationBatch(Base):
    """
    Durable entity representing a defined candidate cohort under a specific scheme version.
    Enforces the strict rule: Once the first review is submitted or the batch is locked,
    application membership is completely immutable.
    """
    __tablename__ = "committee_evaluation_batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheme_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheme_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    application_ids: Mapped[List[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        String(32), default="OPEN_FOR_EVALUATION", nullable=False, index=True
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    scheme = relationship("Scheme")
    scheme_version = relationship("SchemeVersion")
    locker = relationship("User", foreign_keys=[locked_by])
    reviews = relationship("CommitteeReview", back_populates="batch", cascade="all, delete-orphan")
