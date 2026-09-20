"""M-02 Personalized Storage Gate 单元 + 韧性 + 写路径接入测试。

覆盖：
- 五分类规则层关键判定（含"明早8点"≠global 的一次性时间约束语义）；
- 红绿韧性：gate 内部抛异常 → 降级 ignore+log，写路径/聊天主链零感知；
- create_episodic_memory 接入点行为（veto 返回 None；confirm 挂起注解；
  event 有界 scope 注解；kill-switch off 旁路）；
- 语义层熔断降级（超时/坏输出/断路器打开 → 规则默认，且不得自授权 confirm）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.models.memory import EpisodicMemory
from app.services.memory_storage_gate import (
    CONFIRM_CONFIDENCE_CAP,
    EVENT_BOUNDED_TAG,
    PENDING_CONFIRMATION_TAG,
    MemoryStorageGate,
    StorageGateCandidate,
    StorageGateVerdict,
    apply_decision_to_record,
    candidate_from_record,
    classify_by_rules,
    reset_gate_state,
)


def _candidate(**overrides) -> StorageGateCandidate:
    base = dict(
        user_id="user-1",
        summary="我习惯早上背单词",
        subject_type="self",
        source_type="chat",
        source_lane="inferred_extraction",
        semantic_key=None,
        evidence_token="turn-1",
        confidence=0.86,
    )
    base.update(overrides)
    return StorageGateCandidate(**base)


@pytest.fixture(autouse=True)
def _gate_live_mode(monkeypatch):
    """固定 gate=live、语义层关闭，测试纯规则行为（评测基准同口径）。"""
    reset_gate_state()
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", False, raising=False)
    monkeypatch.setattr("app.services.memory_storage_gate.settings", settings, raising=False)
    async def _live_mode(self):
        return "live"

    monkeypatch.setattr(MemoryStorageGate, "_gate_mode", _live_mode)
    yield
    reset_gate_state()


# ---------------------------------------------------------------------------
# 规则层：五分类
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_store_stable_preference():
    decision = await MemoryStorageGate().evaluate(_candidate(summary="我习惯每天早上背单词"))
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.reason == "R9.stable_pattern"


@pytest.mark.asyncio
async def test_rule_event_one_time_constraint_not_global():
    """验收核心：明早8点的瞬时 today constraint 判 event（有界），非全局长期事实。"""
    decision = await MemoryStorageGate().evaluate(
        _candidate(summary="明早8点有英语考试", subject_type="commitment", due_at=datetime(2026, 9, 20, 8, 0))
    )
    assert decision.verdict == StorageGateVerdict.EVENT.value
    assert decision.reason == "R5.one_time_constraint"
    assert decision.annotations["bounded_scope"] is True


@pytest.mark.asyncio
async def test_rule_event_without_due_at_gets_bounded_decay():
    decision = await MemoryStorageGate().evaluate(_candidate(summary="这周五论文投稿截止"))
    assert decision.verdict == StorageGateVerdict.EVENT.value


@pytest.mark.asyncio
async def test_rule_current_state_transient_mood():
    decision = await MemoryStorageGate().evaluate(_candidate(summary="我现在好累，不想学了"))
    assert decision.verdict == StorageGateVerdict.CURRENT_STATE.value
    assert decision.reason == "R6.transient_state"


@pytest.mark.asyncio
async def test_rule_ignore_noise():
    decision = await MemoryStorageGate().evaluate(_candidate(summary="哈哈哈哈"))
    assert decision.verdict == StorageGateVerdict.IGNORE.value
    assert decision.reason == "R7.noise"


@pytest.mark.asyncio
async def test_rule_ignore_banned_identity_label():
    decision = await MemoryStorageGate().evaluate(_candidate(summary="我就是很笨，学不会数学"))
    assert decision.verdict == StorageGateVerdict.IGNORE.value
    assert decision.reason == "R3.banned_identity_label"


@pytest.mark.asyncio
async def test_rule_confirm_sensitive_inferred():
    decision = await MemoryStorageGate().evaluate(_candidate(summary="我最近失眠很严重"))
    assert decision.verdict == StorageGateVerdict.CONFIRM.value
    assert decision.reason == "R4.sensitive_hypothesis"
    assert decision.annotations["pending_confirmation"] is True
    assert decision.annotations["sensitivity"] == "health"


@pytest.mark.asyncio
async def test_rule_explicit_command_overrides_sensitivity():
    """用户显式口令（帮我记住X）不被 confirm 档拦截 —— 用户自己的陈述。"""
    decision = await MemoryStorageGate().evaluate(
        _candidate(
            summary="帮我记住我有抑郁症需要长期服药",
            evidence_schema_versions=("stage16.explicit_command.v1",),
        )
    )
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.reason == "R2.explicit_user_command"


@pytest.mark.asyncio
async def test_rule_user_stated_on_explicit_lane_bypass():
    decision = await MemoryStorageGate().evaluate(
        _candidate(summary="我在吃抗焦虑的药", source_type="user_state", source_lane="direct_capture")
    )
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.layer == "bypass"


@pytest.mark.asyncio
async def test_rule_duplicate_recent_restatement_ignored():
    gate = MemoryStorageGate()
    first = await gate.evaluate(_candidate(summary="我概率论基础还行", semantic_key="k-prob"))
    assert first.verdict == StorageGateVerdict.STORE.value
    second = await gate.evaluate(_candidate(summary="我概率论基础还行", semantic_key="k-prob"))
    assert second.verdict == StorageGateVerdict.IGNORE.value
    assert second.reason == "R8.rapid_duplicate"


@pytest.mark.asyncio
async def test_rule_structured_system_subject_bypass():
    decision = await MemoryStorageGate().evaluate(
        _candidate(
            summary="用户完成了高数第三章练习，正确率80%",
            subject_type="task_outcome",
            source_type="chat_turn",
            source_lane="direct_capture",
        )
    )
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.reason == "B3.structured_system_subject"


# ---------------------------------------------------------------------------
# 规则层补强（接续 worker 修复的三处漏判 + 对抗负例）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_event_explicit_date_with_light_verb():
    """"6月15日要考四级"：日期锚点 + 轻动词"考"（考虑/思考经 lookaround 排除）。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="6月15日要考大学英语四级"))
    assert decision.verdict == StorageGateVerdict.EVENT.value
    assert decision.reason == "R5.one_time_constraint"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "summary",
    [
        "明天我要思考一下选课方向",  # 思考（lookbehind 排除）
        "明天考虑一下要不要报名社团",  # 考虑 + 要不要（否定前视排除）
        "最近考虑转专业的事",  # 无时间锚点
        "我打算考研",  # 无时间锚点
    ],
)
async def test_rule_deliberation_not_event(summary):
    decision = await MemoryStorageGate().evaluate(_candidate(summary=summary))
    assert decision.verdict == StorageGateVerdict.STORE.value


@pytest.mark.asyncio
async def test_rule_modalized_event_verb_commits():
    decision = await MemoryStorageGate().evaluate(_candidate(summary="明天我要报名数学竞赛"))
    assert decision.verdict == StorageGateVerdict.EVENT.value


@pytest.mark.asyncio
async def test_rule_transient_state_with_qualifier():
    """"我今天状态不太好"："状态不好"词形变体（不太好）经 感受token+时间标记 组合命中。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="我今天状态不太好"))
    assert decision.verdict == StorageGateVerdict.CURRENT_STATE.value
    assert decision.reason == "R6.transient_state"


@pytest.mark.asyncio
async def test_rule_stability_claim_overrides_state_token():
    """"状态"命中瞬时档的前提是无稳定性标记："一直"仍走 store。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="我最近状态一直很差"))
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.reason == "R9.stable_pattern"


@pytest.mark.asyncio
@pytest.mark.parametrize("summary", ["嗯嗯知道了", "好的谢谢", "嗯明白", "收到继续"])
async def test_rule_noise_concatenated_backchannels(summary):
    """拼接应答（嗯嗯+知道了）整体被噪声词消耗殆尽 → ignore。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary=summary))
    assert decision.verdict == StorageGateVerdict.IGNORE.value
    assert decision.reason == "R7.noise"


@pytest.mark.asyncio
async def test_rule_noise_prefix_does_not_eat_content():
    """"对，我每天早上都跑步"仅前缀是应答词：不完全消耗 → 不判噪声。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="对，我每天早上都跑步"))
    assert decision.verdict == StorageGateVerdict.STORE.value


# ---------------------------------------------------------------------------
# 韧性红绿：gate 异常不炸写路径 / 聊天主链
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_internal_exception_degrades_to_ignore():
    """红绿之绿：规则层抛异常 → evaluate 永不 raise，降级 ignore+log。"""
    gate = MemoryStorageGate()

    async def _boom(self, candidate, **kwargs):
        raise RuntimeError("rule layer exploded")

    import app.services.memory_storage_gate as gate_module

    original = gate_module.classify_by_rules
    gate_module.classify_by_rules = _boom
    try:
        decision = await gate.evaluate(_candidate(summary="我习惯早上背单词"))
    finally:
        gate_module.classify_by_rules = original
    assert decision.verdict == StorageGateVerdict.IGNORE.value
    assert decision.layer == "error_degraded"
    assert decision.reason == "ERR.internal"


@pytest.mark.asyncio
async def test_gate_veto_does_not_break_write_path(db_session, test_user, monkeypatch):
    """红绿之绿（接入点）：gate veto 时 create_episodic_memory 返回 None 而非抛异常，
    调用方（聊天主链）零感知。"""
    from unittest.mock import AsyncMock

    from app.services.memory_service import MemoryService

    user = test_user
    monkeypatch.setattr(
        "app.services.memory_storage_gate.MemoryStorageGate.evaluate",
        AsyncMock(side_effect=RuntimeError("gate exploded mid-flight")),
    )
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="我习惯早上背单词",
        source_type="chat",
        source_id=None,
        occurred_at=datetime.utcnow(),
        importance_score=0.7,
        confidence=0.8,
        tags=[],
        evidence_refs=[{"type": "chat_turn", "id": "evt", "schema_version": "chat_turn.v1"}],
        emit_system_update=False,
    )
    # gate 抛异常 → 降级 ignore → 写被跳过（None），但绝不向上抛
    assert record is None


@pytest.mark.asyncio
async def test_write_path_lets_store_through(db_session, test_user, monkeypatch):
    from app.services.memory_service import MemoryService

    user = test_user
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="我习惯每天早上背单词，效率最高",
        source_type="chat",
        source_id=None,
        occurred_at=datetime.utcnow(),
        importance_score=0.7,
        confidence=0.86,
        tags=[],
        evidence_refs=[{"type": "chat_turn", "id": "evt-store", "schema_version": "chat_turn.v1"}],
        emit_system_update=False,
    )
    assert record is not None
    assert record.id is not None


@pytest.mark.asyncio
async def test_write_path_confirm_writes_pending_hypothesis(db_session, test_user):
    """confirm 档：写入挂起 HYPOTHESIS（docked confidence + pending tag），
    由既有四动作治理 API 收口（confirm/wrong/outdated/delete），不新造机制。"""
    from app.services.memory_service import MemoryService

    user = test_user
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="我最近失眠很严重，每天只睡四小时",
        source_type="chat",
        source_id=None,
        source_lane="inferred_extraction",
        occurred_at=datetime.utcnow(),
        importance_score=0.8,
        confidence=0.85,
        tags=[],
        evidence_refs=[{"type": "chat_turn", "id": "evt-confirm", "schema_version": "chat_turn.v1"}],
        emit_system_update=True,
    )
    assert record is not None
    assert record.epistemic_class == "HYPOTHESIS"
    assert record.confidence <= CONFIRM_CONFIDENCE_CAP
    assert PENDING_CONFIRMATION_TAG in (record.tags or [])
    assert "m02:sensitive:health" in (record.tags or [])


@pytest.mark.asyncio
async def test_write_path_event_bounded_scope(db_session, test_user):
    from app.services.memory_service import MemoryService

    user = test_user
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="今天下午3点实验课签到",
        source_type="chat",
        source_id=None,
        occurred_at=datetime.utcnow(),
        importance_score=0.7,
        confidence=0.85,
        tags=[],
        evidence_refs=[{"type": "chat_turn", "id": "evt-event", "schema_version": "chat_turn.v1"}],
        decay_policy="30d",
        emit_system_update=False,
    )
    assert record is not None
    assert EVENT_BOUNDED_TAG in (record.tags or [])
    # 无 due_at 的瞬时 today constraint：decay 被压到短窗（7d），非全局长存
    assert record.decay_policy == "7d"


@pytest.mark.asyncio
async def test_write_path_gate_off_bypasses(db_session, test_user, monkeypatch):
    async def _off(self):
        return "off"

    monkeypatch.setattr(MemoryStorageGate, "_gate_mode", _off)
    from app.services.memory_service import MemoryService

    user = test_user
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="哈哈哈哈",
        source_type="chat",
        source_id=None,
        occurred_at=datetime.utcnow(),
        importance_score=0.5,
        confidence=0.6,
        tags=[],
        evidence_refs=[{"type": "chat_turn", "id": "evt-off", "schema_version": "chat_turn.v1"}],
        emit_system_update=False,
    )
    assert record is not None  # gate off → 噪声也照旧写入（恢复既有行为）


@pytest.mark.asyncio
async def test_write_path_gate_vetoes_transient(db_session, test_user):
    from app.services.memory_service import MemoryService

    user = test_user
    service = MemoryService(db_session)
    record = await service.create_episodic_memory(
        user_id=user.id,
        summary="我现在好累，不想学了",
        source_type="chat",
        source_id=None,
        occurred_at=datetime.utcnow(),
        importance_score=0.6,
        confidence=0.7,
        tags=[],
        evidence_refs=[{"type": "chat_turn", "id": "evt-cs", "schema_version": "chat_turn.v1"}],
        emit_system_update=False,
    )
    assert record is None  # current_state → 不落 L1（留在 Redis 工作记忆层）


# ---------------------------------------------------------------------------
# 语义层熔断降级
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_semantic_disabled_uses_rule_layer_only(monkeypatch):
    """语义层默认关闭：R10 歧义残留直接 fail-open store，不发起 LLM 调用。"""
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", False, raising=False)
    calls = []

    async def _llm(prompt):
        calls.append(prompt)
        return {"class": "ignore"}

    gate = MemoryStorageGate(semantic_llm=_llm)
    decision = await gate.evaluate(_candidate(summary="我高数比较薄弱，特别是级数部分"))
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.layer == "rule"
    assert calls == []


@pytest.mark.asyncio
async def test_semantic_refines_ambiguous_candidate(monkeypatch):
    """语义层开启时对规则歧义残留做五分类精化。"""
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", True, raising=False)

    async def _llm(prompt):
        return {"class": "ignore", "reason": "无决策价值的牢骚"}

    gate = MemoryStorageGate(semantic_llm=_llm)
    decision = await gate.evaluate(_candidate(summary="我高数比较薄弱，特别是级数部分"))
    assert decision.verdict == StorageGateVerdict.IGNORE.value
    assert decision.layer == "semantic"


@pytest.mark.asyncio
async def test_semantic_timeout_degrades_to_rule_default(monkeypatch):
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_TIMEOUT_SECONDS", 0.05, raising=False)

    async def _slow_llm(prompt):
        import asyncio

        await asyncio.sleep(1.0)
        return {"class": "ignore"}

    gate = MemoryStorageGate(semantic_llm=_slow_llm)
    decision = await gate.evaluate(_candidate(summary="我高数比较薄弱，特别是级数部分"))
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.layer == "rule"


@pytest.mark.asyncio
async def test_semantic_bad_payload_degrades(monkeypatch):
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", True, raising=False)

    async def _bad_llm(prompt):
        return "not-json-garbage"

    gate = MemoryStorageGate(semantic_llm=_bad_llm)
    decision = await gate.evaluate(_candidate(summary="我高数比较薄弱，特别是级数部分"))
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.layer == "rule"


@pytest.mark.asyncio
async def test_semantic_cannot_self_authorize_confirm(monkeypatch):
    """语义层不得自授权 confirm：敏感确认必须来自可审计的规则命中。"""
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", True, raising=False)

    async def _confirm_llm(prompt):
        return {"class": "confirm", "reason": "llm thinks so"}

    gate = MemoryStorageGate(semantic_llm=_confirm_llm)
    decision = await gate.evaluate(_candidate(summary="我高数比较薄弱，特别是级数部分"))
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.reason == "S1.semantic_confirm_demoted"


@pytest.mark.asyncio
async def test_semantic_breaker_opens_after_consecutive_failures(monkeypatch):
    monkeypatch.setattr(settings, "SPARKLE_STORAGE_GATE_SEMANTIC_ENABLED", True, raising=False)
    calls = []

    async def _flaky(prompt):
        calls.append(prompt)
        raise ConnectionError("llm down")

    gate = MemoryStorageGate(semantic_llm=_flaky)
    texts = ["我高数比较薄弱，特别是级数部分", "我线代基础还可以", "我英语阅读速度偏慢"]
    for text in texts[: MemoryStorageGate.SEMANTIC_BREAKER_THRESHOLD]:
        decision = await gate.evaluate(_candidate(summary=text))
        assert decision.verdict == StorageGateVerdict.STORE.value
        assert decision.layer == "rule"
    assert MemoryStorageGate._semantic_open_until > 0
    calls_before = len(calls)
    # breaker open：不再发起调用，直接规则默认
    await gate.evaluate(_candidate(summary=texts[-1]))
    assert len(calls) == calls_before


@pytest.mark.asyncio
async def test_shadow_mode_never_vetoes(monkeypatch):
    async def _shadow(self):
        return "shadow"

    monkeypatch.setattr(MemoryStorageGate, "_gate_mode", _shadow)
    gate = MemoryStorageGate()
    decision = await gate.evaluate(_candidate(summary="我现在好累"))
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.layer == "shadow"
    assert decision.annotations["shadow_verdict"] == StorageGateVerdict.CURRENT_STATE.value


# ---------------------------------------------------------------------------
# apply_decision_to_record 幂等性（向量运行时降级重建路径会重放）
# ---------------------------------------------------------------------------


def _fake_record(**overrides) -> EpisodicMemory:
    base = dict(
        user_id=uuid4(),
        summary="明早8点有英语考试",
        source_type="chat",
        source_lane="inferred_extraction",
        subject_type="commitment",
        occurred_at=datetime.utcnow(),
        due_at=datetime.utcnow() + timedelta(days=1),
        confidence=0.9,
        tags=["stage16:auto_memory"],
        evidence_refs=[],
        evidence_score=0.5,
    )
    base.update(overrides)
    return EpisodicMemory(**base)


def test_apply_decision_idempotent_for_event():
    from app.services.memory_storage_gate import StorageGateDecision

    record = _fake_record(decay_policy=None)
    decision = StorageGateDecision(
        verdict=StorageGateVerdict.EVENT.value,
        layer="rule",
        reason="R5.one_time_constraint",
        annotations={"bounded_scope": True},
    )
    apply_decision_to_record(record, decision)
    once_tags = list(record.tags)
    once_decay = record.decay_policy
    apply_decision_to_record(record, decision)
    assert record.tags == once_tags
    assert record.decay_policy == once_decay


def test_candidate_from_record_projects_schema_versions():
    record = _fake_record(
        evidence_refs=[{"type": "chat_turn", "id": "t1", "schema_version": "stage16.explicit_command.v1"}]
    )
    candidate = candidate_from_record(record)
    assert candidate.evidence_schema_versions == ("stage16.explicit_command.v1",)
    decision = classify_by_rules(candidate)
    assert decision.verdict == StorageGateVerdict.STORE.value
    assert decision.reason == "R2.explicit_user_command"


# ---------------------------------------------------------------------------
# V3-FIX-41：规则层四处漏判扩面 + R10 敏感域 fail-closed（红→绿）
#
# 证据锚：E-04 R2 回执 §7 复测（backup/2026-09-20/E-04/REVIEW_RECEIPT_2.md）、
# DYNAMIC_ISSUES V3-FIX-41、ai_face_eval cases memory.gate.json 的
# mem-C2b/C3b/C4/C4b/C5 golden。语义层默认关的现状下这些内容曾全部
# R10.ambiguous_inferred → fail-open STORE 无确认入库。
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fix41_event_yaodo_slot_with_time_anchor():
    """漏判①（R5）：「下周五要做课程展示」——时间锚点 +「要做 X」句式判 event。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="下周五要做课程展示"))
    assert decision.verdict == StorageGateVerdict.EVENT.value, decision
    assert decision.reason == "R5.one_time_constraint"
    assert decision.annotations["bounded_scope"] is True


@pytest.mark.asyncio
async def test_fix41_transient_headache_body_state():
    """漏判②（R6）：「今天有点头疼」——身体状态词判 current_state（健康相邻，
    留工作记忆层，绝不长期化）。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="今天有点头疼"))
    assert decision.verdict == StorageGateVerdict.CURRENT_STATE.value, decision
    assert decision.reason == "R6.transient_state"


@pytest.mark.asyncio
async def test_fix41_confirm_financial_balance_distress():
    """漏判③（R4）：「银行卡余额只剩两百块」——经济困境表述判 confirm。"""
    decision = await MemoryStorageGate().evaluate(
        _candidate(summary="用户说他的银行卡余额只剩两百块，担心撑不到月底")
    )
    assert decision.verdict == StorageGateVerdict.CONFIRM.value, decision
    assert decision.reason == "R4.sensitive_hypothesis"
    assert decision.annotations["pending_confirmation"] is True
    assert decision.annotations["sensitivity"] == "financial"


@pytest.mark.asyncio
async def test_fix41_ignore_reported_goodnight():
    """漏判④（R7）：转述语中嵌告别（「说了句晚安准备睡觉」）判 ignore——
    NOISE_EXACT 仅整句精确匹配，转述语模式此前漏 R7。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="用户说了句晚安准备睡觉"))
    assert decision.verdict == StorageGateVerdict.IGNORE.value, decision
    assert decision.reason == "R7.noise"


@pytest.mark.asyncio
async def test_fix41_ignore_reported_gesture_reply():
    """漏判④同族（R7，ai_face mem-C4b golden=ignore）：「回复了一个ok的手势」。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary="用户回复了一个ok的手势"))
    assert decision.verdict == StorageGateVerdict.IGNORE.value, decision
    assert decision.reason == "R7.noise"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "summary",
    [
        "这个月生活费快见底了",  # 金融域措辞（见底）不在 R4 精确词表 → 曾 fail-open store
        "我对花生过敏",  # 健康域（过敏）不在 R4 精确词表 → 曾 fail-open store
    ],
)
async def test_fix41_r10_sensitive_domain_residue_fail_closed(summary):
    """核心缺陷（R10 fail-open → fail-closed）：敏感域措辞漏过 R4 精确词表、
    又无瞬时/事件/稳定信号的歧义残留，不得在语义层默认关时无确认入库——
    拒收为挂起待确认（confirm），敏感域 fail-closed。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary=summary))
    assert decision.verdict == StorageGateVerdict.CONFIRM.value, decision
    assert decision.reason == "R10.sensitive_domain_fail_closed"
    assert decision.annotations["pending_confirmation"] is True
    assert decision.annotations["sensitivity"] in {"financial", "health", "mental_state"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "summary",
    [
        "我高数比较薄弱，特别是级数部分",  # m02-st03 学习画像：非敏感域维持现状
        "我英语阅读速度偏慢",
        "你提到过一位学习相关人物",  # m02-st08
    ],
)
async def test_fix41_r10_non_sensitive_residue_stays_store(summary):
    """非敏感域不过度拒收（负例）：R10 歧义残留维持 store + semantic_eligible，
    避免敏感网过宽破坏推断条目入库体验。"""
    decision = await MemoryStorageGate().evaluate(_candidate(summary=summary))
    assert decision.verdict == StorageGateVerdict.STORE.value, decision
    assert decision.reason == "R10.ambiguous_inferred"
    assert decision.annotations.get("semantic_eligible") is True


class TestP21PotatoNegative:
    """FIX-41 P2-1 回归钉（Leader 顺修）：裸词「吃土」与食物「吃土豆」的
    containment 误命中不得复发——食物偏好不得误确认且错标财务。"""

    def test_potato_food_preference_not_financial(self):
        d = classify_by_rules(_candidate(summary="我喜欢吃土豆"))
        assert not (d.verdict == "confirm_required" and "financial" in str(d.annotations.get("domain", "")) + d.reason + d.detail)

    def test_bare_chitu_still_caught_by_net(self):
        d = classify_by_rules(_candidate(summary="这个月生活费花光了要吃土了"))
        assert d.verdict.startswith("confirm")
