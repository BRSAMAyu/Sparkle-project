"""
Aurora proactive pipeline — low-risk auto-execution authorization gate (P-04).

P-01 管线（event → deterministic filter → Aurora 出口）解决「该不该打扰」；
本模块解决紧随其后的「能不能替用户直接做」：

    P-01 notify 决策 ──附带操作──▶ allowlist 门 → 授权门（grant/revoke）
      → 幂等门（重复 trigger 恰一次 side effect）→ 执行 + receipt/notification

组合位置（卡面约束）：本层在 P-01 投递决策**之后**、真实 side effect **之前**
——不 import、不修改管线既有模块的抑制链语义；管线照旧只投通知（零 side
effect），凡是「替用户做操作」都经本门。

════════════════════════════════════════════════════════════════════════
灵魂红线（本卡灵魂，一票否决）
════════════════════════════════════════════════════════════════════════
1. **未授权 = 0 次自动执行**：授权判定读取失败（redis 故障/文档损坏）→
   fail-closed 转 proposal（``proposal_state_unavailable``），绝不以「空授权
   = 全授权」放行（P-01 state_unavailable 同款语义）。
2. **高风险/不可逆操作在 allowlist 里出现即违宪**：allowlist 是封闭词表，
   每个操作携带 (effect/risk/reversible) 元数据，
   :func:`validate_autoexec_allowlist` 在 import 期 + 契约测试双钉——
   risk != low 或 reversible=False 的条目使校验失败；决策函数在执行前
   **复核**元数据（纵深防御：即使有人绕过校验塞进高危条目，决策层仍然
   转 proposal，永不自动执行）。
3. **revoke 即时生效**：授权文档带内容寻址 ``policy_version``
   （A-05 ``compute_policy_patch_version`` 同款），每次 grant/revoke 重算；
   决策路径**每次 trigger 现读**授权文档（无陈旧缓存），revoke 后下一条
   trigger 即读不到授权 → 转 proposal。需要缓存的消费方用
   :func:`grant_cache_key` 把版本并入键（C-07 缓存失效联动：版本 bump →
   键变 → 缓存不命中）。
4. **重复 trigger 不产生重复 side effect**：幂等键由
   (user, operation, trigger, subject_key) 确定性派生（X-05/X-03 幂等键
   先例）；执行门前查 receipt 索引——同键重放返回既有 receipt，执行器
   恰一次调用。

════════════════════════════════════════════════════════════════════════
设计约定（与 P-01 同族）
════════════════════════════════════════════════════════════════════════
- **零 LLM**：全模块确定性（allowlist 判定、授权判定、幂等判定、receipt
  落账没有任何模型调用；不 import 任何 LLM 客户端，测试静态扫描钉死）。
- **JSON 文档模式**：授权与 receipt 均为每用户一个 Redis JSON 文档键
  （``ProactiveSuppressionStore`` 同款约定；P-01「不建新表、不动迁移」
  先例），读解析、写整体覆盖、TTL 由写路径维护；redis 客户端 duck-typing
  注入（只要求 async ``get``/``set``），测试用内存 Fake。
- **shadow 默认**：门默认 ``shadow=True``——全链路照跑（判定 + would-auto
  记录 + receipt 面），但执行器**零调用**（P-01 shadow 同款纪律）。
- **receipt/notification 双写**：每次 auto 执行产出
  :class:`AutoExecReceipt`（谁/何时/哪个操作/幂等键/结果/授权版本）落
  receipt 存储 + 可注入 sink（审计/DB 持久化扩展点）+ 系统更新形状的
  notification 载荷（:func:`build_autoexec_receipt_notification`，与
  ``SystemUpdateService`` 载荷同形）。
- **proposal 兜底**：一切不满足 auto 条件的路径（不在白名单 / 风险非 low /
  不可逆 / 未授权 / 已 revoke / 总闸 / shadow / 状态不可用 / 执行器失败）
  都返回 proposal 模式结果——转 X-03 action proposal 确认卡路径，绝不静默。

变更流程：本模块词表/语义改动需 bump ``AUTOEXEC_SCHEMA_VERSION`` 并过两位
reviewer（A-05/X-06 冻结声明同款纪律）。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Awaitable, Callable, Mapping

from loguru import logger

__all__ = [
    "AUTOEXEC_SCHEMA_VERSION",
    "AutoExecOperation",
    "AutoExecOpMetadata",
    "AUTOEXEC_OPERATION_REGISTRY",
    "AUTOEXEC_OPERATION_VOCABULARY",
    "validate_autoexec_allowlist",
    "AutoExecDecisionReason",
    "AutoExecDecision",
    "AutoExecGrantStore",
    "AutoExecStateUnavailable",
    "compute_grant_policy_version",
    "AUTOEXEC_EMPTY_VERSION",
    "grant_cache_key",
    "derive_autoexec_idempotency_key",
    "decide_auto_execution",
    "AutoExecRequest",
    "AutoExecReceipt",
    "AutoExecReceiptStore",
    "AutoExecOutcome",
    "ProactiveAutoExecGate",
    "build_autoexec_receipt_notification",
    "AUTOEXEC_RECEIPT_TTL_SECONDS",
]

AUTOEXEC_SCHEMA_VERSION = "aurora_autoexec.v1"

# ---------------------------------------------------------------------------
# 低风险操作 allowlist（封闭词表；本卡灵魂）
# ---------------------------------------------------------------------------


class AutoExecOperation(StrEnum):
    """允许被预授权自动执行的低风险操作（封闭词表，冻结）。

    准入标准（全部满足才可入表）：只读用户可见的内部状态 / **可逆** /
    无外部 side effect（不外发消息、不外部调用、不花钱、不可逆删除）。
    「标记已读 / 收藏 / 推迟提醒」族——用户明确不喜欢时一键可撤销。
    高风险与不可逆操作**没有合法的表内名字**（结构性排除，非运行时拦截）。
    """

    MARK_UPDATE_READ = "notification.mark_read"  # 标记一条主动提醒已读
    BOOKMARK_SUBJECT = "subject.bookmark"  # 收藏提醒主题（书签可移除）
    SNOOZE_TRIGGER = "reminder.snooze"  # 推迟同题提醒（novelty 去重的显式化）


@dataclass(frozen=True)
class AutoExecOpMetadata:
    """allowlist 条目的能力元数据（X-06 ``ToolMetadata`` 同构的确定性投影）。

    - ``effect``：``"write"``（改变内部持久状态）——凡 write 必带幂等键；
    - ``risk``：**必须**为 ``"low"``（validate_autoexec_allowlist 强制）；
    - ``reversible``：**必须**为 ``True``（同上）。
    """

    operation: str
    effect: str
    risk: str
    reversible: bool
    description: str


#: allowlist 注册表（操作 → 元数据；冻结映射，契约测试 sha 双钉）。
AUTOEXEC_OPERATION_REGISTRY: Mapping[str, AutoExecOpMetadata] = {
    AutoExecOperation.MARK_UPDATE_READ.value: AutoExecOpMetadata(
        operation=AutoExecOperation.MARK_UPDATE_READ.value,
        effect="write",
        risk="low",
        reversible=True,
        description="把一条 Aurora 主动提醒标记为已读（读态可切回）",
    ),
    AutoExecOperation.BOOKMARK_SUBJECT.value: AutoExecOpMetadata(
        operation=AutoExecOperation.BOOKMARK_SUBJECT.value,
        effect="write",
        risk="low",
        reversible=True,
        description="收藏提醒主题到用户书签（可随时移除）",
    ),
    AutoExecOperation.SNOOZE_TRIGGER.value: AutoExecOpMetadata(
        operation=AutoExecOperation.SNOOZE_TRIGGER.value,
        effect="write",
        risk="low",
        reversible=True,
        description="推迟同题提醒的新颖性窗口（可提前恢复）",
    ),
}

#: allowlist 词表（封闭集合的平铺视图；扩词表 = 契约变更，两位 reviewer）。
AUTOEXEC_OPERATION_VOCABULARY: frozenset[str] = frozenset(AUTOEXEC_OPERATION_REGISTRY)


def validate_autoexec_allowlist(registry: Mapping[str, AutoExecOpMetadata] | None = None) -> tuple[str, ...]:
    """allowlist 结构校验（import 期 + 契约测试双钉；返回 issues，空 = 通过）。

    灵魂红线的机制化：任何条目 risk != low、reversible=False、effect 越词表、
    operation 名与键不一致 → issue。**高风险/不可逆操作在表内出现即违宪**
    ——本函数是违宪检测器，决策层复核是第二道闸。
    """
    issues: list[str] = []
    reg = AUTOEXEC_OPERATION_REGISTRY if registry is None else registry
    for key, meta in reg.items():
        name = str(getattr(meta, "operation", "") or "")
        if name != str(key):
            issues.append(f"{key}: operation name mismatch ({name!r} != key {key!r})")
        if getattr(meta, "risk", None) != "low":
            issues.append(
                f"{key}: risk must be 'low', got {getattr(meta, 'risk', None)!r} (high-risk ops are forbidden in the allowlist)"
            )
        if getattr(meta, "reversible", None) is not True:
            issues.append(f"{key}: reversible must be True (irreversible ops are forbidden in the allowlist)")
        if getattr(meta, "effect", None) not in {"read", "write"}:
            issues.append(f"{key}: effect must be 'read' or 'write', got {getattr(meta, 'effect', None)!r}")
    return tuple(issues)


#: import 期自检（违宪条目使模块不可用——fail-fast，不留给运行时）。
_IMPORT_ISSUES = validate_autoexec_allowlist()
if _IMPORT_ISSUES:  # pragma: no cover — 仅在人为篡改注册表时触发
    raise ValueError("autoexec allowlist violates soul invariants: " + "; ".join(_IMPORT_ISSUES))


# ---------------------------------------------------------------------------
# 决策 reason codes（封闭词表）
# ---------------------------------------------------------------------------


class AutoExecDecisionReason(StrEnum):
    """auto/proposal 判定的封闭归因（确定性规则输出，非 LLM）。"""

    AUTO_GRANTED = "auto_granted"  # 白名单内 + 元数据复核通过 + 已授权
    PROPOSAL_NOT_ALLOWLISTED = "proposal_not_allowlisted"  # 操作不在 allowlist（含一切未登记名）
    PROPOSAL_RISK_NOT_LOW = "proposal_risk_not_low"  # 元数据复核：风险非 low（纵深防御闸）
    PROPOSAL_IRREVERSIBLE = "proposal_irreversible"  # 元数据复核：不可逆
    PROPOSAL_GRANT_ABSENT = "proposal_grant_absent"  # 未授权 / 已 revoke
    PROPOSAL_MASTER_DISABLED = "proposal_master_disabled"  # 用户级 auto-exec 总闸
    PROPOSAL_SHADOW = "proposal_shadow"  # shadow 模式：would-auto 只记录不执行
    PROPOSAL_STATE_UNAVAILABLE = "proposal_state_unavailable"  # 授权状态读取失败（fail-closed）
    AUTO_EXECUTOR_FAILED = "auto_executor_failed"  # 执行器异常（无 side effect，转 proposal 兜底）
    DEDUP_REPLAY = "dedup_replay"  # 同幂等键重放：返回既有 receipt，不重复执行


# ---------------------------------------------------------------------------
# 授权存储（grant/revoke；版本化 → revoke 即时生效）
# ---------------------------------------------------------------------------

_AUTOEXEC_EMPTY_VERSION = "autox_none"

_GRANT_KEY_TEMPLATE = "aurora:autoexec_grants:{user_id}"
_GRANT_TTL_SECONDS = 180 * 24 * 60 * 60  # 授权文档整体 TTL（180d），写路径续期。

_RECEIPT_KEY_TEMPLATE = "aurora:autoexec_receipts:{user_id}"
_RECEIPT_TTL_SECONDS = 7 * 24 * 60 * 60  # receipt TTL（7d > 48h novelty 窗，覆盖重投递面）
_MAX_RECEIPTS_PER_USER = 200  # 有界（防无界增长；审计聚合归 sink/metrics）


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AutoExecStateUnavailable(RuntimeError):
    """授权状态不可用（redis 故障 / 未配置 / 文档损坏）——fail-closed 信号。"""


def compute_grant_policy_version(granted_operations: Mapping[str, Any] | None) -> str:
    """授权集内容寻址版本（``autox_<sha256[:16]>``；空集 = 常量）。

    A-05 ``compute_policy_patch_version`` 同款纪律：授权集任一变化（授予/
    撤销/总闸翻转）→ 版本必然变化——revoke 即时生效的实现基础（决策路径
    现读文档 + 消费方缓存键并入版本 → bump 即失效）。
    """
    entries = sorted(f"{op}={ts}" for op, ts in (granted_operations or {}).items())
    if not entries:
        return _AUTOEXEC_EMPTY_VERSION
    digest = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()[:16]
    return f"autox_{digest}"


#: 空（或全 revoke 后）授权集的稳定版本常量。
AUTOEXEC_EMPTY_VERSION = _AUTOEXEC_EMPTY_VERSION


def grant_cache_key(base_key: str, version: str) -> str:
    """消费方缓存键并入授权版本（版本 bump → 键变 → 缓存不命中）。

    A-05 ``patch_cache_key`` 同款；C-07 缓存失效联动点。
    """
    return f"{base_key}|autoexec={version}"


def derive_autoexec_idempotency_key(
    *,
    user_id: str,
    operation: str,
    trigger: str,
    subject_key: str,
) -> str:
    """确定性幂等键（``autoxid_<sha256[:32]>``；同 (user, op, trigger, subject)
    重复 trigger 恒同键——重复投递恰一次 side effect 的唯一依据）。"""
    canonical = json.dumps(
        {
            "v": AUTOEXEC_SCHEMA_VERSION,
            "user_id": str(user_id),
            "operation": str(operation),
            "trigger": str(trigger),
            "subject_key": str(subject_key),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "autoxid_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


class AutoExecGrantStore:
    """低风险 auto-exec 授权读写（Redis JSON 文档；抑制状态存取同族约定）。

    文档形状（每用户一键，写整体覆盖）::

        {
            "grants": {"notification.mark_read": "<iso 授予时刻>", ...},
            "master_disabled": false,          # 用户级总闸（一键暂停全部自动执行）
            "policy_version": "autox_<16hex>",  # 内容寻址；每次写重算
            "updated_at": "<iso>",
        }

    - **fail-closed 读**：redis 未配置 / 读失败 / 文档损坏 →
      :class:`AutoExecStateUnavailable`（调用方必须翻译成 proposal，绝不以
      「读不到 = 未授权也放行」的 fail-open 语义处理；「键不存在」= 新用户
      零授权，是合法空态，返回空文档）。
    - **grant/revoke 前置校验**：只有 allowlist 词表内的操作可被授予/撤销
      （越界 ValueError——授权面不可能铸出 allowlist 外的能力，X-06
      PERMISSION_CEILING 同律）。
    - 写路径每次重算 ``policy_version``（**revoke 即时生效的实现点**）。
    """

    def __init__(self, redis: Any = None):
        self.redis = redis

    # -- key ---------------------------------------------------------------

    @staticmethod
    def grant_key(user_id: str) -> str:
        return _GRANT_KEY_TEMPLATE.format(user_id=str(user_id))

    @staticmethod
    def receipt_key(user_id: str) -> str:
        return _RECEIPT_KEY_TEMPLATE.format(user_id=str(user_id))

    # -- read ---------------------------------------------------------------

    async def read(self, user_id: str) -> dict[str, Any]:
        """读授权文档；键不存在返回空 dict（零授权合法态）。

        Raises:
            AutoExecStateUnavailable: redis 未配置 / 读失败 / 文档损坏。
        """
        if self.redis is None:
            raise AutoExecStateUnavailable("autoexec grant redis not configured")
        try:
            raw = await self.redis.get(self.grant_key(user_id))
        except Exception as exc:
            logger.warning("autoexec grant load failed user={}: {!r}", user_id, exc)
            raise AutoExecStateUnavailable(f"autoexec grant read failed: {exc!r}") from exc
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("autoexec grant doc corrupt user={}: {!r}", user_id, exc)
            raise AutoExecStateUnavailable(f"autoexec grant doc corrupt: {exc!r}") from exc
        if not isinstance(parsed, dict):
            raise AutoExecStateUnavailable("autoexec grant doc is not a mapping")
        return parsed

    # -- write ---------------------------------------------------------------

    async def grant(self, user_id: str, operation: str, *, now: datetime | None = None) -> dict[str, Any]:
        """授予一个 allowlist 内操作；返回写后文档（版本已重算）。

        Raises:
            ValueError: 操作不在 allowlist（授权面结构性封闭）。
        """
        op = str(operation)
        if op not in AUTOEXEC_OPERATION_VOCABULARY:
            raise ValueError(
                f"V1.operation_not_allowlisted: {op!r} not in allowlist {sorted(AUTOEXEC_OPERATION_VOCABULARY)}"
            )
        now = now or _utcnow()
        doc = await self._load_or_empty(user_id)
        grants = dict(doc.get("grants") or {})
        grants[op] = now.isoformat()
        doc["grants"] = grants
        return await self._save(user_id, doc, now=now)

    async def revoke(self, user_id: str, operation: str, *, now: datetime | None = None) -> dict[str, Any]:
        """撤销一个操作授权（即时生效：版本重算 + 决策路径现读）。

        撤销不存在的授权是 no-op（仍重算版本/写回——幂等，重复 revoke 安全）。
        """
        now = now or _utcnow()
        doc = await self._load_or_empty(user_id)
        grants = dict(doc.get("grants") or {})
        grants.pop(str(operation), None)
        doc["grants"] = grants
        return await self._save(user_id, doc, now=now)

    async def set_master_switch(self, user_id: str, *, disabled: bool, now: datetime | None = None) -> dict[str, Any]:
        """用户级 auto-exec 总闸（一键暂停/恢复全部自动执行；版本随之 bump）。"""
        now = now or _utcnow()
        doc = await self._load_or_empty(user_id)
        doc["master_disabled"] = bool(disabled)
        return await self._save(user_id, doc, now=now)

    # -- internals -----------------------------------------------------------

    async def _load_or_empty(self, user_id: str) -> dict[str, Any]:
        try:
            return await self.read(user_id)
        except AutoExecStateUnavailable:
            if self.redis is None:
                raise
            # 读故障时拒绝写（fail-closed：不能在损坏文档上盲写覆盖授权）。
            logger.warning("autoexec grant write refused (read path unavailable) user={}", user_id)
            raise

    async def _save(self, user_id: str, doc: dict[str, Any], *, now: datetime) -> dict[str, Any]:
        doc["policy_version"] = compute_grant_policy_version(doc.get("grants") or {})
        doc["updated_at"] = now.isoformat()
        if self.redis is not None:
            try:
                await self.redis.set(
                    self.grant_key(user_id),
                    json.dumps(doc, ensure_ascii=False, default=str),
                    ex=_GRANT_TTL_SECONDS,
                )
            except Exception as exc:
                logger.warning("autoexec grant save failed user={}: {!r}", user_id, exc)
                raise AutoExecStateUnavailable(f"autoexec grant write failed: {exc!r}") from exc
        return doc


# ---------------------------------------------------------------------------
# 决策纯函数（allowlist 门 → 元数据复核门 → 授权门）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AutoExecDecision:
    """一次 auto/proposal 判定的完整记录（可审计；receipt 归因依据）。"""

    #: True = （live 模式下）允许 auto 执行；False = 一律转 proposal。
    allowed: bool
    mode: str  # "auto" | "proposal"
    reason: str  # AutoExecDecisionReason 值
    operation: str
    user_id: str
    idempotency_key: str
    grant_version: str | None = None  # 判定所依据的授权版本（receipt 归因）
    reason_codes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "mode": self.mode,
            "reason": self.reason,
            "operation": self.operation,
            "user_id": self.user_id,
            "idempotency_key": self.idempotency_key,
            "grant_version": self.grant_version,
            "reason_codes": list(self.reason_codes),
            "metadata": dict(self.metadata),
        }


def decide_auto_execution(
    *,
    user_id: str,
    operation: str,
    trigger: str = "",
    subject_key: str = "",
    grant_doc: Mapping[str, Any] | None,
    now: datetime | None = None,
) -> AutoExecDecision:
    """auto/proposal 判定（纯函数；确定性，零 I/O 零 LLM）。

    规则顺序（全部 fail-closed，任一不满足即 proposal）：

    1. 用户级总闸开 → ``proposal_master_disabled``；
    2. 操作不在 allowlist → ``proposal_not_allowlisted``（一切未登记名、
       包括任何高风险操作名，结构性无表内条目）；
    3. 元数据复核：注册表缺条目 → not_allowlisted；risk != low →
       ``proposal_risk_not_low``；reversible=False → ``proposal_irreversible``
       （纵深防御：allowlist 校验器的第二道闸，绕过校验塞入的高危条目
       在此仍被拒绝）；
    4. 授权门：操作不在用户 grants → ``proposal_grant_absent``（未授权/
       已 revoke 同码——revoke 即时生效就是「下一条 trigger 在此门被拦」）。

    幂等键与操作是否被授权无关——确定性派生，供执行门与 receipt 使用。
    """
    user = str(user_id)
    op = str(operation)
    idem = derive_autoexec_idempotency_key(
        user_id=user, operation=op, trigger=str(trigger), subject_key=str(subject_key)
    )
    doc = grant_doc or {}

    if bool(doc.get("master_disabled")):
        return AutoExecDecision(
            allowed=False,
            mode="proposal",
            reason=AutoExecDecisionReason.PROPOSAL_MASTER_DISABLED.value,
            operation=op,
            user_id=user,
            idempotency_key=idem,
            grant_version=str(doc.get("policy_version") or AUTOEXEC_EMPTY_VERSION),
            reason_codes=(AutoExecDecisionReason.PROPOSAL_MASTER_DISABLED.value,),
        )

    # -- allowlist 门（封闭词表；未登记名一律 proposal） -----------------------
    meta = AUTOEXEC_OPERATION_REGISTRY.get(op)
    if meta is None:
        return AutoExecDecision(
            allowed=False,
            mode="proposal",
            reason=AutoExecDecisionReason.PROPOSAL_NOT_ALLOWLISTED.value,
            operation=op,
            user_id=user,
            idempotency_key=idem,
            grant_version=str(doc.get("policy_version") or AUTOEXEC_EMPTY_VERSION),
            reason_codes=(AutoExecDecisionReason.PROPOSAL_NOT_ALLOWLISTED.value,),
        )

    # -- 元数据复核门（纵深防御；违宪条目在此被第二道闸拦下） -------------------
    if meta.risk != "low":
        return AutoExecDecision(
            allowed=False,
            mode="proposal",
            reason=AutoExecDecisionReason.PROPOSAL_RISK_NOT_LOW.value,
            operation=op,
            user_id=user,
            idempotency_key=idem,
            grant_version=str(doc.get("policy_version") or AUTOEXEC_EMPTY_VERSION),
            reason_codes=(AutoExecDecisionReason.PROPOSAL_RISK_NOT_LOW.value,),
            metadata={"risk": meta.risk},
        )
    if meta.reversible is not True:
        return AutoExecDecision(
            allowed=False,
            mode="proposal",
            reason=AutoExecDecisionReason.PROPOSAL_IRREVERSIBLE.value,
            operation=op,
            user_id=user,
            idempotency_key=idem,
            grant_version=str(doc.get("policy_version") or AUTOEXEC_EMPTY_VERSION),
            reason_codes=(AutoExecDecisionReason.PROPOSAL_IRREVERSIBLE.value,),
            metadata={"reversible": meta.reversible},
        )

    # -- 授权门（未授权 / 已 revoke 同码；决策路径现读文档保证即时性） -----------
    grants = doc.get("grants") or {}
    version = str(doc.get("policy_version") or compute_grant_policy_version(grants))
    if op not in grants:
        return AutoExecDecision(
            allowed=False,
            mode="proposal",
            reason=AutoExecDecisionReason.PROPOSAL_GRANT_ABSENT.value,
            operation=op,
            user_id=user,
            idempotency_key=idem,
            grant_version=version,
            reason_codes=(AutoExecDecisionReason.PROPOSAL_GRANT_ABSENT.value,),
        )

    return AutoExecDecision(
        allowed=True,
        mode="auto",
        reason=AutoExecDecisionReason.AUTO_GRANTED.value,
        operation=op,
        user_id=user,
        idempotency_key=idem,
        grant_version=version,
        reason_codes=(AutoExecDecisionReason.AUTO_GRANTED.value,),
        metadata={"effect": meta.effect, "risk": meta.risk, "reversible": meta.reversible},
    )


# ---------------------------------------------------------------------------
# 执行门（幂等 → 执行 → receipt/notification）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AutoExecRequest:
    """执行器入参（结构化、可序列化；执行器只吃这个，不吃对话文本）。"""

    user_id: str
    operation: str
    trigger: str
    subject_key: str
    idempotency_key: str
    grant_version: str
    payload: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AutoExecReceipt:
    """一次 auto 执行的权威回执（谁/何时/哪个操作/幂等键/结果/授权版本）。"""

    user_id: str
    operation: str
    trigger: str
    subject_key: str
    idempotency_key: str
    grant_version: str
    #: "executed"（本次真执行）| "replayed"（同键重放奉还既有回执）
    result: str
    occurred_at: str
    executor_result: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "operation": self.operation,
            "trigger": self.trigger,
            "subject_key": self.subject_key,
            "idempotency_key": self.idempotency_key,
            "grant_version": self.grant_version,
            "result": self.result,
            "occurred_at": self.occurred_at,
            "executor_result": dict(self.executor_result),
        }


@dataclass(frozen=True, slots=True)
class AutoExecOutcome:
    """执行门对一次操作的最终处置（调用方据此走 proposal 确认卡或忽略）。"""

    #: "auto"（已执行/重放）| "proposal"（转确认卡路径）
    mode: str
    reason: str
    decision: AutoExecDecision | None
    receipt: AutoExecReceipt | None = None
    #: shadow 命中 would-auto 时为 True（decision.allowed=True 但未执行）。
    would_auto: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)


#: receipt 索引 TTL（>48h novelty 窗：管线可能重投递同 subject 的窗口内恒去重）。
AUTOEXEC_RECEIPT_TTL_SECONDS = _RECEIPT_TTL_SECONDS

ExecutorFn = Callable[[AutoExecRequest], Awaitable[dict[str, Any]]]
ReceiptSink = Callable[[AutoExecReceipt], Awaitable[None]]


class AutoExecReceiptStore:
    """receipt 存储（每用户一个 Redis JSON 索引文档：幂等键 → receipt）。

    有界（每用户 ≤ :data:`MAX_RECEIPTS`，超出淘汰最早写入）；TTL 7d 覆盖
    novelty 重投递窗口。读失败 → fail-closed（视为无既有 receipt 会导致重复
    执行，因此**读失败时执行门拒绝 auto**——由门把
    :class:`AutoExecStateUnavailable` 翻译成 proposal）。
    """

    MAX_RECEIPTS = _MAX_RECEIPTS_PER_USER

    def __init__(self, redis: Any = None):
        self.redis = redis

    async def find(self, user_id: str, idempotency_key: str) -> AutoExecReceipt | None:
        """按幂等键查既有 receipt；无则 None。读故障上抛（fail-closed 信号）。"""
        doc = await self._load(user_id)
        raw = (doc.get("receipts") or {}).get(str(idempotency_key))
        if not isinstance(raw, Mapping):
            return None
        return AutoExecReceipt(
            user_id=str(raw.get("user_id") or user_id),
            operation=str(raw.get("operation") or ""),
            trigger=str(raw.get("trigger") or ""),
            subject_key=str(raw.get("subject_key") or ""),
            idempotency_key=str(raw.get("idempotency_key") or idempotency_key),
            grant_version=str(raw.get("grant_version") or ""),
            result=str(raw.get("result") or ""),
            occurred_at=str(raw.get("occurred_at") or ""),
            executor_result=dict(raw.get("executor_result") or {}),
        )

    async def record(self, receipt: AutoExecReceipt, *, now: datetime | None = None) -> None:
        """落一条 receipt（同键重复落库 = 覆盖同值，幂等）。写失败仅告警：
        决定已执行（side effect 已发生），审计缺失降级为告警而非回滚。"""
        now = now or _utcnow()
        doc = await self._load(receipt.user_id)
        receipts = dict(doc.get("receipts") or {})
        receipts[receipt.idempotency_key] = receipt.to_dict()
        # 有界淘汰：超出上限按 occurred_at 淘汰最早（同刻按键序，确定性）。
        if len(receipts) > self.MAX_RECEIPTS:
            ordered = sorted(
                receipts.items(),
                key=lambda kv: (str(kv[1].get("occurred_at") or ""), kv[0]),
            )
            for key, _ in ordered[: len(receipts) - self.MAX_RECEIPTS]:
                receipts.pop(key, None)
        doc["receipts"] = receipts
        doc["updated_at"] = now.isoformat()
        if self.redis is not None:
            try:
                await self.redis.set(
                    AutoExecGrantStore.receipt_key(receipt.user_id),
                    json.dumps(doc, ensure_ascii=False, default=str),
                    ex=_RECEIPT_TTL_SECONDS,
                )
            except Exception as exc:
                logger.warning(
                    "autoexec receipt save failed user={} key={}: {!r}",
                    receipt.user_id,
                    receipt.idempotency_key,
                    exc,
                )

    async def _load(self, user_id: str) -> dict[str, Any]:
        if self.redis is None:
            raise AutoExecStateUnavailable("autoexec receipt redis not configured")
        try:
            raw = await self.redis.get(AutoExecGrantStore.receipt_key(user_id))
        except Exception as exc:
            raise AutoExecStateUnavailable(f"autoexec receipt read failed: {exc!r}") from exc
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise AutoExecStateUnavailable(f"autoexec receipt doc corrupt: {exc!r}") from exc
        if not isinstance(parsed, dict):
            raise AutoExecStateUnavailable("autoexec receipt doc is not a mapping")
        return parsed


class ProactiveAutoExecGate:
    """低风险 proactive auto-execution 授权门（P-04 执行层主体）。

    用法（组合位置：P-01 notify 决策之后）::

        gate = ProactiveAutoExecGate(
            grants=AutoExecGrantStore(redis),
            receipts=AutoExecReceiptStore(redis),
            execute=my_low_risk_executor,   # (AutoExecRequest) -> dict
            shadow=settings_shadow,
        )
        outcome = await gate.handle_operation(
            user_id=record.user_id, operation="notification.mark_read",
            trigger=record.trigger, subject_key=record.subject_key,
        )
        if outcome.mode == "proposal":
            ...  # 转 X-03 action proposal 确认卡路径

    保证（测试逐条钉死）：
    - 未授权（无 grant / 已 revoke / 总闸 / 白名单外 / 状态不可用）→
      执行器**零调用**，outcome.mode="proposal"；
    - shadow=True（默认）→ 即便全条件满足，执行器零调用，would_auto=True；
    - 同幂等键重复调用 → 执行器恰一次，第二次返回既有 receipt（replayed）；
    - 执行器异常 → 不落成功 receipt（无 side effect），转 proposal 兜底。
    """

    def __init__(
        self,
        *,
        grants: AutoExecGrantStore,
        receipts: AutoExecReceiptStore,
        execute: ExecutorFn,
        sink: ReceiptSink | None = None,
        notify: ReceiptSink | None = None,
        shadow: bool = True,
    ) -> None:
        self.grants = grants
        self.receipts = receipts
        self._execute = execute
        self._sink = sink
        self._notify = notify
        self.shadow = bool(shadow)
        self._inflight: set[str] = set()
        self._inflight_lock = asyncio.Lock()

    async def handle_operation(
        self,
        *,
        user_id: str,
        operation: str,
        trigger: str = "",
        subject_key: str = "",
        payload: Mapping[str, Any] | None = None,
        now: datetime | None = None,
    ) -> AutoExecOutcome:
        """一次 proactive 操作的授权门入口。永不抛出（失败翻译成 proposal）。"""
        now = now or _utcnow()

        # -- 授权现读（fail-closed：读不到 → proposal，绝不放行） ----------------
        try:
            grant_doc = await self.grants.read(str(user_id))
        except AutoExecStateUnavailable as exc:
            logger.warning("autoexec gate fail-closed (grants unavailable) user={}: {!r}", user_id, exc)
            return AutoExecOutcome(
                mode="proposal",
                reason=AutoExecDecisionReason.PROPOSAL_STATE_UNAVAILABLE.value,
                decision=None,
                details={"error": str(exc)},
            )

        decision = decide_auto_execution(
            user_id=str(user_id),
            operation=str(operation),
            trigger=str(trigger),
            subject_key=str(subject_key),
            grant_doc=grant_doc,
            now=now,
        )

        if not decision.allowed:
            return AutoExecOutcome(mode="proposal", reason=decision.reason, decision=decision)

        # -- shadow：would-auto 只记录，执行器零调用（P-01 shadow 同款纪律） ------
        if self.shadow:
            return AutoExecOutcome(
                mode="proposal",
                reason=AutoExecDecisionReason.PROPOSAL_SHADOW.value,
                decision=decision,
                would_auto=True,
            )

        # -- 幂等门：同键已有 receipt → 原样奉还，执行器不再调用 ------------------
        async with self._inflight_lock:
            if decision.idempotency_key in self._inflight:
                return AutoExecOutcome(
                    mode="proposal",
                    reason=AutoExecDecisionReason.DEDUP_REPLAY.value,
                    decision=decision,
                    details={"inflight": True},
                )
            try:
                prior = await self.receipts.find(str(user_id), decision.idempotency_key)
            except AutoExecStateUnavailable as exc:
                logger.warning("autoexec gate fail-closed (receipts unavailable) user={}: {!r}", user_id, exc)
                return AutoExecOutcome(
                    mode="proposal",
                    reason=AutoExecDecisionReason.PROPOSAL_STATE_UNAVAILABLE.value,
                    decision=decision,
                    details={"error": str(exc)},
                )
            if prior is not None:
                return AutoExecOutcome(
                    mode="auto",
                    reason=AutoExecDecisionReason.DEDUP_REPLAY.value,
                    decision=decision,
                    receipt=prior,
                    details={"replayed": True},
                )
            self._inflight.add(decision.idempotency_key)

        try:
            # -- 授权 + 幂等双门全过：唯一执行点 --------------------------------
            request = AutoExecRequest(
                user_id=str(user_id),
                operation=decision.operation,
                trigger=str(trigger),
                subject_key=str(subject_key),
                idempotency_key=decision.idempotency_key,
                grant_version=str(decision.grant_version or ""),
                payload=dict(payload or {}),
            )
            try:
                result = await self._execute(request)
            except Exception as exc:
                # 执行器失败：无 side effect（无成功 receipt），转 proposal 兜底，
                # 下一条 trigger 允许重试（幂等键不变，成功后恰一次语义不变）。
                logger.warning(
                    "autoexec executor failed user={} op={} key={}: {!r}",
                    user_id,
                    decision.operation,
                    decision.idempotency_key,
                    exc,
                )
                return AutoExecOutcome(
                    mode="proposal",
                    reason=AutoExecDecisionReason.AUTO_EXECUTOR_FAILED.value,
                    decision=decision,
                    details={"error": repr(exc)},
                )

            receipt = AutoExecReceipt(
                user_id=str(user_id),
                operation=decision.operation,
                trigger=str(trigger),
                subject_key=str(subject_key),
                idempotency_key=decision.idempotency_key,
                grant_version=str(decision.grant_version or ""),
                result="executed",
                occurred_at=now.isoformat(),
                executor_result=dict(result or {}),
            )
            # receipt 落库（幂等键索引）+ 审计 sink + notification 出口。
            # side effect 已发生，落账失败降级告警（不回滚执行）。
            await self.receipts.record(receipt, now=now)
            if self._sink is not None:
                try:
                    await self._sink(receipt)
                except Exception as exc:
                    logger.warning("autoexec receipt sink failed: {!r}", exc)
            if self._notify is not None:
                try:
                    await self._notify(receipt)
                except Exception as exc:
                    logger.warning("autoexec receipt notify failed: {!r}", exc)
            return AutoExecOutcome(mode="auto", reason=decision.reason, decision=decision, receipt=receipt)
        finally:
            self._inflight.discard(decision.idempotency_key)


# ---------------------------------------------------------------------------
# notification 载荷（与 SystemUpdateService.build_system_update 同形）
# ---------------------------------------------------------------------------


def build_autoexec_receipt_notification(receipt: AutoExecReceipt) -> dict[str, Any]:
    """receipt → 系统更新形状的通知载荷（P-01 ``build_system_update`` 同形）。

    每次 auto 执行都有 receipt/notification（卡面 Work ③）：receipt 是审计
    真源，notification 是用户可见面（「Aurora 替你做了 X，可撤销」）。
    """
    title = {
        AutoExecOperation.MARK_UPDATE_READ.value: "已替你把提醒标记为已读",
        AutoExecOperation.BOOKMARK_SUBJECT.value: "已替你收藏该主题",
        AutoExecOperation.SNOOZE_TRIGGER.value: "已替你推迟同类提醒",
    }.get(receipt.operation, "已自动完成一个低风险操作")
    return {
        "update_type": f"autoexec_{receipt.operation}",
        "category": "aurora",
        "title": f"Aurora：{title}",
        "description": "预授权低风险自动执行（可在设置中撤销授权）。",
        "priority": "low",
        "metadata": {
            "pipeline": "autoexec_v1",
            "operation": receipt.operation,
            "trigger": receipt.trigger,
            "subject_key": receipt.subject_key,
            "idempotency_key": receipt.idempotency_key,
            "grant_version": receipt.grant_version,
            "result": receipt.result,
            "occurred_at": receipt.occurred_at,
        },
    }
