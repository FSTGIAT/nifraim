"""commission rate per product + reported pct on client_records

Revision ID: t9u0v1w2x3y4
Revises: s8t9u0v1w2x3
Create Date: 2026-05-15 21:30:00.000000

Adds:
- commission_rates.product (nullable) — per-product agreement rate. NULL =
  legacy company-wide rate so existing rows keep working.
- client_records.reported_commission_pct (Numeric(8,4)) — value parsed from
  the company's "אחוז עמלה" column, used to detect deviations against the
  agreement rate.

Drops the existing single-column UNIQUE on (user_id, company_name) is NOT
needed — the prior schema never declared one; the upsert was done in Python
keyed on `company_name`. We keep the data model open so a user can hold many
rows per company differing only by `product`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "t9u0v1w2x3y4"
down_revision: Union[str, Sequence[str], None] = "s8t9u0v1w2x3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commission_rates",
        sa.Column("product", sa.String(length=200), nullable=True),
    )
    op.create_index(
        "ix_commission_rates_user_company_product",
        "commission_rates",
        ["user_id", "company_name", "product"],
    )
    op.add_column(
        "client_records",
        sa.Column("reported_commission_pct", sa.Numeric(8, 4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("client_records", "reported_commission_pct")
    op.drop_index("ix_commission_rates_user_company_product", table_name="commission_rates")
    op.drop_column("commission_rates", "product")
