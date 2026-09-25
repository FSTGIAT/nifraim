"""pension_inquiries.mislaka_number — the מסלקה's own request GUID

The receipt (FEDBKA, record level) carries MISPAR-MISLAKA next to the filename
it answers; every holdings/CONSLT answer carries the same GUID on each product
block. It is the ONLY key that ties an insurer's data file back to our request —
our own reference never appears on the wire.

Hand-written (see mslk_shiyuch_01 for why autogenerate is not used here).

Revision ID: mslk_prod_report_03
Revises: mslk_prod_report_02
Create Date: 2026-09-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "mslk_prod_report_03"
down_revision: Union[str, Sequence[str], None] = "mslk_prod_report_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pension_inquiries", sa.Column("mislaka_number", sa.String(36), nullable=True))
    op.create_index("ix_pension_inquiries_mislaka_number", "pension_inquiries", ["mislaka_number"])


def downgrade() -> None:
    op.drop_index("ix_pension_inquiries_mislaka_number", table_name="pension_inquiries")
    op.drop_column("pension_inquiries", "mislaka_number")
