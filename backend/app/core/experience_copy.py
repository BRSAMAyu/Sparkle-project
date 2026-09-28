"""V4-F03 · experience_event.v1 冻结文案表 + 反馈语义分层路由（契约 §3 R1-C5）。

B05 冻结契约 ``v4/evidence/V4-B05/contract_receipt_min.md`` §3 明文：``copy_key``
取冻结文案表键、**不是**模型自由文本；「冻结文案表（键→文案）owner 指定为
V4-F03 实现卡」。本模块即该表落点（键纪律两段式 ``<域>.<名>`` 由
``ExperiencePresentation`` 构造期强制，本模块冻结**键集 + 文案内容**）。

反馈语义与状态语义严格分层（卡验收 2）的机制化——**结构性**保证，不靠自觉：

- **成功面孔封闭集**：``SUCCESS_FACE_SUBJECT_TYPES = {task, goal, plan}``——
  仅这些 subject 的 committed 回执允许驱动成功类呈现（庆祝动效/成功音/成功触）。
  ``memory`` 的 committed 回执是「记忆已保存」（域内事实），**永不**映射到
  ``task.committed`` 类任务成功文案（B05 §9 反例：「保存了一条记忆」的回执当
  「任务已修改」呈现）；``intervention`` 的 committed 投影是 D01 真实呈现回执
  （已查看，信息性）。
- **精通词缺席**：证据登记（outcome/evidence 登账）的呈现键是
  ``evidence.registered``（「证据已登记」）。全表**不存在**任何「精通/已掌握」
  类键——掌握判定归 I07 hybrid-policy 锁面（mastery/deliverable 目的约束），
  呈现层结构上无词可拼（测试钉死：禁词扫描）。
- **五错误态专用失败键**（契约 §6 表）：``err.*`` 五键与 committed 键互斥，
  永不混用（卡验收 3 的 copy 面）。

扩展 = 契约变更：键集冻结测试（``TestFrozenCopyTable``）钉死成员；新增键/改
文案必须 bump 过 reviewer，本表不得私扩。
"""

from __future__ import annotations

import enum

from app.core.experience_event import (
    ExperienceErrorState,
    ExperienceEventKind,
    ExperienceSubjectType,
)

EXPERIENCE_COPY_TABLE_VERSION = "experience-copy.v1"

# ---------------------------------------------------------------------------
# 冻结文案表（键 → 中文文案；键集与内容均冻结，扩展 = 契约变更）
# ---------------------------------------------------------------------------

EXPERIENCE_COPY_TABLE: dict[str, str] = {
    # --- committed（域内事实，成功面孔仅 task/goal/plan 三域） ---
    "task.committed": "任务已更新",
    "goal.committed": "目标已更新",
    "plan.committed": "计划已更新",
    # --- committed（非成功面孔：域内事实，信息性） ---
    "memory.saved": "记忆已保存",
    "run.completed": "运行已完成",
    "intervention.rendered": "已查看",
    # --- 非 committed kind（信息性呈现） ---
    "state.syncing": "同步中",
    "resume.available": "有可接续的进度",
    "correction.applied": "纠正已生效",
    "calibration.notice": "校准说明",
    # --- 证据/进度（D-02 分级语义：登记 ≠ 精通） ---
    "evidence.registered": "证据已登记",
    "progress.delta": "进度更新",
    # --- 五错误态专用失败键（契约 §6 表；与 committed 键互斥） ---
    "err.version_conflict": "你的设置已更新，需要重新生成",
    "err.unauthorized": "没有权限执行这个操作",
    "err.not_pending": "该操作已处理，无需重复确认",
    "err.expired": "该提案已过期，需要重新生成",
    "err.not_found": "没有找到对应的操作",
}

# ---------------------------------------------------------------------------
# 反馈语义分层路由（封闭；路由表缺失键 = 结构拒绝，不静默归一）
# ---------------------------------------------------------------------------


class SuccessFaceSubject(enum.StrEnum):
    """允许成功类呈现（庆祝动效/成功音/成功触）的 subject 类型封闭集。

    卡验收 2 的机制面：记忆保存/干预呈现/运行完成**不在**集合内——它们的
    committed 回执只产信息性呈现（copy 正确、无庆祝模态）。
    """

    TASK = ExperienceSubjectType.TASK.value
    GOAL = ExperienceSubjectType.GOAL.value
    PLAN = ExperienceSubjectType.PLAN.value


SUCCESS_FACE_SUBJECT_TYPES: frozenset[str] = frozenset(s.value for s in SuccessFaceSubject)

#: committed 回执 → copy_key 的唯一路由（封闭；词表外 subject 拒绝）。
COMMITTED_COPY_KEY_BY_SUBJECT: dict[str, str] = {
    ExperienceSubjectType.TASK.value: "task.committed",
    ExperienceSubjectType.GOAL.value: "goal.committed",
    ExperienceSubjectType.PLAN.value: "plan.committed",
    ExperienceSubjectType.MEMORY.value: "memory.saved",
    ExperienceSubjectType.RUN.value: "run.completed",
    ExperienceSubjectType.INTERVENTION.value: "intervention.rendered",
}

#: 非 committed kind → copy_key（信息性呈现路由；词表外 kind 拒绝）。
KIND_COPY_KEY: dict[str, str] = {
    ExperienceEventKind.STATE_SYNCING.value: "state.syncing",
    ExperienceEventKind.RESUME_AVAILABLE.value: "resume.available",
    ExperienceEventKind.CORRECTION_APPLIED.value: "correction.applied",
    ExperienceEventKind.CALIBRATION_NOTICE.value: "calibration.notice",
    ExperienceEventKind.PROGRESS_DELTA.value: "progress.delta",
}

#: error_state → 失败呈现 copy_key（契约 §6 表 1:1；与 committed 键互斥）。
ERROR_STATE_COPY_KEY: dict[str, str] = {
    ExperienceErrorState.VERSION_CONFLICT.value: "err.version_conflict",
    ExperienceErrorState.UNAUTHORIZED.value: "err.unauthorized",
    ExperienceErrorState.NOT_PENDING.value: "err.not_pending",
    ExperienceErrorState.EXPIRED.value: "err.expired",
    ExperienceErrorState.NOT_FOUND.value: "err.not_found",
}

#: 证据登记语义键（卡验收 2「证据登记不叫精通」的锚键：呈现层对 evidence/outcome
#: 登账唯一可用键——全表无精通类键，见模块 docstring）。
EVIDENCE_REGISTERED_COPY_KEY = "evidence.registered"


def copy_key_for_committed_subject(subject_type: str) -> str:
    """committed 回执 → copy_key（封闭路由；词表外 subject 拒绝，不静默归一）。"""
    key = COMMITTED_COPY_KEY_BY_SUBJECT.get(str(subject_type))
    if key is None:
        raise ValueError(f"subject_type {subject_type!r} has no committed copy route (closed router)")
    return key


def copy_key_for_kind(kind: str) -> str:
    """非 committed kind → copy_key（封闭路由；词表外 kind 拒绝）。"""
    key = KIND_COPY_KEY.get(str(kind))
    if key is None:
        raise ValueError(f"kind {kind!r} has no copy route (closed router)")
    return key


def copy_key_for_error_state(error_state: str) -> str:
    """error_state → 失败呈现 copy_key（契约 §6 表 1:1；词表外拒绝）。"""
    key = ERROR_STATE_COPY_KEY.get(str(error_state))
    if key is None:
        raise ValueError(f"error_state {error_state!r} has no failure copy route (closed router)")
    return key


def resolve_copy(copy_key: str) -> str:
    """冻结表解析；键集外 KeyError（调用方不得拼自由文本）。"""
    return EXPERIENCE_COPY_TABLE[copy_key]


__all__ = [
    "COMMITTED_COPY_KEY_BY_SUBJECT",
    "ERROR_STATE_COPY_KEY",
    "EVIDENCE_REGISTERED_COPY_KEY",
    "EXPERIENCE_COPY_TABLE",
    "EXPERIENCE_COPY_TABLE_VERSION",
    "KIND_COPY_KEY",
    "SUCCESS_FACE_SUBJECT_TYPES",
    "SuccessFaceSubject",
    "copy_key_for_committed_subject",
    "copy_key_for_error_state",
    "copy_key_for_kind",
    "resolve_copy",
]
