"""Policy documents semantic search: doc_chunks (pgvector).

Guarded exactly like calls_04: a server without the `vector` extension skips it and
search_policies stays keyword-only, so a restart can never crash-loop on it.
Vector size = the calls embedder's default model (services/calls/embeddings.py).

Revision ID: policies_02
Revises: policies_01
"""
from alembic import op
import sqlalchemy as sa

revision = "policies_02"
down_revision = "policies_01"
branch_labels = None
depends_on = None

DIM = 384   # multilingual-e5-small


def upgrade() -> None:
    bind = op.get_bind()
    if not bind.execute(sa.text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")).scalar():
        print("policies_02: pgvector not available on this server — policy semantic search off")
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS doc_chunks (
            id BIGSERIAL PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES policy_documents(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            idx INTEGER NOT NULL,
            heading VARCHAR(300),
            text TEXT NOT NULL,
            model VARCHAR(60) NOT NULL,
            embedding vector({DIM}) NOT NULL
        )""")
    op.execute("CREATE INDEX IF NOT EXISTS ix_doc_chunks_user ON doc_chunks (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_doc_chunks_doc ON doc_chunks (document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_doc_chunks_hnsw ON doc_chunks USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS doc_chunks")
