import uuid
from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, Enum, ForeignKey
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
    result: Mapped[SelectionResultEnum] = mapped_column(
        Enum(SelectionResultEnum, native_enum=False), nullable=False, index=True
    )
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    application = relationship("Application", back_populates="selection_results")
    finalizer = relationship("User")
