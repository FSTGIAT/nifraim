"""legacy stub — bridges historical prod revision into the current chain

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4, a0586c3abe01
Create Date: 2026-05-14 09:00:00.000000

Production was migrated to revision `j0e1f2g3h4i5` by a codebase version that
no longer exists locally — that revision had already collapsed the entire
`a0586c3abe01` branch (debts + portal_snapshots tables) and the recruits
sign-date branch into a single point. The current codebase splits them
across two branches and merges later in `k1l2m3n4o5p6`.

This stub re-creates that merge as a no-op so alembic on prod can climb
forward (k1 → m2 → …) WITHOUT trying to re-create tables that already
exist (e.g. `portal_snapshots`). Local and test envs that never saw j0 are
unaffected — alembic walks the chain backward from `p5q6r7s8t9u0` and finds
a valid path.
"""
from typing import Sequence, Union


revision: str = "j0e1f2g3h4i5"
down_revision: Union[str, Sequence[str], None] = ("i9d0e1f2g3h4", "a0586c3abe01")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
