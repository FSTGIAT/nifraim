"""הר הביטוח requests + customer insurance policies + policy documents (Markdown).

Revision ID: policies_01
Revises: calls_05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "policies_01"
down_revision = "calls_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "harb_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id_number", sa.String(20), nullable=False),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("id_issue_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("portal_run_id", UUID(as_uuid=True), sa.ForeignKey("portal_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("policies_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_harb_requests_user_status", "harb_requests", ["user_id", "status"])
    op.create_index("ix_harb_requests_customer_id_number", "harb_requests", ["customer_id_number"])

    op.create_table(
        "insurance_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id_number", sa.String(20), nullable=False),
        sa.Column("harb_request_id", UUID(as_uuid=True), sa.ForeignKey("harb_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="harb"),
        sa.Column("domain", sa.String(80)),
        sa.Column("main_branch", sa.String(120)),
        sa.Column("sub_branch", sa.String(160)),
        sa.Column("product_type", sa.String(160)),
        sa.Column("company", sa.String(160)),
        sa.Column("period_start", sa.Date()),
        sa.Column("period_end", sa.Date()),
        sa.Column("renewing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("premium", sa.Numeric(14, 2)),
        sa.Column("premium_type", sa.String(300)),
        sa.Column("policy_number", sa.String(40)),
        sa.Column("plan_class", sa.String(40)),
        sa.Column("produced_at", sa.Date()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_insurance_policies_user_customer", "insurance_policies", ["user_id", "customer_id_number"])

    op.create_table(
        "policy_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id_number", sa.String(20), nullable=True),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("company", sa.String(160)),
        sa.Column("policy_number", sa.String(40)),
        sa.Column("markdown", sa.Text()),
        sa.Column("file_path", sa.String(500)),
        sa.Column("filename", sa.String(300)),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("harb_request_id", UUID(as_uuid=True), sa.ForeignKey("harb_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ready"),
        sa.Column("error", sa.String(500)),
        sa.Column("index_tries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "sha256", name="uq_policy_documents_user_sha"),
    )
    op.create_index("ix_policy_documents_user_customer", "policy_documents", ["user_id", "customer_id_number"])


def downgrade() -> None:
    op.drop_table("policy_documents")
    op.drop_table("insurance_policies")
    op.drop_table("harb_requests")
