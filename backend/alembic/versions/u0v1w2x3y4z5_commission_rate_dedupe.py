"""commission_rates dedupe + unique index

Revision ID: u0v1w2x3y4z5
Revises: t9u0v1w2x3y4
Create Date: 2026-05-15 22:55:00.000000

Two things:
1. Delete identical-row duplicates that accumulated before the upsert key
   included `product` + `frequency` (Harel had 6 identical 60% rows under
   the same key, etc.). We keep the row with the smallest `id` (the oldest)
   when (user_id, company_name, COALESCE(product,''), COALESCE(payment_frequency,''), rate)
   match. Distinct rates under the same logical key (e.g. Claude returned
   both 45% and 60% for the same product) are preserved — those are
   genuinely different facts.

2. Add a UNIQUE expression index on
   (user_id, company_name, COALESCE(product,''), COALESCE(payment_frequency,''), rate).
   The COALESCE-to-'' is needed because Postgres treats NULL as not-equal
   to NULL in plain unique constraints, which is exactly the bug: two
   `product=NULL` rows looked unique to the DB even though they were
   semantically identical. With the expression, NULL collapses to '' and
   the constraint actually catches the dup. After this, even raw INSERTs
   that bypass _upsert_rates_from_doc will be rejected at the DB level.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "u0v1w2x3y4z5"
down_revision: Union[str, Sequence[str], None] = "t9u0v1w2x3y4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: dedupe — keep the oldest (lowest id) row per identical group.
    op.execute("""
        DELETE FROM commission_rates a
        USING commission_rates b
        WHERE a.id > b.id
          AND a.user_id = b.user_id
          AND a.company_name = b.company_name
          AND COALESCE(a.product, '') = COALESCE(b.product, '')
          AND COALESCE(a.payment_frequency, '') = COALESCE(b.payment_frequency, '')
          AND a.rate = b.rate
    """)

    # Step 2: enforce uniqueness so the bug can't regress.
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_commission_rates_keys
        ON commission_rates (
            user_id,
            company_name,
            COALESCE(product, ''),
            COALESCE(payment_frequency, ''),
            rate
        )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_commission_rates_keys")
    # The deleted duplicate rows are not recreated — there's nothing to
    # restore them from, and they were noise anyway.
