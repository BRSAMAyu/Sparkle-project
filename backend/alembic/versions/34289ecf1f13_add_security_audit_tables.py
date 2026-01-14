"""add_security_audit_tables

Revision ID: 34289ecf1f13
Revises: 087653ac70dd
Create Date: 2026-01-04 09:59:55.625538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.utils.migration_helpers import get_inspector, index_exists, table_exists


# revision identifiers, used by Alembic.
revision: str = '34289ecf1f13'
down_revision: Union[str, None] = '087653ac70dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()
    # 创建登录尝试表
    if not table_exists(inspector, "login_attempts"):
        op.create_table(
            'login_attempts',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=True),
            sa.Column('username', sa.String(length=100), nullable=False),
            sa.Column('ip_address', sa.String(length=45), nullable=False),
            sa.Column('user_agent', sa.String(length=500), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False),
            sa.Column('attempted_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # 创建安全审计日志表
    if not table_exists(inspector, "security_audit_logs"):
        op.create_table(
            'security_audit_logs',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('threat_level', sa.String(length=20), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=True),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('resource', sa.String(length=500), nullable=True),
            sa.Column('action', sa.String(length=100), nullable=True),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('timestamp', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # 创建数据访问日志表
    if not table_exists(inspector, "data_access_logs"):
        op.create_table(
            'data_access_logs',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('resource_type', sa.String(length=100), nullable=False),
            sa.Column('resource_id', sa.String(length=100), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('request_method', sa.String(length=10), nullable=True),
            sa.Column('request_path', sa.String(length=500), nullable=True),
            sa.Column('request_params', sa.JSON(), nullable=True),
            sa.Column('response_status', sa.String(length=10), nullable=True),
            sa.Column('accessed_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # 创建系统配置变更日志表
    if not table_exists(inspector, "system_config_change_logs"):
        op.create_table(
            'system_config_change_logs',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('config_key', sa.String(length=200), nullable=False),
            sa.Column('old_value', sa.JSON(), nullable=True),
            sa.Column('new_value', sa.JSON(), nullable=False),
            sa.Column('change_type', sa.String(length=50), nullable=False),
            sa.Column('changed_by', sa.UUID(), nullable=False),
            sa.Column('ip_address', sa.String(length=45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('impact_level', sa.String(length=20), nullable=True),
            sa.Column('changed_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['changed_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # 创建合规性检查日志表
    if not table_exists(inspector, "compliance_check_logs"):
        op.create_table(
            'compliance_check_logs',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('check_type', sa.String(length=100), nullable=False),
            sa.Column('check_name', sa.String(length=200), nullable=False),
            sa.Column('standard', sa.String(length=100), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('findings', sa.JSON(), nullable=True),
            sa.Column('executed_by', sa.UUID(), nullable=True),
            sa.Column('automated', sa.String(length=10), nullable=False),
            sa.Column('executed_at', sa.DateTime(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['executed_by'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )

    # 创建索引
    if not index_exists(inspector, "login_attempts", "idx_login_attempts_user_id"):
        op.create_index('idx_login_attempts_user_id', 'login_attempts', ['user_id'])
    if not index_exists(inspector, "login_attempts", "idx_login_attempts_username"):
        op.create_index('idx_login_attempts_username', 'login_attempts', ['username'])
    if not index_exists(inspector, "login_attempts", "idx_login_attempts_ip"):
        op.create_index('idx_login_attempts_ip', 'login_attempts', ['ip_address'])
    if not index_exists(inspector, "login_attempts", "idx_login_attempts_success"):
        op.create_index('idx_login_attempts_success', 'login_attempts', ['success'])
    if not index_exists(inspector, "login_attempts", "idx_login_attempts_attempted_at"):
        op.create_index('idx_login_attempts_attempted_at', 'login_attempts', ['attempted_at'])

    if not index_exists(inspector, "security_audit_logs", "idx_security_audit_event_type"):
        op.create_index('idx_security_audit_event_type', 'security_audit_logs', ['event_type'])
    if not index_exists(inspector, "security_audit_logs", "idx_security_audit_threat_level"):
        op.create_index('idx_security_audit_threat_level', 'security_audit_logs', ['threat_level'])
    if not index_exists(inspector, "security_audit_logs", "idx_security_audit_user_id"):
        op.create_index('idx_security_audit_user_id', 'security_audit_logs', ['user_id'])
    if not index_exists(inspector, "security_audit_logs", "idx_security_audit_ip"):
        op.create_index('idx_security_audit_ip', 'security_audit_logs', ['ip_address'])
    if not index_exists(inspector, "security_audit_logs", "idx_security_audit_resource"):
        op.create_index('idx_security_audit_resource', 'security_audit_logs', ['resource'])
    if not index_exists(inspector, "security_audit_logs", "idx_security_audit_timestamp"):
        op.create_index('idx_security_audit_timestamp', 'security_audit_logs', ['timestamp'])

    if not index_exists(inspector, "data_access_logs", "idx_data_access_user_id"):
        op.create_index('idx_data_access_user_id', 'data_access_logs', ['user_id'])
    if not index_exists(inspector, "data_access_logs", "idx_data_access_ip"):
        op.create_index('idx_data_access_ip', 'data_access_logs', ['ip_address'])
    if not index_exists(inspector, "data_access_logs", "idx_data_access_resource_type"):
        op.create_index('idx_data_access_resource_type', 'data_access_logs', ['resource_type'])
    if not index_exists(inspector, "data_access_logs", "idx_data_access_resource_id"):
        op.create_index('idx_data_access_resource_id', 'data_access_logs', ['resource_id'])
    if not index_exists(inspector, "data_access_logs", "idx_data_access_action"):
        op.create_index('idx_data_access_action', 'data_access_logs', ['action'])
    if not index_exists(inspector, "data_access_logs", "idx_data_access_accessed_at"):
        op.create_index('idx_data_access_accessed_at', 'data_access_logs', ['accessed_at'])

    if not index_exists(inspector, "system_config_change_logs", "idx_config_change_config_key"):
        op.create_index('idx_config_change_config_key', 'system_config_change_logs', ['config_key'])
    if not index_exists(inspector, "system_config_change_logs", "idx_config_change_changed_by"):
        op.create_index('idx_config_change_changed_by', 'system_config_change_logs', ['changed_by'])
    if not index_exists(inspector, "system_config_change_logs", "idx_config_change_changed_at"):
        op.create_index('idx_config_change_changed_at', 'system_config_change_logs', ['changed_at'])

    if not index_exists(inspector, "compliance_check_logs", "idx_compliance_check_type"):
        op.create_index('idx_compliance_check_type', 'compliance_check_logs', ['check_type'])
    if not index_exists(inspector, "compliance_check_logs", "idx_compliance_check_status"):
        op.create_index('idx_compliance_check_status', 'compliance_check_logs', ['status'])
    if not index_exists(inspector, "compliance_check_logs", "idx_compliance_check_executed_by"):
        op.create_index('idx_compliance_check_executed_by', 'compliance_check_logs', ['executed_by'])
    if not index_exists(inspector, "compliance_check_logs", "idx_compliance_check_executed_at"):
        op.create_index('idx_compliance_check_executed_at', 'compliance_check_logs', ['executed_at'])


def downgrade() -> None:
    inspector = get_inspector()
    # 删除索引
    if table_exists(inspector, "compliance_check_logs"):
        if index_exists(inspector, "compliance_check_logs", "idx_compliance_check_executed_at"):
            op.drop_index('idx_compliance_check_executed_at', table_name='compliance_check_logs')
        if index_exists(inspector, "compliance_check_logs", "idx_compliance_check_executed_by"):
            op.drop_index('idx_compliance_check_executed_by', table_name='compliance_check_logs')
        if index_exists(inspector, "compliance_check_logs", "idx_compliance_check_status"):
            op.drop_index('idx_compliance_check_status', table_name='compliance_check_logs')
        if index_exists(inspector, "compliance_check_logs", "idx_compliance_check_type"):
            op.drop_index('idx_compliance_check_type', table_name='compliance_check_logs')

    if table_exists(inspector, "system_config_change_logs"):
        if index_exists(inspector, "system_config_change_logs", "idx_config_change_changed_at"):
            op.drop_index('idx_config_change_changed_at', table_name='system_config_change_logs')
        if index_exists(inspector, "system_config_change_logs", "idx_config_change_changed_by"):
            op.drop_index('idx_config_change_changed_by', table_name='system_config_change_logs')
        if index_exists(inspector, "system_config_change_logs", "idx_config_change_config_key"):
            op.drop_index('idx_config_change_config_key', table_name='system_config_change_logs')

    if table_exists(inspector, "data_access_logs"):
        if index_exists(inspector, "data_access_logs", "idx_data_access_accessed_at"):
            op.drop_index('idx_data_access_accessed_at', table_name='data_access_logs')
        if index_exists(inspector, "data_access_logs", "idx_data_access_action"):
            op.drop_index('idx_data_access_action', table_name='data_access_logs')
        if index_exists(inspector, "data_access_logs", "idx_data_access_resource_id"):
            op.drop_index('idx_data_access_resource_id', table_name='data_access_logs')
        if index_exists(inspector, "data_access_logs", "idx_data_access_resource_type"):
            op.drop_index('idx_data_access_resource_type', table_name='data_access_logs')
        if index_exists(inspector, "data_access_logs", "idx_data_access_ip"):
            op.drop_index('idx_data_access_ip', table_name='data_access_logs')
        if index_exists(inspector, "data_access_logs", "idx_data_access_user_id"):
            op.drop_index('idx_data_access_user_id', table_name='data_access_logs')

    if table_exists(inspector, "security_audit_logs"):
        if index_exists(inspector, "security_audit_logs", "idx_security_audit_timestamp"):
            op.drop_index('idx_security_audit_timestamp', table_name='security_audit_logs')
        if index_exists(inspector, "security_audit_logs", "idx_security_audit_resource"):
            op.drop_index('idx_security_audit_resource', table_name='security_audit_logs')
        if index_exists(inspector, "security_audit_logs", "idx_security_audit_ip"):
            op.drop_index('idx_security_audit_ip', table_name='security_audit_logs')
        if index_exists(inspector, "security_audit_logs", "idx_security_audit_user_id"):
            op.drop_index('idx_security_audit_user_id', table_name='security_audit_logs')
        if index_exists(inspector, "security_audit_logs", "idx_security_audit_threat_level"):
            op.drop_index('idx_security_audit_threat_level', table_name='security_audit_logs')
        if index_exists(inspector, "security_audit_logs", "idx_security_audit_event_type"):
            op.drop_index('idx_security_audit_event_type', table_name='security_audit_logs')

    if table_exists(inspector, "login_attempts"):
        if index_exists(inspector, "login_attempts", "idx_login_attempts_attempted_at"):
            op.drop_index('idx_login_attempts_attempted_at', table_name='login_attempts')
        if index_exists(inspector, "login_attempts", "idx_login_attempts_success"):
            op.drop_index('idx_login_attempts_success', table_name='login_attempts')
        if index_exists(inspector, "login_attempts", "idx_login_attempts_ip"):
            op.drop_index('idx_login_attempts_ip', table_name='login_attempts')
        if index_exists(inspector, "login_attempts", "idx_login_attempts_username"):
            op.drop_index('idx_login_attempts_username', table_name='login_attempts')
        if index_exists(inspector, "login_attempts", "idx_login_attempts_user_id"):
            op.drop_index('idx_login_attempts_user_id', table_name='login_attempts')

    # 删除表
    if table_exists(inspector, "compliance_check_logs"):
        op.drop_table('compliance_check_logs')
    if table_exists(inspector, "system_config_change_logs"):
        op.drop_table('system_config_change_logs')
    if table_exists(inspector, "data_access_logs"):
        op.drop_table('data_access_logs')
    if table_exists(inspector, "security_audit_logs"):
        op.drop_table('security_audit_logs')
    if table_exists(inspector, "login_attempts"):
        op.drop_table('login_attempts')
