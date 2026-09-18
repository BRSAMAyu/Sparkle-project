"""bootstrap sparkle_galaxy schema

Revision ID: boot_20260502_sparkle_galaxy
Revises: c12_20260502
Create Date: 2026-09-18

Bootstrap migration: creates the ``sparkle_galaxy`` schema that
``c17_20260502_create_service_roles`` grants USAGE on (for
sparkle_engine / sparkle_celery / sparkle_readonly).  Before this
migration existed, a fresh database failed at c17 with
``schema "sparkle_galaxy" does not exist`` because no earlier
revision (nor env.py / docker initdb) ever created the schema.

File name carries the 20260502 era marker because the revision is
inserted into the chain directly before c17_20260502; the Create
Date reflects when the fix was authored.
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

# Migration Contract:
#   type: forward_only
#   rollback_plan: "no-op (schema intentionally kept; c17 downgrade keeps it too)"
#   verification_query: "SELECT 1 FROM pg_namespace WHERE nspname = 'sparkle_galaxy';"
#   backfill_plan: "n/a"
#   owner: "platform"
#   ticket: "sysrev round1 C-02"


revision: str = "boot_20260502_sparkle_galaxy"
down_revision: str | None = "c12_20260502"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS sparkle_galaxy")


def downgrade() -> None:
    # Intentional no-op: the schema may contain galaxy runtime tables and
    # c17_20260502's downgrade only revokes privileges without dropping it.
    pass
