"""messenger: dm_conversations, dm_messages, dm_presence

Revision ID: d7e8f9a0b1c2
Revises: f4a5b6c7d8e9
Create Date: 2026-07-09 00:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'd7e8f9a0b1c2'
down_revision: Union[str, Sequence[str], None] = 'f4a5b6c7d8e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dm_conversations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_a_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_b_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('last_message_preview', sa.String(140), nullable=True),
        sa.Column('last_sender_id', UUID(as_uuid=True), nullable=True),
        sa.Column('a_unread_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('b_unread_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('a_last_read_at', sa.DateTime(), nullable=True),
        sa.Column('b_last_read_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    # The ordered-pair invariant (user_a_id = min(uuid)) makes this unique index
    # collapse (a,b) and (b,a) onto one row.
    op.create_index('ix_dm_conv_pair', 'dm_conversations', ['user_a_id', 'user_b_id'], unique=True)
    op.create_index('ix_dm_conversations_user_a_id', 'dm_conversations', ['user_a_id'])
    op.create_index('ix_dm_conversations_user_b_id', 'dm_conversations', ['user_b_id'])
    op.create_index('ix_dm_conversations_last_message_at', 'dm_conversations', ['last_message_at'])

    op.create_table(
        'dm_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('seq', sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('dm_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('recipient_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_dm_messages_seq', 'dm_messages', ['seq'], unique=True)
    op.create_index('ix_dm_msg_conv_seq', 'dm_messages', ['conversation_id', 'seq'])
    op.create_index('ix_dm_msg_recipient_seq', 'dm_messages', ['recipient_id', 'seq'])
    op.create_index('ix_dm_msg_sender_created', 'dm_messages', ['sender_id', 'created_at'])

    op.create_table(
        'dm_presence',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_dm_presence_user_id', 'dm_presence', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_dm_presence_user_id', table_name='dm_presence')
    op.drop_table('dm_presence')

    for ix in ('ix_dm_msg_sender_created', 'ix_dm_msg_recipient_seq', 'ix_dm_msg_conv_seq', 'ix_dm_messages_seq'):
        op.drop_index(ix, table_name='dm_messages')
    op.drop_table('dm_messages')

    for ix in ('ix_dm_conversations_last_message_at', 'ix_dm_conversations_user_b_id',
               'ix_dm_conversations_user_a_id', 'ix_dm_conv_pair'):
        op.drop_index(ix, table_name='dm_conversations')
    op.drop_table('dm_conversations')
