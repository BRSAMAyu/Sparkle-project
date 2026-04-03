"""add card sharing tables (card_snapshots, card_share_records, card_adoption_records)

Revision ID: cp002b3c4d5e6
Revises: cp001a2b3c4d5
Create Date: 2026-04-03 15:30:00.000000

Card Protocol Phase C: Sharing and portability protocol.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "cp002b3c4d5e6"
down_revision = "cp001a2b3c4d5"
branch_labels = None
depends_on = None


def _jsonb():
    if op.get_bind().dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    jsonb = _jsonb()
    uuid_type = postgresql.UUID(as_uuid=True)
    if op.get_bind().dialect.name == "sqlite":
        uuid_type = sa.String(36)

    op.create_table(
        "card_snapshots",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("root_card_id", uuid_type, nullable=True),
        sa.Column("source_owner_id", uuid_type, nullable=True),
        sa.Column("source_card_type", sa.String(32), nullable=False),
        sa.Column("schema_version", sa.String(16), nullable=False, server_default="'1.0'"),
        sa.Column("payload", jsonb, nullable=False, server_default="{}"),
        sa.Column("metadata", jsonb, nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["root_card_id"], ["cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_owner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_card_snapshots_deleted_at", "card_snapshots", ["deleted_at"], unique=False)
    op.create_index("ix_card_snapshots_root_card_id", "card_snapshots", ["root_card_id"], unique=False)
    op.create_index("ix_card_snapshots_source_owner_id", "card_snapshots", ["source_owner_id"], unique=False)
    op.create_index("ix_card_snapshots_source_card_type", "card_snapshots", ["source_card_type"], unique=False)
    op.create_index(
        "ix_card_snapshots_root_type",
        "card_snapshots",
        ["root_card_id", "source_card_type"],
        unique=False,
    )
    op.create_index(
        "ix_card_snapshots_owner_type",
        "card_snapshots",
        ["source_owner_id", "source_card_type"],
        unique=False,
    )

    op.create_table(
        "card_share_records",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("snapshot_id", uuid_type, nullable=False),
        sa.Column("root_card_id", uuid_type, nullable=True),
        sa.Column("shared_by_user_id", uuid_type, nullable=False),
        sa.Column("target_user_id", uuid_type, nullable=True),
        sa.Column("group_id", uuid_type, nullable=True),
        sa.Column("scope", sa.String(24), nullable=False),
        sa.Column("permission", sa.String(24), nullable=False, server_default="'ADOPT'"),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("adoption_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("metadata", jsonb, nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["card_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["root_card_id"], ["cards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shared_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_card_share_records_deleted_at", "card_share_records", ["deleted_at"], unique=False)
    op.create_index("ix_card_share_records_snapshot_id", "card_share_records", ["snapshot_id"], unique=False)
    op.create_index("ix_card_share_records_root_card_id", "card_share_records", ["root_card_id"], unique=False)
    op.create_index(
        "ix_card_share_records_shared_by_user_id",
        "card_share_records",
        ["shared_by_user_id"],
        unique=False,
    )
    op.create_index("ix_card_share_records_target_user_id", "card_share_records", ["target_user_id"], unique=False)
    op.create_index("ix_card_share_records_group_id", "card_share_records", ["group_id"], unique=False)
    op.create_index("ix_card_share_records_scope", "card_share_records", ["scope"], unique=False)
    op.create_index(
        "ix_card_share_scope_group",
        "card_share_records",
        ["scope", "group_id"],
        unique=False,
    )
    op.create_index(
        "ix_card_share_scope_target",
        "card_share_records",
        ["scope", "target_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_card_share_owner_scope",
        "card_share_records",
        ["shared_by_user_id", "scope"],
        unique=False,
    )

    op.create_table(
        "card_adoption_records",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("share_record_id", uuid_type, nullable=False),
        sa.Column("adopter_user_id", uuid_type, nullable=False),
        sa.Column("adopted_root_card_id", uuid_type, nullable=True),
        sa.Column("import_mode", sa.String(24), nullable=False),
        sa.Column("attribution_payload", jsonb, nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["share_record_id"], ["card_share_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["adopter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["adopted_root_card_id"], ["cards.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_card_adoption_records_deleted_at", "card_adoption_records", ["deleted_at"], unique=False)
    op.create_index("ix_card_adoption_records_share_record_id", "card_adoption_records", ["share_record_id"], unique=False)
    op.create_index("ix_card_adoption_records_adopter_user_id", "card_adoption_records", ["adopter_user_id"], unique=False)
    op.create_index("ix_card_adoption_records_adopted_root_card_id", "card_adoption_records", ["adopted_root_card_id"], unique=False)
    op.create_index("ix_card_adoption_records_import_mode", "card_adoption_records", ["import_mode"], unique=False)
    op.create_index(
        "ix_card_adoption_user_mode",
        "card_adoption_records",
        ["adopter_user_id", "import_mode"],
        unique=False,
    )

    op.add_column(
        "shared_resources",
        sa.Column("card_share_record_id", uuid_type, nullable=True),
    )
    op.create_foreign_key(
        "fk_shared_resources_card_share_record_id",
        "shared_resources",
        "card_share_records",
        ["card_share_record_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_shared_resources_card_share_record_id",
        "shared_resources",
        ["card_share_record_id"],
        unique=False,
    )
    op.create_index(
        "idx_share_card_share_record",
        "shared_resources",
        ["card_share_record_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_share_card_share_record", table_name="shared_resources")
    op.drop_index("ix_shared_resources_card_share_record_id", table_name="shared_resources")
    op.drop_constraint("fk_shared_resources_card_share_record_id", "shared_resources", type_="foreignkey")
    op.drop_column("shared_resources", "card_share_record_id")

    op.drop_table("card_adoption_records")
    op.drop_table("card_share_records")
    op.drop_table("card_snapshots")
