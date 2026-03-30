from app.models.execution_intent import ExecutionIntent


def test_execution_intent_uses_non_native_enums() -> None:
    columns = (
        ExecutionIntent.__table__.c.execution_mode,
        ExecutionIntent.__table__.c.executor,
        ExecutionIntent.__table__.c.target_env,
        ExecutionIntent.__table__.c.status,
        ExecutionIntent.__table__.c.trust_level,
    )

    assert all(getattr(column.type, "native_enum", True) is False for column in columns)
