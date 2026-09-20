"""phase 8 fellowship management and disbursements

Revision ID: 0008_phase8_fellowships
Revises: 0007_phase7_analytics_indexes
Create Date: 2026-09-20 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_phase8_fellowships"
down_revision: Union[str, None] = "0007_phase7_analytics_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update fellowship_records foreign key and unique constraint
    op.drop_constraint("fk_fellowship_records_application_id_applications", "fellowship_records", type_="foreignkey")
    op.create_foreign_key(
        "fk_fellowship_records_application_id_applications",
        "fellowship_records",
        "applications",
        ["application_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_fellowship_application",
        "fellowship_records",
        ["application_id"],
    )

    # Add columns to fellowship_records
    op.add_column("fellowship_records", sa.Column("fellowship_number", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_fellowship_number", "fellowship_records", ["fellowship_number"])

    op.add_column("fellowship_records", sa.Column("sanction_order_number", sa.String(128), nullable=True))
    op.create_unique_constraint("uq_fellowship_sanction_order_number", "fellowship_records", ["sanction_order_number"])

    op.add_column("fellowship_records", sa.Column("sanction_mode", sa.String(32), nullable=False, server_default="DEMO_SIMULATED"))
    op.add_column("fellowship_records", sa.Column("sanction_date", sa.Date(), nullable=True))

    op.add_column("fellowship_records", sa.Column("scheme_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_fellowship_records_scheme_id", "fellowship_records", "schemes", ["scheme_id"], ["id"], ondelete="RESTRICT")

    op.add_column("fellowship_records", sa.Column("scheme_version_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_fellowship_records_scheme_version_id", "fellowship_records", "scheme_versions", ["scheme_version_id"], ["id"], ondelete="RESTRICT")

    op.add_column("fellowship_records", sa.Column("applicant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_fellowship_records_applicant_id", "fellowship_records", "users", ["applicant_id"], ["id"], ondelete="RESTRICT")

    op.add_column("fellowship_records", sa.Column("assigned_officer_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_fellowship_records_assigned_officer_id", "fellowship_records", "users", ["assigned_officer_id"], ["id"], ondelete="SET NULL")

    op.add_column("fellowship_records", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("fellowship_records", sa.Column("end_date", sa.Date(), nullable=True))
    op.add_column("fellowship_records", sa.Column("tenure_years", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("fellowship_records", sa.Column("institution_name", sa.String(255), nullable=True))
    op.add_column("fellowship_records", sa.Column("department", sa.String(255), nullable=True))
    op.add_column("fellowship_records", sa.Column("guide_name", sa.String(255), nullable=True))
    op.add_column("fellowship_records", sa.Column("research_topic", sa.Text(), nullable=True))
    op.add_column("fellowship_records", sa.Column("award_letter_url", sa.String(512), nullable=True))

    op.create_index("ix_fellowship_records_applicant_status", "fellowship_records", ["applicant_id", "status"])
    op.create_index("ix_fellowship_records_scheme_status", "fellowship_records", ["scheme_id", "status"])

    # 2. Update renewal_submissions
    op.drop_constraint("fk_renewal_submissions_fellowship_id_fellowship_records", "renewal_submissions", type_="foreignkey")
    op.create_foreign_key(
        "fk_renewal_submissions_fellowship_id_fellowship_records",
        "renewal_submissions",
        "fellowship_records",
        ["fellowship_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("renewal_submissions", sa.Column("renewal_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("renewal_submissions", sa.Column("annual_progress_summary", sa.Text(), nullable=True))
    op.add_column("renewal_submissions", sa.Column("marks_percentage", sa.Float(), nullable=True))
    op.add_column("renewal_submissions", sa.Column("continuation_certificate_path", sa.String(512), nullable=True))
    op.add_column("renewal_submissions", sa.Column("marksheet_document_path", sa.String(512), nullable=True))

    op.add_column("renewal_submissions", sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_renewal_submissions_reviewer_id", "renewal_submissions", "users", ["reviewer_id"], ["id"], ondelete="SET NULL")

    op.add_column("renewal_submissions", sa.Column("reviewer_decision", sa.String(32), nullable=True))
    op.add_column("renewal_submissions", sa.Column("reviewer_remarks", sa.Text(), nullable=True))

    op.add_column("renewal_submissions", sa.Column("deficiency_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_renewal_submissions_deficiency_id", "renewal_submissions", "deficiencies", ["deficiency_id"], ["id"], ondelete="SET NULL")

    op.add_column("renewal_submissions", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_unique_constraint("uq_fellowship_renewal_year", "renewal_submissions", ["fellowship_id", "academic_year"])

    # 3. Update progress_reports
    op.drop_constraint("fk_progress_reports_fellowship_id_fellowship_records", "progress_reports", type_="foreignkey")
    op.create_foreign_key(
        "fk_progress_reports_fellowship_id_fellowship_records",
        "progress_reports",
        "fellowship_records",
        ["fellowship_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("progress_reports", sa.Column("report_period_start", sa.Date(), nullable=True))
    op.add_column("progress_reports", sa.Column("report_period_end", sa.Date(), nullable=True))
    op.add_column("progress_reports", sa.Column("publications_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("progress_reports", sa.Column("presentations_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("progress_reports", sa.Column("patents_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("progress_reports", sa.Column("supervisor_remarks", sa.Text(), nullable=True))
    op.add_column("progress_reports", sa.Column("supervisor_approved", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("progress_reports", sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_progress_reports_reviewer_id", "progress_reports", "users", ["reviewer_id"], ["id"], ondelete="SET NULL")

    op.add_column("progress_reports", sa.Column("reviewer_decision", sa.String(32), nullable=True))
    op.add_column("progress_reports", sa.Column("reviewer_remarks", sa.Text(), nullable=True))

    op.add_column("progress_reports", sa.Column("deficiency_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_progress_reports_deficiency_id", "progress_reports", "deficiencies", ["deficiency_id"], ["id"], ondelete="SET NULL")

    op.add_column("progress_reports", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    # 4. Create disbursement_installments
    op.create_table(
        "disbursement_installments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fellowship_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("stipend_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("contingency_amount", sa.Numeric(12, 2), nullable=False, server_default="0.0"),
        sa.Column("hra_amount", sa.Numeric(12, 2), nullable=False, server_default="0.0"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_status", sa.String(32), nullable=False, server_default="SCHEDULED"),
        sa.Column("integration_mode", sa.String(32), nullable=False, server_default="SIMULATED_MOCK"),
        sa.Column("payment_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pfms_reference_id", sa.String(128), nullable=True),
        sa.Column("bank_reference_utr", sa.String(128), nullable=True),
        sa.Column("account_number_last4", sa.String(4), nullable=False),
        sa.Column("ifsc_code", sa.String(16), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["fellowship_id"], ["fellowship_records.id"], name="fk_disbursement_installments_fellowship_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name="fk_disbursement_installments_approved_by", ondelete="SET NULL"),
        sa.UniqueConstraint("payment_request_id", name="uq_disbursement_payment_request_id"),
        sa.UniqueConstraint("bank_reference_utr", name="uq_disbursement_bank_reference_utr"),
        sa.UniqueConstraint("fellowship_id", "installment_number", name="uq_fellowship_installment"),
    )
    op.create_index("ix_disbursements_fellowship_status", "disbursement_installments", ["fellowship_id", "payment_status"])
    op.create_index("ix_disbursements_payment_status_created", "disbursement_installments", ["payment_status", "created_at"])


def downgrade() -> None:
    op.drop_table("disbursement_installments")

    op.drop_constraint("uq_fellowship_renewal_year", "renewal_submissions", type_="unique")
    op.drop_constraint("fk_renewal_submissions_deficiency_id", "renewal_submissions", type_="foreignkey")
    op.drop_constraint("fk_renewal_submissions_reviewer_id", "renewal_submissions", type_="foreignkey")
    op.drop_column("renewal_submissions", "updated_at")
    op.drop_column("renewal_submissions", "deficiency_id")
    op.drop_column("renewal_submissions", "reviewer_remarks")
    op.drop_column("renewal_submissions", "reviewer_decision")
    op.drop_column("renewal_submissions", "reviewer_id")
    op.drop_column("renewal_submissions", "marksheet_document_path")
    op.drop_column("renewal_submissions", "continuation_certificate_path")
    op.drop_column("renewal_submissions", "marks_percentage")
    op.drop_column("renewal_submissions", "annual_progress_summary")
    op.drop_column("renewal_submissions", "renewal_number")

    op.drop_constraint("fk_progress_reports_deficiency_id", "progress_reports", type_="foreignkey")
    op.drop_constraint("fk_progress_reports_reviewer_id", "progress_reports", type_="foreignkey")
    op.drop_column("progress_reports", "updated_at")
    op.drop_column("progress_reports", "deficiency_id")
    op.drop_column("progress_reports", "reviewer_remarks")
    op.drop_column("progress_reports", "reviewer_decision")
    op.drop_column("progress_reports", "reviewer_id")
    op.drop_column("progress_reports", "supervisor_approved")
    op.drop_column("progress_reports", "supervisor_remarks")
    op.drop_column("progress_reports", "patents_count")
    op.drop_column("progress_reports", "presentations_count")
    op.drop_column("progress_reports", "publications_count")
    op.drop_column("progress_reports", "report_period_end")
    op.drop_column("progress_reports", "report_period_start")

    op.drop_index("ix_fellowship_records_scheme_status", "fellowship_records")
    op.drop_index("ix_fellowship_records_applicant_status", "fellowship_records")
    op.drop_constraint("uq_fellowship_sanction_order_number", "fellowship_records", type_="unique")
    op.drop_constraint("uq_fellowship_number", "fellowship_records", type_="unique")
    op.drop_constraint("uq_fellowship_application", "fellowship_records", type_="unique")
    op.drop_constraint("fk_fellowship_records_assigned_officer_id", "fellowship_records", type_="foreignkey")
    op.drop_constraint("fk_fellowship_records_applicant_id", "fellowship_records", type_="foreignkey")
    op.drop_constraint("fk_fellowship_records_scheme_version_id", "fellowship_records", type_="foreignkey")
    op.drop_constraint("fk_fellowship_records_scheme_id", "fellowship_records", type_="foreignkey")
    op.drop_column("fellowship_records", "award_letter_url")
    op.drop_column("fellowship_records", "research_topic")
    op.drop_column("fellowship_records", "guide_name")
    op.drop_column("fellowship_records", "department")
    op.drop_column("fellowship_records", "institution_name")
    op.drop_column("fellowship_records", "tenure_years")
    op.drop_column("fellowship_records", "end_date")
    op.drop_column("fellowship_records", "start_date")
    op.drop_column("fellowship_records", "assigned_officer_id")
    op.drop_column("fellowship_records", "applicant_id")
    op.drop_column("fellowship_records", "scheme_version_id")
    op.drop_column("fellowship_records", "scheme_id")
    op.drop_column("fellowship_records", "sanction_date")
    op.drop_column("fellowship_records", "sanction_mode")
    op.drop_column("fellowship_records", "sanction_order_number")
    op.drop_column("fellowship_records", "fellowship_number")
