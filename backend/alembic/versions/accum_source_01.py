"""client_records.accumulation_source — where a production row's צבירה came from.

NULL = the production file itself. 'nifraim' = the file reported ₪0 and the same
company's נפרעים for the same period reported a balance on the same policy
number (services/accumulation_backfill.py). Kept so the fill is visible in the
UI and reversible.

Revision ID: accum_source_01
Revises: test_user_02
"""
from alembic import op
import sqlalchemy as sa

revision = "accum_source_01"
down_revision = "test_user_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("client_records", sa.Column("accumulation_source", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("client_records", "accumulation_source")
