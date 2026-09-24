"""maslaka_agent_links: approval-watcher audit columns

Revision ID: mslk_shiyuch_02
Revises: mslk_shiyuch_01
Create Date: 2026-09-24

Additive and nullable only — safe on the live table (one row today).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "mslk_shiyuch_02"
down_revision: Union[str, Sequence[str], None] = "mslk_shiyuch_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = (
    ("sent_message_id", sa.String(255)),
    ("reply_message_id", sa.String(255)),
    ("reply_received_at", sa.DateTime()),
    ("reply_subject", sa.String(500)),
    ("reply_snippet", sa.Text()),
    ("decided_via", sa.String(16)),
)


def upgrade() -> None:
    for name, type_ in _COLS:
        op.add_column("maslaka_agent_links", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLS):
        op.drop_column("maslaka_agent_links", name)
