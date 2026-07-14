"""Pin a user's worker to one approved machine.

A worker's identity is its TOKEN, not its hardware. Running one agent's installer
link on a second PC turns that PC into a full copy of their worker: it heartbeats
as them, claims their batches, logs into the insurers with their credentials, and
writes their clients' files to its own disk. Live incident: kiko's token was
installed on a colleague's laptop, and whichever machine was powered on took the
batch — so Phoenix's green terminal (which needs the PowerTerm client, installed
only on kiko's own desktop) worked or failed depending on hardware nobody tracked.

NULL = unpinned = the previous behaviour, so this cannot lock anyone out.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
"""
from alembic import op
import sqlalchemy as sa

revision = "e7f8a9b0c1d2"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "worker_heartbeats",
        sa.Column("approved_hostname", sa.String(length=120), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("worker_heartbeats", "approved_hostname")
