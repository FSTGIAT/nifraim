"""commission_rates: add rate_scope (policy-year band) + include it in unique key

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-05 12:00:00.000000

Adds `rate_scope` — the policy-year band a rate applies to (e.g. "שנה 1-5" /
"שנה 6-15" / "שנה 16+"). Insurance agreements tier the נפרעים rate by how long
the policy has been active (ספר + תוספת change per band). We now capture the
band from the agreement's year columns so the data is complete per band.

The band is added to the uniqueness index so two tiers of the SAME product that
happen to share a rate value no longer collapse into one row (the old key was
(user, company, product, freq, rate, effective_from) — identical-value tiers
deduped and the band was lost).

Note: this migration only PERSISTS the band. The matcher that selects a rate by
the policy's age is a separate, later change — for now selection is unchanged.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commission_rates",
        sa.Column("rate_scope", sa.String(length=40), nullable=True),
    )

    # Rebuild the unique index to include the policy-year band so same-value
    # tiers of one product can coexist.
    op.execute("DROP INDEX IF EXISTS uq_commission_rates_keys")
    op.execute("""
        CREATE UNIQUE INDEX uq_commission_rates_keys
        ON commission_rates (
            user_id,
            company_name,
            COALESCE(product, ''),
            COALESCE(payment_frequency, ''),
            rate,
            COALESCE(effective_from, '1900-01-01'::date),
            COALESCE(rate_scope, '')
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
            rate,
            COALESCE(effective_from, '1900-01-01'::date)
        )
    """)
    op.drop_column("commission_rates", "rate_scope")
