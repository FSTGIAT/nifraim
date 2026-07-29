"""Split product information out of commission_rates.company_name.

Legacy and seeded rate rows smuggled the PRODUCT into the COMPANY column and
left `product` NULL:

    company_name='הראל מגוון'      product=NULL   rate=0.0050
    company_name='מגדל קשת'        product=NULL   rate=0.0030
    company_name='פניקס פוליסות'   product=NULL   rate=0.0034
    company_name='פניקס גמל והשתלמות' product=NULL rate=0.0045

AI-extracted rows get it right (`company_name='הראל פנסיה וגמל'` +
`product='פוליסות מסוג מגוון'`). The mixed shape had two costs:

1. The shelf shows 'הראל מגוון' as if it were a company, so an agent reading
   their own agreements sees companies that don't exist.
2. The last two rows above BOTH normalise to 'הפניקס' with a NULL product, so
   the matcher had to pick between two different company-wide rates — 0.34%
   and 0.45% — with nothing to tell them apart.

This moves the residue into `product`, leaving the brand stem as the company.
The matcher handles both shapes (it derives the residue at match time), so this
migration is about legibility and about retiring that fallback — it is NOT
required for correctness and deliberately makes no behavioural promise beyond
what the matcher already does.

Ordering note: the matcher ships FIRST and works on un-migrated data, which is
the state every existing row is in. Applying this against an older matcher is
the one sequence that could route a row through two different paths.

Revision ID: b7c8d9e0f1a2
Revises: m1a2s3l4k5a6
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.utils.company_norm import company_stem, product_residue

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "m1a2s3l4k5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mirrors uq_commission_rates_keys. A rewrite that would collide with an
# existing row is SKIPPED rather than merged — two rows that collapse to the
# same key are the same agreement line, and dropping one silently would change
# what the agent sees without telling them.
#
# Every bind is CAST explicitly. Postgres cannot type a bare NULL or a bare
# '1900-01-01' literal against a DATE column and fails the whole migration with
# `operator does not exist: date = text`; the nullable columns here
# (effective_from, payment_frequency, rate_scope) all hit that path.
_COLLISION_SQL = sa.text(
    """
    SELECT 1 FROM commission_rates
     WHERE user_id = :user_id
       AND company_name = :company_name
       AND COALESCE(product, '') = CAST(:product AS VARCHAR)
       AND COALESCE(payment_frequency, '') = COALESCE(CAST(:payment_frequency AS VARCHAR), '')
       AND rate = CAST(:rate AS NUMERIC)
       AND COALESCE(effective_from, DATE '1900-01-01')
           = COALESCE(CAST(:effective_from AS DATE), DATE '1900-01-01')
       AND COALESCE(rate_scope, '') = COALESCE(CAST(:rate_scope AS VARCHAR), '')
       AND id <> :id
     LIMIT 1
    """
)


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, user_id, company_name, payment_frequency, rate, "
            "effective_from, rate_scope FROM commission_rates WHERE product IS NULL"
        )
    ).mappings().all()

    moved = skipped = 0
    for r in rows:
        residue = product_residue(r["company_name"])
        stem = company_stem(r["company_name"])
        # No PRODUCT residue → the company column holds only a company (or
        # only business-line wording, which `product_residue` deliberately
        # refuses to promote). Re-running is therefore a no-op.
        if not residue or not stem or stem == r["company_name"]:
            continue

        collision = conn.execute(
            _COLLISION_SQL,
            {
                "user_id": r["user_id"],
                "company_name": stem,
                "product": residue,
                "payment_frequency": r["payment_frequency"],
                "rate": r["rate"],
                "effective_from": r["effective_from"],
                "rate_scope": r["rate_scope"],
                "id": r["id"],
            },
        ).first()
        if collision:
            skipped += 1
            continue

        conn.execute(
            sa.text(
                "UPDATE commission_rates SET company_name = :c, product = :p "
                "WHERE id = :id"
            ),
            {"c": stem, "p": residue, "id": r["id"]},
        )
        moved += 1

    print(f"[commission_rate split] moved={moved} skipped_collision={skipped}")


def downgrade() -> None:
    """Deliberately a no-op.

    Reversing would mean re-concatenating company + product back into the
    company column, but nothing records WHICH rows this migration touched — a
    blind re-join would also corrupt the AI-extracted rows that always had a
    real product. The shape after upgrade is valid input for every code path,
    so leaving it in place is safe; there is nothing to undo.
    """
