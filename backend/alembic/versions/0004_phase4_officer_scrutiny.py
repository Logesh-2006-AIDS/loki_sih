"""phase 4 officer scrutiny

Revision ID: 0004_phase4_officer_scrutiny
Revises: 0003_phase3_verifications
Create Date: 2026-09-20 07:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004_phase4_officer_scrutiny"
down_revision: Union[str, None] = "0003_phase3_verifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add scrutiny columns to applications
    op.add_column(
        "applications",
        sa.Column("scrutiny_remarks", sa.Text(), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column(
            "scrutiny_officer_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "applications",
        sa.Column("scrutiny_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_applications_scrutiny_officer_id",
        "applications",
        ["scrutiny_officer_id"],
        unique=False,
    )

    # 2. Add human scrutiny decision columns to document_verifications
    op.add_column(
        "document_verifications",
        sa.Column("officer_decision", sa.String(32), nullable=True),
    )
    op.add_column(
        "document_verifications",
        sa.Column("officer_remarks", sa.Text(), nullable=True),
    )
    op.add_column(
        "document_verifications",
        sa.Column(
            "ai_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "document_verifications",
        sa.Column("override_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_verifications", "override_reason")
    op.drop_column("document_verifications", "ai_override")
    op.drop_column("document_verifications", "officer_remarks")
    op.drop_column("document_verifications", "officer_decision")

    op.drop_index("ix_applications_scrutiny_officer_id", table_name="applications")
    op.drop_column("applications", "scrutiny_completed_at")
    op.drop_column("applications", "scrutiny_officer_id")
    op.drop_column("applications", "scrutiny_remarks")
