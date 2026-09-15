"""create service roles for production RBAC

Revision ID: c17_20260502
Revises: c12_20260502
Create Date: 2026-05-02 14:20:00
"""

from __future__ import annotations

import os
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "c17_20260502"
down_revision: str | None = "c12_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SERVICE_ROLES: tuple[str, ...] = (
    "sparkle_gateway",
    "sparkle_engine",
    "sparkle_celery",
    "sparkle_readonly",
)

ROLE_PASSWORD_ENVS: dict[str, str] = {
    "sparkle_gateway": "SPARKLE_GATEWAY_DB_PASSWORD",
    "sparkle_engine": "SPARKLE_ENGINE_DB_PASSWORD",
    "sparkle_celery": "SPARKLE_CELERY_DB_PASSWORD",
    "sparkle_readonly": "SPARKLE_READONLY_DB_PASSWORD",
}

GATEWAY_RW_TABLES: tuple[str, ...] = (
    "auth_audit_log",
    "chat_messages",
    "chat_sessions",
    "crdt_operation_log",
    "crdt_snapshots",
    "data_access_logs",
    "event_outbox",
    "event_sequence_counters",
    "event_store",
    "idempotency_keys",
    "login_attempts",
    "message_favorites",
    "message_reports",
    "offline_message_queue",
    "processed_events",
    "projection_metadata",
    "projection_snapshots",
    "security_audit_logs",
    "stored_files",
    "user_devices",
    "user_preferences_center",
    "user_sessions",
)

GATEWAY_RO_TABLES: tuple[str, ...] = (
    "users",
    "tasks",
    "plans",
    "knowledge_nodes",
    "node_relations",
    "user_node_status",
    "shared_resources",
)

ENGINE_PREFIXES: tuple[str, ...] = (
    "ab_experiment",
    "accountability_",
    "agent_",
    "aurora_",
    "background_",
    "behavior",
    "calendar_",
    "capsule_",
    "cognitive_",
    "context_",
    "curiosity_",
    "document_",
    "episodic_",
    "error_",
    "evolution_",
    "execution_",
    "expansion_",
    "focus_",
    "galaxy_",
    "group_",
    "intervention_",
    "irt_",
    "item_",
    "job",
    "knowledge_",
    "learning_",
    "ltm_",
    "mastery_",
    "memory_",
    "next_action_",
    "nightly_",
    "node_",
    "notification_",
    "passive_",
    "persona_",
    "plan_",
    "push_",
    "recommendation_",
    "review_",
    "scaffolding_",
    "seed_",
    "semantic_",
    "shared_",
    "smoke_document_",
    "spark_",
    "strategy_",
    "study_",
    "subject",
    "subtask",
    "task_",
    "token_",
    "tracking_",
    "user_",
    "visual_",
    "word_",
)

ENGINE_RW_TABLES: tuple[str, ...] = (
    "behavioral_outcomes",
    "calendar_events",
    "chat_messages",
    "chat_sessions",
    "curiosity_capsules",
    "decision_records",
    "dictionary_entries",
    "intervention_requests",
    "jobs",
    "knowledge_nodes",
    "learning_assets",
    "notifications",
    "plans",
    "posts",
    "response_feedback",
    "shared_resources",
    "stored_files",
    "tasks",
    "users",
)

CELERY_EXTRA_RW_TABLES: tuple[str, ...] = (
    "dlq_replay_audit_logs",
    "event_outbox",
    "event_sequence_counters",
    "event_store",
    "processed_events",
    "projection_metadata",
    "projection_snapshots",
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _execute(sql: str, **params: object) -> None:
    op.get_bind().execute(sa.text(sql), params)


def _array_literal(values: Sequence[str]) -> str:
    return "ARRAY[" + ", ".join("'" + value.replace("'", "''") + "'" for value in values) + "]"


def _create_role(role: str) -> None:
    _execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :role_name) THEN
                EXECUTE format(
                    'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
                    :role_name
                );
            ELSE
                EXECUTE format(
                    'ALTER ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
                    :role_name
                );
            END IF;
        END
        $$;
        """,
        role_name=role,
    )
    password = os.getenv(ROLE_PASSWORD_ENVS[role], "").strip()
    if password:
        _execute(f"ALTER ROLE {role} PASSWORD :password", password=password)


def _grant_schema_usage(role: str, schema: str = "public") -> None:
    _execute(f"GRANT USAGE ON SCHEMA {schema} TO {role}")
    _execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO {role}")
    _execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT USAGE, SELECT ON SEQUENCES TO {role}")


def _grant_tables(role: str, privileges: str, table_names: Sequence[str]) -> None:
    if not table_names:
        return
    _execute(
        f"""
        DO $$
        DECLARE
            table_name text;
        BEGIN
            FOREACH table_name IN ARRAY {_array_literal(table_names)} LOOP
                IF to_regclass('public.' || quote_ident(table_name)) IS NOT NULL THEN
                    EXECUTE format('GRANT %s ON TABLE public.%I TO %I', :privileges, table_name, :role_name);
                END IF;
            END LOOP;
        END
        $$;
        """,
        role_name=role,
        privileges=privileges,
    )


def _grant_by_prefix(role: str, privileges: str, prefixes: Sequence[str]) -> None:
    _execute(
        f"""
        DO $$
        DECLARE
            rec record;
        BEGIN
            FOR rec IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND EXISTS (
                      SELECT 1
                      FROM unnest({_array_literal(prefixes)}) AS prefix
                      WHERE tablename LIKE prefix || '%'
                  )
            LOOP
                EXECUTE format('GRANT %s ON TABLE public.%I TO %I', :privileges, rec.tablename, :role_name);
            END LOOP;
        END
        $$;
        """,
        role_name=role,
        privileges=privileges,
    )


def _grant_all_tables(role: str, privileges: str, schema: str = "public") -> None:
    _execute(f"GRANT {privileges} ON ALL TABLES IN SCHEMA {schema} TO {role}")
    _execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT {privileges} ON TABLES TO {role}")


def upgrade() -> None:
    if not _is_postgresql():
        return

    for role in SERVICE_ROLES:
        _create_role(role)

    for role in SERVICE_ROLES:
        _grant_schema_usage(role, "public")

    _grant_tables("sparkle_gateway", "SELECT, INSERT, UPDATE, DELETE", GATEWAY_RW_TABLES)
    _grant_tables("sparkle_gateway", "SELECT", GATEWAY_RO_TABLES)

    _grant_by_prefix("sparkle_engine", "SELECT, INSERT, UPDATE, DELETE", ENGINE_PREFIXES)
    _grant_tables("sparkle_engine", "SELECT, INSERT, UPDATE, DELETE", ENGINE_RW_TABLES)
    _grant_schema_usage("sparkle_engine", "sparkle_galaxy")
    _grant_all_tables("sparkle_engine", "SELECT, INSERT, UPDATE, DELETE", "sparkle_galaxy")

    _grant_by_prefix("sparkle_celery", "SELECT, INSERT, UPDATE, DELETE", ENGINE_PREFIXES)
    _grant_tables("sparkle_celery", "SELECT, INSERT, UPDATE, DELETE", ENGINE_RW_TABLES + CELERY_EXTRA_RW_TABLES)
    _grant_schema_usage("sparkle_celery", "sparkle_galaxy")
    _grant_all_tables("sparkle_celery", "SELECT, INSERT, UPDATE, DELETE", "sparkle_galaxy")

    _grant_all_tables("sparkle_readonly", "SELECT", "public")
    _grant_schema_usage("sparkle_readonly", "sparkle_galaxy")
    _grant_all_tables("sparkle_readonly", "SELECT", "sparkle_galaxy")


def downgrade() -> None:
    if not _is_postgresql():
        return

    for schema in ("sparkle_galaxy", "public"):
        for role in SERVICE_ROLES:
            _execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} REVOKE ALL ON TABLES FROM {role}")
            _execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} REVOKE ALL ON SEQUENCES FROM {role}")
            _execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} FROM {role}")
            _execute(f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema} FROM {role}")
            _execute(f"REVOKE USAGE ON SCHEMA {schema} FROM {role}")

    for role in reversed(SERVICE_ROLES):
        _execute(f"DROP ROLE IF EXISTS {role}")
