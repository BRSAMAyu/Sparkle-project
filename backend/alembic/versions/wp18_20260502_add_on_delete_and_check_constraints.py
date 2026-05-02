"""add on delete actions, check constraints, and hnsw indexes

Revision ID: wp18_20260502
Revises: c11_20260502
Create Date: 2026-05-02 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "wp18_20260502"
down_revision: str | None = "c11_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FK_UPGRADES: tuple[tuple[str, str, str, str, str, str | None], ...] = (
    ("achievements", "achievements_first_unlocker_id_fkey", "first_unlocker_id", "users", "id", "SET NULL"),
    ("achievements", "achievements_parent_id_fkey", "parent_id", "achievements", "id", "SET NULL"),
    ("behavior_patterns", "behavior_patterns_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("chat_messages", "chat_messages_task_id_fkey", "task_id", "tasks", "id", "CASCADE"),
    ("chat_messages", "chat_messages_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("chat_sessions", "chat_sessions_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("cognitive_fragments", "cognitive_fragments_task_id_fkey", "task_id", "tasks", "id", "SET NULL"),
    ("cognitive_fragments", "cognitive_fragments_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("curiosity_capsules", "curiosity_capsules_related_task_id_fkey", "related_task_id", "tasks", "id", "SET NULL"),
    ("curiosity_capsules", "curiosity_capsules_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("episodic_memories", "episodic_memories_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("focus_sessions", "focus_sessions_task_id_fkey", "task_id", "tasks", "id", "SET NULL"),
    ("focus_sessions", "focus_sessions_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("memory_corrections", "memory_corrections_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("memory_goals", "memory_goals_linked_plan_id_fkey", "linked_plan_id", "plans", "id", "SET NULL"),
    ("memory_goals", "memory_goals_linked_task_id_fkey", "linked_task_id", "tasks", "id", "SET NULL"),
    ("memory_goals", "memory_goals_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("memory_preferences", "memory_preferences_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("nightly_reviews", "nightly_reviews_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("plans", "plans_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("tasks", "tasks_knowledge_node_id_fkey", "knowledge_node_id", "knowledge_nodes", "id", "SET NULL"),
    ("tasks", "tasks_plan_id_fkey", "plan_id", "plans", "id", "CASCADE"),
    ("tasks", "tasks_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_achievements", "user_achievements_achievement_id_fkey", "achievement_id", "achievements", "id", "CASCADE"),
    ("user_achievements", "user_achievements_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_devices", "user_devices_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_galaxy_skins", "user_galaxy_skins_skin_id_fkey", "skin_id", "galaxy_skins", "id", "CASCADE"),
    ("user_galaxy_skins", "user_galaxy_skins_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_memory_settings", "user_memory_settings_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_preferences_center", "user_preferences_center_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_sessions", "user_sessions_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_settings", "user_settings_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    ("user_streak_stats", "user_streak_stats_user_id_fkey", "user_id", "users", "id", "CASCADE"),
    (
        "user_titles",
        "user_titles_source_achievement_id_fkey",
        "source_achievement_id",
        "achievements",
        "id",
        "SET NULL",
    ),
    ("user_titles", "user_titles_user_id_fkey", "user_id", "users", "id", "CASCADE"),
)


CHECK_CONSTRAINTS: tuple[tuple[str, str, str], ...] = (
    ("users", "chk_users_photon_balance_non_negative", "photon_balance >= 0"),
    ("users", "chk_users_flame_level_range", "flame_level BETWEEN 0 AND 100"),
    ("users", "chk_users_flame_brightness_range", "flame_brightness BETWEEN 0 AND 1"),
    ("users", "chk_users_depth_preference_range", "depth_preference BETWEEN 0 AND 1"),
    ("users", "chk_users_curiosity_preference_range", "curiosity_preference BETWEEN 0 AND 1"),
    ("tasks", "chk_tasks_difficulty_range", "difficulty BETWEEN 1 AND 5"),
    ("tasks", "chk_tasks_energy_cost_range", "energy_cost BETWEEN 1 AND 5"),
    ("tasks", "chk_tasks_estimated_minutes_non_negative", "estimated_minutes >= 0"),
    ("tasks", "chk_tasks_actual_minutes_non_negative", "actual_minutes IS NULL OR actual_minutes >= 0"),
    ("tasks", "chk_tasks_subtask_counts_non_negative", "subtasks_total >= 0 AND subtasks_completed >= 0"),
    ("tasks", "chk_tasks_subtasks_completed_lte_total", "subtasks_completed <= subtasks_total"),
    ("shop_purchases", "chk_shop_purchases_price_paid_non_negative", "price_paid >= 0"),
    ("shop_purchases", "chk_shop_purchases_balance_before_non_negative", "photon_balance_before >= 0"),
    ("shop_purchases", "chk_shop_purchases_balance_after_non_negative", "photon_balance_after >= 0"),
)


HNSW_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("seed_items", "embedding", "idx_seed_items_embedding_hnsw"),
    ("smoke_document_vectors", "embedding", "idx_smoke_document_vectors_embedding_hnsw"),
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _pgvector_installed() -> bool:
    result = op.get_bind().execute(sa.text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    return result.first() is not None


def _column_exists(table_name: str, column_name: str) -> bool:
    result = op.get_bind().execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.first() is not None


def _replace_fk(
    table_name: str,
    constraint_name: str,
    local_column: str,
    referred_table: str,
    referred_column: str,
    on_delete: str | None,
) -> None:
    on_delete_clause = f" ON DELETE {on_delete}" if on_delete else ""
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table_name}') IS NOT NULL
                   AND to_regclass('public.{referred_table}') IS NOT NULL THEN
                    ALTER TABLE ONLY public.{table_name}
                    DROP CONSTRAINT IF EXISTS {constraint_name};

                    ALTER TABLE ONLY public.{table_name}
                    ADD CONSTRAINT {constraint_name}
                    FOREIGN KEY ({local_column})
                    REFERENCES public.{referred_table} ({referred_column}){on_delete_clause};
                END IF;
            END
            $$;
            """
        )
    )


def _drop_constraint_if_exists(table_name: str, constraint_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table_name}') IS NOT NULL THEN
                    ALTER TABLE ONLY public.{table_name}
                    DROP CONSTRAINT IF EXISTS {constraint_name};
                END IF;
            END
            $$;
            """
        )
    )


def _add_check_constraint(table_name: str, constraint_name: str, condition: str) -> None:
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table_name}') IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1
                       FROM pg_constraint
                       WHERE conname = '{constraint_name}'
                         AND conrelid = 'public.{table_name}'::regclass
                   ) THEN
                    ALTER TABLE ONLY public.{table_name}
                    ADD CONSTRAINT {constraint_name} CHECK ({condition}) NOT VALID;
                END IF;
            END
            $$;
            """
        )
    )


def _create_hnsw_indexes() -> None:
    if not _pgvector_installed():
        return

    ctx = op.get_context()
    with ctx.autocommit_block():
        for table_name, column_name, index_name in HNSW_INDEXES:
            if not _column_exists(table_name, column_name):
                continue
            op.execute(
                sa.text(
                    f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name}
                    ON public.{table_name} USING hnsw ({column_name} vector_cosine_ops)
                    WHERE {column_name} IS NOT NULL
                    """
                )
            )


def _drop_hnsw_indexes() -> None:
    ctx = op.get_context()
    with ctx.autocommit_block():
        for _, _, index_name in reversed(HNSW_INDEXES):
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS public.{index_name}"))


def upgrade() -> None:
    if not _is_postgresql():
        return

    for fk in FK_UPGRADES:
        _replace_fk(*fk)

    for check_constraint in CHECK_CONSTRAINTS:
        _add_check_constraint(*check_constraint)

    _create_hnsw_indexes()


def downgrade() -> None:
    if not _is_postgresql():
        return

    _drop_hnsw_indexes()

    for table_name, constraint_name, _ in reversed(CHECK_CONSTRAINTS):
        _drop_constraint_if_exists(table_name, constraint_name)

    for table_name, constraint_name, local_column, referred_table, referred_column, _ in reversed(FK_UPGRADES):
        _replace_fk(table_name, constraint_name, local_column, referred_table, referred_column, None)
