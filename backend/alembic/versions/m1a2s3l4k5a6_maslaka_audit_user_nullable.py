"""maslaka: pension_audit_logs.user_id nullable (system-poll errors have no user)

The system-wide poll (`poll_and_ingest(user_id=None)`) can fail on an inbound
file before it has been matched to an inquiry — so there is no user to attribute
the error to. The code used to pass `uuid.UUID(int=0)`, which violates the
`users.id` FK: the audit insert fails and the failed flush poisons the session.
Make the column nullable and let the audit row record "system, no user".

Revision ID: m1a2s3l4k5a6
Revises: e7f8a9b0c1d2
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'm1a2s3l4k5a6'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'pension_audit_logs',
        'user_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Rows written by the system poll have a NULL user and cannot be given one
    # back — drop them rather than fail the NOT NULL re-add.
    op.execute("DELETE FROM pension_audit_logs WHERE user_id IS NULL")
    op.alter_column(
        'pension_audit_logs',
        'user_id',
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
