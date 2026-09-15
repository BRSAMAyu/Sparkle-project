from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

from app.models.execution_intent import ExecutionIntent
from app.services.execution_profile_service import _is_succeeded_status


def test_succeeded_status_filter_compiles_without_postgres_enum_cast():
    stmt = select(
        func.sum(
            func.coalesce(
                _is_succeeded_status().cast(postgresql.INTEGER),
                0,
            )
        )
    ).where(_is_succeeded_status())

    compiled = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "executionintentstatus" not in compiled.lower()
    assert "CAST(execution_intents.status AS VARCHAR) = 'succeeded'" in compiled
