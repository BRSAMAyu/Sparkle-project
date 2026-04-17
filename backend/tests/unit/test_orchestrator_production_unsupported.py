import pytest

from app.orchestration.orchestrator_production import ProductionChatOrchestrator


def test_production_orchestrator_is_explicitly_unsupported_by_default() -> None:
    with pytest.raises(RuntimeError, match="legacy and unsupported"):
        ProductionChatOrchestrator()
