import uuid
from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Float, Integer, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class MeritScore(Base):
    __tablename__ = "merit_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheme_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scheme_versions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("committee_evaluation_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tie_break_level: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    formula_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    calculated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    application = relationship("Application", back_populates="merit_scores")
    scheme_version = relationship("SchemeVersion")
    calculator = relationship("User")
