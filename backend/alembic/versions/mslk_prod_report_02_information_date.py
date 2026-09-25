"""pension_inquiries.information_date — TAARICH-NECHONUT-MEIDA asked for

A production request can carry an as-of date (YYYYMMDD). Stored so the Gateway
worker builds exactly what the agent asked for — e.g. 20260831 to probe whether
a past month's production report can be requested.

Hand-written (see mslk_shiyuch_01 for why autogenerate is not used here).

Revision ID: mslk_prod_report_02
Revises: mslk_prod_report_01
Create Date: 2026-09-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "mslk_prod_report_02"
down_revision: Union[str, Sequence[str], None] = "mslk_prod_report_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pension_inquiries", sa.Column("information_date", sa.String(8), nullable=True))


def downgrade() -> None:
    op.drop_column("pension_inquiries", "information_date")
