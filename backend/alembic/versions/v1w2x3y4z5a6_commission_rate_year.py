"""commission_rates: validity dates + year-aware unique key

Revision ID: v1w2x3y4z5a6
Revises: u0v1w2x3y4z5
Create Date: 2026-05-15 23:10:00.000000

Adds `effective_from` / `effective_to` DATE columns. An insurance agreement
typically declares a validity window (e.g. "01/01/2025 to 31/12/2026"); the
same product can have different rates across years, and which rate applies
to a given policy depends on the policy's sign date. Without year context,
the deviation matcher silently picks "the closest rate", which hides real
underpayments when an older policy is paid at last year's lower rate.

We also rebuild the uniqueness index so 2025 and 2018 rates for the same
product can coexist intentionally — the old index keyed on rate alone,
which already let them coexist, but as a side-effect of identical key
material rather than a deliberate dimension. Including `effective_from`
makes the intent explicit and lets the matcher distinguish them by year.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v1w2x3y4z5a6"
down_revision: Union[str, Sequence[str], None] = "u0v1w2x3y4z5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commission_rates",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "commission_rates",
        sa.Column("effective_to", sa.Date(), nullable=True),
    )

    # Drop the old unique index (didn't include validity) so we can rebuild
    # with effective_from as part of the key.
    op.execute("DROP INDEX IF EXISTS uq_commission_rates_keys")
    op.execute("""
        CREATE UNIQUE INDEX uq_commission_rates_keys
        ON commission_rates (
            user_id,
            company_name,
            COALESCE(product, ''),
            COALESCE(payment_frequency, ''),
            rate,
            COALESCE(effective_from, '1900-01-01'::date)
        )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_commission_rates_keys")
    op.execute("""
        CREATE UNIQUE INDEX uq_commission_rates_keys
        ON commission_rates (
            user_id,
            company_name,
            COALESCE(product, ''),
            COALESCE(payment_frequency, ''),
            rate
        )
    """)
    op.drop_column("commission_rates", "effective_to")
    op.drop_column("commission_rates", "effective_from")
