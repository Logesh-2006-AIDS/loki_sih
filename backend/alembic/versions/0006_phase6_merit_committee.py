"""phase 6 merit scoring and committee selection

Revision ID: 0006_phase6_merit_committee
Revises: 0005_phase5_resubmission
Create Date: 2026-09-20 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase6_merit_committee"
down_revision: Union[str, None] = "0005_phase5_resubmission"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create committee_assignments table
    op.create_table(
        "committee_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_in_committee", sa.String(length=64), nullable=False, server_default="MEMBER"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_committee_assignments_user_id", "committee_assignments", ["user_id"])
    op.create_index("ix_committee_assignments_scheme_id", "committee_assignments", ["scheme_id"])

    # 2. Create committee_evaluation_batches table
    op.create_table(
        "committee_evaluation_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scheme_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN_FOR_EVALUATION"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_committee_evaluation_batches_scheme_id", "committee_evaluation_batches", ["scheme_id"])
    op.create_index("ix_committee_evaluation_batches_scheme_version_id", "committee_evaluation_batches", ["scheme_version_id"])
    op.create_index("ix_committee_evaluation_batches_status", "committee_evaluation_batches", ["status"])

    # 3. Create committee_reviews table
    op.create_table(
        "committee_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("committee_member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scheme_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("committee_evaluation_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.String(length=32), nullable=False, server_default="RECOMMEND"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("application_id", "committee_member_id", "batch_id", name="uq_committee_app_member_batch"),
    )
    op.create_index("ix_committee_reviews_application_id", "committee_reviews", ["application_id"])
    op.create_index("ix_committee_reviews_committee_member_id", "committee_reviews", ["committee_member_id"])
    op.create_index("ix_committee_reviews_scheme_id", "committee_reviews", ["scheme_id"])
    op.create_index("ix_committee_reviews_batch_id", "committee_reviews", ["batch_id"])

    # 4. Enhance merit_scores table
    op.add_column("merit_scores", sa.Column("scheme_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scheme_versions.id", ondelete="CASCADE"), nullable=True))
    op.add_column("merit_scores", sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("committee_evaluation_batches.id", ondelete="SET NULL"), nullable=True))
    op.add_column("merit_scores", sa.Column("rank", sa.Integer(), nullable=True))
    op.add_column("merit_scores", sa.Column("tie_break_level", sa.String(length=64), nullable=True))
    op.add_column("merit_scores", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("merit_scores", sa.Column("formula_version", sa.String(length=32), nullable=False, server_default="1.0"))
    op.create_index("ix_merit_scores_scheme_version_id", "merit_scores", ["scheme_version_id"])
    op.create_index("ix_merit_scores_batch_id", "merit_scores", ["batch_id"])

    # 5. Enhance selection_results table
    op.add_column("selection_results", sa.Column("scheme_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scheme_versions.id", ondelete="CASCADE"), nullable=True))
    op.add_column("selection_results", sa.Column("batch_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("committee_evaluation_batches.id", ondelete="SET NULL"), nullable=True))
    op.add_column("selection_results", sa.Column("quota_category", sa.String(length=64), nullable=False, server_default="GENERAL_ST"))
    op.add_column("selection_results", sa.Column("committee_minutes", sa.Text(), nullable=True))
    op.add_column("selection_results", sa.Column("authority_reference", sa.String(length=128), nullable=True))
    op.add_column("selection_results", sa.Column("selection_round", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("selection_results", sa.Column("is_override", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("selection_results", sa.Column("override_reason", sa.Text(), nullable=True))
    op.add_column("selection_results", sa.Column("override_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("selection_results", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_selection_results_scheme_version_id", "selection_results", ["scheme_version_id"])
    op.create_index("ix_selection_results_batch_id", "selection_results", ["batch_id"])


def downgrade() -> None:
    # 5. Revert selection_results columns
    op.drop_index("ix_selection_results_batch_id", table_name="selection_results")
    op.drop_index("ix_selection_results_scheme_version_id", table_name="selection_results")
    op.drop_column("selection_results", "created_at")
    op.drop_column("selection_results", "override_by")
    op.drop_column("selection_results", "override_reason")
    op.drop_column("selection_results", "is_override")
    op.drop_column("selection_results", "selection_round")
    op.drop_column("selection_results", "authority_reference")
    op.drop_column("selection_results", "committee_minutes")
    op.drop_column("selection_results", "quota_category")
    op.drop_column("selection_results", "batch_id")
    op.drop_column("selection_results", "scheme_version_id")

    # 4. Revert merit_scores columns
    op.drop_index("ix_merit_scores_batch_id", table_name="merit_scores")
    op.drop_index("ix_merit_scores_scheme_version_id", table_name="merit_scores")
    op.drop_column("merit_scores", "formula_version")
    op.drop_column("merit_scores", "is_current")
    op.drop_column("merit_scores", "tie_break_level")
    op.drop_column("merit_scores", "rank")
    op.drop_column("merit_scores", "batch_id")
    op.drop_column("merit_scores", "scheme_version_id")

    # 3. Drop committee_reviews
    op.drop_table("committee_reviews")

    # 2. Drop committee_evaluation_batches
    op.drop_table("committee_evaluation_batches")

    # 1. Drop committee_assignments
    op.drop_table("committee_assignments")
