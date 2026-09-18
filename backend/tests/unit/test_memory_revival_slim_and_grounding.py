"""MR-2 slim 上下文清空 + MR-4 grounding 自相矛盾 红绿测试。

多端实测（memory-rag-seedlib-eval）：
- MR-2：``_build_slim_user_context_for_standard_reply`` 返回空 dict——短问句
  （"根据你的记忆，我之前提到过什么考试？"）默认走 slim，记忆/画像全不进提示词。
- MR-4：``use_document_context:true`` 下 GraphRAG 块已水合进提示词
  （document_chunks usage=354），但 ``user_material_grounding`` 段仍宣称
  "这轮没有拿到足够可用的材料证据"，模型听从后者连续拒用已检索资料。
"""

from __future__ import annotations

import json

from app.agents.standard_workflow import _build_slim_user_context_for_standard_reply
from app.core.context_pack import estimate_tokens
from app.orchestration.prompts import (
    _format_user_material_grounding_section,
    build_system_prompt,
)


def _memory_window() -> list[dict]:
    return [
        {
            "id": "m1",
            "summary": "用户下周三有数据结构期中考试",
            "subject_type": "self",
            "source_type": "chat",
            "occurred_at": "2026-09-17T09:00:00",
            "confidence": 0.9,
        },
        {
            "id": "m2",
            "summary": "用户最喜欢的电影是《星际穿越》",
            "subject_type": "self",
            "source_type": "chat",
            "occurred_at": "2026-09-17T09:05:00",
            "confidence": 0.9,
        },
        {
            "id": "m3",
            "summary": "用户正在复习操作系统死锁处理机制",
            "subject_type": "self",
            "source_type": "chat",
            "occurred_at": "2026-09-16T21:00:00",
            "confidence": 0.85,
        },
        {
            "id": "m4",
            "summary": "用户提到和同学约好周末一起刷题",
            "subject_type": "person_mention",
            "source_type": "chat",
            "occurred_at": "2026-09-15T18:00:00",
            "confidence": 0.8,
        },
    ]


def _full_user_context() -> dict:
    return {
        "episodic_memories": _memory_window(),
        "preferences": {"tone": "encouraging", "depth_preference": 0.7, "verbosity": "balanced"},
        "active_goals": [{"title": "数据结构期中备考", "status": "active"}],
        "llm_profile": {"verbosity_target": "balanced"},
        "preference_version": 3,
        "current_query": "根据你的记忆，我之前提到过什么考试？",
        # 以下为 slim 必须裁剪的噪音
        "next_actions": [{"title": "完成线代作业第三章", "estimated_minutes": 30, "type": "task"}],
        "focus_stats": {"total_minutes": 45, "pomodoro_count": 2},
        "active_plans": [{"title": "期末复习计划", "type": "study", "progress": 0.4}],
        "recent_tool_usage": [{"tool_name": "get_plan_state", "summary": "查询了计划状态"}],
    }


# ---------------------------------------------------------------------------
# MR-2 slim 记忆窗口
# ---------------------------------------------------------------------------


def test_slim_standard_context_is_not_empty():
    slim = _build_slim_user_context_for_standard_reply(_full_user_context())
    assert slim, "MR-2: slim 路径不得返回空 dict（记忆/画像被整体清空）"


def test_slim_standard_context_keeps_top3_episodic():
    slim = _build_slim_user_context_for_standard_reply(_full_user_context())
    episodic = slim.get("episodic_memories") or []
    assert 1 <= len(episodic) <= 3, f"slim 记忆窗口应为 top-1..3 条 episodic，实际 {len(episodic)}"
    summaries = json.dumps(episodic, ensure_ascii=False)
    assert "数据结构期中" in summaries


def test_slim_standard_context_drops_task_noise():
    slim = _build_slim_user_context_for_standard_reply(_full_user_context())
    for noise_key in ("next_actions", "focus_stats", "active_plans", "recent_tool_usage"):
        assert noise_key not in slim, f"slim 必须继续裁剪任务/统计噪音: {noise_key}"


def test_slim_standard_context_token_budget():
    slim = _build_slim_user_context_for_standard_reply(_full_user_context())
    tokens = estimate_tokens(json.dumps(slim, ensure_ascii=False, default=str))
    assert tokens <= 600, f"slim 记忆窗口应控制在 ~500 token 预算内（实测 {tokens}）"


def test_slim_prompt_renders_memory_for_short_memory_question():
    slim = _build_slim_user_context_for_standard_reply(_full_user_context())
    prompt = build_system_prompt(
        slim,
        conversation_history={"messages": []},
        prompt_version="v1",
        context_level="light",
    )
    assert "数据结构期中" in prompt, "slim 路径提示词必须包含既有记忆内容"


# ---------------------------------------------------------------------------
# MR-4 grounding 段与实际检索结果一致
# ---------------------------------------------------------------------------


def _hydrated_document_context() -> dict:
    return {
        "document_context": (
            "Relevant Documents (showing top 2 of 3 results):\n"
            "- [ZB-2049协议白皮书.pdf | 总则 | p1] ZB-2049 是一种实验室物料编码规范，"
            "其中 ZB 前缀代表中试批次。\n"
            "- [ZB-2049协议白皮书.pdf | 附录 | p4] ZB-2049 条目需包含批次号与责任人。"
        ),
        "document_context_retrieval": {
            "source": "graphrag",
            "mode": "selective",
            "total_retrieved": 3,
            "total_passed": 3,
            "context_receipt": {
                "used": [],
                "used_names": ["ZB-2049协议白皮书.pdf"],
                "used_count": 2,
                "total_retrieved": 3,
            },
        },
        "user_material_grounding": {
            "status": "no_scoped_files",
            "query": "ZB-2049 是什么",
            "results": [],
        },
    }


def test_grounding_no_longer_contradicts_hydrated_documents():
    section = _format_user_material_grounding_section(user_context=_hydrated_document_context())
    assert section, "已有水合文档证据时 grounding 段应生成材料指引"
    assert "没有拿到" not in section, "MR-4: 已有检索证据时不得宣称'没拿到材料'"
    assert "没有足够可用" not in section
    assert "ZB-2049" in section, "grounding 段应引用实际命中的材料名"


def test_grounding_keeps_honest_no_material_when_nothing_hydrated():
    ctx = {
        "user_material_grounding": {"status": "no_hits", "query": "量子纠错表面码", "results": []},
    }
    section = _format_user_material_grounding_section(user_context=ctx)
    assert section
    assert "没有拿到" in section or "没有足够" in section, "真无材料时保留诚实的'没有材料'口径"


def test_grounding_grounded_status_still_lists_snippets():
    ctx = {
        "user_material_grounding": {
            "status": "grounded",
            "query": "ZB-2049",
            "results": [
                {
                    "file_name": "ZB-2049协议白皮书.pdf",
                    "section_title": "总则",
                    "page_numbers": [1],
                    "snippet": "ZB-2049 是一种实验室物料编码规范。",
                }
            ],
        },
    }
    section = _format_user_material_grounding_section(user_context=ctx)
    assert "ZB-2049" in section
    assert "没有拿到" not in section


def test_build_system_prompt_has_no_grounding_contradiction():
    """端到端：build_system_prompt 产物中 grounding 段与 document 块不得互相矛盾。"""
    ctx = _hydrated_document_context()
    prompt = build_system_prompt(
        ctx,
        conversation_history={"messages": []},
        prompt_version="v1",
        context_level="full",
    )
    assert "这轮没有拿到足够可用的材料证据" not in prompt, "MR-4: 提示词仍在否定已检索到的材料"
    assert "ZB-2049" in prompt
