import uuid
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, Text, DateTime, Enum, ForeignKey, func
from sqlalchemy import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.core.enums import SelectionResultEnum


class SelectionResult(Base):
    __tablename__ = "selection_results"

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
    result: Mapped[SelectionResultEnum] = mapped_column(
        Enum(SelectionResultEnum, native_enum=False), nullable=False, index=True
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quota_category: Mapped[str] = mapped_column(String(64), default="GENERAL_ST", nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    committee_minutes: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selection_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    override_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    application = relationship("Application", back_populates="selection_results")
    scheme_version = relationship("SchemeVersion")
    batch = relationship("CommitteeEvaluationBatch")
    finalizer = relationship("User", foreign_keys=[finalized_by])
    overrider = relationship("User", foreign_keys=[override_by])
