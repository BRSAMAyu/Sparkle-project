"""REDFLAG5 裁决守卫 — goals 跨通道回填边界归属（裁决=合法，钉死防劣化不变量）。

裁决对象：GAIN-EVAL §5 红旗 5（原 wt198 基线 prompts.py:4479-4484，基线 490acf7a
上为 prompts.py:4501-4507「Canonical insight state enrichment」goals 回填）——
canonical insight（画像编译态）的 goals 在注入面 active_goals 为空时可回填进
【当前目标】渲染面。wt205 同型扫描判「非捏造，登记备查留裁决」，本卡裁决为
**合法**（裁决链全文见 v3-output/REDFLAG5/REPORT.md）：

- 回填源 = UserInsightCompiler 编译态 goals，仅来自**真实记录事实**
  （preferences.learning_goal_type/goal_type、preferences.exam_urgency、
  knowledge_summary.active_learning_subjects、日历 exam_urgency），零数据用户
  goals==[] → 回填不触发（诚实空态）；
- 语义类别权威（context_sources.py，C-02/USER_WORLD_MODEL）：goal/active_goals/
  profile 皆 **state**（Current State，「类别按语义对象，不按表名」）——
  画像→goals 槽是 state→state 的同类事实回填，非四类边界穿越；
- M-05「降档条目正文不回灌」辖**记忆闸降档的 memory 记录**；画像编译态事实
  未过记忆闸、非被裁正文 → 不构成回灌违背；
- 回填为 fallback-only（only-if-missing，[:3] 截断），主通道（stage34 Plan 面 /
  context_pack MemoryGoal 面）在场时绝不覆盖。

本文件钉死三条防劣化不变量（未来任何一条变红 = 回填面正在劣化为捏造面/
覆盖面，必须回裁决）：
1. provenance：编译器产出的每个 goal 条目必带 source ∈ 封闭真实事实词表
   （AST 钉，M-05 wiring 同法），且 label/type 键在场（防空标题条目进 prompt）；
2. 零数据诚实空态：空 goals → 不回填、不造默认 goal，prompt 无目标断言；
3. fallback-only：主通道 payload 全形状保留，绝不覆盖/合并。
"""

from __future__ import annotations

import ast
from pathlib import Path

import app.services.user_insight_compiler as _compiler_mod
from app.core.profile_context import CognitiveSummary, KnowledgeSummary, ProfileContext
from app.core.user_insight_state import UserInsightState
from app.orchestration.prompts import _normalize_user_context, build_system_prompt
from app.services.user_insight_compiler import UserInsightCompiler

# V3-FIX-120：锚定模块真实文件（原 cwd 相对路径 + parents[1] 兜底在 CI 从仓库根
# 跑全量时解析成 backend/tests/app/... FileNotFoundError）
COMPILER_MODULE_PATH = Path(_compiler_mod.__file__).resolve()

#: 封闭真实事实出处词表（=编译器全部合法 goal 来源）。扩展必须先过裁决：
#: 新 source 必须能证明「来自真实用户记录」而非推断/默认值，并同步本词表。
REAL_FACT_GOAL_SOURCES = frozenset({"preferences", "knowledge_summary", "exam_urgency"})


def _goal_emitter_dict_literals() -> list[tuple[int, ast.Dict]]:
    """收集编译器模块内所有 `goals.append({...})` / `state.goals.append({...})` 的字面量。"""
    tree = ast.parse(COMPILER_MODULE_PATH.read_text(encoding="utf-8"))
    found: list[tuple[int, ast.Dict]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "append":
            continue
        target = node.func.value
        is_goal_target = (isinstance(target, ast.Name) and target.id == "goals") or (
            isinstance(target, ast.Attribute) and target.attr == "goals"
        )
        if not is_goal_target:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                found.append((node.lineno, arg))
    return found


# ---------------------------------------------------------------------------
# 不变量 1：provenance —— 编译器 goal 条目只能来自真实记录事实（AST 钉 + 行为钉）
# ---------------------------------------------------------------------------


def test_compiler_goal_emitters_carry_real_fact_provenance_ast_pin() -> None:
    """AST 钉（M-05 wiring 同法）：每个 goal 产出点必带真实事实 source + label/type。

    词表/产出点数被冻结：新增 goal emitter 或换 source 必须显式过本测试改钉——
    这是「回填面劣化成捏造面」的 tripwire（无 source 的推断型 goal 一律拦下）。
    """
    emitters = _goal_emitter_dict_literals()
    # 封闭产出点：_build_base_state 3 处（goal:primary / goal:exam_window /
    # goal:active_subjects）+ _apply_calendar_signals 1 处（goal:exam_pressure）。
    assert len(emitters) == 4, (
        "UserInsightCompiler 的 goal 产出点数变化（登记=4）：新增产出点必须携带 "
        "真实事实 source 并同步本钉（防未申报的推断型 goal 进入画像回填面）"
    )
    for lineno, dict_node in emitters:
        pairs = {
            k.value: v for k, v in zip(dict_node.keys, dict_node.values, strict=False) if isinstance(k, ast.Constant)
        }
        assert "source" in pairs, f"goal emitter @L{lineno} 缺 source（真实事实出处必标）"
        source_value = pairs["source"]
        assert isinstance(source_value, ast.Constant) and source_value.value in REAL_FACT_GOAL_SOURCES, (
            f"goal emitter @L{lineno} 的 source={source_value.value!r} 不在真实事实词表 "
            f"{sorted(REAL_FACT_GOAL_SOURCES)}（推断/默认值来源禁入画像回填面）"
        )
        assert {"label", "type"} & set(pairs), f"goal emitter @L{lineno} 缺 label/type（防空标题条目进 prompt 目标面）"


def test_base_state_goal_sources_behavioral_pin() -> None:
    """行为钉：_build_base_state 三种画像输入下 goals 均源自真实事实或诚实为空。"""
    compiler = UserInsightCompiler(db=None)  # _build_base_state 零 I/O，不触 db

    # (a) 声明型事实：goal_type + exam_urgency → 2 条，source 全在词表
    declared = ProfileContext(
        preferences={
            "learning_goal_type": "考研",
            "exam_urgency": {"days_left": 30, "urgency": "high"},
        },
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.5, weak_spots=[], recent_mastery_changes=[], active_learning_subjects=[]
        ),
        cognitive_summary=CognitiveSummary(active_patterns=[], dominant_pattern_type=None, risk_signals=[]),
    )
    state = compiler._build_base_state(profile_context=declared)
    assert [g["id"] for g in state.goals] == ["goal:primary", "goal:exam_window"]
    assert all(g["source"] in REAL_FACT_GOAL_SOURCES for g in state.goals)
    assert all(str(g.get("label") or "").strip() for g in state.goals)

    # (b) 回退事实：无声明 goal 时由真实在学科目派生 learning_scope，仍带事实出处
    fallback = ProfileContext(
        preferences={},
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.5, weak_spots=[], recent_mastery_changes=[], active_learning_subjects=["高数", "线代"]
        ),
        cognitive_summary=CognitiveSummary(active_patterns=[], dominant_pattern_type=None, risk_signals=[]),
    )
    state_fb = compiler._build_base_state(profile_context=fallback)
    assert len(state_fb.goals) == 1
    assert state_fb.goals[0]["source"] == "knowledge_summary"
    assert state_fb.goals[0]["label"] == "高数 / 线代"

    # (c) 零事实：goals 诚实为空（源端不造默认 goal）
    zero = ProfileContext(
        preferences={},
        preference_version=1,
        knowledge_summary=KnowledgeSummary(
            overall_mastery=0.0, weak_spots=[], recent_mastery_changes=[], active_learning_subjects=[]
        ),
        cognitive_summary=CognitiveSummary(active_patterns=[], dominant_pattern_type=None, risk_signals=[]),
    )
    assert compiler._build_base_state(profile_context=zero).goals == []


# ---------------------------------------------------------------------------
# 不变量 2：零数据诚实空态 —— 空 goals 不回填、不造默认 goal
# ---------------------------------------------------------------------------


def test_backfill_zero_data_user_honest_empty_no_default_goal() -> None:
    """零数据用户（goals=[]）：回填绝不触发，prompt 无任何目标断言（诚实空态）。

    红证方向：若回填面未来劣化为「空数据也注入默认/推断目标」（GAIN-EVAL 红旗 1
    同型捏造），本测试即红。
    """
    insight = UserInsightState()  # 零数据编译态：goals=[]
    normalized = _normalize_user_context({"user_insight_state": insight})
    assert "active_goals" not in normalized, "零数据用户不得被回填出 active_goals（诚实空态）"

    prompt = build_system_prompt(
        user_context={"user_insight_state": insight},
        conversation_history={"messages": []},
    )
    assert "【当前目标】" not in prompt
    assert "当前目标:" not in prompt


# ---------------------------------------------------------------------------
# 不变量 3：fallback-only —— 主通道在场时绝不覆盖
# ---------------------------------------------------------------------------


def test_backfill_never_overrides_primary_channel_payload() -> None:
    """stage34/pack 主通道的 active_goals 全形状保留（id/progress 等字段不动）。"""
    stage34_goal = {
        "id": "plan-1",
        "title": "高数期中冲刺",
        "status": "active",
        "type": "exam",
        "plan_stage": "sprint",
        "subject": "math",
        "target_date": "2026-09-30",
        "progress": 0.42,
    }
    insight = UserInsightState(
        goals=[{"id": "goal:primary", "type": "考研", "label": "考研上岸", "source": "preferences"}]
    )
    normalized = _normalize_user_context({"user_insight_state": insight, "active_goals": [stage34_goal]})
    assert normalized["active_goals"] == [stage34_goal], "主通道在场时回填必须让位（fallback-only）"


# ---------------------------------------------------------------------------
# 回填内容边界：只消费编译态 label，[:3] 截断，状态恒 active
# ---------------------------------------------------------------------------


def test_backfill_entries_bounded_to_compiled_labels() -> None:
    """回填条目标题 ⊆ 编译态 goals 的 label/type 投影；[:3] 截断；状态恒 active。"""
    compiled_goals = [
        {"id": "goal:primary", "type": "考研", "label": "考研上岸", "source": "preferences"},
        {"id": "goal:exam_window", "type": "exam_window", "label": "30 days left", "source": "preferences"},
        {
            "id": "goal:active_subjects",
            "type": "learning_scope",
            "label": "高数 / 线代",
            "source": "knowledge_summary",
        },
        {"id": "goal:exam_pressure", "type": "exam_window", "label": "Exam in 9 days", "source": "exam_urgency"},
    ]
    normalized = _normalize_user_context({"user_insight_state": UserInsightState(goals=compiled_goals)})

    backfilled = normalized["active_goals"]
    assert len(backfilled) == 3, "回填上限 [:3]（第四条截断）"
    compiled_projections = {str(g.get("label") or g.get("type") or "") for g in compiled_goals}
    assert all(g["title"] in compiled_projections for g in backfilled), "回填标题只能来自编译态事实投影"
    assert all(g.get("status") == "active" for g in backfilled)
    assert all("id" not in g for g in backfilled), "回填条目无记忆记录 id（不冒充 MemoryGoal 记录）"


# ---------------------------------------------------------------------------
# 阳性对照：合法回填必须照常渲染（防守卫误杀合法画像面）
# ---------------------------------------------------------------------------


def test_backfilled_goal_renders_current_goal_section_positive_control() -> None:
    """有真实 goal 事实的零 Plan 用户：【当前目标】照常落节（合法回填不误伤）。"""
    insight = UserInsightState(
        goals=[{"id": "goal:primary", "type": "考研", "label": "考研上岸", "source": "preferences"}]
    )
    prompt = build_system_prompt(
        user_context={"user_insight_state": insight},
        conversation_history={"messages": []},
    )
    assert "【当前目标】" in prompt
    assert "- 考研上岸 (active)" in prompt
