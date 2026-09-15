from __future__ import annotations

from app.orchestration.statechart_engine import WorkflowState


def test_workflow_state_evicts_oldest_context_keys(monkeypatch):
    monkeypatch.setattr("app.orchestration.statechart_engine.settings.MAX_CONTEXT_DATA_KEYS", 2)
    monkeypatch.setattr("app.orchestration.statechart_engine.settings.MAX_CONTEXT_DATA_VALUE_BYTES", 1024)

    state = WorkflowState()
    state.update({"first": 1, "second": 2})
    state.update({"third": 3})

    assert list(state.context_data.keys()) == ["second", "third"]


def test_workflow_state_summarizes_oversized_values(monkeypatch):
    monkeypatch.setattr("app.orchestration.statechart_engine.settings.MAX_CONTEXT_DATA_KEYS", 10)
    monkeypatch.setattr("app.orchestration.statechart_engine.settings.MAX_CONTEXT_DATA_VALUE_BYTES", 32)

    state = WorkflowState()
    state.update({"large": "x" * 128})

    stored = state.context_data["large"]
    assert stored["truncated"] is True
    assert stored["original_size_bytes"] > 32
    assert "summary" in stored
