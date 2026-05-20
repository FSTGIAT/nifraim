"""yield_recommendations: add recommended_fund_name, risk_class, move_type.

Revision ID: z5a6b7c8d9e0
Revises: y4z5a6b7c8d9
Create Date: 2026-05-19 21:00:00.000000

Smarter yield recommender — instead of recommending the whole TRACK average,
we pick the specific top fund within the destination track (more variety,
matches what gemel-net surfaces). Also tag each recommendation with its risk
class so the UI can split same-risk moves from aggressive upgrades.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "y4z5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "yield_recommendations",
        sa.Column("recommended_fund_name", sa.String(160), nullable=True),
    )
    op.add_column(
        "yield_recommendations",
        sa.Column(
            "risk_class",
            sa.String(16),
            nullable=False,
            server_default="general",
        ),
    )
    op.add_column(
        "yield_recommendations",
        sa.Column(
            "move_type",
            sa.String(16),
            nullable=False,
            server_default="same",
        ),
    )


def downgrade() -> None:
    op.drop_column("yield_recommendations", "move_type")
    op.drop_column("yield_recommendations", "risk_class")
    op.drop_column("yield_recommendations", "recommended_fund_name")
