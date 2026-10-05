"""Calls from the agent's phone: source, phone_number, direction, started_at, id_number.

A call recorded by the phone's dialer (Samsung Recordings/Call) is uploaded by the
Nifraim app; the number from the call log links it to the customer, so the transcript
no longer has to guess who the customer was.

Revision ID: calls_02
Revises: calls_01
"""
from alembic import op
import sqlalchemy as sa

revision = "calls_02"
down_revision = "calls_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("call_recordings", sa.Column("source", sa.String(16), nullable=False, server_default="widget"))
    op.add_column("call_recordings", sa.Column("phone_number", sa.String(30), nullable=True))
    op.add_column("call_recordings", sa.Column("direction", sa.String(8), nullable=True))
    op.add_column("call_recordings", sa.Column("started_at", sa.DateTime, nullable=True))
    op.add_column("call_recordings", sa.Column("id_number", sa.String(20), nullable=True))
    op.add_column("call_recordings", sa.Column("source_ref", sa.String(80), nullable=True))
    op.create_index("ix_call_recordings_user_id_number", "call_recordings", ["user_id", "id_number"])
    op.create_index("ix_call_recordings_user_source_ref", "call_recordings", ["user_id", "source_ref"])


def downgrade() -> None:
    op.drop_index("ix_call_recordings_user_source_ref", "call_recordings")
    op.drop_index("ix_call_recordings_user_id_number", "call_recordings")
    for c in ("source_ref", "id_number", "started_at", "direction", "phone_number", "source"):
        op.drop_column("call_recordings", c)
