"""maslaka_agent_links.auto_production — the agent's consent to monthly production

When set, approval by the מסלקה automatically opens a monthly production-report
subscription (2100, five-month minimum commitment) with every body the agent has
customers at, and a daily job adds bodies that appear later. Consent is recorded
with its timestamp; nothing is subscribed without it.

Hand-written (see mslk_shiyuch_01 for why autogenerate is not used here).

Revision ID: mslk_auto_prod_04
Revises: mslk_prod_report_03
Create Date: 2026-09-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "mslk_auto_prod_04"
down_revision: Union[str, Sequence[str], None] = "mslk_prod_report_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("maslaka_agent_links", sa.Column(
        "auto_production", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("maslaka_agent_links", sa.Column("auto_production_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("maslaka_agent_links", "auto_production_at")
    op.drop_column("maslaka_agent_links", "auto_production")
