"""commission_rates: rate_kind enum column

Revision ID: q9r0s1t2u3v4
Revises: 0aa057d40b6f
Create Date: 2026-05-18 14:00:00.000000

Adds `rate_kind` to distinguish the kind of rate a row represents:
- `single` (default for legacy rows / single-number tables)
- `book` (עמלת ספר — base rate per category)
- `reward` (שיעור תגמול / תוספת נפרעים — additive component)
- `total` (סה״כ — sum literally printed in the document)
- `addition` (informational delta; NOT inserted as a standalone DB row)

Without this, the chat layer couldn't tell whether a 7.2% row was a stand-
alone single rate or just the "reward" component of a 22.2% total — which
is exactly the test1-3 confusion that produced fabricated 25.4% answers.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "q9r0s1t2u3v4"
down_revision: Union[str, Sequence[str], None] = "0aa057d40b6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commission_rates",
        sa.Column(
            "rate_kind",
            sa.String(16),
            nullable=False,
            server_default="single",
        ),
    )


def downgrade() -> None:
    op.drop_column("commission_rates", "rate_kind")
