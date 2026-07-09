"""Username handles — the messenger's search key.

`users.username` is NOT NULL UNIQUE, so every path that creates a User must
supply one. Registration lets the user choose; admin-created accounts and the
migration backfill derive one from the email local-part.

Keep `_derive`/`_dedupe` in sync with the same helpers in the migration
`f4a5b6c7d8e9_users_username.py` — that copy is frozen at its revision and must
not import from here (a migration that imports live app code breaks the moment
that code changes).
"""
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

USERNAME_MAX = 32
USERNAME_MIN = 3

# Lowercase-only, so `@Kiko` and `@kiko` cannot coexist and impersonate each other.
USERNAME_RE = re.compile(r'^[a-z0-9_]{3,32}$')
_STRIP_RE = re.compile(r'[^a-z0-9_]')


def normalize_username(raw: str) -> str:
    return (raw or '').strip().lstrip('@').lower()


def is_valid_username(raw: str) -> bool:
    return bool(USERNAME_RE.match(raw or ''))


def _derive(email: str) -> str:
    local = (email or '').split('@')[0].lower()
    base = _STRIP_RE.sub('', local)
    if len(base) < USERNAME_MIN:
        base = f'user{base}'
    return base[:USERNAME_MAX]


async def _is_taken(db: AsyncSession, handle: str) -> bool:
    result = await db.execute(select(User.id).where(User.username == handle))
    return result.first() is not None


async def generate_unique_username(db: AsyncSession, email: str) -> str:
    """Derive a free handle from an email. Used by admin-create and as a fallback.

    Racy by nature — two concurrent signups can both see `kiko` as free. The
    unique index is the real guard; callers must catch IntegrityError and retry.
    """
    base = _derive(email)
    if not await _is_taken(db, base):
        return base

    n = 2
    while True:
        suffix = str(n)
        candidate = f'{base[:USERNAME_MAX - len(suffix)]}{suffix}'
        if not await _is_taken(db, candidate):
            return candidate
        n += 1
