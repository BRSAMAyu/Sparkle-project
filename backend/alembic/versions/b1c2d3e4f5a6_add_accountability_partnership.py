"""add_accountability_partnership

Revision ID: b1c2d3e4f5a6
Revises: a3c5d7e9f1b2
Create Date: 2026-03-17 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "a3c5d7e9f1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create accountability_partnership table
    op.create_table(
        "accountability_partnership",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "initiator_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "partner_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "friendship_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("initiator_goal", sa.Text(), nullable=False),
        sa.Column("partner_goal", sa.Text(), nullable=True),
        sa.Column(
            "check_in_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "active",
                "paused",
                "ended",
                name="accountabilitystatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["initiator_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["friendship_id"], ["friendships.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "initiator_id",
            "partner_id",
            name="uq_accountability_partnership_pair",
        ),
    )
    op.create_index(
        "idx_accountability_initiator_status",
        "accountability_partnership",
        ["initiator_id", "status"],
    )
    op.create_index(
        "idx_accountability_partner_status",
        "accountability_partnership",
        ["partner_id", "status"],
    )

    # Create accountability_checkin table
    op.create_table(
        "accountability_checkin",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "partnership_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "mood",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("3"),
        ),
        sa.Column(
            "minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["partnership_id"],
            ["accountability_partnership.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_accountability_checkin_partnership_user",
        "accountability_checkin",
        ["partnership_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_accountability_checkin_partnership_user",
        table_name="accountability_checkin",
    )
    op.drop_table("accountability_checkin")
    op.drop_index(
        "idx_accountability_partner_status",
        table_name="accountability_partnership",
    )
    op.drop_index(
        "idx_accountability_initiator_status",
        table_name="accountability_partnership",
    )
    op.drop_table("accountability_partnership")
    op.execute("DROP TYPE IF EXISTS accountabilitystatus")
