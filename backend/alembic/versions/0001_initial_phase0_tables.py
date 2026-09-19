"""initial phase0 tables

Revision ID: 0001_initial_phase0_tables
Revises: 
Create Date: 2026-09-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_phase0_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="APPLICANT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mocked_ekyc_ref", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. schemes table
    op.create_table(
        "schemes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scheme_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheme_version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("eligibility_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("form_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required_documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scoring_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_schemes_scheme_code", "schemes", ["scheme_code"], unique=True)

    # 3. applications table
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reference_id", sa.String(length=64), nullable=False),
        sa.Column("applicant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="DRAFT"),
        sa.Column("form_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("merit_score", sa.Float(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_applications_reference_id", "applications", ["reference_id"], unique=True)
    op.create_index("ix_applications_applicant_id", "applications", ["applicant_id"])
    op.create_index("ix_applications_scheme_id", "applications", ["scheme_id"])
    op.create_index("ix_applications_status", "applications", ["status"])

    # 4. documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="PENDING"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_application_id", "documents", ["application_id"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("ix_documents_status", "documents", ["status"])

    # 5. document_verifications table
    op.create_table(
        "document_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_status", sa.String(length=64), nullable=False),
        sa.Column("extracted_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("matched_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mismatched_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("verification_source", sa.String(length=64), nullable=False, server_default="MANUAL"),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_verifications_document_id", "document_verifications", ["document_id"])

    # 6. deficiencies table
    op.create_table(
        "deficiencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("applicant_message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_deficiencies_application_id", "deficiencies", ["application_id"])
    op.create_index("ix_deficiencies_document_id", "deficiencies", ["document_id"])

    # 7. merit_scores table
    op.create_table(
        "merit_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("score_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("calculated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_merit_scores_application_id", "merit_scores", ["application_id"])

    # 8. selection_results table
    op.create_table(
        "selection_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("finalized_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_selection_results_application_id", "selection_results", ["application_id"])

    # 9. fellowship_records table
    op.create_table(
        "fellowship_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("current_year", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("disbursement_status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fellowship_records_application_id", "fellowship_records", ["application_id"])

    # 10. renewal_submissions table
    op.create_table(
        "renewal_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fellowship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fellowship_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("documents", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_renewal_submissions_fellowship_id", "renewal_submissions", ["fellowship_id"])

    # 11. progress_reports table
    op.create_table(
        "progress_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fellowship_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fellowship_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_progress_reports_fellowship_id", "progress_reports", ["fellowship_id"])

    # 12. officer_assignments table
    op.create_table(
        "officer_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("officer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("schemes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_officer_assignments_officer_id", "officer_assignments", ["officer_id"])
    op.create_index("ix_officer_assignments_state", "officer_assignments", ["state"])
    op.create_index("ix_officer_assignments_scheme_id", "officer_assignments", ["scheme_id"])

    # 13. notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False, server_default="IN_APP"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="UNREAD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_application_id", "notifications", ["application_id"])

    # 14. audit_logs table (includes entity targeting: entity_type, entity_id)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False, server_default="APPLICATION"),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("previous_status", sa.String(length=64), nullable=True),
        sa.Column("new_status", sa.String(length=64), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_application_id", "audit_logs", ["application_id"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("officer_assignments")
    op.drop_table("progress_reports")
    op.drop_table("renewal_submissions")
    op.drop_table("fellowship_records")
    op.drop_table("selection_results")
    op.drop_table("merit_scores")
    op.drop_table("deficiencies")
    op.drop_table("document_verifications")
    op.drop_table("documents")
    op.drop_table("applications")
    op.drop_table("schemes")
    op.drop_table("users")
