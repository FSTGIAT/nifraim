"""customer_product_snapshots: month-by-month history of every customer's products.

Revision ID: customer_history_01
Revises: pensyanet_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "customer_history_01"
down_revision = "pensyanet_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_product_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("period_month", sa.Date, nullable=False, index=True),
        sa.Column("customer_id_number", sa.String(20), nullable=False, index=True),
        sa.Column("customer_name", sa.String(200)),
        sa.Column("company", sa.String(160), nullable=False, server_default=""),
        sa.Column("product_type", sa.String(160), nullable=False, server_default=""),
        sa.Column("product", sa.String(200)),
        sa.Column("policy_number", sa.String(60), nullable=False, server_default=""),
        sa.Column("track", sa.String(200), nullable=False, server_default=""),
        sa.Column("status", sa.String(80)),
        sa.Column("accumulation", sa.Numeric(16, 2)),
        sa.Column("premium", sa.Numeric(14, 2)),
        sa.Column("source_upload_id", UUID(as_uuid=True), index=True),
        sa.Column("captured_at", sa.DateTime),
        sa.UniqueConstraint("user_id", "period_month", "customer_id_number", "company", "policy_number",
                            "product_type", "track", name="uq_customer_product_month"),
    )
    op.create_table(
        "customer_snapshot_uploads",
        sa.Column("upload_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("captured_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("customer_snapshot_uploads")
    op.drop_table("customer_product_snapshots")
