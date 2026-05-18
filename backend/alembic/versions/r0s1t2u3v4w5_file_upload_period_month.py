"""file_uploads.period_month — first-of-month for the data described.

Revision ID: r0s1t2u3v4w5
Revises: q9r0s1t2u3v4
Create Date: 2026-05-18 14:30:00.000000

Today APR vs MAR pairing is inferred from filenames inside the parser.
That's fragile — re-uploaded files keep the wrong filename, and Mimshak
ZIP exports have no month in their name at all. period_month is detected
once at upload time from filename → data_date → uploaded_at fallback, then
trusted by the production-compare endpoint instead of re-deriving from
filename strings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "r0s1t2u3v4w5"
down_revision: Union[str, Sequence[str], None] = "q9r0s1t2u3v4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "file_uploads",
        sa.Column("period_month", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_file_uploads_period_month",
        "file_uploads",
        ["user_id", "file_category", "period_month"],
    )


def downgrade() -> None:
    op.drop_index("ix_file_uploads_period_month", table_name="file_uploads")
    op.drop_column("file_uploads", "period_month")
