"""client_records.track_split — a policy's balance per investment track.

The clearinghouse "מסלולי השקעה" sheet splits one policy across several tracks
(kikohib: 244 policies, ₪73.3M of ₪331M). The single `track` column held only
one of them, so a "לפי אפיק" view put the whole balance under whichever track
row came last. JSON list of {"track": name, "amount": ₪}; NULL for a policy in
one track (then `track` + `accumulation` say it all).

Revision ID: track_split_01
Revises: accum_source_01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "track_split_01"
down_revision = "accum_source_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("client_records", sa.Column("track_split", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("client_records", "track_split")
