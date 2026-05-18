"""NULL commission_expected for all menora rows (it was holding a premium).

Revision ID: s1t2u3v4w5x6
Revises: r0s1t2u3v4w5
Create Date: 2026-05-18 18:30:00.000000

Menora's "פרמיה לעמלה" column was mistakenly mapped to commission_expected
in hebrew_mappings.py. That column holds a PREMIUM (sum=₪163,447 across 815
admin rows), not an expected commission. Downstream code treated it as
commission and polluted totals (comparison_service._get_commission fallback,
the AI chat's expected-commission paragraph, reconciliation_service deviation
math).

The mapping is now removed, so new uploads won't accumulate more pollution.
This migration NULLs the bad values already in the DB for existing menora
rows. Idempotent — safe to re-run.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "s1t2u3v4w5x6"
down_revision: Union[str, Sequence[str], None] = "r0s1t2u3v4w5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE client_records cr
        SET commission_expected = NULL
        FROM file_uploads fu
        WHERE cr.upload_id = fu.id
          AND fu.format_type = 'menora'
          AND cr.commission_expected IS NOT NULL
        """
    )


def downgrade() -> None:
    # Cannot reverse — the original values are lost. Re-uploading the
    # source files (after restoring the bad mapping) is the only recovery.
    pass
