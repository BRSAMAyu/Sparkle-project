"""persona v3.1 core models

Revision ID: p10_persona_v31
Revises: p10_add_cognitive_tags
Create Date: 2026-01-08 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.models.base import GUID
from app.utils.migration_helpers import column_exists, get_inspector, index_exists, table_exists

# revision identifiers, used by Alembic.
revision = 'p10_persona_v31'
down_revision = 'p10_add_cognitive_tags'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    json_type = postgresql.JSONB() if bind.dialect.name == "postgresql" else sa.JSON()
    inspector = get_inspector()

    if table_exists(inspector, "user_node_status"):
        if not column_exists(inspector, "user_node_status", "bkt_mastery_prob"):
            op.add_column('user_node_status', sa.Column('bkt_mastery_prob', sa.Float(), nullable=False, server_default='0'))
        if not column_exists(inspector, "user_node_status", "bkt_last_updated_at"):
            op.add_column('user_node_status', sa.Column('bkt_last_updated_at', sa.DateTime(), nullable=True))

    if table_exists(inspector, "cognitive_fragments"):
        if not column_exists(inspector, "cognitive_fragments", "persona_version"):
            op.add_column('cognitive_fragments', sa.Column('persona_version', sa.String(length=50), nullable=True))
        if not column_exists(inspector, "cognitive_fragments", "source_event_id"):
            op.add_column('cognitive_fragments', sa.Column('source_event_id', sa.String(length=64), nullable=True))
        if not column_exists(inspector, "cognitive_fragments", "sensitive_tags_encrypted"):
            op.add_column('cognitive_fragments', sa.Column('sensitive_tags_encrypted', sa.Text(), nullable=True))
        if not column_exists(inspector, "cognitive_fragments", "sensitive_tags_version"):
            op.add_column('cognitive_fragments', sa.Column('sensitive_tags_version', sa.Integer(), nullable=True))
        if not column_exists(inspector, "cognitive_fragments", "sensitive_tags_key_id"):
            op.add_column('cognitive_fragments', sa.Column('sensitive_tags_key_id', sa.String(length=100), nullable=True))
        if not index_exists(inspector, "cognitive_fragments", "idx_cognitive_fragments_source_event_id"):
            op.create_index('idx_cognitive_fragments_source_event_id', 'cognitive_fragments', ['source_event_id'], unique=False)

    if table_exists(inspector, "users"):
        if not column_exists(inspector, "users", "is_minor"):
            op.add_column('users', sa.Column('is_minor', sa.Boolean(), nullable=True))
        if not column_exists(inspector, "users", "age_verified"):
            op.add_column('users', sa.Column('age_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
        if not column_exists(inspector, "users", "age_verification_source"):
            op.add_column('users', sa.Column('age_verification_source', sa.String(length=50), nullable=True))
        if not column_exists(inspector, "users", "age_verified_at"):
            op.add_column('users', sa.Column('age_verified_at', sa.DateTime(), nullable=True))

    if not table_exists(inspector, "legal_holds"):
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
    if not index_exists(inspector, "legal_holds", "idx_legal_holds_user"):
        op.create_index('idx_legal_holds_user', 'legal_holds', ['user_id'], unique=False)
    if not index_exists(inspector, "legal_holds", "idx_legal_holds_device"):
        op.create_index('idx_legal_holds_device', 'legal_holds', ['device_id'], unique=False)
    if not index_exists(inspector, "legal_holds", "idx_legal_holds_case"):
        op.create_index('idx_legal_holds_case', 'legal_holds', ['case_ref'], unique=False)

    if not table_exists(inspector, "user_persona_keys"):
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
    if not index_exists(inspector, "user_persona_keys", "idx_user_persona_keys_user"):
        op.create_index('idx_user_persona_keys_user', 'user_persona_keys', ['user_id'], unique=False)
    if not index_exists(inspector, "user_persona_keys", "idx_user_persona_keys_key"):
        op.create_index('idx_user_persona_keys_key', 'user_persona_keys', ['key_id'], unique=False)

    if not table_exists(inspector, "crypto_shredding_certificates"):
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
    if not index_exists(inspector, "crypto_shredding_certificates", "idx_crypto_shredding_certificates_user"):
        op.create_index('idx_crypto_shredding_certificates_user', 'crypto_shredding_certificates', ['user_id'], unique=False)

    if not table_exists(inspector, "dlq_replay_audit_logs"):
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
    if not index_exists(inspector, "dlq_replay_audit_logs", "idx_dlq_replay_message"):
        op.create_index('idx_dlq_replay_message', 'dlq_replay_audit_logs', ['message_id'], unique=False)

    if not table_exists(inspector, "persona_snapshots"):
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
    if not index_exists(inspector, "persona_snapshots", "idx_persona_snapshots_user"):
        op.create_index('idx_persona_snapshots_user', 'persona_snapshots', ['user_id'], unique=False)
    if not index_exists(inspector, "persona_snapshots", "idx_persona_snapshots_version"):
        op.create_index('idx_persona_snapshots_version', 'persona_snapshots', ['persona_version'], unique=False)

    if not table_exists(inspector, "irt_item_parameters"):
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
    if not index_exists(inspector, "irt_item_parameters", "idx_irt_item_question"):
        op.create_index('idx_irt_item_question', 'irt_item_parameters', ['question_id'], unique=False)
    if not index_exists(inspector, "irt_item_parameters", "idx_irt_item_subject"):
        op.create_index('idx_irt_item_subject', 'irt_item_parameters', ['subject_id'], unique=False)

    if not table_exists(inspector, "user_irt_ability"):
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
    if not index_exists(inspector, "user_irt_ability", "idx_user_irt_user"):
        op.create_index('idx_user_irt_user', 'user_irt_ability', ['user_id'], unique=False)
    if not index_exists(inspector, "user_irt_ability", "idx_user_irt_subject"):
        op.create_index('idx_user_irt_subject', 'user_irt_ability', ['subject_id'], unique=False)


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "user_irt_ability"):
        if index_exists(inspector, "user_irt_ability", "idx_user_irt_subject"):
            op.drop_index('idx_user_irt_subject', table_name='user_irt_ability')
        if index_exists(inspector, "user_irt_ability", "idx_user_irt_user"):
            op.drop_index('idx_user_irt_user', table_name='user_irt_ability')
        op.drop_table('user_irt_ability')

    if table_exists(inspector, "irt_item_parameters"):
        if index_exists(inspector, "irt_item_parameters", "idx_irt_item_subject"):
            op.drop_index('idx_irt_item_subject', table_name='irt_item_parameters')
        if index_exists(inspector, "irt_item_parameters", "idx_irt_item_question"):
            op.drop_index('idx_irt_item_question', table_name='irt_item_parameters')
        op.drop_table('irt_item_parameters')

    if table_exists(inspector, "persona_snapshots"):
        if index_exists(inspector, "persona_snapshots", "idx_persona_snapshots_version"):
            op.drop_index('idx_persona_snapshots_version', table_name='persona_snapshots')
        if index_exists(inspector, "persona_snapshots", "idx_persona_snapshots_user"):
            op.drop_index('idx_persona_snapshots_user', table_name='persona_snapshots')
        op.drop_table('persona_snapshots')

    if table_exists(inspector, "dlq_replay_audit_logs"):
        if index_exists(inspector, "dlq_replay_audit_logs", "idx_dlq_replay_message"):
            op.drop_index('idx_dlq_replay_message', table_name='dlq_replay_audit_logs')
        op.drop_table('dlq_replay_audit_logs')

    if table_exists(inspector, "crypto_shredding_certificates"):
        if index_exists(inspector, "crypto_shredding_certificates", "idx_crypto_shredding_certificates_user"):
            op.drop_index('idx_crypto_shredding_certificates_user', table_name='crypto_shredding_certificates')
        op.drop_table('crypto_shredding_certificates')

    if table_exists(inspector, "user_persona_keys"):
        if index_exists(inspector, "user_persona_keys", "idx_user_persona_keys_key"):
            op.drop_index('idx_user_persona_keys_key', table_name='user_persona_keys')
        if index_exists(inspector, "user_persona_keys", "idx_user_persona_keys_user"):
            op.drop_index('idx_user_persona_keys_user', table_name='user_persona_keys')
        op.drop_table('user_persona_keys')

    if table_exists(inspector, "legal_holds"):
        if index_exists(inspector, "legal_holds", "idx_legal_holds_case"):
            op.drop_index('idx_legal_holds_case', table_name='legal_holds')
        if index_exists(inspector, "legal_holds", "idx_legal_holds_device"):
            op.drop_index('idx_legal_holds_device', table_name='legal_holds')
        if index_exists(inspector, "legal_holds", "idx_legal_holds_user"):
            op.drop_index('idx_legal_holds_user', table_name='legal_holds')
        op.drop_table('legal_holds')

    if table_exists(inspector, "users"):
        if column_exists(inspector, "users", "age_verified_at"):
            op.drop_column('users', 'age_verified_at')
        if column_exists(inspector, "users", "age_verification_source"):
            op.drop_column('users', 'age_verification_source')
        if column_exists(inspector, "users", "age_verified"):
            op.drop_column('users', 'age_verified')
        if column_exists(inspector, "users", "is_minor"):
            op.drop_column('users', 'is_minor')

    if table_exists(inspector, "cognitive_fragments"):
        if index_exists(inspector, "cognitive_fragments", "idx_cognitive_fragments_source_event_id"):
            op.drop_index('idx_cognitive_fragments_source_event_id', table_name='cognitive_fragments')
        if column_exists(inspector, "cognitive_fragments", "sensitive_tags_key_id"):
            op.drop_column('cognitive_fragments', 'sensitive_tags_key_id')
        if column_exists(inspector, "cognitive_fragments", "sensitive_tags_version"):
            op.drop_column('cognitive_fragments', 'sensitive_tags_version')
        if column_exists(inspector, "cognitive_fragments", "sensitive_tags_encrypted"):
            op.drop_column('cognitive_fragments', 'sensitive_tags_encrypted')
        if column_exists(inspector, "cognitive_fragments", "source_event_id"):
            op.drop_column('cognitive_fragments', 'source_event_id')
        if column_exists(inspector, "cognitive_fragments", "persona_version"):
            op.drop_column('cognitive_fragments', 'persona_version')

    if table_exists(inspector, "user_node_status"):
        if column_exists(inspector, "user_node_status", "bkt_last_updated_at"):
            op.drop_column('user_node_status', 'bkt_last_updated_at')
        if column_exists(inspector, "user_node_status", "bkt_mastery_prob"):
            op.drop_column('user_node_status', 'bkt_mastery_prob')
