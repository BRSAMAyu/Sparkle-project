"""D-06 · WVPL 北极星查询服务守卫（sqlite 隔离，不触 dev DB）。

覆盖验收项（卡面 + 派单）：
- 固定 fixture → 确定性结果（分子/分母/比率逐数字断言）；
- 边界：跨周（半开窗口）、重复 event（重复查询/多条回声不双计）、
  撤销 outcome（文件证据撤销 → actual 回落 → loop 消失）；
- 历史/seed/demo cohort 分离（seed 用户的 loop 永不混入生产数字）；
- 幂等：同 as_of 复跑 → canonical JSON 逐字节一致；as_of 漂移 → 窗口成员变化；
- 零模型参与（代码级 pin：查询层源码无 LLM 基础设施引用）；
- 词表一致 pin：谓词引用的 D-02 冻结常量值不被复制漂移。
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.core.north_star_wvpl import (
    GOAL_STALL_THRESHOLD_DAYS,
    WINDOW_DAYS,
    WVPL_CALIBER_VERSION,
    WVPL_FACT_SCHEMA,
)
from app.core.outcome_ledger import ECHO_STUDY_RECORD_TYPES, QUIZ_FEEDBACK_SOURCES
from app.models.chat import ChatMessage, MessageRole
from app.models.file_storage import StoredFile
from app.models.intervention_adaptive import BehavioralOutcome
from app.services.north_star_wvpl_service import NorthStarWvplService, canonical_fact_json
from app.services.outcome_ledger_service import EXCLUDED_COHORT_REGISTRATION_SOURCES
from tests.golden.north_star_wvpl_fixture import (
    AS_OF as _AS_OF,
)
from tests.golden.north_star_wvpl_fixture import (
    WINDOW_START as _WINDOW_START,
)
from tests.golden.north_star_wvpl_fixture import (
    build_standard_fixture as _build_standard_fixture,
)
from tests.golden.north_star_wvpl_fixture import (
    echo as _echo,
)
from tests.golden.north_star_wvpl_fixture import (
    file_evidence as _file_evidence,
)
from tests.golden.north_star_wvpl_fixture import (
    make_goal_plan as _make_goal_plan,
)
from tests.golden.north_star_wvpl_fixture import (
    make_user as _make_user,
)
from tests.golden.north_star_wvpl_fixture import (
    task as _task,
)

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# 固定 fixture 的确定性数字
# ---------------------------------------------------------------------------


async def test_fixed_fixture_deterministic_numbers(db_session):
    fx = await _build_standard_fixture(db_session)
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)

    assert fact["schema"] == WVPL_FACT_SCHEMA
    assert fact["caliber_version"] == WVPL_CALIBER_VERSION
    assert fact["window"] == {
        "start": (_AS_OF - timedelta(days=WINDOW_DAYS)).isoformat(),
        "end": _AS_OF.isoformat(),
        "days": WINDOW_DAYS,
        "half_open": "[start, end)",
    }
    # 北极星：分母保留，比率不伪造
    ns = fact["north_star"]
    assert ns["active_users"] == 3  # alice, bob, carol（dave 无信号，seed 在 demo face）
    assert ns["wvpl_users"] == 1  # 只有 alice 有 loop（bob 缺 state 腿）
    assert ns["wvpl_ratio"] == 0.3333
    assert ns["loops_total"] == 2  # T1 + T2（两条回声不双计）
    assert ns["loops_per_wvpl_user"] == 2.0

    # outcome types（五源，同因合并：回声 study_record 并入 task 证据，不独立计数）
    assert fact["outcomes"]["by_source"] == {
        "task_completion": 4,  # T1, T2, T3, T5
        "study_record": 0,
        "focus_session": 2,  # T2、T5 的 focus（standalone 行为观察）
        "quiz_feedback": 0,
        "behavioral": 0,
    }
    tc = fact["outcomes"]["truth_coverage"]
    assert (tc["total"], tc["actual"], tc["self_reported"], tc["unknown"]) == (4, 3, 1, 0)
    assert tc["actual_ratio"] == 0.75
    # action→outcome conversion（goal-linked 面）：T1/T2/T5 全 actual
    conv = fact["outcomes"]["action_outcome_conversion"]
    assert conv == {"goal_linked_completions": 3, "actual": 3, "ratio": 1.0}

    # loop 溯源样本：可回查 outcome_id + task/plan/goal ref
    samples = fact["loops"]["samples"]
    assert len(samples) == 2
    by_task = {s["task_id"]: s for s in samples}
    assert set(by_task) == {str(fx["t1"].id), str(fx["t2"].id)}
    t1_sample = by_task[str(fx["t1"].id)]
    assert t1_sample["goal_id"] == str(fx["alice_goal"].id)
    assert t1_sample["outcome_id"].startswith("outc_")
    assert t1_sample["source_ref"] == f"task://{fx['t1'].id}"

    # 有界全史：alice 的旧 loop T4 在窗口外、只进全史
    assert fact["loops"]["all_time_bounded"] == {"loops_total": 3, "truncated": False}

    # cohort 分离：seed 用户的 loop 不进生产分子/分母，demo face 单列
    assert fact["cohort"]["excluded_users"] == 1
    assert fact["cohort"]["excluded_users_with_window_signals"] == 1
    assert ns["wvpl_users"] == 1 and ns["loops_total"] == 2

    assert fact["provenance"]["truncated"] is False
    assert fact["provenance"]["outcome_ledger_schema_version"] == "outcome.ledger.v1"


async def test_empty_db_no_fabricated_numbers(db_session):
    """空库：分母 0 → 比率 None（没有分母不伪造比率），无异常。"""
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert fact["north_star"] == {
        "active_users": 0,
        "wvpl_users": 0,
        "wvpl_ratio": None,
        "loops_total": 0,
        "loops_per_wvpl_user": None,
    }
    assert fact["outcomes"]["truth_coverage"]["actual_ratio"] is None
    assert fact["outcomes"]["action_outcome_conversion"]["ratio"] is None
    assert fact["outcome_metrics"]["time_to_first_meaningful_value"]["median_days"] is None
    assert fact["outcome_metrics"]["goal_recovery_after_stall"]["median_recovery_days"] is None


# ---------------------------------------------------------------------------
# 边界：跨周 / 重复 event / 撤销 outcome
# ---------------------------------------------------------------------------


async def test_cross_week_half_open_boundary(db_session):
    """恰在窗口起点 → 计入；恰在窗口终点（=as_of）→ 排除（半开 [start, end)）。"""
    user = await _make_user(db_session)
    goal, plan = await _make_goal_plan(db_session, user)

    async def _loop_at(moment: datetime):
        task = _task(user.id, plan_id=plan.id, completed_at=moment)
        db_session.add(task)
        await db_session.flush()
        await _file_evidence(db_session, user, task)
        db_session.add(_echo(user.id, task_id=task.id, at=moment))
        await db_session.commit()
        return task

    await _loop_at(_WINDOW_START)  # 起点：含
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert fact["north_star"]["loops_total"] == 1

    await _loop_at(_AS_OF)  # 终点：半开不含
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert fact["north_star"]["loops_total"] == 1  # 仍只有起点那条
    assert fact["loops"]["all_time_bounded"]["loops_total"] == 2  # 全史两条都在


async def test_duplicate_events_and_reruns_never_double_count(db_session):
    """重复查询 + 多条回声 study_record → loop 恒为一个（身份 = (task_completion, task_id)）。"""
    user = await _make_user(db_session)
    goal, plan = await _make_goal_plan(db_session, user)
    task = _task(user.id, plan_id=plan.id, completed_at=_AS_OF - timedelta(days=1))
    db_session.add(task)
    await db_session.flush()
    await _file_evidence(db_session, user, task)
    db_session.add(_echo(user.id, task_id=task.id, at=_AS_OF - timedelta(days=1)))
    db_session.add(_echo(user.id, task_id=task.id, at=_AS_OF - timedelta(days=1)))
    await db_session.commit()

    service = NorthStarWvplService(db_session)
    first = await service.build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    second = await service.build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert first["north_star"]["loops_total"] == 1
    assert canonical_fact_json(first) == canonical_fact_json(second)  # 幂等复跑逐字节一致
    assert first["outcomes"]["by_source"]["study_record"] == 0  # 回声不独立计数
    assert first["outcomes"]["by_source"]["task_completion"] == 1


async def test_revoked_outcome_drops_loop(db_session):
    """撤销 outcome：文件证据 revoked（生命周期撤销）→ actual 回落 self_reported → loop 消失。"""
    user = await _make_user(db_session)
    goal, plan = await _make_goal_plan(db_session, user)
    task = _task(user.id, plan_id=plan.id, completed_at=_AS_OF - timedelta(days=1))
    db_session.add(task)
    await db_session.flush()
    await _file_evidence(db_session, user, task)
    db_session.add(_echo(user.id, task_id=task.id, at=_AS_OF - timedelta(days=1)))
    await db_session.commit()

    service = NorthStarWvplService(db_session)
    before = await service.build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert before["north_star"]["loops_total"] == 1
    assert before["outcomes"]["action_outcome_conversion"] == {"goal_linked_completions": 1, "actual": 1, "ratio": 1.0}

    # 撤销：lifecycle_status → revoked（D-02 读模型查询时重算 → 诚实回落）
    from sqlalchemy import select

    stored = (await db_session.execute(select(StoredFile))).scalars().first()
    stored.lifecycle_status = "revoked"
    await db_session.commit()

    after = await service.build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert after["north_star"]["loops_total"] == 0
    assert after["north_star"]["wvpl_users"] == 0
    assert after["outcomes"]["action_outcome_conversion"]["actual"] == 0
    assert after["outcomes"]["action_outcome_conversion"]["ratio"] == 0.0
    assert after["outcomes"]["truth_coverage"]["self_reported"] == 1


# ---------------------------------------------------------------------------
# cohort 分离
# ---------------------------------------------------------------------------


async def test_seed_cohort_never_mixes_into_production_numbers(db_session):
    fx = await _build_standard_fixture(db_session)
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    # seed 用户的 loop 不出现在任何生产样本里
    sample_user_ids = {s["user_id"] for s in fact["loops"]["samples"]}
    assert str(fx["seed"].id) not in sample_user_ids
    # demo face 如实单列
    assert fact["cohort"]["excluded_users"] == 1
    assert fact["cohort"]["excluded_users_with_window_signals"] == 1


async def test_word_vocabulary_pins_not_drifted(db_session):
    """谓词引用的 D-02 冻结词表值 pin（复制漂移即刻红）。"""
    assert EXCLUDED_COHORT_REGISTRATION_SOURCES == ("guest", "seed")
    assert frozenset({"task_complete"}) == ECHO_STUDY_RECORD_TYPES
    assert frozenset({"quiz_passed", "quiz_failed"}) == QUIZ_FEEDBACK_SOURCES
    assert WINDOW_DAYS == 7
    assert GOAL_STALL_THRESHOLD_DAYS == 14


# ---------------------------------------------------------------------------
# 幂等 / as_of 锚点
# ---------------------------------------------------------------------------


async def test_as_of_anchor_moves_window_membership(db_session):
    fx = await _build_standard_fixture(db_session)
    service = NorthStarWvplService(db_session)
    fact_now = await service.build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    # as_of 后移 8 天：T1/T2 移出窗口，新窗口 loop=0；无新窗口信号的用户不在有界扫描内
    later = _AS_OF + timedelta(days=8)
    fact_later = await service.build_fact(as_of=later, generated_at=_AS_OF)
    assert fact_now["north_star"]["loops_total"] == 2
    assert fact_later["north_star"]["loops_total"] == 0
    assert fact_later["north_star"]["wvpl_ratio"] is None
    assert fact_later["loops"]["all_time_bounded"]["loops_total"] == 0
    # alice 在新窗口有 engagement 信号（聊天）→ 回到有界扫描，全史 loop 重新可见
    db_session.add(
        ChatMessage(
            user_id=fx["alice"].id,
            session_id=uuid4(),
            role=MessageRole.USER,
            content="still here",
            created_at=later - timedelta(hours=1),
        )
    )
    await db_session.commit()
    fact_later_active = await service.build_fact(as_of=later, generated_at=_AS_OF)
    assert fact_later_active["north_star"]["active_users"] == 1
    assert fact_later_active["north_star"]["loops_total"] == 0  # 新窗口内无新 loop
    assert fact_later_active["loops"]["all_time_bounded"]["loops_total"] == 3  # 全史（有界）不变
    assert fact_now["as_of"] == _AS_OF.isoformat()
    assert fact_later_active["as_of"] == later.isoformat()


# ---------------------------------------------------------------------------
# outcome metrics：TTFMV / goal recovery
# ---------------------------------------------------------------------------


async def test_ttfmv_first_loop_in_window_and_goal_recovery_after_stall(db_session):
    """erin：19 天前旧 loop → 窗口内新 loop = 同 goal 停滞 19 天后恢复；
    frank：注册 5 天后窗口内迎来人生第一个 loop（TTFMV cohort）。"""
    erin = await _make_user(db_session)
    frank = await _make_user(db_session)
    erin.created_at = _AS_OF - timedelta(days=40)
    frank.created_at = _AS_OF - timedelta(days=5)
    db_session.add_all([erin, frank])
    _, erin_plan = await _make_goal_plan(db_session, erin)
    _, frank_plan = await _make_goal_plan(db_session, frank)
    await db_session.commit()

    async def _erin_loop_at(moment: datetime):
        task = _task(erin.id, plan_id=erin_plan.id, completed_at=moment)
        db_session.add(task)
        await db_session.flush()
        await _file_evidence(db_session, erin, task)
        db_session.add(_echo(erin.id, task_id=task.id, at=moment))
        await db_session.commit()

    await _erin_loop_at(_AS_OF - timedelta(days=20))
    await _erin_loop_at(_AS_OF - timedelta(days=1))

    frank_task = _task(frank.id, plan_id=frank_plan.id, completed_at=_AS_OF - timedelta(days=1))
    db_session.add(frank_task)
    await db_session.flush()
    await _file_evidence(db_session, frank, frank_task)
    db_session.add(_echo(frank.id, task_id=frank_task.id, at=_AS_OF - timedelta(days=1)))
    await db_session.commit()

    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    ttfmv = fact["outcome_metrics"]["time_to_first_meaningful_value"]
    recovery = fact["outcome_metrics"]["goal_recovery_after_stall"]

    # frank 第一个 loop（也是唯一 loop）在窗口内：注册 → 首个 loop 4 天
    assert ttfmv["newly_converted_users"] == 1
    assert ttfmv["median_days"] == 4.0
    # erin 的 19 天停滞（≥ 14 阈值）被窗口内的 loop 关闭
    assert recovery["recovered_in_window"] == 1
    assert recovery["median_recovery_days"] == 19.0


# ---------------------------------------------------------------------------
# 零模型参与（代码级证明 pin）
# ---------------------------------------------------------------------------


async def test_query_layer_has_zero_llm_participation():
    """卡面灵魂：北极星数字零模型计算。查询层源码不引用任何 LLM 基础设施。"""
    import app.core.north_star_wvpl as contract
    import app.services.north_star_wvpl_service as service

    forbidden = (
        "openai",
        "anthropic",
        "litellm",
        "langchain",
        "chatcompletion",
        "llm_router",
        "llmservice",
        "agentservice",
        "streamchat",
        "chatorchestrator",
    )
    for module in (contract, service):
        source = inspect.getsource(module).lower()
        for token in forbidden:
            assert token not in source, f"{module.__name__} must not reference {token} (zero-model red line)"


# ---------------------------------------------------------------------------
# proactive / mode 面
# ---------------------------------------------------------------------------


async def test_proactive_and_mode_faces(db_session):
    """mode/proactive：lifecycle 六段词表计数 + started 按 execution_mode 分桶 +
    behavioral outcome_type 分桶（纯确定性 SQL 面）。"""
    from app.models.intervention_lifecycle import InterventionLifecycleEvent

    user = await _make_user(db_session)
    db_session.add_all(
        [
            InterventionLifecycleEvent(
                user_id=user.id,
                decision_id=f"aurora_{uuid4().hex[:32]}",
                event_type="started",
                intervention_type="nudge",
                execution_mode="agent",
                goal_type="unknown",
                friction_tag="unattributed",
                occurred_at=_AS_OF - timedelta(days=1),
            ),
            InterventionLifecycleEvent(
                user_id=user.id,
                decision_id=f"aurora_{uuid4().hex[:32]}",
                event_type="started",
                intervention_type="nudge",
                execution_mode="human",
                goal_type="unknown",
                friction_tag="unattributed",
                occurred_at=_AS_OF - timedelta(days=1),
            ),
            InterventionLifecycleEvent(
                user_id=user.id,
                decision_id=f"aurora_{uuid4().hex[:32]}",
                event_type="exposed",
                intervention_type="nudge",
                execution_mode=None,
                goal_type="unknown",
                friction_tag="unattributed",
                occurred_at=_AS_OF - timedelta(days=1),
            ),
            InterventionLifecycleEvent(
                user_id=user.id,
                decision_id=f"aurora_{uuid4().hex[:32]}",
                event_type="started",
                intervention_type="nudge",
                execution_mode=None,  # 词表外/NULL 模式 → other 桶
                goal_type="unknown",
                friction_tag="unattributed",
                occurred_at=_AS_OF - timedelta(days=1),
            ),
            BehavioralOutcome(
                user_id=user.id,
                intervention_id=uuid4(),
                outcome_type="action_taken",
                time_to_outcome=3600,
                success=True,
                timestamp=_AS_OF - timedelta(days=1),
            ),
        ]
    )
    await db_session.commit()

    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert fact["proactive"]["lifecycle_events_by_type"] == {"started": 3, "exposed": 1}
    assert fact["proactive"]["started_by_execution_mode"] == {"human": 1, "agent": 1, "hybrid": 0, "other": 1}
    assert fact["outcomes"]["behavioral_by_outcome_type"] == {"action_taken": {"total": 1, "success": 1}}


# ---------------------------------------------------------------------------
# 事实 JSON 结构冻结（schema 面）
# ---------------------------------------------------------------------------


async def test_fact_json_structure_is_frozen(db_session):
    await _build_standard_fixture(db_session)
    fact = await NorthStarWvplService(db_session).build_fact(as_of=_AS_OF, generated_at=_AS_OF)
    assert set(fact) == {
        "schema",
        "caliber_version",
        "as_of",
        "window",
        "north_star",
        "outcomes",
        "proactive",
        "outcome_metrics",
        "loops",
        "cohort",
        "provenance",
        "definitions",
        "limitations",
    }
    # 口径注释随 JSON 输出（machine-readable 口径，可审计三件套之一）
    assert fact["definitions"]["loop"]
    assert "generated_at" in fact["provenance"]
    assert len(fact["provenance"]["source_queries"]) >= 5


async def test_canonical_serialization_is_byte_stable():
    fact = {"b": 1, "a": {"y": "中", "x": 2}}
    assert canonical_fact_json(fact) == canonical_fact_json(dict(reversed(list(fact.items()))))
    json.loads(canonical_fact_json(fact))  # 合法 JSON
