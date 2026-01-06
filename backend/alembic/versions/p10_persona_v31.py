"""persona v3.1 core models

Revision ID: p10_persona_v31
Revises: p10_add_cognitive_tags
Create Date: 2026-01-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.models.base import GUID

# revision identifiers, used by Alembic.
revision = 'p10_persona_v31'
down_revision = 'p10_add_cognitive_tags'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    json_type = postgresql.JSONB() if bind.dialect.name == "postgresql" else sa.JSON()

    op.add_column('user_node_status', sa.Column('bkt_mastery_prob', sa.Float(), nullable=False, server_default='0'))
    op.add_column('user_node_status', sa.Column('bkt_last_updated_at', sa.DateTime(), nullable=True))

    op.add_column('cognitive_fragments', sa.Column('persona_version', sa.String(length=50), nullable=True))
    op.add_column('cognitive_fragments', sa.Column('source_event_id', sa.String(length=64), nullable=True))
    op.add_column('cognitive_fragments', sa.Column('sensitive_tags_encrypted', sa.Text(), nullable=True))
    op.add_column('cognitive_fragments', sa.Column('sensitive_tags_version', sa.Integer(), nullable=True))
    op.add_column('cognitive_fragments', sa.Column('sensitive_tags_key_id', sa.String(length=100), nullable=True))
    op.create_index('idx_cognitive_fragments_source_event_id', 'cognitive_fragments', ['source_event_id'], unique=False)

    op.add_column('users', sa.Column('is_minor', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('age_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('age_verification_source', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('age_verified_at', sa.DateTime(), nullable=True))

    op.create_table(
        'legal_holds',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=True),
        sa.Column('device_id', sa.String(length=128), nullable=True),
        sa.Column('case_ref', sa.String(length=120), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('admin_id', GUID(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('released_at', sa.DateTime(), nullable=True),
        sa.Column('released_by', GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id']),
        sa.ForeignKeyConstraint(['released_by'], ['users.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_legal_holds_user', 'legal_holds', ['user_id'], unique=False)
    op.create_index('idx_legal_holds_device', 'legal_holds', ['device_id'], unique=False)
    op.create_index('idx_legal_holds_case', 'legal_holds', ['case_ref'], unique=False)

    op.create_table(
        'user_persona_keys',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('key_id', sa.String(length=128), nullable=False),
        sa.Column('encrypted_key', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('destroyed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_persona_keys_user', 'user_persona_keys', ['user_id'], unique=False)
    op.create_index('idx_user_persona_keys_key', 'user_persona_keys', ['key_id'], unique=False)

    op.create_table(
        'crypto_shredding_certificates',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('key_id', sa.String(length=128), nullable=False),
        sa.Column('destruction_time', sa.DateTime(), nullable=False),
        sa.Column('cloud_provider_ack', sa.Text(), nullable=True),
        sa.Column('certificate_data', json_type, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crypto_shredding_certificates_user', 'crypto_shredding_certificates', ['user_id'], unique=False)

    op.create_table(
        'dlq_replay_audit_logs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('message_id', sa.String(length=128), nullable=False),
        sa.Column('admin_id', GUID(), nullable=False),
        sa.Column('approver_id', GUID(), nullable=False),
        sa.Column('reason_code', sa.String(length=64), nullable=False),
        sa.Column('payload_hash', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id']),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_dlq_replay_message', 'dlq_replay_audit_logs', ['message_id'], unique=False)

    op.create_table(
        'persona_snapshots',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('persona_version', sa.String(length=50), nullable=False),
        sa.Column('audit_token', sa.String(length=128), nullable=True),
        sa.Column('source_event_id', sa.String(length=64), nullable=True),
        sa.Column('snapshot_data', json_type, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_persona_snapshots_user', 'persona_snapshots', ['user_id'], unique=False)
    op.create_index('idx_persona_snapshots_version', 'persona_snapshots', ['persona_version'], unique=False)

    op.create_table(
        'irt_item_parameters',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('question_id', GUID(), nullable=False),
        sa.Column('subject_id', sa.String(length=32), nullable=True),
        sa.Column('a', sa.Float(), nullable=False, server_default='1'),
        sa.Column('b', sa.Float(), nullable=False, server_default='0'),
        sa.Column('c', sa.Float(), nullable=False, server_default='0.2'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_irt_item_question', 'irt_item_parameters', ['question_id'], unique=False)
    op.create_index('idx_irt_item_subject', 'irt_item_parameters', ['subject_id'], unique=False)

    op.create_table(
        'user_irt_ability',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('subject_id', sa.String(length=32), nullable=True),
        sa.Column('theta', sa.Float(), nullable=False, server_default='0'),
        sa.Column('last_updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_irt_user', 'user_irt_ability', ['user_id'], unique=False)
    op.create_index('idx_user_irt_subject', 'user_irt_ability', ['subject_id'], unique=False)


def downgrade():
    op.drop_index('idx_user_irt_subject', table_name='user_irt_ability')
    op.drop_index('idx_user_irt_user', table_name='user_irt_ability')
    op.drop_table('user_irt_ability')

    op.drop_index('idx_irt_item_subject', table_name='irt_item_parameters')
    op.drop_index('idx_irt_item_question', table_name='irt_item_parameters')
    op.drop_table('irt_item_parameters')

    op.drop_index('idx_persona_snapshots_version', table_name='persona_snapshots')
    op.drop_index('idx_persona_snapshots_user', table_name='persona_snapshots')
    op.drop_table('persona_snapshots')

    op.drop_index('idx_dlq_replay_message', table_name='dlq_replay_audit_logs')
    op.drop_table('dlq_replay_audit_logs')

    op.drop_index('idx_crypto_shredding_certificates_user', table_name='crypto_shredding_certificates')
    op.drop_table('crypto_shredding_certificates')

    op.drop_index('idx_user_persona_keys_key', table_name='user_persona_keys')
    op.drop_index('idx_user_persona_keys_user', table_name='user_persona_keys')
    op.drop_table('user_persona_keys')

    op.drop_index('idx_legal_holds_case', table_name='legal_holds')
    op.drop_index('idx_legal_holds_device', table_name='legal_holds')
    op.drop_index('idx_legal_holds_user', table_name='legal_holds')
    op.drop_table('legal_holds')

    op.drop_column('users', 'age_verified_at')
    op.drop_column('users', 'age_verification_source')
    op.drop_column('users', 'age_verified')
    op.drop_column('users', 'is_minor')

    op.drop_index('idx_cognitive_fragments_source_event_id', table_name='cognitive_fragments')
    op.drop_column('cognitive_fragments', 'sensitive_tags_key_id')
    op.drop_column('cognitive_fragments', 'sensitive_tags_version')
    op.drop_column('cognitive_fragments', 'sensitive_tags_encrypted')
    op.drop_column('cognitive_fragments', 'source_event_id')
    op.drop_column('cognitive_fragments', 'persona_version')

    op.drop_column('user_node_status', 'bkt_last_updated_at')
    op.drop_column('user_node_status', 'bkt_mastery_prob')
