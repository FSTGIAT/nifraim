"""users.username — unique handle for the messenger directory

Adds a NOT NULL UNIQUE `username` to `users`, backfilled from the email
local-part with collision suffixes.

The three-phase shape (nullable -> backfill -> NOT NULL) is required: the table
already has rows, so the column cannot be born NOT NULL. The de-duplication
cannot be expressed as a single UPDATE either — two users with the same email
local-part (kiko@a.co.il, kiko@b.com) must land on `kiko` and `kiko2`, which
needs a sequential scan with a running set of taken handles.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-09 00:00:00.000000
"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4a5b6c7d8e9'
down_revision: Union[str, Sequence[str], None] = 'e3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USERNAME_MAX = 32
USERNAME_MIN = 3
_STRIP_RE = re.compile(r'[^a-z0-9_]')


def _derive(email: str) -> str:
    """email local-part -> a syntactically valid (not yet unique) handle."""
    local = (email or '').split('@')[0].lower()
    base = _STRIP_RE.sub('', local)
    if len(base) < USERNAME_MIN:
        # 'a@x.com' or an all-punctuation local-part still needs a legal handle.
        base = f'user{base}'
    return base[:USERNAME_MAX]


def _dedupe(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    n = 2
    while True:
        suffix = str(n)
        candidate = f'{base[:USERNAME_MAX - len(suffix)]}{suffix}'
        if candidate not in taken:
            return candidate
        n += 1


def upgrade() -> None:
    op.add_column('users', sa.Column('username', sa.String(USERNAME_MAX), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(
        sa.text('SELECT id, email FROM users ORDER BY created_at NULLS FIRST, id')
    ).fetchall()

    taken: set[str] = set()
    for row in rows:
        handle = _dedupe(_derive(row.email), taken)
        taken.add(handle)
        conn.execute(
            sa.text('UPDATE users SET username = :u WHERE id = :i'),
            {'u': handle, 'i': row.id},
        )

    op.alter_column('users', 'username', nullable=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_check_constraint(
        'ck_users_username_format', 'users', r"username ~ '^[a-z0-9_]{3,32}$'"
    )


def downgrade() -> None:
    op.drop_constraint('ck_users_username_format', 'users', type_='check')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'username')
