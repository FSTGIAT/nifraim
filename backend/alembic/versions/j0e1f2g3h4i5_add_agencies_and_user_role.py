"""add agencies, agency_invites + role/agency_id on users

Revision ID: j0e1f2g3h4i5
Revises: a0586c3abe01, i9d0e1f2g3h4
Create Date: 2026-04-25 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "j0e1f2g3h4i5"
# Merges the two outstanding heads into one chain.
down_revision: Union[str, Sequence[str], None] = ("a0586c3abe01", "i9d0e1f2g3h4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agencies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("owner_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_agencies_slug", "agencies", ["slug"], unique=True)

    op.create_table(
        "agency_invites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agency_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=96), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False, server_default="agent"),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column("accepted_user_id", sa.UUID(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["agency_id"], ["agencies.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["accepted_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_agency_invites_token", "agency_invites", ["token"], unique=True)
    op.create_index("ix_agency_invites_email", "agency_invites", ["email"], unique=False)
    op.create_index("ix_agency_invites_agency_id", "agency_invites", ["agency_id"], unique=False)

    op.add_column(
        "users",
        sa.Column("role", sa.String(length=40), nullable=False, server_default="agent"),
    )
    op.add_column(
        "users",
        sa.Column("agency_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_agency_id",
        "users",
        "agencies",
        ["agency_id"],
        ["id"],
    )
    op.create_index("ix_users_agency_id", "users", ["agency_id"], unique=False)
    # Backfill: every existing user keeps role='agent' (server_default takes care of inserts).
    op.execute("UPDATE users SET role = 'agent' WHERE role IS NULL")


def downgrade() -> None:
    op.drop_index("ix_users_agency_id", table_name="users")
    op.drop_constraint("fk_users_agency_id", "users", type_="foreignkey")
    op.drop_column("users", "agency_id")
    op.drop_column("users", "role")

    op.drop_index("ix_agency_invites_agency_id", table_name="agency_invites")
    op.drop_index("ix_agency_invites_email", table_name="agency_invites")
    op.drop_index("ix_agency_invites_token", table_name="agency_invites")
    op.drop_table("agency_invites")

    op.drop_index("ix_agencies_slug", table_name="agencies")
    op.drop_table("agencies")
