"""
P-04 — 低风险 Auto-execute 授权模型 单测。

钉住验收三条（卡定义原文，本卡灵魂）：
1. **未授权 = 0 次自动执行** —— mock 执行器断言零调用：无授权 / 已 revoke /
   总闸 / 白名单外 / 授权状态读取故障（fail-closed）全路径逐一断言；
2. **revoke 后立即失效** —— grant → auto 执行 → revoke → 下一条 trigger
   即转 proposal（授权路径现读文档 + 版本 bump，无陈旧缓存）；
3. **重复 trigger 不产生重复 side effect** —— 同 (user, op, trigger, subject)
   重复投递：执行器**恰一次**，第二次返回既有 receipt（replayed）。

红线钉桩：
4. **高风险/不可逆操作永远 proposal** —— allowlist 结构性排除（封闭词表 +
   元数据校验 risk=low/reversible=True，import 期自检）+ 决策层元数据复核
   （纵深防御：篡改注册表塞入高危条目仍被第二道闸拦下）；
5. **每次 auto 执行有 receipt/notification** —— receipt 六要素完整
   （谁/何时/哪个操作/幂等键/结果/授权版本）+ notification 载荷同形；
6. **零 LLM** —— 全模块确定性；包源码静态扫描无 LLM 引用（P-01 同款）。

测试完全 hermetic：内存 FakeRedis、无 DB、无网络、无 Celery、无真实 LLM。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import pytest

from app.aurora.proactive.autoexec import (
    AUTOEXEC_EMPTY_VERSION,
    AUTOEXEC_OPERATION_REGISTRY,
    AUTOEXEC_OPERATION_VOCABULARY,
    AUTOEXEC_SCHEMA_VERSION,
    AutoExecDecisionReason,
    AutoExecGrantStore,
    AutoExecOpMetadata,
    AutoExecReceipt,
    AutoExecReceiptStore,
    AutoExecRequest,
    AutoExecStateUnavailable,
    ProactiveAutoExecGate,
    build_autoexec_receipt_notification,
    compute_grant_policy_version,
    decide_auto_execution,
    derive_autoexec_idempotency_key,
    validate_autoexec_allowlist,
)

_USER = "user-p04-0001"
_NOW = datetime(2026, 9, 21, 12, 0, 0)  # 固定 naive-UTC


def _now() -> datetime:
    return _NOW


# --- FakeRedis（duck-typing：只实现 store 用到的 get/set） -------------------


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.data[key] = value
        return True


class BrokenRedis:
    """读/写必炸的 redis 探针（fail-closed 故障注入）。"""

    async def get(self, key: str) -> str:
        raise ConnectionError("redis down")

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        raise ConnectionError("redis down")


class ExecutorSpy:
    """执行器探针：记录每次调用并返回固定结果（零调用断言的真源）。"""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[AutoExecRequest] = []
        self.fail = fail

    async def __call__(self, request: AutoExecRequest) -> dict[str, Any]:
        self.calls.append(request)
        if self.fail:
            raise RuntimeError("executor boom")
        return {"ok": True, "op": request.operation, "subject": request.subject_key}


def _make_gate(
    redis: FakeRedis | None = None,
    *,
    shadow: bool = False,
    executor: ExecutorSpy | None = None,
    sinked: list[AutoExecReceipt] | None = None,
    notified: list[AutoExecReceipt] | None = None,
) -> tuple[ProactiveAutoExecGate, ExecutorSpy, AutoExecGrantStore, AutoExecReceiptStore]:
    r = redis if redis is not None else FakeRedis()
    grants = AutoExecGrantStore(r)
    receipts = AutoExecReceiptStore(r)
    spy = executor if executor is not None else ExecutorSpy()

    async def sink(receipt: AutoExecReceipt) -> None:
        if sinked is not None:
            sinked.append(receipt)

    async def notify(receipt: AutoExecReceipt) -> None:
        if notified is not None:
            notified.append(receipt)

    gate = ProactiveAutoExecGate(
        grants=grants,
        receipts=receipts,
        execute=spy,
        sink=sink,
        notify=notify,
        shadow=shadow,
    )
    return gate, spy, grants, receipts


async def _grant(grants: AutoExecGrantStore, op: str) -> None:
    await grants.grant(_USER, op, now=_now())


# ===========================================================================
# 1. allowlist 契约（封闭词表 + 元数据红线；高风险结构性无表内名字）
# ===========================================================================


def test_allowlist_vocabulary_is_frozen():
    """allowlist 词表封闭且逐字钉死（扩词表 = 契约变更，测试必红）。"""
    assert AUTOEXEC_SCHEMA_VERSION == "aurora_autoexec.v1"
    assert (
        frozenset(
            {
                "notification.mark_read",
                "subject.bookmark",
                "reminder.snooze",
            }
        )
        == AUTOEXEC_OPERATION_VOCABULARY
    )


def test_allowlist_metadata_soul_invariants():
    """灵魂红线：表内每个操作 risk=low 且 reversible=True（违宪条目=校验失败）。"""
    assert validate_autoexec_allowlist() == ()
    for name in AUTOEXEC_OPERATION_VOCABULARY:
        meta = AUTOEXEC_OPERATION_REGISTRY[name]
        assert meta.risk == "low", f"{name} risk 必须是 low"
        assert meta.reversible is True, f"{name} 必须可逆"
        assert meta.effect in {"read", "write"}
        assert meta.operation == name


def test_high_risk_entry_fails_allowlist_validation():
    """变异守卫基线：把高风险条目塞进（假想）注册表 → 校验必须报违宪 issue。"""
    bogus = {
        **AUTOEXEC_OPERATION_REGISTRY,
        "task.delete_all": AutoExecOpMetadata(
            operation="task.delete_all",
            effect="write",
            risk="high",  # 违宪：高风险
            reversible=False,  # 违宪：不可逆
            description="bogus",
        ),
    }
    issues = validate_autoexec_allowlist(bogus)
    assert any("task.delete_all" in i and "risk" in i for i in issues), issues
    assert any("task.delete_all" in i and "reversible" in i for i in issues), issues
    # 真实注册表无任何高危名（结构性排除的真源断言）。
    assert "task.delete_all" not in AUTOEXEC_OPERATION_VOCABULARY


def test_high_risk_names_are_never_allowlisted():
    """高风险/不可逆/外部 side-effect 操作族在 allowlist 里没有合法名字。"""
    for dangerous in (
        "task.delete_all",
        "task.delete",
        "plan.delete",
        "memory.purge",
        "external.email.send",
        "external.payment.charge",
        "chat.message.send",
        "document.hard_delete",
    ):
        assert dangerous not in AUTOEXEC_OPERATION_VOCABULARY, dangerous
        # 即使授权文档被污染塞入了高危名，决策也在 allowlist 门被拦。
        decision = decide_auto_execution(
            user_id=_USER,
            operation=dangerous,
            trigger="deadline",
            subject_key="t1",
            grant_doc={"grants": {dangerous: _NOW.isoformat()}},
            now=_now(),
        )
        assert decision.allowed is False
        assert decision.mode == "proposal"
        assert decision.reason == AutoExecDecisionReason.PROPOSAL_NOT_ALLOWLISTED.value


def test_metadata_recheck_blocks_tampered_registry_entry():
    """纵深防御：篡改注册表把已知 allowlist 操作改成高危 → 决策层复核仍拒绝。"""
    op = "notification.mark_read"
    tampered = {
        **AUTOEXEC_OPERATION_REGISTRY,
        op: AutoExecOpMetadata(operation=op, effect="write", risk="high", reversible=False, description="tampered"),
    }
    from app.aurora.proactive import autoexec as mod

    original = mod.AUTOEXEC_OPERATION_REGISTRY
    try:
        mod.AUTOEXEC_OPERATION_REGISTRY = tampered
        decision = decide_auto_execution(
            user_id=_USER,
            operation=op,
            trigger="deadline",
            subject_key="t1",
            grant_doc={"grants": {op: _NOW.isoformat()}, "policy_version": "autox_x"},
            now=_now(),
        )
        assert decision.allowed is False
        assert decision.reason == AutoExecDecisionReason.PROPOSAL_RISK_NOT_LOW.value
    finally:
        mod.AUTOEXEC_OPERATION_REGISTRY = original


# ===========================================================================
# 2. 决策纯函数：授权语义（确定性）
# ===========================================================================


@pytest.mark.parametrize("op", sorted(AUTOEXEC_OPERATION_VOCABULARY))
def test_ungranted_operation_is_always_proposal(op: str):
    """表内操作但未授权 → proposal（grant_absent）。"""
    decision = decide_auto_execution(
        user_id=_USER, operation=op, trigger="deadline", subject_key="t1", grant_doc={}, now=_now()
    )
    assert decision.allowed is False
    assert decision.mode == "proposal"
    assert decision.reason == AutoExecDecisionReason.PROPOSAL_GRANT_ABSENT.value


def test_granted_operation_is_auto_with_version_attribution():
    op = "subject.bookmark"
    doc = {"grants": {op: _NOW.isoformat()}, "policy_version": "autox_abcd1234"}
    decision = decide_auto_execution(
        user_id=_USER, operation=op, trigger="deadline", subject_key="t1", grant_doc=doc, now=_now()
    )
    assert decision.allowed is True
    assert decision.mode == "auto"
    assert decision.reason == AutoExecDecisionReason.AUTO_GRANTED.value
    assert decision.grant_version == "autox_abcd1234"


def test_master_switch_forces_proposal_even_when_granted():
    op = "notification.mark_read"
    doc = {
        "grants": {op: _NOW.isoformat()},
        "master_disabled": True,
        "policy_version": "autox_abcd1234",
    }
    decision = decide_auto_execution(
        user_id=_USER, operation=op, trigger="deadline", subject_key="t1", grant_doc=doc, now=_now()
    )
    assert decision.allowed is False
    assert decision.reason == AutoExecDecisionReason.PROPOSAL_MASTER_DISABLED.value


def test_idempotency_key_is_deterministic_and_discriminating():
    kw = {"user_id": _USER, "operation": "reminder.snooze", "trigger": "deadline"}
    k1 = derive_autoexec_idempotency_key(**kw, subject_key="t1")
    k2 = derive_autoexec_idempotency_key(**kw, subject_key="t1")
    assert k1 == k2, "同输入恒同键（重复 trigger 去重依据）"
    assert k1.startswith("autoxid_") and len(k1) == len("autoxid_") + 32
    for changed in (
        {**kw, "subject_key": "t2"},  # subject 不同 → 新键（新的合法执行）
        {**kw, "operation": "subject.bookmark", "subject_key": "t1"},
        {**kw, "user_id": "user-p04-0002", "subject_key": "t1"},
    ):
        assert derive_autoexec_idempotency_key(**changed) != k1


def test_grant_version_content_addressed():
    """版本内容寻址（A-05 同款）：授权集变化 → 版本必然变化（revoke 即时生效
    与执行门二次版本校验的共同依据）。"""
    v_empty = compute_grant_policy_version({})
    assert v_empty == AUTOEXEC_EMPTY_VERSION == "autox_none"
    v1 = compute_grant_policy_version({"notification.mark_read": "t0"})
    v2 = compute_grant_policy_version({"notification.mark_read": "t0", "subject.bookmark": "t1"})
    v1_again = compute_grant_policy_version({"notification.mark_read": "t0"})
    assert v1 != v2 and v1 == v1_again and v1.startswith("autox_")


def test_grant_cache_key_removed_not_wired():
    """FIX-47③：决策路径每次 trigger 现读授权文档、无携带授权语义的缓存
    消费方——``grant_cache_key`` 原语按论证**删除**而非假接线（假接线 = 给
    每次 context 构建加一次 Redis 读、零 stale 收益）。复活条件已登记在模块
    文档：若未来 context 缓存开始消费授权状态，必须把版本并入
    ``ContextCacheVersions``。本测试钉住删除决定，重加导出 = 有意识的
    接线决策，必须伴随消费方。"""
    import app.aurora.proactive.autoexec as mod

    assert not hasattr(mod, "grant_cache_key")
    assert "grant_cache_key" not in getattr(mod, "__all__", [])


# ===========================================================================
# 3. 授权存储：grant/revoke + 版本 bump（revoke 即时生效的实现点）
# ===========================================================================


async def test_grant_and_revoke_roundtrip_with_version_bump():
    redis = FakeRedis()
    grants = AutoExecGrantStore(redis)
    op = "notification.mark_read"

    empty_doc = await grants.read(_USER)
    assert empty_doc == {}  # 新用户零授权是合法空态

    doc1 = await grants.grant(_USER, op, now=_now())
    assert doc1["grants"][op]
    v1 = doc1["policy_version"]
    assert v1 != AUTOEXEC_EMPTY_VERSION

    doc2 = await grants.revoke(_USER, op, now=_now())
    assert op not in doc2["grants"]
    assert doc2["policy_version"] != v1, "revoke 必须 bump 版本（即时生效的实现点）"
    assert doc2["policy_version"] == AUTOEXEC_EMPTY_VERSION  # 授权集空 → 稳定常量

    # 持久化到 redis 且可再读（决策路径现读的依据）。
    reread = await grants.read(_USER)
    assert op not in reread["grants"]


async def test_grant_rejects_non_allowlisted_operation():
    """授权面结构性封闭：allowlist 外的名字不可被授予（ValueError）。"""
    grants = AutoExecGrantStore(FakeRedis())
    with pytest.raises(ValueError, match="not_allowlisted"):
        await grants.grant(_USER, "task.delete_all", now=_now())
    with pytest.raises(ValueError, match="not_allowlisted"):
        await grants.grant(_USER, "", now=_now())


async def test_duplicate_grant_is_idempotent():
    redis = FakeRedis()
    grants = AutoExecGrantStore(redis)
    doc1 = await grants.grant(_USER, "reminder.snooze", now=_now())
    doc2 = await grants.grant(_USER, "reminder.snooze", now=_now())
    assert doc1["policy_version"] == doc2["policy_version"]
    assert list(doc2["grants"]) == ["reminder.snooze"]


async def test_corrupt_grant_doc_fails_closed():
    grants = AutoExecGrantStore(CorruptGrantRedis("not-json{{"))
    with pytest.raises(AutoExecStateUnavailable):
        await grants.read(_USER)


class CorruptGrantRedis:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    async def get(self, key: str) -> str:
        return self.payload

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        return True


# ===========================================================================
# 4. 灵魂验收 ①：未授权 = 0 次自动执行（mock 执行器零调用）
# ===========================================================================


@pytest.mark.parametrize(
    "scenario",
    ["no_grants", "revoked", "master_disabled", "not_allowlisted", "grants_unavailable", "receipts_unavailable"],
)
async def test_unauthorized_paths_never_execute(scenario: str):
    """全未授权路径：执行器零调用 + outcome 一律 proposal。"""
    redis = FakeRedis()
    grants_store = AutoExecGrantStore(redis)
    if scenario == "revoked":
        await grants_store.grant(_USER, "notification.mark_read", now=_now())
        await grants_store.revoke(_USER, "notification.mark_read", now=_now())
    elif scenario == "master_disabled":
        await grants_store.grant(_USER, "notification.mark_read", now=_now())
        await grants_store.set_master_switch(_USER, disabled=True, now=_now())
    elif scenario == "receipts_unavailable":
        # 已授权（授权门通过）但 receipt 索引读不到 → fail-closed（避免重复执行）。
        await grants_store.grant(_USER, "notification.mark_read", now=_now())

    gate, spy, grants, receipts = _make_gate(redis, shadow=False)
    gate.grants = grants_store
    if scenario == "grants_unavailable":
        gate.grants = AutoExecGrantStore(BrokenRedis())
    elif scenario == "receipts_unavailable":
        gate.receipts = AutoExecReceiptStore(BrokenRedis())

    op = "task.delete_all" if scenario == "not_allowlisted" else "notification.mark_read"
    outcome = await gate.handle_operation(user_id=_USER, operation=op, trigger="deadline", subject_key="t1", now=_now())

    assert spy.calls == [], f"{scenario}: 未授权路径执行器必须零调用"
    assert outcome.mode == "proposal"
    assert outcome.receipt is None
    if scenario == "no_grants" or scenario == "revoked":
        assert outcome.reason == AutoExecDecisionReason.PROPOSAL_GRANT_ABSENT.value
    elif scenario == "master_disabled":
        assert outcome.reason == AutoExecDecisionReason.PROPOSAL_MASTER_DISABLED.value
    elif scenario == "not_allowlisted":
        assert outcome.reason == AutoExecDecisionReason.PROPOSAL_NOT_ALLOWLISTED.value
    elif scenario == "grants_unavailable" or scenario == "receipts_unavailable":
        assert outcome.reason == AutoExecDecisionReason.PROPOSAL_STATE_UNAVAILABLE.value


async def test_only_granted_operation_executes_others_proposal():
    """授权了 A 不代表 B：同用户下未授权操作零执行（授权粒度=操作级）。"""
    gate, spy, grants, _receipts = _make_gate(shadow=False)
    await _grant(grants, "notification.mark_read")

    executed = await gate.handle_operation(
        user_id=_USER, operation="notification.mark_read", trigger="deadline", subject_key="t1", now=_now()
    )
    assert executed.mode == "auto" and len(spy.calls) == 1

    denied = await gate.handle_operation(
        user_id=_USER, operation="subject.bookmark", trigger="deadline", subject_key="t1", now=_now()
    )
    assert denied.mode == "proposal"
    assert denied.reason == AutoExecDecisionReason.PROPOSAL_GRANT_ABSENT.value
    assert len(spy.calls) == 1, "未授权操作不得增加执行器调用"


async def test_other_user_grant_does_not_leak():
    """授权按用户隔离：user A 的授权不适用于 user B（B 零执行）。"""
    gate, spy, grants, _receipts = _make_gate(shadow=False)
    await grants.grant("user-p04-0002", "notification.mark_read", now=_now())

    outcome = await gate.handle_operation(
        user_id=_USER, operation="notification.mark_read", trigger="deadline", subject_key="t1", now=_now()
    )
    assert outcome.mode == "proposal"
    assert spy.calls == []


async def test_shadow_mode_never_executes_even_when_granted():
    """shadow（默认）：即便白名单+已授权，执行器零调用，would_auto=True。"""
    gate, spy, grants, _receipts = _make_gate(shadow=True)
    await _grant(grants, "subject.bookmark")

    outcome = await gate.handle_operation(
        user_id=_USER, operation="subject.bookmark", trigger="deadline", subject_key="t1", now=_now()
    )
    assert outcome.mode == "proposal"
    assert outcome.reason == AutoExecDecisionReason.PROPOSAL_SHADOW.value
    assert outcome.would_auto is True
    assert outcome.decision is not None and outcome.decision.allowed is True
    assert spy.calls == [], "shadow 模式执行器必须零调用"


# ===========================================================================
# 5. 灵魂验收 ②：revoke 后下一条 trigger 立即转 proposal
# ===========================================================================


async def test_revoke_takes_effect_on_next_trigger():
    """grant → auto 执行 → revoke → 下一条（不同 subject）即不执行。"""
    gate, spy, grants, _receipts = _make_gate(shadow=False)
    await _grant(grants, "reminder.snooze")

    first = await gate.handle_operation(
        user_id=_USER, operation="reminder.snooze", trigger="deadline", subject_key="t1", now=_now()
    )
    assert first.mode == "auto" and first.receipt is not None
    assert len(spy.calls) == 1

    await grants.revoke(_USER, "reminder.snooze", now=_now())

    second = await gate.handle_operation(
        user_id=_USER, operation="reminder.snooze", trigger="overdue", subject_key="t2", now=_now()
    )
    assert second.mode == "proposal", "revoke 后下一条 trigger 必须立即转 proposal"
    assert second.reason == AutoExecDecisionReason.PROPOSAL_GRANT_ABSENT.value
    assert len(spy.calls) == 1, "revoke 后执行器零新增调用"


async def test_master_switch_stops_execution_immediately():
    """总闸同样即时：已授权+已执行 → 开总闸 → 下一条 proposal。"""
    gate, spy, grants, _receipts = _make_gate(shadow=False)
    await _grant(grants, "subject.bookmark")
    ok = await gate.handle_operation(
        user_id=_USER, operation="subject.bookmark", trigger="deadline", subject_key="t1", now=_now()
    )
    assert ok.mode == "auto"

    await grants.set_master_switch(_USER, disabled=True, now=_now())
    stopped = await gate.handle_operation(
        user_id=_USER, operation="subject.bookmark", trigger="deadline", subject_key="t2", now=_now()
    )
    assert stopped.mode == "proposal"
    assert stopped.reason == AutoExecDecisionReason.PROPOSAL_MASTER_DISABLED.value
    assert len(spy.calls) == 1


# ===========================================================================
# 6. 灵魂验收 ③：重复 trigger 恰一次 side effect（幂等键去重）
# ===========================================================================


async def test_duplicate_trigger_executes_exactly_once():
    """同一 (user, op, trigger, subject) 重复投递：执行器恰一次，第二次 replay。"""
    gate, spy, grants, receipts = _make_gate(shadow=False)
    await _grant(grants, "notification.mark_read")

    kw = {"user_id": _USER, "operation": "notification.mark_read", "trigger": "deadline", "subject_key": "t1"}
    first = await gate.handle_operation(now=_now(), **kw)
    second = await gate.handle_operation(now=_now(), **kw)

    assert first.mode == "auto" and first.reason == AutoExecDecisionReason.AUTO_GRANTED.value
    assert first.receipt is not None and first.receipt.result == "executed"
    assert second.mode == "auto"
    assert second.reason == AutoExecDecisionReason.DEDUP_REPLAY.value
    assert second.details.get("replayed") is True
    assert len(spy.calls) == 1, "重复 trigger 执行器必须恰一次调用"
    assert second.receipt.idempotency_key == first.receipt.idempotency_key
    assert second.receipt.result == "executed"  # 奉还既有回执本体

    # receipt 索引恰一条。
    stored = await receipts.find(_USER, first.receipt.idempotency_key)
    assert stored is not None and stored.result == "executed"


async def test_distinct_subjects_each_execute_once():
    """不同 subject → 不同幂等键 → 各自执行一次（去重不越权吞掉新事件）。"""
    gate, spy, grants, _receipts = _make_gate(shadow=False)
    await _grant(grants, "reminder.snooze")
    for i, subject in enumerate(("t1", "t2", "t1")):  # t1 重复 → 只 2 次执行
        outcome = await gate.handle_operation(
            user_id=_USER,
            operation="reminder.snooze",
            trigger="deadline",
            subject_key=subject,
            now=_now(),
        )
        assert outcome.mode == "auto"
        assert (outcome.reason == AutoExecDecisionReason.AUTO_GRANTED.value) is (subject != "t1" or i == 0)
    assert len(spy.calls) == 2, f"t1/t2 各一次，t1 重放：实际 {len(spy.calls)} 次"


async def test_executor_failure_falls_back_to_proposal_and_allows_retry():
    """执行器异常：无成功 receipt（无 side effect）→ proposal 兜底；重试可行。"""
    redis = FakeRedis()
    failing = ExecutorSpy(fail=True)
    gate, spy, grants, _receipts = _make_gate(redis, shadow=False, executor=failing)
    await _grant(grants, "subject.bookmark")

    failed = await gate.handle_operation(
        user_id=_USER, operation="subject.bookmark", trigger="deadline", subject_key="t1", now=_now()
    )
    assert failed.mode == "proposal"
    assert failed.reason == AutoExecDecisionReason.AUTO_EXECUTOR_FAILED.value
    assert len(failing.calls) == 1

    # 执行器恢复后重试（同键）成功：恰一次语义不被失败污染。
    recovered = ExecutorSpy()
    gate2, spy2, _grants2, receipts2 = _make_gate(redis, shadow=False, executor=recovered)
    gate2.grants = grants
    retry = await gate2.handle_operation(
        user_id=_USER, operation="subject.bookmark", trigger="deadline", subject_key="t1", now=_now()
    )
    assert retry.mode == "auto" and retry.receipt is not None
    assert len(recovered.calls) == 1


# ===========================================================================
# 7. 灵魂红线 ③：每次 auto 执行有 receipt/notification
# ===========================================================================


async def test_receipt_completeness_and_notification_payload():
    """receipt 六要素（谁/何时/哪个操作/幂等键/结果/授权版本）+ notification 同形。"""
    sinked: list[AutoExecReceipt] = []
    notified: list[AutoExecReceipt] = []
    gate, spy, grants, _receipts = _make_gate(shadow=False, sinked=sinked, notified=notified)
    await _grant(grants, "notification.mark_read")

    outcome = await gate.handle_operation(
        user_id=_USER, operation="notification.mark_read", trigger="deadline", subject_key="task-9", now=_now()
    )
    assert outcome.mode == "auto"
    receipt = outcome.receipt
    assert receipt is not None
    assert receipt.user_id == _USER  # 谁
    assert receipt.occurred_at == _NOW.isoformat()  # 何时
    assert receipt.operation == "notification.mark_read"  # 哪个操作
    assert receipt.idempotency_key == outcome.decision.idempotency_key  # 幂等键
    assert receipt.result == "executed"  # 结果
    assert receipt.grant_version == outcome.decision.grant_version  # 授权版本
    assert receipt.executor_result == {"ok": True, "op": "notification.mark_read", "subject": "task-9"}
    assert sinked == [receipt] and notified == [receipt]

    payload = build_autoexec_receipt_notification(receipt)
    assert payload["update_type"] == "autoexec_notification.mark_read"
    assert payload["category"] == "aurora"
    assert payload["metadata"]["idempotency_key"] == receipt.idempotency_key
    assert payload["metadata"]["grant_version"] == receipt.grant_version
    assert payload["metadata"]["result"] == "executed"


async def test_replayed_execution_emits_no_duplicate_sink_notification():
    """重放（dedup hit）不重复发 sink/notification（恰一次语义覆盖通知面）。"""
    sinked: list[AutoExecReceipt] = []
    notified: list[AutoExecReceipt] = []
    gate, spy, grants, _receipts = _make_gate(shadow=False, sinked=sinked, notified=notified)
    await _grant(grants, "reminder.snooze")

    kw = {"user_id": _USER, "operation": "reminder.snooze", "trigger": "overdue", "subject_key": "s1"}
    await gate.handle_operation(now=_now(), **kw)
    await gate.handle_operation(now=_now(), **kw)

    assert len(sinked) == 1 and len(notified) == 1, "重复 trigger 不得重复发 receipt notification"


# ===========================================================================
# 8. 零 LLM（本卡红线）+ 确定性
# ===========================================================================


def test_autoexec_source_has_no_llm_references():
    """静态扫描：autoexec 模块源码不出现任何 LLM 客户端引用（P-01 同款）。"""
    import pathlib

    path = pathlib.Path(__file__).resolve().parents[2] / "app" / "aurora" / "proactive" / "autoexec.py"
    text = path.read_text(encoding="utf-8")
    banned = ("llm_service", "llm_router", "llm_client", "LLMClient", "openai", "anthropic", "chat_complet")
    for token in banned:
        assert token not in text, f"autoexec.py 含 LLM 引用 {token!r}"


def test_decision_is_deterministic():
    """同输入同输出（决策/幂等键/版本全部确定性）。"""
    doc = {"grants": {"subject.bookmark": "t0"}, "policy_version": "autox_x"}
    results = {
        (
            d.allowed,
            d.mode,
            d.reason,
            d.idempotency_key,
            d.grant_version,
        )
        for d in (
            decide_auto_execution(
                user_id=_USER,
                operation="subject.bookmark",
                trigger="deadline",
                subject_key="t1",
                grant_doc=doc,
                now=_now(),
            )
            for _ in range(20)
        )
    }
    assert len(results) == 1


def test_receipt_ttl_covers_novelty_redelivery_window():
    """receipt TTL 必须 ≥ novelty 窗（48h）：管线可能重投递的窗口内恒去重。"""
    from app.aurora.proactive.autoexec import AUTOEXEC_RECEIPT_TTL_SECONDS
    from app.aurora.proactive.suppression import NOVELTY_TTL

    assert int(NOVELTY_TTL.total_seconds()) <= AUTOEXEC_RECEIPT_TTL_SECONDS


# ===========================================================================
# 9. FIX-47 加固（P-04 R2 §8 登记项收口；全部确定性、零 LLM）
# ===========================================================================


class _RevokeAfterDecisionReadStore(AutoExecGrantStore):
    """①竞态注入：armed 状态下，读返回「已授权」快照后立即落一个并发
    revoke——精确复现 R2 探针 2 的「决策读之后、执行之前」TOCTOU 窗口。"""

    def __init__(self, redis: Any, op_to_revoke: str) -> None:
        super().__init__(redis)
        self.op_to_revoke = op_to_revoke
        self.armed = False
        self.injected = False

    async def read(self, user_id: str) -> dict[str, Any]:
        doc = await super().read(user_id)
        if self.armed:
            self.armed = False
            self.injected = True
            await super().revoke(user_id, self.op_to_revoke)
        return doc


class _FailOnSecondReadStore(AutoExecGrantStore):
    """①故障注入：第 2 次读（执行前 recheck）读失败 → 必须 fail-closed。"""

    def __init__(self, redis: Any) -> None:
        super().__init__(redis)
        self.reads = 0

    async def read(self, user_id: str) -> dict[str, Any]:
        self.reads += 1
        if self.reads == 2:
            raise AutoExecStateUnavailable("recheck read down")
        return await super().read(user_id)


async def test_toctou_midflight_revoke_converts_to_proposal():
    """①核心竞态（R2 §8-1）：决策读后、执行前发生 revoke → 执行前二次版本
    校验转 proposal，执行器零调用。变异守卫：去掉 recheck 本测试必红。"""
    redis = FakeRedis()
    seed = AutoExecGrantStore(redis)
    await seed.grant(_USER, "notification.mark_read", now=_now())

    racing = _RevokeAfterDecisionReadStore(redis, "notification.mark_read")
    racing.armed = True
    gate, spy, _grants, _receipts = _make_gate(redis, shadow=False)
    gate.grants = racing

    outcome = await gate.handle_operation(
        user_id=_USER, operation="notification.mark_read", trigger="deadline", subject_key="t1", now=_now()
    )

    assert racing.injected is True, "竞态注入必须发生在决策读与执行之间"
    assert outcome.mode == "proposal", "窗口内 revoke 必须把本次执行拦成 proposal"
    assert outcome.reason == AutoExecDecisionReason.PROPOSAL_GRANT_ABSENT.value
    assert outcome.details.get("grant_version_changed") is True
    assert outcome.details.get("decision_grant_version") != outcome.details.get("fresh_grant_version")
    assert outcome.receipt is None
    assert spy.calls == [], "TOCTOU 拦截后执行器必须零调用"


async def test_toctou_recheck_read_failure_fails_closed():
    """①二次读故障 → fail-closed 转 state_unavailable，执行器零调用、零落账
    （与决策读同款纪律：读不到授权状态就没有资格执行）。"""
    redis = FakeRedis()
    seed = AutoExecGrantStore(redis)
    await seed.grant(_USER, "notification.mark_read", now=_now())

    flaky = _FailOnSecondReadStore(redis)
    gate, spy, _grants, _receipts = _make_gate(redis, shadow=False)
    gate.grants = flaky

    outcome = await gate.handle_operation(
        user_id=_USER, operation="notification.mark_read", trigger="deadline", subject_key="t1", now=_now()
    )

    assert flaky.reads == 2, "授权文档必须被读两次（决策 + 执行前校验）"
    assert outcome.mode == "proposal"
    assert outcome.reason == AutoExecDecisionReason.PROPOSAL_STATE_UNAVAILABLE.value
    assert outcome.details.get("phase") == "pre_execute_recheck"
    assert outcome.receipt is None
    assert spy.calls == []


async def test_toctou_unrelated_grant_change_converts_conservatively():
    """①保守语义钉桩：窗口内变化的是**另一个**操作的授权（本操作 grant 仍在）
    → 全文档版本比对同样转 proposal。方向性选择：授权状态在窗口内发生过
    变化即不放行，宁可多一张确认卡（fail-closed 家族语义）。"""
    redis = FakeRedis()
    seed = AutoExecGrantStore(redis)
    await seed.grant(_USER, "notification.mark_read", now=_now())
    await seed.grant(_USER, "subject.bookmark", now=_now())

    racing = _RevokeAfterDecisionReadStore(redis, "subject.bookmark")  # 撤销的是无关操作
    racing.armed = True
    gate, spy, _grants, _receipts = _make_gate(redis, shadow=False)
    gate.grants = racing

    outcome = await gate.handle_operation(
        user_id=_USER, operation="notification.mark_read", trigger="deadline", subject_key="t1", now=_now()
    )

    assert racing.injected is True
    assert outcome.mode == "proposal"
    assert outcome.details.get("grant_version_changed") is True
    assert spy.calls == []


def test_import_time_self_check_guard_raises_on_tampered_source_copy(tmp_path):
    """②自检守护（R2 变异 V3 盲区收口）：篡改注册表的模块源码副本重导入时
    必须在 import 期 raise（违宪条目使模块不可用）。副本继承**真实源码**的
    守卫逻辑——若守卫被短路（如 ``if False and _IMPORT_ISSUES``），本测试红。"""
    import importlib.util
    import pathlib

    src = pathlib.Path(__file__).resolve().parents[2] / "app" / "aurora" / "proactive" / "autoexec.py"
    text = src.read_text(encoding="utf-8")
    tampered = text.replace('risk="low",', 'risk="high",', 1)  # 首个表内条目违宪
    assert tampered != text, "自检守护测试的源码锚点失效（注册表字面量被重构，需更新锚点）"

    target = tmp_path / "autoexec_tampered_probe.py"
    target.write_text(tampered, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("_autoexec_tampered_probe", target)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module  # dataclass 注解解析需要可查 module（标准 spec 加载模式）
    try:
        with pytest.raises(ValueError, match="soul invariants"):
            spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)  # 探针模块自清（导入必败，不留进程污染）


def test_import_time_self_check_source_pattern_pinned():
    """②源码钉：自检守卫必须是「计算即校验 + 非空即 raise」形态，
    防 R2 变异 V3 的 ``if False and`` 短路旁路（守卫分支内紧跟 raise）。"""
    import pathlib

    text = (pathlib.Path(__file__).resolve().parents[2] / "app" / "aurora" / "proactive" / "autoexec.py").read_text(
        encoding="utf-8"
    )
    assert "_IMPORT_ISSUES = validate_autoexec_allowlist()" in text
    assert "if _IMPORT_ISSUES:" in text
    assert "if False and _IMPORT_ISSUES" not in text
    guard_tail = text[text.index("if _IMPORT_ISSUES:") :]
    assert "raise ValueError" in guard_tail[:300], "自检守卫分支内必须紧跟 raise"


async def test_inflight_concurrent_second_call_is_not_a_real_proposal():
    """⑤in-flight UI 语义钉桩（R2 §8-5）：并发同键第二调用者 → proposal +
    ``details.inflight=True``（操作进行中信号，非真 proposal，UI 不得渲染成
    确认卡）；首个完成后同键重投递 → replay/auto。全程执行器恰一次。"""

    entered = asyncio.Event()
    release = asyncio.Event()

    class BlockingExecutor:
        def __init__(self) -> None:
            self.calls: list[AutoExecRequest] = []

        async def __call__(self, request: AutoExecRequest) -> dict[str, Any]:
            self.calls.append(request)
            entered.set()
            await release.wait()
            return {"ok": True}

    redis = FakeRedis()
    blocker = BlockingExecutor()
    gate, _spy, grants, _receipts = _make_gate(redis, shadow=False, executor=blocker)
    await _grant(grants, "notification.mark_read")

    kw = {"user_id": _USER, "operation": "notification.mark_read", "trigger": "deadline", "subject_key": "t1"}
    first_task = asyncio.create_task(gate.handle_operation(now=_now(), **kw))
    await asyncio.wait_for(entered.wait(), timeout=5)  # 首个已过幂等门、正在执行

    second = await gate.handle_operation(now=_now(), **kw)
    assert second.mode == "proposal"
    assert second.reason == AutoExecDecisionReason.DEDUP_REPLAY.value
    assert second.details.get("inflight") is True, "in-flight 第二调用者必须带 inflight 标记"
    assert second.receipt is None

    release.set()
    first = await first_task
    assert first.mode == "auto" and first.receipt is not None

    third = await gate.handle_operation(now=_now(), **kw)
    assert third.mode == "auto", "首个完成后同键重投递是 replay，不是确认卡"
    assert third.reason == AutoExecDecisionReason.DEDUP_REPLAY.value
    assert third.details.get("replayed") is True
    assert len(blocker.calls) == 1, "并发窗口 + 重投递合计执行器恰一次"


async def test_executor_failure_leaves_no_receipt_retry_path_stays_clean():
    """⑥原子性契约钉桩（R2 §8-6）：receipt 只在执行器成功返回后落账
    （receipt 后行）——失败执行零落账，receipt 索引无残留 → 同键重试干净
    可行。执行器必须原子或自身幂等：部分 side effect 后抛错 = 接线卡契约
    违例，本门不补偿（模块文档「执行器原子性契约」）。"""
    redis = FakeRedis()
    failing = ExecutorSpy(fail=True)
    gate, _spy, grants, receipts = _make_gate(redis, shadow=False, executor=failing)
    await _grant(grants, "subject.bookmark")

    kw = {"user_id": _USER, "operation": "subject.bookmark", "trigger": "deadline", "subject_key": "t1"}
    failed = await gate.handle_operation(now=_now(), **kw)
    assert failed.mode == "proposal"
    assert failed.reason == AutoExecDecisionReason.AUTO_EXECUTOR_FAILED.value

    key = derive_autoexec_idempotency_key(
        user_id=_USER, operation="subject.bookmark", trigger="deadline", subject_key="t1"
    )
    assert await receipts.find(_USER, key) is None, "失败执行不得在 receipt 索引留下残留"

    recovered = ExecutorSpy()
    gate2, _spy2, _grants2, _receipts2 = _make_gate(redis, shadow=False, executor=recovered)
    gate2.grants = grants
    retry = await gate2.handle_operation(now=_now(), **kw)
    assert retry.mode == "auto" and retry.receipt is not None
    assert len(recovered.calls) == 1, "重试路径不被失败残留污染（恰一次语义保持）"
