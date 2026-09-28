"""V4-I04 · 无动作仍可纠正与一次决策性澄清（FIX97 落地）单元测试。

三验收面（卡面，必须可失败——每面一正一反）：

1. **没有错误提案也能纠正并形成合法经验**：无提案/no_action 面自由补充入口
   恒可达（FIX97）；``apply_free_supplement(prior=None)`` 翻转出口并产出合法
   经验记录（封闭 ref + 会话作用域 + 可撤回 + 永久偏好写授权空集）；用户主动
   补充不占系统追问预算。反例：act/ask 面不得重复出面（各有既有通道）。
2. **今天15分钟不写永久偏好；「不是不会」不追难度**：今日时间预算 → 会话
   作用域记录（``permanent_preference_write=False``）；非今日口径 fail-closed
   返 None（A-05 契约 owner 域，不猜）；难度族纯否定证据不抬高难度占比。
   反例：写授权面出现成员 / 否定词牌被计分即红。
3. **澄清后行动改变依据可追踪，用户可跳过/暂停**：一次决策性澄清预算（≤1
   自动轮）尽后引擎仍想追问 → 出口斜坡（question 恒 None，不连环追问）；
   追踪内容寻址 + 重开可见通道声明 + user_can skip/pause。反例：伪造保守
   方案（无引擎 reason 背书）即红。

接线面（``NO_ACTION_CORRECTION_MODE``）：off 零行为（V3 第二问链保持）、
shadow 行为零变化（一审 F-1 整改：跳过/暂停词表与澄清压制的**行为应用
live-only**，shadow 只留观察注记——不清 pending、不产 no_action）、
live 出面 + 显式 WARN；跳过/暂停轮；FIX97 入口在 FIX-49 门拦静默面恒可达。

一审（PASS_WITH_CHALLENGES）四项跟进（本文件整改钉）：
- **F-1**：shadow 档 marker 句 pending 保持 + 与 off 行为级零差量断言
  （live 行为照常由 ``test_skip_turn_clears_pending…`` /
  ``test_pause_turn_is_visible…`` 双钉）；
- **F-3/R2**：否定前缀复合句（「别停一下」/「不想跳过这题」）按宁漏报
  fail-closed 不命中 + 纯命中不误杀；
- **F-4/R4**：非空 ``evidence_refs`` 样例让引用传播断言真咬合（旗舰样例
  空集语义显式钉死）。

I03 移交闭合（本卡线顺手落）：
- **O-1**：冻结语料快照对活代码重算 diff（零 mismatch）——快照漂移即刻暴露；
- **O-2**：``_RULE_DECISION_TO_INTERVENTIONS`` 干预名 import 期不变式复核。

真实 LLM 0 次；Redis 用 fakeredis；零 db 依赖（wiring 面 redis 可缺席降级，
本测试用 fakeredis 走完整 pending 面）。
"""

from __future__ import annotations

import json
from pathlib import Path

import fakeredis.aioredis
import pytest

from app.aurora.friction_diagnosis import (
    DEFAULT_SESSION_QUESTION_LIMIT,
    diagnose_friction,
)
from app.aurora.no_action_supplement import (
    CLARIFICATION_EXIT_KINDS,
    MARKER_NEGATION_PREFIXES,
    NO_ACTION_SUPPLEMENT_VERSION,
    SUPPLEMENT_INVITATION,
    SUPPLEMENT_WRITE_SURFACES,
    V4_AUTO_CLARIFICATION_BUDGET,
    apply_free_supplement,
    budget_declared_replay,
    clarification_exit_ramp,
    classify_supplement_constraint,
    conservative_option_from,
    correction_trace,
    difficulty_not_chased,
    match_pause_marker,
    match_skip_marker,
    supplement_entry,
)
from app.config import settings
from app.core.aurora_decision import AURORA_INTERVENTION_TYPES
from app.services.friction_chat_wiring import (
    _CORRECTION_MODE_WARNED,
    FRICTION_ANSWER_CONTEXT_KEY,
    FrictionChatWiringService,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SNAPSHOT_PATH = _REPO_ROOT / "v4" / "evidence" / "V4-I03" / "probe_corpus_snapshot.json"


@pytest.fixture()
def correction_mode(monkeypatch):
    """档位切换 + live WARN 一次性标记复位（隔离测试序）。"""

    def _set(mode: str) -> str:
        monkeypatch.setattr(settings, "NO_ACTION_CORRECTION_MODE", mode)
        monkeypatch.setattr("app.services.friction_chat_wiring._CORRECTION_MODE_WARNED", False)
        return mode

    return _set


@pytest.fixture()
async def fake_redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose() if hasattr(client, "aclose") else None


# ---------------------------------------------------------------------------
# 面一：FIX97 无动作自由补充（验收①）
# ---------------------------------------------------------------------------


class TestSupplementEntry:
    def test_entry_available_without_any_proposal(self):
        """正例：连提案都没有（outcome=None）→ 入口恒可达（FIX97 核心）。"""
        entry = supplement_entry(outcome=None)
        assert entry is not None
        assert entry["available"] is True
        assert entry["invitation"] == SUPPLEMENT_INVITATION == "还有什么情况需要我知道？"
        assert entry["budget_impact"] == "none"

    def test_entry_available_on_no_action_and_abstain(self):
        for outcome in ("no_action", "abstain"):
            entry = supplement_entry(outcome=outcome)
            assert entry is not None and entry["available"] is True

    def test_entry_absent_on_act_and_ask_surfaces(self):
        """反例（可失败）：act/ask 面有各自的纠正/回答通道——入口不得双轨出面。"""
        assert supplement_entry(outcome="act") is None
        assert supplement_entry(outcome="ask") is None

    def test_examples_only_two_different_consequences(self):
        """FIX97 纪律：至多 2 个例子且必须不同操作后果；同名/目录外不给。"""
        entry = supplement_entry(
            outcome="no_action",
            contender_primary_nominations={"difficulty": "split", "energy": "pause", "skill": "practice"},
        )
        assert entry is not None
        assert len(entry["examples"]) == 2
        primaries = {example["primary_intervention"] for example in entry["examples"]}
        assert len(primaries) == 2  # 不同后果
        assert primaries <= AURORA_INTERVENTION_TYPES
        same = supplement_entry(
            outcome="no_action",
            contender_primary_nominations={"difficulty": "split", "plan_drift": "split"},
        )
        assert same is not None and same["examples"] == []  # 同名 → 纯自由输入
        outsider = supplement_entry(
            outcome="no_action",
            contender_primary_nominations={"mystery": "rm_rf_slash"},
        )
        assert outsider is not None and outsider["examples"] == []  # 目录外 fail-closed

    def test_apply_free_supplement_without_prior_forms_legal_experience(self):
        """正例：没有错误提案（prior=None）也能纠正并形成合法经验。"""
        out = apply_free_supplement("不是不会，是不知道怎么开始")
        assert out.diagnosis.outcome == "act"
        assert out.diagnosis.friction_type == "entry"  # 不是难度归因
        assert out.diagnosis.nominated_interventions == ("rescope", "split")
        assert out.trace["before_outcome"] is None
        assert out.trace["after_outcome"] == "act"
        experience = out.experience
        assert experience["kind"] == "user_supplement_evidence"
        assert experience["scope"] == "session"
        assert experience["retractable"] is True
        assert experience["permanent_preference_write"] is False
        assert experience["write_surfaces"] == []
        # 一审 F-4/R4 整改：旗舰样例的引擎证据引用**如实为空**（该 utterance 无
        # signal:// 级证据）——空集语义显式钉死（引用是引擎 passthrough，本层
        # 零伪造；有引用面的传播断言见 test_…_propagates_nonempty_engine_evidence_refs）。
        assert out.diagnosis.evidence_refs == ()
        assert experience["evidence_refs"] == list(out.diagnosis.evidence_refs) == []
        assert out.trace["basis"]["evidence_refs"] == []

    def test_apply_free_supplement_propagates_nonempty_engine_evidence_refs(self):
        """一审 F-4/R4 整改正例：非空 evidence_refs 样例让引用断言真咬合——
        spine 状态证据（signal:// scheme，引擎自身产出）经重放进入经验记录与
        纠正追踪，逐条 scheme 合法且三处恒等（零伪造、零丢失、可失败）。"""
        out = apply_free_supplement("真的做不下去了，最近状态很差", spine_state_keys=("crisis_mode",))
        refs = list(out.diagnosis.evidence_refs)
        assert refs == ["signal://crisis_mode"]  # 引擎产出非空——不再空转
        assert out.experience["evidence_refs"] == refs  # 经验记录逐条携带（不丢失）
        assert out.trace["basis"]["evidence_refs"] == refs  # 追踪依据同源（不另造）
        for ref in refs:
            scheme, _, body = ref.partition("://")
            assert scheme in ("signal", "user_state") and body  # 既有封闭 scheme（引擎 docstring 契约）

    def test_supplement_does_not_consume_clarification_budget(self):
        """用户主动补充不算系统追问：预算计数原样透传不递增。"""
        prior = diagnose_friction({"utterance": "做不下去", "questions_asked_session": 1, "questions_asked_day": 1})
        out = apply_free_supplement("其实我不知道怎么开始", prior=prior)
        snapshot = out.diagnosis.annotations["input_snapshot"]
        assert snapshot["questions_asked_session"] == 1  # 不递增
        assert snapshot["questions_asked_day"] == 1
        assert out.budget_impact == "none"

    def test_no_evidence_supplement_keeps_honest_uncertainty(self):
        """诚实性面：无证据补充绝不伪造行动翻转——要么引擎自身的根分裂问
        （budget 内合法追问，friction unknown = 不假诊断），要么预算声明下
        如实 no_action + 显式 insufficient_context（可纠正状态，非永久失败）。"""
        default = apply_free_supplement("嗯")
        assert default.diagnosis.outcome in ("no_action", "ask")
        assert default.diagnosis.outcome != "act"  # 零证据不伪造行动
        assert default.diagnosis.friction_type == "unknown"
        exhausted_prior = diagnose_friction({"utterance": "做不下去", "questions_asked_session": 2})
        out = apply_free_supplement("嗯", prior=exhausted_prior)
        assert out.diagnosis.outcome == "no_action"
        assert "insufficient_context" in out.diagnosis.uncertainty_kinds
        assert out.experience["permanent_preference_write"] is False


# ---------------------------------------------------------------------------
# 面二：临时约束不写永久偏好 + 「不是不会」不追难度（验收②）
# ---------------------------------------------------------------------------


class TestTemporaryConstraintAndDifficultyGuard:
    def test_today_time_budget_is_session_scoped_never_permanent(self):
        """正例：「今天只有15分钟」→ 会话作用域，永久偏好写 = False。"""
        constraint = classify_supplement_constraint("今天只有15分钟，能不能就做一个小节")
        assert constraint is not None
        assert constraint["kind"] == "time_budget_today"
        assert constraint["scope"] == "this_session"
        assert constraint["expires_same_day"] is True
        assert constraint["permanent_preference_write"] is False
        assert constraint["write_surfaces"] == []

    def test_non_today_horizon_fail_closed(self):
        """反例（可失败）：每周/每次口径不在本层词表——fail-closed 返 None
        （多天枚举归 A-05 契约 owner 迁移面，不猜）。"""
        assert classify_supplement_constraint("我每周只有15分钟") is None
        assert classify_supplement_constraint("每次只想学15分钟") is None
        assert classify_supplement_constraint("") is None

    def test_write_surfaces_structurally_empty(self):
        """结构保证：补充层对永久偏好面的写授权是空集（出现成员即红）。"""
        assert frozenset() == SUPPLEMENT_WRITE_SURFACES
        assert V4_AUTO_CLARIFICATION_BUDGET == 1

    def test_negated_difficulty_does_not_chase_difficulty(self):
        """正例：「不是太难了」否定极性 → 难度零权重，难度归因不追。"""
        out = apply_free_supplement("其实不是太难了，是材料还没给我")
        assert out.diagnosis.outcome == "act"
        assert out.diagnosis.friction_type == "dependency"  # 材料等待，不是难度
        negated = out.diagnosis.annotations.get("utterance_negated_matches") or []
        assert "difficulty:太难了" in negated
        matched = out.diagnosis.annotations.get("utterance_matches") or []
        assert all(not item.startswith("difficulty") for item in matched)
        assert out.guard_checks["difficulty_not_chased"] is True

    def test_difficulty_guard_catches_naive_wordmark_counting(self):
        """反例（可失败）：否定词牌被计分（绕过引擎否定感知）→ 守卫 False。
        这是「未来改动让补充面绕过 FIX-110」的显式失败面。"""
        prior = diagnose_friction({"utterance": ""})
        assert (
            difficulty_not_chased(
                prior.posterior,
                (("difficulty", 0.6), ("energy", 0.4)),
                after_annotations={
                    "utterance_negated_matches": ["difficulty:太难了"],
                    "utterance_matches": [],
                },
            )
            is False
        )

    def test_positive_difficulty_report_is_legitimate_not_chasing(self):
        """真实难度自报（正向词牌）是合法归因——守卫域外，不误伤。"""
        out = apply_free_supplement("是真的太难了，完全超出我的水平")
        assert out.diagnosis.friction_type == "difficulty"
        assert out.guard_checks["difficulty_not_chased"] is True


# ---------------------------------------------------------------------------
# 面三：一次决策性澄清 + 出口斜坡 + 纠正追踪（验收③）
# ---------------------------------------------------------------------------


class TestOneDecisiveClarificationAndTrace:
    def test_exit_ramp_never_carries_a_question(self):
        """正例：预算尽后的斜坡结构上不携带追问（question 恒 None）。"""
        ramp = clarification_exit_ramp(
            conservative_option={"intervention": "pause", "source_reason": "B1.budget_exhausted_best_guess"}
        )
        assert ramp["question"] is None
        assert set(ramp["kinds"]) == CLARIFICATION_EXIT_KINDS == {"tell_situation", "conservative_option", "pause"}
        assert ramp["conservative_option"]["delivery"] == "recommendation"  # 建议非执行
        assert ramp["supplement_invitation"] == SUPPLEMENT_INVITATION

    def test_exit_ramp_rejects_fabricated_conservative_option(self):
        """反例（可失败）：保守方案必须有引擎 reason 背书 + 目录内干预——
        本层零伪造第二诊断。"""
        with pytest.raises(ValueError, match="source_reason"):
            clarification_exit_ramp(conservative_option={"intervention": "pause"})  # 无引擎背书
        with pytest.raises(ValueError, match="out of AURORA_INTERVENTION_TYPES"):
            clarification_exit_ramp(
                conservative_option={"intervention": "rm_rf_slash", "source_reason": "B1.budget_exhausted_best_guess"}
            )

    def test_budget_declared_replay_produces_engine_b1_option(self):
        """保守可试方案只能来自引擎自身「预算已用完」B1 出口（J-05 同律）。"""
        diagnosis = budget_declared_replay(
            {"utterance": "做不下去", "recent_failure_count": 5, "has_task_context": True},
        )
        assert "B1.budget_exhausted_best_guess" in diagnosis.reasons
        assert diagnosis.uncertain is True
        option = conservative_option_from(diagnosis)
        assert option is not None
        assert option["intervention"] in AURORA_INTERVENTION_TYPES
        assert option["source_reason"] == "B1.budget_exhausted_best_guess"

    def test_conservative_option_requires_engine_b1_endorsement(self):
        """B2/B3 无行动出口如实给 None（不把 no_action 包装成保守方案）。"""
        diagnosis = budget_declared_replay({})
        assert diagnosis.outcome == "no_action"
        assert conservative_option_from(diagnosis) is None

    def test_trace_is_content_addressed_and_reopen_visible(self):
        """正例：追踪内容寻址（重放 id 恒定）+ 重开可见通道 + user_can。"""
        basis = {"channel": "clarification_answer", "answered_branch_key": "tried_unsure"}
        first = correction_trace(before_outcome="ask", after_outcome="act", basis=basis)
        second = correction_trace(before_outcome="ask", after_outcome="act", basis=basis)
        assert first["trace_id"] == second["trace_id"]
        assert first["trace_id"].startswith("nactrace_")
        assert first["changed"] is True
        assert first["user_can"] == {"skip": True, "pause": True}
        assert first["reopen_visible_via"] == "context_data.friction_decision"
        assert first["permanent_preference_write"] is False
        assert first["schema_version"] == NO_ACTION_SUPPLEMENT_VERSION
        flipped = correction_trace(before_outcome="ask", after_outcome="act", basis={**basis, "x": 1})
        assert flipped["trace_id"] != first["trace_id"]  # 依据变 → id 变（不碰撞）

    def test_skip_and_pause_markers_are_closed_vocabularies(self):
        assert match_skip_marker("跳过，先不回答") is not None
        assert match_skip_marker("这个先不用问了") is not None
        assert match_pause_marker("先暂停一下") is not None
        assert match_skip_marker("今天继续学") is None
        assert match_pause_marker("不可以停止进步") is None  # 「停一下」≠「不可以停…」误伤面

    def test_negation_prefix_compounds_fail_closed(self):
        """一审 F-3/R2 整改（「宁漏报」收紧）：否定前缀复合句 fail-closed 不命中
        ——「别停一下」是「不要停」不是「要暂停」、「不想跳过这题」不是「要跳过」
        （一审实测的过报形态）；误清 pending/误静默比漏识别（用户再点选或改述）
        代价高。"""
        assert match_pause_marker("别停一下") is None
        assert match_pause_marker("先别停一下") is None
        assert match_skip_marker("不想跳过这题，让我再试试") is None
        assert match_skip_marker("不是不想回答") is None  # 双重否定：不是「不想回答」

    def test_negation_guard_does_not_kill_plain_marker_hits(self):
        """反例（守卫不误杀）：无否定前缀的纯命中照常；否定词本身是词表成员的
        （「不用问了」）不受守卫影响（守卫只看命中 span 之前的前缀）——词表
        主通道保持（wiring live 档行为面不变）。"""
        assert match_pause_marker("先暂停一下") == "暂停一下"
        assert match_skip_marker("跳过，先不回答") == "跳过"
        assert match_skip_marker("这个先不用问了") == "不用问了"
        assert match_pause_marker("我要求暂停一下") == "暂停一下"

    def test_marker_negation_prefixes_frozen_closed_set(self):
        """守卫词表封闭且与实现窗口契约一致（1-2 字前缀；扩展过 reviewer 同词表纪律）。
        已知边界（如实登记，不猜）：英文否定（don't skip）不在守卫域——
        按「宁漏报」原则后续词表变更过 reviewer 再收。"""
        assert {"别", "不要", "不想", "不是", "不用"} <= MARKER_NEGATION_PREFIXES
        assert all(len(prefix) <= 2 for prefix in MARKER_NEGATION_PREFIXES)  # 1-2 字窗口契约
        assert match_skip_marker("don't skip") == "skip"  # 边界如实：英文否定不守卫


# ---------------------------------------------------------------------------
# 接线面：NO_ACTION_CORRECTION_MODE 三档
# ---------------------------------------------------------------------------


class TestWiringModes:
    async def test_off_mode_keeps_v3_second_ask_chain(self, fake_redis, correction_mode):
        """反例（可失败·回滚面）：off = V3 行为级零差量（一审勘误：payload 仅
        version 串 v3→v4 与 3 个 null 键不同）——第二问链保持、三面零出面。"""
        correction_mode("off")
        svc = FrictionChatWiringService(None, fake_redis)
        first = await svc.process_turn(
            user_id="u1",
            session_id="s-off",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
        )
        assert first.outcome == "ask" and first.question is not None
        assert first.supplement_entry is None and first.exit_ramp is None and first.correction_trace is None
        second = await svc.process_turn(
            user_id="u1",
            session_id="s-off",
            user_message="",
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": first.question["question_id"],
                    "branch_key": "tried_unsure",
                }
            },
        )
        # V3 允许会话问句预算 2 → 追问面保持（本测试即「不实现时的行为」反例）
        assert second.question is not None
        assert second.supplement_entry is None and second.exit_ramp is None and second.correction_trace is None

    async def test_live_mode_suppresses_second_ask_with_exit_ramp(self, fake_redis, correction_mode):
        """正例：live 档已答 1 轮仍想追问 → 不 surfaced 第二问，出口斜坡出面。"""
        correction_mode("live")
        svc = FrictionChatWiringService(None, fake_redis)
        first = await svc.process_turn(
            user_id="u1",
            session_id="s-live",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
        )
        assert first.outcome == "ask"
        second = await svc.process_turn(
            user_id="u1",
            session_id="s-live",
            user_message="",
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": first.question["question_id"],
                    "branch_key": "tried_unsure",
                }
            },
        )
        # 不连环追问：被压制的第二问可审计，出口斜坡结构上零追问
        assert second.annotations["suppressed_second_ask"] == "q_content_vs_state"
        assert second.annotations["exit_reason"] == "v4_clarification_budget_exhausted"
        assert second.question is None
        assert second.exit_ramp is not None
        assert second.exit_ramp["question"] is None
        assert set(second.exit_ramp["kinds"]) == CLARIFICATION_EXIT_KINDS
        # 行动改变依据可追踪
        trace = second.correction_trace
        assert trace is not None
        assert trace["before_outcome"] == "ask"
        assert trace["basis"]["answered_branch_key"] == "tried_unsure"
        assert trace["user_can"] == {"skip": True, "pause": True}
        # pending 已消费，不再挂新问题
        assert await svc._load_pending("u1", "s-live") is None

    async def test_live_mode_surfaces_entry_on_gate_silenced_no_action(self, fake_redis, correction_mode):
        """正例：FIX-49 门拦静默面（无词牌普通消息）→ 补充入口恒可达（FIX97）。"""
        correction_mode("live")
        svc = FrictionChatWiringService(None, fake_redis)
        outcome = await svc.process_turn(
            user_id="u1",
            session_id="s-entry",
            user_message="今天天气不错",
            user_context_payload={},
            request_extra_context={},
        )
        assert outcome.outcome == "no_action"
        assert outcome.question is None  # 门拦的介入面不出
        assert outcome.supplement_entry is not None  # 补充出口仍可达
        assert outcome.supplement_entry["invitation"] == SUPPLEMENT_INVITATION
        assert outcome.supplement_entry["budget_impact"] == "none"

    async def test_live_mode_free_supplement_trace_with_constraint(self, fake_redis, correction_mode):
        """正例：补充轮产出纠正追踪（临时约束分类 + 难度守卫 + 预算零影响）。"""
        correction_mode("live")
        svc = FrictionChatWiringService(None, fake_redis)
        outcome = await svc.process_turn(
            user_id="u1",
            session_id="s-fs",
            user_message="不是不会，是不知道怎么开始，今天只有15分钟",
            user_context_payload={},
            request_extra_context={},
        )
        assert outcome.outcome == "act"
        assert outcome.friction_type == "entry"  # 「不是不会」不落难度
        trace = outcome.correction_trace
        assert trace is not None
        assert trace["basis"]["channel"] == "free_supplement"
        assert trace["basis"]["constraint_kind"] == "time_budget_today"
        assert trace["basis"]["constraint_scope"] == "this_session"
        assert trace["basis"]["difficulty_guard_ok"] is True
        assert trace["basis"]["budget_impact"] == "none"

    async def test_skip_turn_clears_pending_with_conservative_or_honest_no_action(self, fake_redis, correction_mode):
        """正例：用户可跳过——pending 清除 + 保守可试方案或如实无行动，不锁聊天。"""
        correction_mode("live")
        svc = FrictionChatWiringService(None, fake_redis)
        first = await svc.process_turn(
            user_id="u1",
            session_id="s-skip",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
        )
        assert first.outcome == "ask"
        second = await svc.process_turn(
            user_id="u1",
            session_id="s-skip",
            user_message="跳过，先不回答",
            user_context_payload={},
            request_extra_context={},
        )
        assert second.annotations["clarification_exit"] == "skip"
        assert second.correction_trace is not None and second.correction_trace["skipped"] is True
        assert second.question is None  # 不锁：跳过后零追问
        assert await svc._load_pending("u1", "s-skip") is None

    async def test_pause_turn_is_visible_user_choice_not_failure(self, fake_redis, correction_mode):
        """正例：用户可暂停——本域静默 + 追踪 paused=True（不是永久失败固化）。"""
        correction_mode("live")
        svc = FrictionChatWiringService(None, fake_redis)
        first = await svc.process_turn(
            user_id="u1",
            session_id="s-pause",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
        )
        assert first.outcome == "ask"
        second = await svc.process_turn(
            user_id="u1",
            session_id="s-pause",
            user_message="先暂停一下",
            user_context_payload={},
            request_extra_context={},
        )
        assert second.outcome == "no_action"
        assert second.annotations["clarification_exit"] == "pause"
        assert second.question is None and second.intervention is None
        assert second.correction_trace is not None and second.correction_trace["paused"] is True
        assert await svc._load_pending("u1", "s-pause") is None

    async def test_shadow_mode_records_without_payload_change(self, fake_redis, correction_mode):
        """shadow = 指标/日志留痕，payload 零变化（三面恒 None + V3 第二问保持）。
        （非 marker 语句面；marker 句的观察注记面见 test_shadow_mode_marker_sentence_keeps_pending。）"""
        correction_mode("shadow")
        svc = FrictionChatWiringService(None, fake_redis)
        outcome = await svc.process_turn(
            user_id="u1",
            session_id="s-shadow",
            user_message="今天天气不错",
            user_context_payload={},
            request_extra_context={},
        )
        assert outcome.outcome == "no_action"
        assert outcome.supplement_entry is None  # payload 零变化
        assert outcome.correction_trace is None and outcome.exit_ramp is None

    async def test_shadow_mode_marker_sentence_keeps_pending(self, fake_redis, correction_mode):
        """一审 F-1 整改正例：shadow 档 marker 句**只观察不清 pending**——

        - 行为面与 off 档逐项恒等（outcome/annotations/pending 生命周期），
          唯一差量是显式 ``shadow_marker_observation`` 注记（applied=False）；
        - 不产 no_action、不产追踪/斜坡（三面恒 None）；
        - pending 未被破坏：下一轮结构化回答照常消费。
        （一审实测：旧实现 shadow 下「先暂停一下」清 pending + no_action，
        与「shadow=观察零行为变化」声明不符——本测试使该回归即刻变红。）
        """
        behavior: dict[str, dict] = {}
        for mode in ("off", "shadow"):
            correction_mode(mode)
            svc = FrictionChatWiringService(None, fake_redis)
            sid = f"s-mk-{mode}"
            first = await svc.process_turn(
                user_id="u1",
                session_id=sid,
                user_message="最近做不下去",
                user_context_payload={},
                request_extra_context={},
            )
            assert first.outcome == "ask" and first.question is not None
            second = await svc.process_turn(
                user_id="u1",
                session_id=sid,
                user_message="先暂停一下",
                user_context_payload={},
                request_extra_context={},
            )
            behavior[mode] = {
                "outcome": second.outcome,
                "annotations": dict(second.annotations),
                "pending": await svc._load_pending("u1", sid),
                "question_id": first.question["question_id"],
            }
            # 两档同律：不产 no_action、无介入面、无追踪/斜坡/入口（行为零变化）
            assert second.outcome == "ask"
            assert second.question is None and second.intervention is None
            assert second.correction_trace is None and second.exit_ramp is None
            assert second.supplement_entry is None
            assert behavior[mode]["pending"] is not None  # pending 保持
        # 与 off 逐项恒等：shadow 的 annotations == off 的 annotations + 观察注记
        shadow_annotations = behavior["shadow"]["annotations"]
        observation = shadow_annotations.pop("shadow_marker_observation")
        assert shadow_annotations == behavior["off"]["annotations"]
        assert observation == {"kind": "pause", "marker": "暂停一下", "applied": False}
        # pending 未被 marker 破坏：下一轮结构化回答照常消费（shadow 会话）——
        # V3 链同构：答案消费后引擎第二问正常出面并挂新 pending（非 marker 问句）
        third = await svc.process_turn(
            user_id="u1",
            session_id="s-mk-shadow",
            user_message="",
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": behavior["shadow"]["question_id"],
                    "branch_key": "tried_unsure",
                }
            },
        )
        assert third.outcome == "ask" and third.question is not None
        assert third.question["question_id"] != behavior["shadow"]["question_id"]
        new_pending = await svc._load_pending("u1", "s-mk-shadow")
        assert (new_pending or {}).get("question_id") == third.question["question_id"]

    async def test_shadow_mode_keeps_v3_second_ask_chain(self, fake_redis, correction_mode):
        """一审 F-1 整改（同一红线覆盖澄清压制面）：shadow 不应用第二问压制——
        V3 第二问照常出面并挂新 pending（行为与 off 零差量），无压制注记、
        无斜坡、无追踪（压制应用 live-only，live 对照 =
        test_live_mode_suppresses_second_ask_with_exit_ramp）。"""
        correction_mode("shadow")
        svc = FrictionChatWiringService(None, fake_redis)
        first = await svc.process_turn(
            user_id="u1",
            session_id="s-shadow2",
            user_message="最近做不下去",
            user_context_payload={},
            request_extra_context={},
        )
        assert first.outcome == "ask"
        second = await svc.process_turn(
            user_id="u1",
            session_id="s-shadow2",
            user_message="",
            user_context_payload={},
            request_extra_context={
                FRICTION_ANSWER_CONTEXT_KEY: {
                    "question_id": first.question["question_id"],
                    "branch_key": "tried_unsure",
                }
            },
        )
        assert second.question is not None  # 第二问未被压制（V3 链保持）
        assert "suppressed_second_ask" not in second.annotations
        assert second.exit_ramp is None and second.correction_trace is None
        assert await svc._load_pending("u1", "s-shadow2") is not None  # 新问句正常挂起

    async def test_live_mode_activation_warns_explicitly(self, fake_redis, correction_mode):
        """I03 N-2 移交闭合：live 激活有显式 WARN（消费侧标识，防运维误读），
        且一次性（重入不重复告警）。"""
        from loguru import logger

        correction_mode("live")
        records: list = []
        handler_id = logger.add(records.append, level="WARNING")
        try:
            svc = FrictionChatWiringService(None, fake_redis)
            await svc.process_turn(
                user_id="u1",
                session_id="s-warn",
                user_message="今天天气不错",
                user_context_payload={},
                request_extra_context={},
            )
            first_count = sum("NO_ACTION_CORRECTION_MODE=live" in record for record in records)
            await svc.process_turn(
                user_id="u1",
                session_id="s-warn2",
                user_message="今天天气不错",
                user_context_payload={},
                request_extra_context={},
            )
            total_count = sum("NO_ACTION_CORRECTION_MODE=live" in record for record in records)
        finally:
            logger.remove(handler_id)
        assert first_count == 1
        assert total_count == 1  # 一次性：重入不重复告警

    async def test_unknown_mode_fails_closed_to_off(self, fake_redis, correction_mode):
        """fail-closed：未知档位按 off（不猜），payload 零变化。"""
        correction_mode("LIVE-TURBO")
        svc = FrictionChatWiringService(None, fake_redis)
        outcome = await svc.process_turn(
            user_id="u1",
            session_id="s-unknown",
            user_message="今天天气不错",
            user_context_payload={},
            request_extra_context={},
        )
        assert outcome.outcome == "no_action"
        assert outcome.supplement_entry is None


# ---------------------------------------------------------------------------
# I03 移交闭合（本卡线）
# ---------------------------------------------------------------------------


class TestI03HandoverClosures:
    def test_o1_corpus_snapshot_recomputes_zero_mismatch(self):
        """O-1：冻结语料快照直读重算——对活代码 diff 零 mismatch（漂移即红）。

        I03 交付时快照零测试消费者（双份维护静默漂移风险）；本测试让快照
        成为被钉死的回归资产：模式/词表任何一面变更未 bump 快照即失败。
        """
        from app.orchestration.semantic_selector import (
            probe_complex_expression,
            rule_arm_decide,
        )

        snapshot = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        assert snapshot["captured_with"] == "semantic_selector.v4.i03.v1"
        corpus = snapshot["corpus"]
        assert len(corpus) == 23
        mismatches: list[dict[str, object]] = []
        for item in corpus:
            profile = probe_complex_expression(item["text"])
            actual_forms = sorted(form.value for form in profile.forms)
            rule_decision = rule_arm_decide(profile).kind.value
            if actual_forms != item["expected"] or item["match"] is not True:
                mismatches.append({"text": item["text"], "expected": item["expected"], "actual": actual_forms})
            if rule_decision != item["rule_arm_decision"]:
                mismatches.append(
                    {
                        "text": item["text"],
                        "expected_rule_arm": item["rule_arm_decision"],
                        "actual_rule_arm": rule_decision,
                    }
                )
        assert mismatches == []

    def test_o2_rule_decision_interventions_import_invariant(self):
        """O-2：``_RULE_DECISION_TO_INTERVENTIONS`` 干预名 import 期不变式复核。"""
        from app.orchestration.semantic_selector import _RULE_DECISION_TO_INTERVENTIONS

        for kind, names in _RULE_DECISION_TO_INTERVENTIONS.items():
            assert names <= AURORA_INTERVENTION_TYPES, f"{kind}: {sorted(names - AURORA_INTERVENTION_TYPES)}"

    def test_settings_flag_declared_default_off(self):
        """档位声明：NO_ACTION_CORRECTION_MODE 默认 off（回滚 = 关旗标）。"""
        assert settings.NO_ACTION_CORRECTION_MODE == "off"


# ---------------------------------------------------------------------------
# 回归锚：引擎预算常量不被本卡漂移（V3 冻结面）
# ---------------------------------------------------------------------------


def test_engine_session_budget_unchanged():
    """V4 的 ≤1 自动澄清轮在消费层执行——引擎冻结预算（2/5）零改动。"""
    assert DEFAULT_SESSION_QUESTION_LIMIT == 2
    assert V4_AUTO_CLARIFICATION_BUDGET == 1


def test_correction_mode_warned_flag_exists_for_reset():
    """live WARN 一次性标记存在（测试隔离复位面；接线面结构锚）。"""
    import app.services.friction_chat_wiring as wiring

    assert isinstance(_CORRECTION_MODE_WARNED, bool)
    assert wiring._CORRECTION_MODE_WARNED in (True, False)
