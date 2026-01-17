from __future__ import annotations

from alembic import op
import sqlalchemy as sa


def get_inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def table_exists(inspector: sa.Inspector, table_name: str, schema: str = "public") -> bool:
    return table_name in inspector.get_table_names(schema=schema)


def column_exists(inspector: sa.Inspector, table_name: str, column_name: str, schema: str = "public") -> bool:
    if not table_exists(inspector, table_name, schema=schema):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name, schema=schema))


def index_exists(inspector: sa.Inspector, table_name: str, index_name: str, schema: str = "public") -> bool:
    if not table_exists(inspector, table_name, schema=schema):
        return False
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name, schema=schema))


def unique_constraint_exists(
    inspector: sa.Inspector, table_name: str, constraint_name: str, schema: str = "public"
) -> bool:
    if not table_exists(inspector, table_name, schema=schema):
        return False
    return any(
        constraint.get("name") == constraint_name
        for constraint in inspector.get_unique_constraints(table_name, schema=schema)
    )


def foreign_key_exists(inspector: sa.Inspector, table_name: str, fk_name: str, schema: str = "public") -> bool:
    if not table_exists(inspector, table_name, schema=schema):
        return False
    return any(
        fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name, schema=schema)
    )


def is_partitioned_table(bind: sa.engine.Connection, table_name: str, schema: str = "public") -> bool:
    if bind.dialect.name != "postgresql":
        return False
    query = sa.text(
        """
        SELECT 1
        FROM pg_partitioned_table pt
        JOIN pg_class c ON c.oid = pt.partrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = :table_name
          AND n.nspname = :schema
        """
    )
    return bind.execute(query, {"table_name": table_name, "schema": schema}).scalar() is not None
