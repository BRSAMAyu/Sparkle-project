"""
Aurora proactive pipeline — relevance decision layer (P-02).

P-01 抑制链解决「现在能不能打扰」（quiet hours / mute / cap / cooldown /
rejection / novelty —— **频控面**）；本模块解决紧随其后的「值不值得打扰」
（**内容语义面**，PROACTIVE_SYSTEM.md §4 Quality threshold：通知必须回答
*为什么现在、有什么新信息、点开后能得到什么*；§3 Suppression 的
``insufficient novelty`` / ``no actionable next step`` 的语义子集）：

    P-01 频控面 allowed ──▶ evaluate_relevance ──▶ act / no_action(+reason)
                              （本模块，纯函数）
                                ├─ act ──▶ 出口投递（其后才是 P-04 授权门）
                                └─ no_action ──▶ 落审计（record/metrics），零投递

════════════════════════════════════════════════════════════════════════
四问裁决（固定短路序；每个 no_action 带稳定结构化 reason）
════════════════════════════════════════════════════════════════════════
1. ``duplicate`` — 本次将携带的内容摘要与上次**就同一 subject 的提醒**完全
   一致：我们在重复自己（频控面的 novelty 只看 (trigger, subject) 且有
   48h TTL；本判定看**内容**，TTL 过期后内容未变依然是重复）。
2. ``already_aware`` — 用户对该 subject 的最近查看/交互时刻 ≥ 当前状态的
   起点时刻：用户已经亲眼见过我们要说的状态（卡面原例：逾期但用户一小时
   前刚看过任务页且其后无新变化 → 不打扰）。
3. ``no_new_information`` — 上次提醒时刻 ≥ 当前状态起点：当前状态早已告知
   过用户，其后没有新变化（提醒过 ≠ 用户点开看了，但我们已无更优的确定性
   手段，重复催看只增负担）。
4. ``not_actionable`` — 有用户未见的新信息，但不存在可执行的下一步
   （PROACTIVE_SYSTEM.md §3 "no actionable next step"）：点开后无所得。
5. ``context_unavailable`` — 相关性上下文读失败（redis 故障/文档损坏）：
   **fail-closed 不打扰**（P-01 ``state_unavailable`` / P-04
   ``proposal_state_unavailable`` 同源哲学：宁可漏报不可误报）。

════════════════════════════════════════════════════════════════════════
正向证据原则（本层与频控面的分界，如实申报的范围决策）
════════════════════════════════════════════════════════════════════════
判定只吃**正向证据**：空上下文（从未查看/从未提醒/无状态起点）一律放行
（act）——"无证据" ≠ "负证据"，此时频控面仍是唯一守门，P-01 既有行为
（含 bare ``user_active`` 直通）零改动。所有 no_action 判定都要求存在
确定性证据（摘要相等 / 时刻可比）。语义正确性与「违规打扰 = 0」红线由
成对 scenarios（该提醒 vs 不该提醒的镜像对）穷举钉死。

硬约束（与 P-01 同族）：
- **零 LLM**：全模块确定性纯函数 + 确定性摘要/起点派生 + duck-typing 存储；
  不 import 任何 LLM 客户端，测试静态扫描钉死。
- **确定性**：同一 (trigger, context) 输入永远得到同一裁决；同一
  (trigger, subject, payload) 永远得到同一 digest/onset。
- **可审计**：每个 no_action 的 reason ∈ :data:`RELEVANCE_REASONS`
  （封闭五值，有界 label，无基数风险），details 只含哈希摘要/ISO 时刻/
  证据来源词，不含用户内容。
- **管线位置**：P-01 抑制链之后、状态消费与出口之前——no_action 事件
  **不消耗** cap/cooldown/novelty 计数（只有真发/would-notify 消耗），
  也永不到达 P-04 授权门。

I/O（Redis 读取）只发生在 :class:`ProactiveRelevanceStore`，判定本身
（:func:`evaluate_relevance` / 派生函数）零 I/O，可脱离基础设施单独穷举。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Mapping

from loguru import logger

from app.aurora.proactive.triggers import DEADLINE_SOON_DAYS, ProactiveTrigger

__all__ = [
    "RELEVANCE_STEP",
    "RELEVANCE_REASONS",
    "RelevanceContext",
    "RelevanceDecision",
    "evaluate_relevance",
    "derive_information_digest",
    "derive_information_onset",
    "ProactiveRelevanceStore",
    "ProactiveRelevanceContextUnavailable",
    "RELEVANCE_CONTEXT_TTL_SECONDS",
]


#: 管线记录里本层的 step 名（与 P-01 抑制链 step 同位的审计锚点）。
RELEVANCE_STEP = "relevance"

#: no_action reason 封闭词表（有界 label；新增值必须进此元组并过契约测试）。
#: 顺序即裁决短路序（context_unavailable 由管线侧在构建上下文失败时使用）。
RELEVANCE_REASONS: tuple[str, ...] = (
    "duplicate",
    "already_aware",
    "no_new_information",
    "not_actionable",
    "context_unavailable",
)

#: 相关性上下文文档整体 TTL（与 P-01 抑制状态文档同族，30d，读路径续期）。
RELEVANCE_CONTEXT_TTL_SECONDS = 30 * 24 * 60 * 60

_KEY_TEMPLATE = "aurora:proactive_relevance:{scope}:{user_id}"


def _naive(value: datetime) -> datetime:
    """统一成 naive-UTC（与 P-01 suppress/triggers 的时刻惯例一致）。"""
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _clean_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _parse_datetime(value: Any) -> datetime | None:
    """naive-UTC 解析；解析失败返回 None（确定性：坏输入 = 无证据）。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return _naive(value)
    text = _clean_str(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _naive(parsed)


# ---------------------------------------------------------------------------
# 确定性派生：信息摘要 与 状态起点（零 I/O，同一输入永远同一输出）
# ---------------------------------------------------------------------------

#: 各触发承载信息内容的载荷字段（封闭映射；摘要只看语义字段，避免噪声字段
#: 变化稀释重复判定）。``USER_ACTIVE`` 为空：用户自己的动作对其本人不是
#: 新闻（PROACTIVE_SYSTEM.md §4：纯"继续学习"式 nudge 不构成新信息）。
_DIGEST_FIELDS: Mapping[ProactiveTrigger, tuple[str, ...]] = {
    ProactiveTrigger.DEADLINE: ("due_at",),
    ProactiveTrigger.OVERDUE: ("due_at",),
    ProactiveTrigger.SLOT_MISSED: ("session_id",),
    ProactiveTrigger.UPSTREAM_COMPLETED: ("task_id", "run_id", "status"),
    ProactiveTrigger.GOAL_STALLED: ("plan_id",),
    ProactiveTrigger.RUN_AWAITING: ("run_id", "to_status"),
    ProactiveTrigger.USER_ACTIVE: (),
}


def derive_information_digest(trigger: ProactiveTrigger, subject_key: str, payload: Mapping[str, Any]) -> str:
    """从事件载荷确定性派生「本次将携带内容」的摘要（16 hex 字符）。

    subject 参与摘要——不同 subject 永不碰撞；语义字段全缺失时返回
    ``""``（= 事件不承载可告知内容，属确定性事实而非缺证据）。
    ``USER_ACTIVE`` 恒为 ``""``：用户自己的动作对其本人不是新闻。
    """
    if trigger is ProactiveTrigger.USER_ACTIVE:
        return ""
    fields = _DIGEST_FIELDS[trigger]
    parts = [f"subject={subject_key}"] if subject_key else []
    for name in fields:
        value = _clean_str(payload.get(name))
        if value:
            parts.append(f"{name}={value}")
    if not parts:
        return ""
    canonical = "|".join([str(trigger.value), *parts])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def derive_information_onset(
    trigger: ProactiveTrigger, payload: Mapping[str, Any], *, now: datetime
) -> datetime | None:
    """确定性派生「当前将告知的状态自何时起为真」（状态起点）。

    - DEADLINE：临期窗起点 = due 日 − DEADLINE_SOON_DAYS 的零点（"临近"
      这个事实从那刻起为真——与 triggers.classify 的窗口判定同一参数）。
    - OVERDUE：due 日的次日零点（日期粒度过期 = due 日结束那刻起为真）。
    - 其余事实型触发：事件序列化的 ``timestamp``（事实发生时刻）。
    - USER_ACTIVE：``None``（用户自己的动作，不承载对其的新事实）。
    - 无法派生（字段缺失/坏值）→ ``None``（无起点证据，判定层放行）。
    """
    now = _naive(now)

    def _due_date() -> date | None:
        for key in ("due_at", "deadline_at", "deadline"):
            parsed = _parse_datetime(payload.get(key))
            if parsed is not None:
                return parsed.date()
        return None

    if trigger is ProactiveTrigger.DEADLINE:
        due = _due_date()
        if due is None:
            return None
        return datetime.combine(due - timedelta(days=DEADLINE_SOON_DAYS), time.min)
    if trigger is ProactiveTrigger.OVERDUE:
        due = _due_date()
        if due is None:
            return None
        return datetime.combine(due + timedelta(days=1), time.min)
    if trigger is ProactiveTrigger.USER_ACTIVE:
        return None
    # 事实型触发：事实发生时刻 = 事件时间戳（载荷序列化字段，无则无证据）。
    return _parse_datetime(payload.get("timestamp"))


# ---------------------------------------------------------------------------
# 纯函数判定层
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RelevanceContext:
    """相关性判定的输入快照（用户近况 + 本次携带内容，全部由调用方注入）。

    全部字段可缺省——缺省 = 无证据（判定层放行，正向证据原则）。
    时刻均为 naive-UTC（tz-aware 输入会被归一化后比较）。
    """

    #: 用户最后一次查看该 subject（任务页/计划页/运行页…）时刻。
    subject_last_viewed_at: datetime | None = None
    #: 用户最后一次对该 subject 做出有效操作（推进/完成/调整…）时刻。
    subject_last_interaction_at: datetime | None = None
    #: 上次就同 subject 提醒（真发或 would-notify）的时刻。
    last_reminder_at: datetime | None = None
    #: 上次提醒所携带内容的摘要（:func:`derive_information_digest` 同源）。
    last_reminder_digest: str = ""
    #: 本次将携带内容的摘要；"" = 本次事件不承载可告知内容。
    current_digest: str = ""
    #: 当前将告知的状态起点（None = 无起点证据）。
    subject_state_changed_at: datetime | None = None
    #: 是否存在可执行的下一步（PROACTIVE_SYSTEM.md §4"点开后能得到什么"）。
    has_actionable_step: bool = True


@dataclass(frozen=True, slots=True)
class RelevanceDecision:
    """一步裁决：act（放行给出口）或 no_action（结构化原因 + 审计细节）。"""

    allowed: bool
    #: no_action 原因（∈ :data:`RELEVANCE_REASONS`）；act 时为 None。
    reason: str | None = None
    #: 审计细节（哈希摘要/ISO 时刻/证据来源词），不含用户内容。
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def suppressed(self) -> bool:
        return not self.allowed


def evaluate_relevance(*, trigger: ProactiveTrigger, context: RelevanceContext) -> RelevanceDecision:
    """确定性相关性裁决（固定短路序，见模块 docstring 四问）。

    纯函数：零 I/O、零时钟读取、零 LLM；同一输入永远同一输出。
    """
    changed = _naive(context.subject_state_changed_at) if context.subject_state_changed_at is not None else None
    viewed = _naive(context.subject_last_viewed_at) if context.subject_last_viewed_at is not None else None
    interacted = (
        _naive(context.subject_last_interaction_at) if context.subject_last_interaction_at is not None else None
    )
    last_reminder = _naive(context.last_reminder_at) if context.last_reminder_at is not None else None

    # 1. duplicate —— 内容级重复：与上次提醒携带的摘要完全一致。
    #    （比频控面 novelty 更强：48h TTL 过期后内容未变仍是重复。）
    if context.current_digest and context.last_reminder_digest == context.current_digest:
        return RelevanceDecision(
            False,
            "duplicate",
            {"digest": context.current_digest, "rule": "digest_match"},
        )

    # 2. already_aware —— 用户已亲眼见过当前状态（查看/交互 ≥ 状态起点；
    #    取两者较晚者；边界相等视为已知晓）。卡面原例的判定落点。
    aware_sources: list[str] = []
    aware_at: datetime | None = None
    for source, at in (("view", viewed), ("interaction", interacted)):
        if at is not None:
            aware_sources.append(source)
            if aware_at is None or at > aware_at:
                aware_at = at
    if changed is not None and aware_at is not None and aware_at >= changed:
        return RelevanceDecision(
            False,
            "already_aware",
            {
                "aware_source": "+".join(aware_sources),
                "aware_at": aware_at.isoformat(),
                "changed_at": changed.isoformat(),
            },
        )

    # 3. no_new_information —— 当前状态早已提醒过，其后无新变化
    #    （提醒内容与状态是否一致由规则 1 的摘要相等先行短路，此处兜住
    #    "已告知过当前状态、其后无实质更新" 的一般情形）。
    if changed is not None and last_reminder is not None and last_reminder >= changed:
        return RelevanceDecision(
            False,
            "no_new_information",
            {
                "last_reminder_at": last_reminder.isoformat(),
                "changed_at": changed.isoformat(),
            },
        )

    # 4. not_actionable —— 有未见的新信息，但点开后无可执行的下一步。
    if not context.has_actionable_step:
        return RelevanceDecision(False, "not_actionable", {"has_actionable_step": False})

    # 无负向证据 → act（正向证据原则；频控面之后语义面放行）。
    return RelevanceDecision(True)


# ---------------------------------------------------------------------------
# 上下文存取（Redis JSON 文档；P-01 抑制状态存储同族约定）
# ---------------------------------------------------------------------------


class ProactiveRelevanceContextUnavailable(RuntimeError):
    """相关性上下文不可用（redis 故障 / 未配置 / 文档损坏）——fail-closed 信号。"""


def _iso(value: datetime) -> str:
    return _naive(value).isoformat()


class ProactiveRelevanceStore:
    """用户近况上下文读写（Redis JSON 文档，``ProactiveSuppressionStore`` 同族）。

    文档形状（每用户每 scope 一个键，读解析、写整体覆盖、TTL 写路径维护）::

        {"subjects": {"<subject_key>": {
            "last_viewed_at": iso, "last_interaction_at": iso,
            "last_reminder_at": iso, "last_reminder_digest": hex,
            "last_changed_at": iso}}, "updated_at": iso}

    - 写 API（:meth:`record_subject_view` / :meth:`record_subject_interaction` /
      :meth:`record_subject_change`）供真实生产方接入（移动端已读回执桥、
      未来 follow-up 卡）；本卡管线只接 :meth:`record_reminder`（notify/
      would-notify 时写摘要——duplicate/no_new_information 的记忆来源）。
    - 读路径异常语义与 P-01 一致：redis 未配置/读失败/文档损坏抛
      :class:`ProactiveRelevanceContextUnavailable`（管线翻译成
      ``context_unavailable`` fail-closed）；「键不存在」是合法空态返回
      空上下文（新用户零历史属真实状态，不是故障）。
    """

    def __init__(self, redis: Any = None):
        self.redis = redis

    @staticmethod
    def context_key(scope: str, user_id: str) -> str:
        return _KEY_TEMPLATE.format(scope=scope, user_id=str(user_id))

    # -- read -------------------------------------------------------------

    async def build_context(
        self,
        user_id: str,
        subject_key: str,
        *,
        scope: str = "live",
        now: datetime | None = None,
    ) -> RelevanceContext:
        """读取某 subject 的用户近况上下文（键不存在 = 全缺省空态）。

        Raises:
            ProactiveRelevanceContextUnavailable: redis 未配置 / 读失败 /
                文档损坏——调用方必须翻译成 ``context_unavailable`` 不打扰，
                不得以空上下文放行（fail-closed，与 P-01 同源）。
        """
        if not subject_key:
            # 无 subject 无法定位用户近况：返回空上下文（合法无证据态）。
            return RelevanceContext()
        doc = await self._load(user_id, scope)
        entry = (doc.get("subjects") or {}).get(subject_key)
        if not isinstance(entry, Mapping):
            return RelevanceContext()
        return RelevanceContext(
            subject_last_viewed_at=_parse_datetime(entry.get("last_viewed_at")),
            subject_last_interaction_at=_parse_datetime(entry.get("last_interaction_at")),
            last_reminder_at=_parse_datetime(entry.get("last_reminder_at")),
            last_reminder_digest=_clean_str(entry.get("last_reminder_digest")),
        )

    # -- write ------------------------------------------------------------

    async def record_reminder(
        self,
        user_id: str,
        subject_key: str,
        *,
        digest: str,
        at: datetime,
        scope: str = "live",
    ) -> None:
        """提醒落账（notify / would-notify 时由管线调用；best-effort）。"""
        if not subject_key:
            return
        doc = await self._load(user_id, scope)
        subjects = dict(doc.get("subjects") or {})
        entry = dict(subjects.get(subject_key) or {})
        entry["last_reminder_at"] = _iso(at)
        entry["last_reminder_digest"] = str(digest)
        subjects[subject_key] = entry
        doc["subjects"] = subjects
        doc["updated_at"] = _iso(at)
        await self._save(user_id, scope, doc)

    async def record_subject_view(self, user_id: str, subject_key: str, *, at: datetime, scope: str = "live") -> None:
        """用户查看 subject 落账（生产方接入点；best-effort）。"""
        await self._record_subject_field(user_id, subject_key, "last_viewed_at", at, scope)

    async def record_subject_interaction(
        self, user_id: str, subject_key: str, *, at: datetime, scope: str = "live"
    ) -> None:
        """用户操作 subject 落账（生产方接入点；best-effort）。"""
        await self._record_subject_field(user_id, subject_key, "last_interaction_at", at, scope)

    async def record_subject_change(self, user_id: str, subject_key: str, *, at: datetime, scope: str = "live") -> None:
        """subject 实质变化落账（生产方接入点；best-effort）。

        读取侧不消费此字段（起点以载荷派生为准），落账仅供审计与后续卡
        （无载荷起点的事实型变化需要存储起点时的扩展位）。
        """
        await self._record_subject_field(user_id, subject_key, "last_changed_at", at, scope)

    # -- internals --------------------------------------------------------

    async def _record_subject_field(
        self, user_id: str, subject_key: str, field_name: str, at: datetime, scope: str
    ) -> None:
        if not subject_key:
            return
        doc = await self._load(user_id, scope)
        subjects = dict(doc.get("subjects") or {})
        entry = dict(subjects.get(subject_key) or {})
        entry[field_name] = _iso(at)
        subjects[subject_key] = entry
        doc["subjects"] = subjects
        doc["updated_at"] = _iso(at)
        await self._save(user_id, scope, doc)

    async def _load(self, user_id: str, scope: str) -> dict[str, Any]:
        """读上下文文档；键不存在返回空 dict（合法零态），其余故障上抛。"""
        if self.redis is None:
            raise ProactiveRelevanceContextUnavailable("proactive relevance redis not configured")
        try:
            raw = await self.redis.get(self.context_key(scope, user_id))
        except Exception as exc:
            logger.warning("proactive relevance load failed scope={} user={}: {!r}", scope, user_id, exc)
            raise ProactiveRelevanceContextUnavailable(f"proactive relevance read failed: {exc!r}") from exc
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("proactive relevance doc corrupt scope={} user={}: {!r}", scope, user_id, exc)
            raise ProactiveRelevanceContextUnavailable(f"proactive relevance doc corrupt: {exc!r}") from exc
        if not isinstance(parsed, dict):
            raise ProactiveRelevanceContextUnavailable("proactive relevance doc is not a mapping")
        return parsed

    async def _save(self, user_id: str, scope: str, doc: Mapping[str, Any]) -> None:
        if self.redis is None:
            return
        try:
            await self.redis.set(
                self.context_key(scope, user_id),
                json.dumps(doc, ensure_ascii=False, default=str),
                ex=RELEVANCE_CONTEXT_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("proactive relevance save failed scope={} user={}: {!r}", scope, user_id, exc)
