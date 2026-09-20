"""X-04 · Human Action Flow —— actual 时长真源 + completion evidence 分型.

两条 X-04 验收红线的单一实现点（task 生命周期四态 start/complete/abandon/rescope
共用的权威逻辑，禁止在调用方复制）：

1. **实际时长永不从 estimated 回填**（灵魂红线）：
   ``resolve_actual_minutes`` 只认两个真源——调用方提供的**实测**分钟数
   （如客户端计时器），或任务真实起止时间（started_at → 终态时刻）减去暂停
   区间。两者皆缺 → None（诚实缺省），**任何路径都不允许**拿
   ``estimated_minutes`` 顶替——estimated 是计划输入，不是执行观测。
   分级信任（实测 > 起止推算 > 缺省）与 G-01 evidence 融合的 task_outcome
   上游语义对齐：宁可缺省，不可编造。

2. **completion evidence 类型化**（词表复用 X-01 ``EVIDENCE_KINDS`` 封闭枚举，
   零新增词表）：
   - 期望证据按 action 类型路由（``expected_evidence_kinds``）：plan 侧声明
     （X-01 ``tasks.completion_evidence`` 列）优先，否则按 TaskType/execution_mode
     确定性推导；
   - 完成时用户附带的证据逐条校验（kind 封闭 + ref scheme 封闭）；
   - **无证据时类型正确**：不伪造 artifact/quiz——回落为与证据来源相称的诚实
     类型（用户显式确认 → ``user_confirmation``；focus 计时器自动完成 →
     ``system_event``；agent 代执行 → ``system_event``），并在记录里如实标注
     ``declared_kinds`` 未满足（``fulfilled=False``）。「focus timer 不等于学习
     成果」（GOAL_TASK_PLAN_CALENDAR_FOCUS.md）由此落到证据信任分级上。

记录落点：``tasks.guide_json["completion_evidence_record"]``——X-01 的
``completion_evidence`` 列保持 plan 侧声明语义不被覆写（契约冻结），actual
记录是增量附加，G-01 task_outcome 证据融合的直读上游。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.action_plan import ACTION_SOURCE_REF_SCHEMES, EVIDENCE_KINDS
from app.models.task import Task, TaskType

COMPLETION_EVIDENCE_RECORD_VERSION = "completion_evidence.v1"

#: 完成证据来源（谁断言了「完成」）——决定无证据时回落类型（诚实分级）
EVIDENCE_SOURCES: frozenset[str] = frozenset({"user", "focus_auto", "agent", "system"})

#: source → 无附带证据时的回落 evidence_kind（诚实类型，绝不伪造 artifact/quiz）
_SOURCE_FALLBACK_KIND: dict[str, str] = {
    "user": "user_confirmation",
    "focus_auto": "system_event",
    "agent": "system_event",
    "system": "system_event",
}

#: 无 plan 声明时的 action 类型 → 期望证据路由（确定性，TaskType 封闭词表）
_TASK_TYPE_EXPECTED_KINDS: dict[TaskType, tuple[str, ...]] = {
    TaskType.OCR: ("artifact",),  # 产出手写/扫描产物
    TaskType.PLANNING: ("artifact",),  # 产出计划文档
    TaskType.ERROR_FIX: ("quiz_result",),  # 重做同类题验证
    TaskType.TRAINING: ("quiz_result",),  # 练习/测验结果
    TaskType.REFLECTION: ("self_report",),  # 反思自述
    TaskType.LEARNING: ("self_report",),  # 学习型默认自报（低信任）
    TaskType.SOCIAL: ("self_report",),
}

#: guide_json 落点键名（append-only 历史）
COMPLETION_EVIDENCE_RECORD_KEY = "completion_evidence_record"
REOPEN_HISTORY_KEY = "reopen_history"
ABANDON_RECORD_KEY = "abandon_record"
RESCOPE_HISTORY_KEY = "rescope_history"

#: rescope 允许调整的字段白名单（与 X-03 TASK_FIELD_WHITELIST 语义对齐；
#: 独立声明以解耦 command 契约与 service 语义——词表一致）
RESCOPE_FIELD_WHITELIST: frozenset[str] = frozenset(
    {
        "title",
        "estimated_minutes",
        "difficulty",
        "energy_cost",
        "priority",
        "due_date",
        "success_criteria",
    }
)


def _ref_scheme(ref: str) -> str:
    return ref.split("://", 1)[0] if "://" in ref else ""


# ---------------------------------------------------------------------------
# 1. actual 时长真源（红线：永不从 estimated 回填）
# ---------------------------------------------------------------------------


def _paused_seconds(task: Task) -> int:
    """从 guide_json.pause_state 提取可考的累计暂停秒数（有则用，无则 0）.

    pause() 写 paused_at、resume() 写 resumed_at（既有真源）；本函数只读，
    不要求调用方预先累计——单次区间可考则扣除，历史缺失部分诚实忽略
    （宁少扣不少算：actual 偏保守小于等于真实活跃时长，仍绝不等于 estimated）。
    """
    guide = task.guide_json if isinstance(task.guide_json, dict) else {}
    pause_state = guide.get("pause_state") if isinstance(guide.get("pause_state"), dict) else {}

    total = pause_state.get("total_paused_seconds")
    if isinstance(total, (int, float)) and total >= 0:
        return int(total)

    # 单次区间回退：paused_at 与 resumed_at 成对可考时扣除一段
    paused_at = pause_state.get("paused_at")
    resumed_at = pause_state.get("resumed_at")
    if isinstance(paused_at, str) and isinstance(resumed_at, str):
        try:
            start = datetime.fromisoformat(paused_at)
            end = datetime.fromisoformat(resumed_at)
            seconds = (end - start).total_seconds()
            return int(seconds) if seconds > 0 else 0
        except ValueError:
            return 0
    return 0


def compute_actual_minutes_from_timestamps(task: Task, *, ended_at: datetime) -> int | None:
    """真实起止推算：ended_at - started_at - 暂停区间；无 started_at → None.

    下限 0（时钟回拨等异常不产生负时长）；分钟向下取整（保守）。
    """
    started_at = task.started_at
    if started_at is None:
        return None
    if ended_at.tzinfo is not None:
        ended_at = ended_at.replace(tzinfo=None)
    if started_at.tzinfo is not None:
        started_at = started_at.replace(tzinfo=None)
    seconds = (ended_at - started_at).total_seconds() - _paused_seconds(task)
    return max(0, int(seconds // 60))


def resolve_actual_minutes(
    task: Task,
    *,
    provided: int | None,
    ended_at: datetime,
) -> int | None:
    """actual 时长裁决（唯一权威）：实测 > 真实起止推算 > None。

    ``provided`` 必须是**实测**值（客户端计时器等）；本函数不看
    ``estimated_minutes``——红线守护点，任何调用方不得绕过此函数自行回填。
    """
    if provided is not None:
        minutes = int(provided)
        if minutes <= 0:
            raise ValueError("actual_minutes must be a positive measured value")
        return minutes
    return compute_actual_minutes_from_timestamps(task, ended_at=ended_at)


def resolve_spark_study_minutes(actual_minutes: int | None) -> int:
    """Galaxy spark 的 study_minutes：只认真实时长，缺省为 0（不再 estimated 回填）."""
    if actual_minutes is None or actual_minutes <= 0:
        return 0
    return int(actual_minutes)


# ---------------------------------------------------------------------------
# 2. completion evidence 分型（X-01 词表复用；无证据时类型正确）
# ---------------------------------------------------------------------------


def expected_evidence_kinds(task: Task) -> tuple[str, ...]:
    """期望证据类型：plan 侧声明优先，否则按 action 类型确定性路由.

    plan 声明（X-01 ``completion_evidence`` 列）中的 kind 经词表过滤——损坏行
    降级为类型路由，不让脏数据把期望集变空。
    """
    declared: list[str] = []
    raw = getattr(task, "completion_evidence", None)
    if isinstance(raw, list):
        for entry in raw:
            if isinstance(entry, dict) and entry.get("evidence_kind") in EVIDENCE_KINDS:
                declared.append(str(entry["evidence_kind"]))
    if declared:
        return tuple(dict.fromkeys(declared))

    routed = _TASK_TYPE_EXPECTED_KINDS.get(task.type, ("self_report",))
    if str(getattr(task, "execution_mode", None) or "") == "agent":
        # agent 代执行：run receipt（系统事件）才是第一手证据
        routed = ("system_event",) + routed
    return routed


def validate_evidence_entries(entries: Any) -> list[dict[str, Any]]:
    """校验用户/系统附带的完成证据（kind 封闭 + ref scheme 封闭），非法即拒."""
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise ValueError("evidence must be a list of {evidence_kind, ref?, description?}")
    normalized: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"evidence[{index}] must be an object")
        kind = entry.get("evidence_kind")
        if kind not in EVIDENCE_KINDS:
            raise ValueError(
                f"evidence[{index}].evidence_kind {kind!r} out of vocabulary (closed: {sorted(EVIDENCE_KINDS)})"
            )
        ref = entry.get("ref")
        if ref is not None:
            ref = str(ref).strip() or None
        if ref is not None and _ref_scheme(ref) not in ACTION_SOURCE_REF_SCHEMES:
            raise ValueError(f"evidence[{index}].ref has unknown scheme: {ref!r}")
        description = entry.get("description")
        normalized.append(
            {
                "evidence_kind": str(kind),
                "ref": ref,
                "description": (str(description)[:500] if description else None),
            }
        )
    return normalized


def build_completion_evidence_record(
    task: Task,
    *,
    provided: list[dict[str, Any]] | None,
    source: str,
    completed_at: datetime,
) -> dict[str, Any]:
    """完成证据记录（G-01 task_outcome 融合的上游；无证据时类型正确）.

    - provided：用户/系统实际附带的证据（已校验）；
    - declared：plan 侧声明的期望类型（未满足如实保留，不伪造满足）；
    - 无 provided 时回落类型由 source 决定（诚实分级，绝不伪造 artifact/quiz）。
    """
    if source not in EVIDENCE_SOURCES:
        raise ValueError(f"unknown evidence source {source!r} (closed vocabulary)")
    entries = list(provided or [])
    declared = expected_evidence_kinds(task)
    provided_kinds = {entry["evidence_kind"] for entry in entries}
    fulfilled = any(kind in declared for kind in provided_kinds)

    if not entries:
        fallback_kind = _SOURCE_FALLBACK_KIND[source]
        entries = [
            {
                "evidence_kind": fallback_kind,
                "ref": None,
                "description": "完成确认未附带证据（诚实回落类型，非伪造产物/测验）",
                "origin": "fallback",
            }
        ]
    else:
        entries = [{**entry, "origin": "provided"} for entry in entries]

    return {
        "schema_version": COMPLETION_EVIDENCE_RECORD_VERSION,
        "recorded_at": completed_at.isoformat(timespec="seconds"),
        "source": source,
        "declared_kinds": list(declared),
        "fulfilled": fulfilled,
        "entries": entries,
    }


def append_completion_evidence_record(task: Task, record: dict[str, Any]) -> None:
    """把完成证据记录写进 guide_json（保留旧尝试的记录历史，重开不抹）."""
    guide = dict(task.guide_json or {})
    history = guide.get(COMPLETION_EVIDENCE_RECORD_KEY)
    if isinstance(history, list):
        history = [*history, record]
    elif history is None:
        history = [record]
    else:  # 脏形态 → 收敛为历史列表，不丢已有内容
        history = [history, record]
    guide[COMPLETION_EVIDENCE_RECORD_KEY] = history
    task.guide_json = guide
