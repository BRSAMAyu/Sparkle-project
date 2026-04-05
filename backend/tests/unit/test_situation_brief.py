import pytest

from app.orchestration.residual_diagnosis import ResidualDiagnosisRuntime
from app.orchestration.situation_brief import SituationBriefBuilder, format_situation_brief_section
from app.semantic.state_primitives import StudyDomainSemanticAdapter


@pytest.mark.asyncio
async def test_situation_brief_builder_uses_existing_context_sources() -> None:
    brief = (await SituationBriefBuilder().build(
        user_context_payload={
            "learning_gaps_summary": "热力学第二定律相关概念仍然容易混淆。",
            "context_focus": {
                "focus_mode": "knowledge_focus",
                "route_intent": "knowledge",
            },
            "profile_context": {
                "knowledge_summary": {
                    "weak_spots": [
                        {"node_id": "thermo-entropy-direction", "node_name": "熵增方向判断", "mastery": 42},
                    ],
                    "recent_mastery_changes": [
                        {
                            "node_id": "thermo-efficiency",
                            "node_name": "热机效率",
                            "old_mastery": 31,
                            "new_mastery": 46,
                            "changed_at": "2026-04-04T08:30:00",
                        }
                    ],
                    "active_learning_subjects": ["热力学", "数学"],
                },
                "cognitive_summary": {
                    "active_patterns": [
                        {
                            "pattern_name": "完美主义回避循环",
                            "pattern_type": "execution",
                            "confidence": 0.76,
                        }
                    ]
                },
            },
            "active_goals": [{"title": "在期中前拿下热力学第二章"}],
            "evolution_highlights": ["最近 7 天你在 3 个知识点上有推进。"],
            "active_interventions": [
                {
                    "intervention_id": "iv-1",
                    "label": "降载微调",
                    "acceptance_status": "accepted",
                    "source": "pending_record",
                }
            ],
            "last_feedback_binding": {
                "intervention_id": "iv-1",
                "sentiment": "helped",
                "user_words": "这样轻一点我就能开始了。",
            },
            "validated_outcome_learning": {
                "plan_generation_hints_from_outcomes": ["Default to a lighter first step."],
                "known_failure_avoidance_rules": ["Avoid dense first steps when similar conditions recur."],
                "validated_learnings": [{"learning_key": "dense_first_step_overloads_user"}],
            },
        },
        plan_context={
            "plan_title": "热力学冲刺计划",
            "goal": "掌握热力学第二章",
            "plan_stage": "冲刺阶段",
        },
        focused_memory={},
        context_briefing_note="当前重点：先补第二定律，再推进题目训练。",
        visible_update_context={
            "proactive_opening_message": "我注意到你最近在条件判断题上连续卡住了几次。",
        },
        dual_core_snapshot={
            "decision": {"mode": "balanced"},
            "signal_snapshot": {"current_guidance": "先搭桥澄清概念卡点，再给执行动作。"},
            "prompt_instruction": "优先澄清概念，再推进执行。",
        },
        session_feedback_signal={"signal_type": "simplify"},
        progress_snapshot={
            "highlights": ["最近 7 天你在 3 个知识点上有推进。"],
            "attention_areas": ["知识掌握推进速度比上一周期慢了一些。"],
            "generated_at": "2026-04-04T09:00:00",
        },
        adaptation_records=[{"strategy_name": "降载微调", "effectiveness": "accepted"}],
    )).to_dict()

    assert "在期中前拿下热力学第二章" in brief["focus_question"]
    assert brief["summary"].startswith("目标图景是")
    assert brief["vision"]["active_plan"] == "热力学冲刺计划"
    assert brief["current_state"]["focus_mode"] == "knowledge_focus"
    assert brief["primary_obstacle"]["source"] == "dual_core_signal_snapshot.current_guidance"
    assert brief["intervention"]["active"] is True
    assert brief["outcome"]["status"] == "progressing"
    assert brief["sparkle_self_state"]["dual_core_mode"] == "balanced"
    assert brief["sparkle_self_state"]["confidence_estimate"] > 0.5
    assert brief["decision_context"]["primary_residual"] == "R_e"
    assert brief["decision_context"]["loop_type"] == "truth_seeking"
    assert brief["decision_context"]["grounding_priority"][0] == "user_materials"
    assert brief["decision_context"]["experience_mode"] == "explain"
    assert brief["decision_context"]["intervention_family"] == "understanding_repair"
    assert brief["decision_context"]["system_adjustments"][0]["field"] == "retrieval_emphasis"
    assert brief["decision_context"]["body_awareness_guidance"]["primary_subsystem"]["id"] == "galaxy"
    assert brief["body_map"]["available_organs"]
    assert brief["capability_requirements"]["grounding_required"] == "mandatory"
    assert brief["capability_selection"]["summary"]["retrieval_mode"] == "user_materials_first"
    assert brief["capability_selection"]["model_selection"]["preferred_tier"] in {"standard", "plus"}
    assert brief["decision_context"]["planning_readiness"] in {"medium", "high"}
    assert "progress_snapshot" in brief["source_trace"]["used_sources"]
    assert "outcome_learning" in brief["source_trace"]["used_sources"]
    assert brief["outcome_learning"]["plan_generation_hints_from_outcomes"][0] == "Default to a lighter first step."
    assert brief["source_trace"]["semantic_layer"]["adapter_name"] == StudyDomainSemanticAdapter.adapter_name
    assert "vision" in brief["semantic_primitives"]["source_mapping"]


def test_format_situation_brief_section_renders_compact_prompt_block() -> None:
    section = format_situation_brief_section(
        {
            "focus_question": "为了继续推进「热力学第二章」，这轮最该先处理的阻力是什么，为什么是现在？",
            "summary": "目标图景是「热力学第二章」；当前状态是第二定律相关概念仍然容易混淆；主要阻力是概念混淆；最近证据是最近 7 天你在 3 个知识点上有推进；本轮宜先抓住最关键阻力，再给结构化推进。",
            "vision": {
                "primary_goal": "热力学第二章",
                "active_plan": "热力学冲刺计划",
                "why_now": "考试倒计时 12 天",
            },
            "current_state": {
                "snapshot": "热力学第二定律相关概念仍然容易混淆；最近 7 天你在 3 个知识点上有推进。",
            },
            "primary_obstacle": {
                "summary": "先搭桥澄清概念卡点，再给执行动作。",
            },
            "evidence": {
                "freshest_items": [
                    "最近 7 天你在 3 个知识点上有推进。",
                    "热机效率 最近掌握度变化约 +15.0",
                ]
            },
            "intervention": {
                "summary": "当前正在跟踪的支持动作是「降载微调」，状态 accepted，最近反馈 helped",
            },
            "outcome": {
                "summary": "最近结果信号显示 这样轻一点我就能开始了。",
            },
            "recommended_stance": {
                "stance": "先抓住最关键阻力，再给结构化推进。",
            },
            "decision_context": {
                "what_matters_now": "先找出真正没想通的点，并用用户材料把概念校准清楚。",
                "primary_residual_label": "cognitive",
                "loop_type": "truth_seeking",
                "confidence_label": "high",
                "experience_mode": "explain",
                "intervention_family": "understanding_repair",
                "reversibility_level": "medium",
                "planning_readiness": "low",
                "planning_readiness_action": "ask",
                "planning_blocking_unknowns": ["baseline_mastery", "capacity_hours"],
                "strategic_clarification_questions": ["你目前对这个主题的掌握大概在哪个水平？"],
                "body_awareness_guidance": {
                    "primary_subsystem": {
                        "label": "Galaxy Knowledge Systems",
                        "why": "This turn benefits from grounded retrieval and structure-aware knowledge support.",
                    }
                },
            },
        }
    )

    assert "## Situation Brief [L0 简报]" in section
    assert "目标图景: 热力学第二章 / 当前计划 热力学冲刺计划" in section
    assert "最新证据" in section
    assert "当前干预" in section
    assert "最近结果" in section
    assert "当前判断" in section
    assert "规划就绪度" in section
    assert "计划前仍需补齐" in section
    assert "优先澄清问题" in section
    assert "残差诊断" in section
    assert "决策策略" in section
    assert "当前优先调用的系统器官: Galaxy Knowledge Systems" in section
    assert "本轮站位" in section


def test_residual_diagnosis_runtime_detects_normative_loop() -> None:
    diagnosis = ResidualDiagnosisRuntime().diagnose(
        user_context_payload={
            "current_query": "I do not want the answer. Help me decide whether I should drop this course.",
        },
        plan_context={"plan_title": "Course recovery"},
        context_briefing_note="User wants help deciding between staying and withdrawing.",
        visible_update_context={},
        session_feedback_signal={},
        user_strategy_state={"session_mode": "guided"},
        vision={"primary_goal": "Protect GPA"},
        current_state={"route_intent": "decision", "focus_mode": "general_focus"},
        primary_obstacle={"summary": "The user is torn between two futures.", "obstacle_type": "alignment_gap"},
        evidence={"summary": "They have conflicting priorities."},
        intervention={},
        outcome={},
        sparkle_self_state={"confidence_estimate": 0.72},
    ).to_dict()

    assert diagnosis["primary_residual"] == "R_n"
    assert diagnosis["loop_type"] == "normative"
    assert diagnosis["grounding_priority"][0] == "user_values_and_constraints"


def test_five_layer_growth_summary_reports_active_and_inactive_outcome_learning_states() -> None:
    summary = SituationBriefBuilder()._build_five_layer_growth_summary(
        user_context={
            "layer_alignment": {
                "contract_version": "2026-04-05.phase_e.v1",
                "active_conflicts": [{"conflict_id": "companion-conflict"}],
                "stale_items": [],
            },
            "user_strategy_state": {"meta": {}},
        },
        outcome_learning={
            "active_validated_learnings": [{"learning_key": "grounded_plans_work_better"}],
            "inactive_validated_learnings": [
                {"learning_key": "dense_first_step_overloads_user", "governance_status": "demoted"},
                {"learning_key": "needs_revalidation", "governance_status": "review_due"},
            ],
            "pending_reviews": [{"learning_key": "needs_revalidation", "status": "review_due"}],
            "stale_items": [
                {"learning_key": "needs_revalidation", "status": "review_due"},
                {"learning_key": "expired_pattern", "status": "stale"},
            ],
            "shared_conflict_reports": [{"conflict_id": "outcome-conflict"}],
            "governance_summary": {
                "policy": {
                    "effective_runtime_statuses": ["active"],
                    "inactive_runtime_statuses": ["blocked", "demoted", "review_due", "stale"],
                    "review_due_runtime_policy": "exclude_until_revalidated",
                }
            },
            "episode_layer_active": True,
            "profile_layer_active": False,
        },
        registry={"system_layer_knobs": [{"id": "session_mode"}]},
        capability_selection={"bounded_adjustments": [{"field": "session_mode"}]},
    )

    assert summary["active_conflict_count"] == 2
    assert summary["review_due_count"] == 1
    assert summary["stale_item_count"] == 2
    assert summary["outcome_learning_state"]["active_learning_count"] == 1
    assert summary["outcome_learning_state"]["inactive_learning_count"] == 2
    assert summary["outcome_learning_state"]["review_due_count"] == 1
    assert summary["outcome_learning_state"]["stale_learning_count"] == 1
    assert summary["outcome_learning_state"]["governance_policy"]["review_due_runtime_policy"] == "exclude_until_revalidated"


@pytest.mark.asyncio
async def test_situation_brief_compiles_decision_policy_for_control_overload() -> None:
    brief = (await SituationBriefBuilder().build(
        user_context_payload={
            "current_query": "This is too much and I still cannot start.",
            "context_focus": {"focus_mode": "general_focus", "route_intent": "chat"},
            "user_strategy_state": {
                "difficulty_level": 4,
                "session_mode": "guided",
                "intervention_intensity": "medium",
                "push_vs_support": 0.6,
            },
            "profile_context": {
                "cognitive_summary": {
                    "active_patterns": [
                        {"pattern_name": "启动困难", "pattern_type": "execution", "confidence": 0.83}
                    ]
                }
            },
        },
        plan_context={"plan_title": "Thermo sprint", "goal": "Finish thermo review"},
        focused_memory={},
        context_briefing_note="User is overloaded and struggling to start.",
        visible_update_context={},
        dual_core_snapshot={"decision": {"mode": "execution_first"}},
        session_feedback_signal={},
        progress_snapshot={"attention_areas": ["Load is too high this week."]},
        adaptation_records=[],
    )).to_dict()

    decision_context = brief["decision_context"]
    assert decision_context["experience_mode"] == "stabilize"
    assert decision_context["intervention_family"] == "load_shedding"
    assert decision_context["system_adjustments"][0]["field"] == "session_mode"
    assert decision_context["system_adjustments"][0]["recommended_value"] == "recovery"


@pytest.mark.asyncio
async def test_situation_brief_uses_phase_a_gate_to_force_clarify_before_planning() -> None:
    brief = await SituationBriefBuilder().build(
        user_context_payload={
            "current_query": "帮我做一个两周内通过热力学考试的计划。",
            "context_focus": {"focus_mode": "knowledge_focus", "route_intent": "plan"},
            "profile_context": {
                "knowledge_summary": {
                    "overall_mastery": 0.0,
                    "weak_spots": [],
                    "recent_mastery_changes": [],
                    "active_learning_subjects": [],
                },
                "cognitive_summary": {
                    "active_patterns": [],
                    "dominant_pattern_type": None,
                    "risk_signals": [],
                },
            },
        },
        plan_context={},
        focused_memory={},
        context_briefing_note=None,
        visible_update_context={},
        dual_core_snapshot={},
        session_feedback_signal={},
        adaptation_records=[],
    )

    assert brief.insight_state["readiness_level"] == "low"
    assert brief.decision_context["planning_readiness"] == "low"
    assert brief.decision_context["planning_readiness_action"] == "ask"
    assert brief.decision_context["experience_mode"] == "clarify"
    assert brief.decision_context["phase_a_guardrail"] == "ask_before_plan"
    assert brief.decision_context["strategic_clarification_questions"]


@pytest.mark.asyncio
async def test_situation_brief_selects_specialist_path_when_error_diagnosis_is_required() -> None:
    brief = await SituationBriefBuilder().build(
        user_context_payload={
            "current_query": "Help me debug the root cause of why I keep missing the sign in this thermodynamics derivation.",
            "context_focus": {"focus_mode": "knowledge_focus", "route_intent": "error_diagnosis"},
            "profile_context": {
                "knowledge_summary": {"overall_mastery": 0.52},
                "cognitive_summary": {"active_patterns": []},
            },
            "attached_materials": [{"file_id": "file-1"}],
        },
        plan_context={},
        focused_memory={},
        context_briefing_note="User wants a root-cause diagnosis, not a generic explanation.",
        visible_update_context={},
        dual_core_snapshot={},
        session_feedback_signal={},
        adaptation_records=[],
    )

    assert brief.capability_requirements["specialization_required"] is True
    assert brief.capability_selection["summary"]["specialist_strategy"] == "specialist_required"
    assert brief.capability_selection["specialist_selection"]["selected_experts"]
    assert "mandatory" == brief.capability_requirements["grounding_required"]
