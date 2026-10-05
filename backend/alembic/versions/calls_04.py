"""Calls semantic search: pgvector + call_chunks (passages + embeddings).

Guarded: only when the server offers the `vector` extension (Railway prod PG17 has 0.8.6;
local docker postgres:16-alpine needs it compiled in — see ARCHITECTURE §18). Without it
the migration is a no-op and search_calls stays keyword-only, so a restart can never
crash-loop on it. Vector size = the default model's (services/calls/embeddings.py).

Revision ID: calls_04
Revises: calls_03
"""
from alembic import op
import sqlalchemy as sa

revision = "calls_04"
down_revision = "calls_03"
branch_labels = None
depends_on = None

DIM = 384   # multilingual-e5-small


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")).scalar():
        print("calls_04: pgvector not available on this server — semantic search off")
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS call_chunks (
            id BIGSERIAL PRIMARY KEY,
            call_id UUID NOT NULL REFERENCES call_recordings(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            idx INTEGER NOT NULL,
            kind VARCHAR(12) NOT NULL,
            start_s REAL, end_s REAL,
            role VARCHAR(12),
            text TEXT NOT NULL,
            model VARCHAR(60) NOT NULL,
            embedding vector({DIM}) NOT NULL
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_call_chunks_user ON call_chunks (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_call_chunks_call ON call_chunks (call_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_call_chunks_hnsw ON call_chunks USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS call_chunks")
