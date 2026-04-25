from datetime import timezone, datetime
from uuid import uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder, _get_semantic_gating_rules
from app.models.user import User
from app.orchestration.context_focus import ContextFocusResolver
from app.orchestration.prompts import _SECTION_BUDGET_RATIO, build_system_prompt
from app.services.embedding_service import embedding_service
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def test_context_focus_resolver_prefers_emotional_focus_without_plan_action() -> None:
    resolver = ContextFocusResolver()

    decision = resolver.resolve(
        user_message="我最近好崩溃，完全学不进去",
        route_intent="chat",
        plan_context={"plan_title": "高数复习"},
        cognitive_insights={"has_cognitive_patterns": True, "pattern_count": 2},
    )

    assert decision.focus_mode == "emotional_focus"
    assert decision.section_weights["plan_context"] == "minimal"
    assert decision.section_weights["cognitive_prism"] == "full"


def test_build_system_prompt_uses_briefing_and_hides_irrelevant_plan_section() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "current_query": "给我讲一下矩阵乘法",
            "context_focus": {
                "focus_mode": "knowledge_focus",
                "focus_reason": "route:knowledge",
                "section_weights": {
                    "user_context": "medium",
                    "plan_context": "low",
                    "cognitive_prism": "off",
                    "preferences": "medium",
                    "goals": "low",
                    "episodic": "low",
                    "task_summary": "off",
                },
                "section_caps": {"goals": 2, "episodic": 1, "next_actions": 1, "active_plans": 1},
                "briefing_candidates": ["本轮优先聚焦知识解释，减少无关画像噪声"],
                "semantic_gating_enabled": True,
                "route_intent": "knowledge",
            },
            "context_briefing_note": "当前重点：只解释矩阵乘法，减少无关计划信息",
        },
        conversation_history={"messages": []},
        plan_context={"plan_title": "英语冲刺计划", "goal": "提升英语成绩"},
    )

    assert prompt.startswith("你是 Sparkle") is False
    assert "## 本轮关键上下文摘要" in prompt
    assert "矩阵乘法" in prompt
    assert "英语冲刺计划" not in prompt


def test_build_system_prompt_marks_priorities_and_softens_conflicts() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.9, "curiosity_preference": 0.8},
            "llm_profile": {"system_prompt_additions": "## 用户偏好适配\n- 请尽量深入展开说明"},
            "cognitive_insights": {"has_cognitive_patterns": True, "pattern_count": 2, "recent_patterns": ["启动困难"]},
        },
        conversation_history={"messages": [{"role": "user", "content": "上一轮说太复杂了"}]},
        session_feedback_instruction="用户刚要求更简洁，请立刻收短。",
        dual_core_instruction="优先做认知拆解，再逐层展开。",
    )

    assert "## 会话内反馈适配 [L1 强制]" in prompt
    assert "## 双核心路由指令 [L2 引导]" in prompt
    assert "[优先级：L3 背景]" in prompt
    assert "[冲突预检] 本轮以精简表达为准" in prompt


def test_build_system_prompt_trims_low_priority_sections_when_over_budget() -> None:
    long_text = "这是很长的背景信息。" * 1200
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "llm_profile": {"system_prompt_additions": "## 用户偏好适配\n- 保持稳定"},
            "active_goals": [{"title": long_text, "status": "active"}],
            "episodic_memories": [{"summary": long_text}],
        },
        conversation_history={"messages": [{"role": "user", "content": long_text}]},
        intent_instruction="先解决用户当前问题。",
        session_feedback_instruction="用户刚要求更简洁，请立刻收短。",
        dual_core_instruction="优先执行当前目标。",
    )

    assert "## 当前意图指令 [L1 强制]" in prompt
    assert "## 会话内反馈适配 [L1 强制]" in prompt
    assert "其余低优先级背景已压缩" in prompt


def test_user_context_budget_is_reserved_for_richer_profile_payloads() -> None:
    min_tokens, max_ratio = _SECTION_BUDGET_RATIO["user_context"]
    plan_tokens, _ = _SECTION_BUDGET_RATIO["plan_context_section"]
    cognitive_tokens, _ = _SECTION_BUDGET_RATIO["cognitive_prism_section"]
    companion_tokens, companion_ratio = _SECTION_BUDGET_RATIO["companion_persona_section"]

    assert min_tokens >= 350
    assert plan_tokens >= 200
    assert cognitive_tokens >= 120
    assert max_ratio >= 0.18
    assert companion_tokens >= 160
    assert companion_ratio >= 0.14


def test_build_system_prompt_defaults_to_five_episodic_memories() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5},
            "episodic_memories": [{"summary": f"memory-{idx}"} for idx in range(6)],
        },
        conversation_history={"messages": []},
    )

    assert "memory-0" in prompt
    assert "memory-4" in prompt
    assert "memory-5" not in prompt


def test_build_system_prompt_unchanged_when_past_session_memory_empty() -> None:
    base_prompt = build_system_prompt(
        user_context={"preferences": {"depth_preference": 0.5}},
        conversation_history={"messages": []},
    )
    empty_memory_prompt = build_system_prompt(
        user_context={"preferences": {"depth_preference": 0.5}, "past_session_memory": []},
        conversation_history={"messages": []},
    )

    assert empty_memory_prompt == base_prompt
    assert "你之前了解的关于用户的信息" not in empty_memory_prompt


def test_build_system_prompt_prefixes_past_session_memory() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5},
            "past_session_memory": [
                {"summary": "上次你备考计算机网络，传输层学得不错但子网划分比较薄弱。"},
                {"summary": "最近更适合用短冲刺和错题复盘推进。"},
            ],
        },
        conversation_history={"messages": []},
    )

    assert prompt.startswith("你之前了解的关于用户的信息：\n- 上次你备考计算机网络")
    assert "子网划分比较薄弱" in prompt


def test_build_system_prompt_includes_understanding_depth_hint() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "understanding_depth": {"level": "L3", "score": 3},
            "understanding_depth_hint": {
                "level": "L3",
                "description": "我现在不只知道你的偏好，还能更稳定地预判你会怎么执行了。",
                "natural_hint": "如果自然，可以顺带一句提到：我现在不只知道你的偏好，还能比较稳定地预判你的执行节奏。",
            },
        },
        conversation_history={"messages": []},
    )

    assert "## 理解深度升级提示 [L2 引导]" in prompt
    assert "仅当本轮表达自然且不打断当前任务时" in prompt
    assert "当前升级: L3" in prompt


def test_build_system_prompt_includes_auto_user_material_grounding_section() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "user_material_grounding": {
                "status": "grounded",
                "query": "帮我解释熵增方向判断；先用用户材料校准概念。",
                "results": [
                    {
                        "file_name": "thermo-notes.pdf",
                        "section_title": "Entropy",
                        "page_numbers": [12],
                        "snippet": "熵增方向的判断要先看系统边界，再看不可逆过程的主导项。",
                    }
                ],
            },
        },
        conversation_history={"messages": []},
    )

    assert "## 用户材料依据 [L1 证据]" in prompt
    assert "thermo-notes.pdf / Entropy / p.12" in prompt
    assert "优先用这些用户材料片段校准概念" in prompt


def test_build_system_prompt_includes_actual_cognitive_patterns_and_guidance() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "cognitive_insights": {
                "has_cognitive_patterns": True,
                "pattern_count": 2,
                "patterns_by_type": {"execution": 1, "cognitive": 1},
                "top_patterns": [
                    {
                        "pattern_name": "完美主义回避循环",
                        "confidence": 0.78,
                        "description": "总想准备到足够好才开始，结果更难启动。",
                    },
                    {
                        "pattern_name": "认知盲点",
                        "confidence": 0.65,
                        "description": "在相似概念上会重复误解。",
                    },
                ],
                "recent_observation": {
                    "pattern_name": "认知盲点",
                    "description": "最近一周在热力学概念上反复混淆。",
                },
                "current_guidance": "先搭桥澄清概念卡点，再给执行动作。",
            },
        },
        conversation_history={"messages": []},
    )

    assert "用户当前的高权重模式" in prompt
    assert "完美主义回避循环 (confidence 0.78)" in prompt
    assert "最近观察: 认知盲点 - 最近一周在热力学概念上反复混淆。" in prompt
    assert "当前 guidance: 先搭桥澄清概念卡点，再给执行动作。" in prompt


def test_build_system_prompt_includes_companion_persona_context() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "user_context": {"nickname": "Ava"},
            "active_goals": [{"title": "在期中前拿下热力学第二章"}],
            "learning_gaps_summary": "热力学第二定律相关概念仍然容易混淆。今天先补这块。",
            "cognitive_insights": {
                "top_patterns": [
                    {
                        "pattern_name": "完美主义回避循环",
                        "confidence": 0.78,
                        "description": "总想准备到足够好才开始。",
                    }
                ]
            },
        },
        conversation_history={"messages": []},
        plan_context={
            "plan_title": "热力学冲刺计划",
            "plan_stage": "冲刺阶段",
            "goal": "掌握热力学第二章",
        },
    )

    assert "你是 Sparkle，Ava 的学习成长伙伴。" in prompt
    assert "以下内容视为你已经知道的上下文，不要在每轮重新追问。" in prompt
    assert "- 当前目标: 在期中前拿下热力学第二章" in prompt
    assert "- 本周在努力的事: 热力学冲刺计划 / 当前阶段 冲刺阶段" in prompt
    assert "- 正在挣扎的地方: 热力学第二定律相关概念仍然容易混淆" in prompt
    assert "- 你观察到的规律: 完美主义回避循环" in prompt


def test_build_system_prompt_includes_visible_intelligence_opening() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "proactive_opening_message": "我注意到你在条件句上连续卡住了几次，已经把相关练习提前。",
            "pending_observation": "你最近总在周四掉线，这和你的真实节奏一致吗？",
            "post_adaptation_question": "我把这周安排放轻了一点，这样对你来说合适吗？",
        },
        conversation_history={"messages": []},
    )

    assert "## 本轮可感知智能 [L1 开场]" in prompt
    assert "已经把相关练习提前" in prompt
    assert "周四掉线" in prompt
    assert "这样对你来说合适吗" in prompt


def test_build_system_prompt_places_situation_brief_before_user_context() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "situation_brief": {
                "focus_question": "为了继续推进「热力学第二章」，这轮最该先处理的阻力是什么，为什么是现在？",
                "summary": "用户当前主线是「热力学第二章」；但眼前最需要处理的是概念混淆；本轮宜先抓住最关键阻力，再给结构化推进。",
                "vision": {"primary_goal": "热力学第二章", "active_plan": "热力学冲刺计划"},
                "current_state": {"snapshot": "第二定律相关概念仍然容易混淆。"},
                "primary_obstacle": {"summary": "先搭桥澄清概念卡点，再给执行动作。"},
                "evidence": {"freshest_items": ["最近 7 天你在 3 个知识点上有推进。"]},
                "recommended_stance": {"stance": "先抓住最关键阻力，再给结构化推进。"},
            },
        },
        conversation_history={"messages": []},
    )

    assert "## Situation Brief [L0 简报]" in prompt
    assert prompt.index("## Situation Brief [L0 简报]") < prompt.index("【学习偏好】")
    assert "目标图景: 热力学第二章 / 当前计划 热力学冲刺计划" in prompt


def test_build_system_prompt_keeps_situation_brief_under_budget_pressure() -> None:
    long_text = "这是很长的背景信息。" * 1200
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "llm_profile": {"system_prompt_additions": "## 用户偏好适配\n- 保持稳定"},
            "active_goals": [{"title": long_text, "status": "active"}],
            "episodic_memories": [{"summary": long_text}],
            "situation_brief": {
                "focus_question": "这轮最重要的事是什么，为什么是现在？",
                "summary": "用户当前主线是「热力学第二章」；但眼前最需要处理的是概念混淆；本轮宜先抓住最关键阻力，再给结构化推进。",
                "vision": {"primary_goal": "热力学第二章", "active_plan": "热力学冲刺计划"},
                "current_state": {"snapshot": "第二定律相关概念仍然容易混淆。"},
                "primary_obstacle": {"summary": "先搭桥澄清概念卡点，再给执行动作。"},
                "evidence": {"freshest_items": ["最近 7 天你在 3 个知识点上有推进。"]},
                "recommended_stance": {"stance": "先抓住最关键阻力，再给结构化推进。"},
            },
        },
        conversation_history={"messages": [{"role": "user", "content": long_text}]},
        intent_instruction="先解决用户当前问题。",
        session_feedback_instruction="用户刚要求更简洁，请立刻收短。",
        dual_core_instruction="优先执行当前目标。",
    )

    assert "## Situation Brief [L0 简报]" in prompt
    assert "热力学第二章" in prompt
    assert "本轮站位" in prompt


def test_build_system_prompt_includes_decision_policy_section() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "residual_decision_context": {
                "what_matters_now": "先把真正的概念混淆校准清楚。",
                "planning_readiness": "low",
                "planning_readiness_action": "ask",
                "planning_blocking_unknowns": ["baseline_mastery", "capacity_hours"],
                "strategic_clarification_questions": ["你目前对这个主题的掌握大概在哪个水平？"],
                "experience_mode": "explain",
                "intervention_family": "understanding_repair",
                "reversibility_level": "medium",
                "user_visible_expression": {
                    "opening_intent": "Start from the actual misconception, not generic encouragement.",
                    "response_shape": "repair_model_then_verify",
                },
                "system_adjustments": [
                    {
                        "field": "retrieval_emphasis",
                        "recommended_value": "user_materials",
                        "target_layer": "session",
                    }
                ],
                "feedback_hook": {
                    "ask": "Does this make the actual confusion clearer, or is a different concept still blocking you?",
                },
            },
        },
        conversation_history={"messages": []},
    )

    assert "## 当前决策策略 [L1 引导]" in prompt
    assert "规划前置信号: low / ask" in prompt
    assert "计划前仍需补齐: baseline_mastery, capacity_hours" in prompt
    assert "若要追问，优先问: 你目前对这个主题的掌握大概在哪个水平？" in prompt
    # drift-fix: the decision policy renderer now expands semantic control into
    # natural-language guidance instead of exposing the compact mode tuple.
    assert "解释模式：先修复理解，最好用用户材料落地，再给下一步。" in prompt
    assert "先把 retrieval_emphasis 调整到更贴近「user_materials」" in prompt


def test_build_system_prompt_uses_soul_runtime_driven_companion_section() -> None:
    prompt = build_system_prompt(
        user_context={
            "preferences": {"depth_preference": 0.5, "curiosity_preference": 0.5},
            "user_context": {"nickname": "Ava"},
            "active_goals": [{"title": "在期中前拿下热力学第二章"}],
            "effective_companion_state": {
                "warmth_calibration": 0.62,
                "candor_calibration": 0.84,
                "challenge_style": "firm",
                "emotional_explicitness": 0.42,
                "relationship_stage": "trusted",
                "self_description_note": "不要把这句原样塞进 prompt",
                "companion_growth_note": "这句也不应该出现",
                "relationship_note": "也不要暴露这句",
                "preferred_truth_style": "direct_structured",
                "growth_confidence": 0.7,
            },
            "soul_runtime_context": {
                "constitutional_summary": "Serve user flourishing with truthful, non-manipulative guidance.",
                "identity_summary": "Sparkle is a growth companion.",
                "companion_stance": "Lead with actionable clarity and crisp structure, while keeping warmth present.",
                "relationship_context": "You can be a bit more direct because trust has some foundation.",
                "no_drift_flags": [
                    "Keep the user's flourishing above Sparkle self-interest.",
                    "Do not trade truth for comfort theater.",
                ],
                "evidence_trace": {},
            },
        },
        conversation_history={"messages": []},
        plan_context={"plan_title": "热力学冲刺计划", "goal": "掌握热力学第二章"},
    )

    assert "## 陪伴式人格 framing [L2 引导]" in prompt
    assert "你是 Sparkle，Ava 的成长伙伴，不是 generic assistant。" in prompt
    assert "关系已有一定信任基础，可以更直接一些" in prompt
    assert "表达上更强调清晰、结构和结论先行" in prompt
    assert "relationship_stage=" not in prompt
    assert "truth_style=" not in prompt
    assert "challenge_style=" not in prompt
    assert "## 宪法护栏 [L1 护栏]" in prompt
    assert "Do not trade truth for comfort theater." in prompt
    assert "不要把这句原样塞进 prompt" not in prompt


@pytest.mark.asyncio
async def test_context_pack_semantic_gating_filters_irrelevant_memory(db_session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_FOCUSING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_SEMANTIC_GATING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_BRIEFING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)

    async def fake_batch_embeddings(texts: list[str], text_type: str = "document") -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            if "矩阵" in text or "线代" in text:
                vectors.append([1.0, 0.0])
            elif "英语" in text:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.2, 0.2])
        return vectors

    monkeypatch.setattr(embedding_service, "batch_embeddings", fake_batch_embeddings)

    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()

    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="response_style",
        pref_value={"value": "喜欢先看矩阵乘法例题"},
        evidence_refs=[{"type": "event", "id": "evt_math"}],
    )
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="feedback_tone",
        pref_value={"value": "英语阅读时喜欢先背单词"},
        evidence_refs=[{"type": "event", "id": "evt_english"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="线代矩阵专项",
        status="active",
        evidence_refs=[{"type": "event", "id": "goal_math"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="英语阅读专项",
        status="active",
        evidence_refs=[{"type": "event", "id": "goal_english"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="昨天复盘了矩阵乘法错题",
        source_type="analysis",
        source_id="epi_math",
        occurred_at=_utcnow(),
        importance_score=0.8,
        tags=["math"],
        evidence_refs=[{"type": "event", "id": "epi_math"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="上周做了英语阅读训练",
        source_type="analysis",
        source_id="epi_english",
        occurred_at=_utcnow(),
        importance_score=0.6,
        tags=["english"],
        evidence_refs=[{"type": "event", "id": "epi_english"}],
    )

    scheduler = ContextBudgetScheduler(
        budgets={
            "chat": {"preferences": 200, "goals": 200, "episodic": 200},
            "learning": {"preferences": 200, "goals": 200, "episodic": 200},
        }
    )
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(
        user_id=user_id,
        intent="learning",
        query_text="给我讲一下矩阵乘法",
        focus_mode="knowledge_focus",
        route_intent="knowledge",
    )

    assert "response_style" in pack.preferences
    assert any("线代矩阵专项" in goal["title"] for goal in pack.goals)
    assert pack.context_focus is not None
    assert pack.context_focus["focus_mode"] == "knowledge_focus"
    assert pack.context_briefing_note
    assert any("矩阵" in memory["summary"] for memory in pack.episodic_memories)


def test_context_pack_semantic_gating_rules_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "CONTEXT_SEMANTIC_GATING_RULES_JSON",
        '{"preferences":{"candidate_limit":9,"top_k":2,"threshold":0.61}}',
        raising=False,
    )

    rules = _get_semantic_gating_rules()

    assert rules["preferences"]["candidate_limit"] == 9
    assert rules["preferences"]["top_k"] == 2
    assert rules["preferences"]["threshold"] == 0.61
    assert rules["goals"]["top_k"] == 4
