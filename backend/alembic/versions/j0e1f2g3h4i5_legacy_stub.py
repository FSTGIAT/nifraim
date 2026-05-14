"""legacy stub — bridges historical prod revision into the current chain

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-05-14 09:00:00.000000

Production was migrated to revision `j0e1f2g3h4i5` by a codebase version that
no longer exists locally. This empty migration restores the link so alembic
can continue forward without `Can't locate revision identified by` errors.
Whatever schema change j0 originally applied is already present in prod; in
local/test envs that never saw j0, a no-op upgrade is correct.
"""
from typing import Sequence, Union


revision: str = "j0e1f2g3h4i5"
down_revision: Union[str, Sequence[str], None] = "i9d0e1f2g3h4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
