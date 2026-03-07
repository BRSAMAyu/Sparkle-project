"""add_knowledge_node_to_shared_resources

Revision ID: b7c1f2d4e6a1
Revises: 9c4d7e8f1a2b
Create Date: 2026-03-07 23:10:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7c1f2d4e6a1"
down_revision: Union[str, None] = "9c4d7e8f1a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE shared_resources
            ADD COLUMN IF NOT EXISTS knowledge_node_id uuid;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'shared_resources_knowledge_node_id_fkey'
            ) THEN
                ALTER TABLE shared_resources
                    ADD CONSTRAINT shared_resources_knowledge_node_id_fkey
                    FOREIGN KEY (knowledge_node_id) REFERENCES knowledge_nodes(id);
            END IF;
        END $$;

        CREATE INDEX IF NOT EXISTS idx_share_resource_knowledge_node
            ON shared_resources (knowledge_node_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS idx_share_resource_knowledge_node;

        ALTER TABLE shared_resources
            DROP CONSTRAINT IF EXISTS shared_resources_knowledge_node_id_fkey;

        ALTER TABLE shared_resources
            DROP COLUMN IF EXISTS knowledge_node_id;
        """
    )
