"""pension_inquiries.target_yatzran_id — the body a production report asks

A 2000/2100 production report is "מיצרן ספציפי": one request per institutional
body, named by its ח.פ in KodEirua/Mutzar/NetuneiMutzar/KOD-MEZAHE-YATZRAN. The
inquiry row has to remember which body, so the Gateway worker can build it.

Hand-written (see mslk_shiyuch_01 for why autogenerate is not used here).

Revision ID: mslk_prod_report_01
Revises: mail_agent_02
Create Date: 2026-09-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "mslk_prod_report_01"
down_revision: Union[str, Sequence[str], None] = "mail_agent_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pension_inquiries",
        sa.Column("target_yatzran_id", sa.String(9), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pension_inquiries", "target_yatzran_id")
