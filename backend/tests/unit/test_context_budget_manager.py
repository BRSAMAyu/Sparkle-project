import json
from datetime import timedelta
from types import SimpleNamespace

from app.config import settings
from app.core.business_metrics import CONTEXT_BUDGET_UTILIZATION, snapshot_metric
from app.core.context_pack import ContextBudgetManager, estimate_tokens, _utcnow


def _chunk(
    *,
    idx: int,
    file_name: str,
    relevance_score: float,
    days_old: int,
    mastery_gap: float,
    content: str,
):
    updated_at = (_utcnow() - timedelta(days=days_old)).isoformat()
    chunk = SimpleNamespace(
        content=content,
        section_title=f"Section {idx}",
        page_numbers=[idx + 1],
        chunk_index=idx,
        updated_at=updated_at,
    )
    return SimpleNamespace(
        chunk=chunk,
        file_name=file_name,
        relevance_score=relevance_score,
        metadata={
            "filename": file_name,
            "updated_at": updated_at,
            "mastery_gap": mastery_gap,
            "chunk_index": idx,
        },
    )


def test_context_budget_manager_trims_sources_and_places_documents_last(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 800, raising=False)
    monkeypatch.setattr(settings, "CONVERSATION_HISTORY_CONTEXT_RATIO", 0.40, raising=False)
    monkeypatch.setattr(settings, "DOCUMENT_CONTEXT_RATIO", 0.25, raising=False)
    monkeypatch.setattr(settings, "GALAXY_KNOWLEDGE_CONTEXT_RATIO", 0.15, raising=False)
    monkeypatch.setattr(settings, "TASK_ERROR_CONTEXT_RATIO", 0.10, raising=False)
    monkeypatch.setattr(settings, "COGNITIVE_PROFILE_CONTEXT_RATIO", 0.10, raising=False)
    monkeypatch.setattr(settings, "DOCUMENT_CONTEXT_MAX_CHUNKS", 10, raising=False)

    conversation_history = [
        {"role": "user" if idx % 2 == 0 else "assistant", "content": f"turn {idx} " + ("history " * 90)}
        for idx in range(20)
    ]
    chunks = [
        _chunk(
            idx=idx,
            file_name=f"plain-{idx}.pdf",
            relevance_score=0.9 - (idx * 0.01),
            days_old=90,
            mastery_gap=0.0,
            content=f"plain chunk {idx} " + ("document evidence " * 120),
        )
        for idx in range(10)
    ]
    chunks.append(
        _chunk(
            idx=99,
            file_name="boosted-gap.pdf",
            relevance_score=0.72,
            days_old=0,
            mastery_gap=0.9,
            content="boosted mastery gap evidence " + ("critical proof " * 120),
        )
    )

    manager = ContextBudgetManager()
    result = manager.assemble_prompt(
        base_system_prompt="System shell.",
        user_message="Use the documents and continue our thread.",
        conversation_history=conversation_history,
        document_chunks=chunks,
        galaxy_knowledge="galaxy " * 240,
        task_error_context="task error " * 140,
        cognitive_profile="cognitive profile " * 120,
    )

    total_tokens = (
        estimate_tokens(result.system_prompt)
        + estimate_tokens(json.dumps(result.conversation_history, ensure_ascii=False, default=str))
        + estimate_tokens(result.user_message)
    )
    assert total_tokens <= settings.CONTEXT_TOTAL_TOKEN_BUDGET
    assert result.token_usage["conversation_history"] <= result.budgets["conversation_history"]
    assert result.token_usage["document_chunks"] <= result.budgets["document_chunks"]
    assert len(result.conversation_history) < len(conversation_history)
    # R2-final placement：注入材料离开 system prompt，紧贴最后一条 user 消息
    # （user_message 前缀 = 回显保底声明 + 材料块 + 原始问题），metadata 与
    # 实际行为一致。
    assert "showing top" not in result.system_prompt
    assert "## Retrieved Documents" not in result.system_prompt
    assert "showing top" in result.user_message
    assert "## Retrieved Documents" in result.user_message
    assert result.user_message.endswith("Use the documents and continue our thread.")
    assert result.user_message.index("boosted mastery gap evidence") < result.user_message.rindex(
        "Use the documents and continue our thread."
    )
    assert result.user_message.startswith("（系统注：本轮已注入你上传的资料原文，回答必须优先引用）")
    assert result.document_block and "## Retrieved Documents" in result.document_block
    assert result.metadata["placement"]["document_chunks"] == "last_before_user_message"
    assert result.metadata["placement"]["document_context"] == "last_before_user_message"
    assert result.metadata["placement"]["injection_surface"] == "user_message_prefix"

    document_ranking = result.metadata["document_context"]["ranking"]
    assert document_ranking[0]["label"].startswith("boosted-gap.pdf")
    assert "type=document_chunks" in snapshot_metric(CONTEXT_BUDGET_UTILIZATION)
