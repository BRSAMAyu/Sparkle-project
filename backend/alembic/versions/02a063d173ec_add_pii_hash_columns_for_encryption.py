"""add_pii_hash_columns_for_encryption

Revision ID: 02a063d173ec
Revises: wp19_20260507
Create Date: 2026-05-07 20:45:12.078758

Add SHA-256 hash columns for sensitive PII fields to enable deterministic lookups
after the fields are encrypted at the application layer (AES-256-GCM / Fernet).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT username_hash, email_hash, google_id_hash, apple_id_hash, wechat_unionid_hash FROM users LIMIT 1;"
#   backfill_plan: "python scripts/backfill_pii_hashes.py"
#   owner: "security"
#   ticket: "P1-1"

revision: str = '02a063d173ec'
down_revision: Union[str, None] = 'wp19_20260507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users table: add hash columns for PII fields ──
    op.add_column('users', sa.Column('username_hash', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('email_hash', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('google_id_hash', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('apple_id_hash', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('wechat_unionid_hash', sa.String(64), nullable=True))

    op.create_index('ix_users_username_hash', 'users', ['username_hash'])
    op.create_index('ix_users_email_hash', 'users', ['email_hash'])
    op.create_index('ix_users_google_id_hash', 'users', ['google_id_hash'])
    op.create_index('ix_users_apple_id_hash', 'users', ['apple_id_hash'])
    op.create_index('ix_users_wechat_unionid_hash', 'users', ['wechat_unionid_hash'])

    # Widen encrypted columns to accommodate Fernet tokens (~170-230 bytes for typical values)
    op.alter_column('users', 'google_id', type_=sa.String(512), existing_type=sa.String(255))
    op.alter_column('users', 'apple_id', type_=sa.String(512), existing_type=sa.String(255))
    op.alter_column('users', 'wechat_unionid', type_=sa.String(512), existing_type=sa.String(255))

    # ── user_devices table: add hash column for push_token ──
    op.add_column('user_devices', sa.Column('push_token_hash', sa.String(64), nullable=True))
    op.create_index('ix_user_devices_push_token_hash', 'user_devices', ['push_token_hash'])
    op.alter_column('user_devices', 'push_token', type_=sa.String(1024), existing_type=sa.String(500))


def downgrade() -> None:
    # ── user_devices: revert ──
    op.alter_column('user_devices', 'push_token', type_=sa.String(500), existing_type=sa.String(1024))
    op.drop_index('ix_user_devices_push_token_hash', table_name='user_devices')
    op.drop_column('user_devices', 'push_token_hash')

    # ── users: revert ──
    op.alter_column('users', 'wechat_unionid', type_=sa.String(255), existing_type=sa.String(512))
    op.alter_column('users', 'apple_id', type_=sa.String(255), existing_type=sa.String(512))
    op.alter_column('users', 'google_id', type_=sa.String(255), existing_type=sa.String(512))

    op.drop_index('ix_users_wechat_unionid_hash', table_name='users')
    op.drop_index('ix_users_apple_id_hash', table_name='users')
    op.drop_index('ix_users_google_id_hash', table_name='users')
    op.drop_index('ix_users_email_hash', table_name='users')
    op.drop_index('ix_users_username_hash', table_name='users')

    op.drop_column('users', 'wechat_unionid_hash')
    op.drop_column('users', 'apple_id_hash')
    op.drop_column('users', 'google_id_hash')
    op.drop_column('users', 'email_hash')
    op.drop_column('users', 'username_hash')
