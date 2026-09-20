"""X-03 · 任务域 Action 命令处理器（proposal → TaskService 的薄执行层）.

设计纪律（「统一 command path，权威逻辑单点」）：
- **prepare**（proposal 创建时）：确定性预筛——owner 校验、FSM 合法性（复用
  task_service 的 ``_VALID_TRANSITIONS`` 单一真源，import 不复制）、字段白名单
  （封闭集合）、before/after 快照与 diff、版本 token 捕获；
- **validate_subject**（approve 时、commit 前）：重读 subject 行比对版本 token
  ——stale 拒绝（乐观并发不覆盖）；
- **execute**（commit）：**路由既有 TaskService**（任务写唯一权威），不旁路、
  不重建写路径。TaskService.update/create 内部 commit 会原子携带本服务在同一
  session 事务内已 stage 的 proposal/receipt/transition 写（单次 commit 全落）。

命令词表（ActionCommandType，契约层冻结）：task.update_status /
task.update_fields / task.create_batch。
"""

from __future__ import annotations

from datetime import date as DateType
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import (
    ActionCommandType,
    CommandEffects,
    CommandValidationError,
    PreparedCommand,
    ProposalNotFoundError,
    build_diff,
    version_token,
)
from app.models.action_proposal import ActionProposal
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task_service import _VALID_TRANSITIONS, TaskService

#: task.update_fields 的封闭字段白名单（UI 可提案修改的列；新增 = 契约变更）
TASK_FIELD_WHITELIST: frozenset[str] = frozenset(
    {
        "title",
        "estimated_minutes",
        "difficulty",
        "energy_cost",
        "priority",
        "due_date",
        "user_note",
        "success_criteria",
    }
)

#: diff / receipt 中呈现的 subject 快照字段（稳定投影，避免整行泄漏）
_SUBJECT_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "status",
    "title",
    "priority",
    "estimated_minutes",
    "difficulty",
    "energy_cost",
    "due_date",
    "user_note",
    "completed_at",
    "started_at",
    "paused_at",
)

_STATUS_ALIASES: dict[str, TaskStatus] = {s.value.lower(): s for s in TaskStatus}

#: FSM 无出边的终态目标（task_service._VALID_TRANSITIONS 的语义投影：终态不可逆；
#: complete 还携带 galaxy spark 等不可撤销副作用）——R2 P2-1 返修：reversible
#: 不再是硬编码常量，按目标态真实推导。
_IRREVERSIBLE_TARGET_STATUSES: frozenset[TaskStatus] = frozenset(
    {status for status, targets in _VALID_TRANSITIONS.items() if not targets}
)


def status_change_semantics(target: TaskStatus) -> tuple[str, bool]:
    """``task.update_status`` 的 per-command 授权语义导出（确定性，非调用方输入）.

    返回 ``(risk_class, reversible)``，词表对齐 X-01 RiskClass（low/medium/high/critical）：
    - 非终态目标（start/pause/resume/stuck）：``("low", True)``——状态可再迁移回去；
    - 终态目标（COMPLETED/ABANDONED）：``("medium", False)``——FSM 无出边且携带
      galaxy spark 等不可撤销副作用，授权门「auto 需可逆」条件对其真实生效。
    """
    irreversible = target in _IRREVERSIBLE_TARGET_STATUSES
    return ("medium" if irreversible else "low"), (not irreversible)


def _snapshot(task: Task) -> dict[str, Any]:
    snap: dict[str, Any] = {}
    for field_name in _SUBJECT_SNAPSHOT_FIELDS:
        value = getattr(task, field_name, None)
        if isinstance(value, DateType):
            value = value.isoformat()
        elif hasattr(value, "isoformat"):  # datetime
            value = value.isoformat(timespec="seconds") if value else None
        elif hasattr(value, "value"):  # enum
            value = value.value
        snap[field_name] = value
    return snap


async def _load_user_task(db: AsyncSession, *, task_id: Any, user_id: Any, for_update: bool = False) -> Task:
    if task_id is None:
        raise CommandValidationError("task_id is required for task.* commands")
    try:
        task_uuid = _to_uuid(task_id)
    except (TypeError, ValueError) as exc:
        raise CommandValidationError(f"invalid task_id {task_id!r}") from exc
    stmt = select(Task).where(
        Task.id == task_uuid,
        Task.user_id == _to_uuid(user_id),
        Task.deleted_at.is_(None),
    )
    if for_update:
        # R2 P3 返修：validate_subject 在 approve 关键段内重读 subject 时加行锁，
        # 封闭「同 task 两个不同 proposal 并发 approve」的 validate→execute 交错窗
        # （TOCTOU）。锁序固定 proposal → task（approve 先锁 proposal 行，TaskService
        # 永不反序锁 proposal），无死环。sqlite 方言静默丢弃 FOR UPDATE 子句——
        # 测试由版本 token + 复查兜底（与 proposal 行锁同款限定），真并发仅在 PG 成立。
        stmt = stmt.with_for_update()
    task = (await db.execute(stmt)).scalar_one_or_none()
    if task is None:
        raise ProposalNotFoundError(f"task {task_id} not found for user")
    return task


def _to_uuid(value: Any):
    from uuid import UUID

    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _resolve_status(raw: Any) -> TaskStatus:
    if isinstance(raw, TaskStatus):
        return raw
    normalized = str(raw).strip().lower()
    matched = _STATUS_ALIASES.get(normalized)
    if matched is None:
        raise CommandValidationError(f"unknown task status {raw!r} (TaskStatus vocabulary)")
    return matched


class TaskUpdateStatusCommand:
    """``task.update_status`` —— 状态迁移提案（Aurora/chat/task 入口共用）."""

    command_type = ActionCommandType.TASK_UPDATE_STATUS.value

    async def prepare(self, db: AsyncSession, *, payload: dict[str, Any], user_id: Any) -> PreparedCommand:
        target_status = _resolve_status(payload.get("to_status"))
        task = await _load_user_task(db, task_id=payload.get("task_id"), user_id=user_id)

        # 确定性预筛：FSM 合法性复用 task_service 单一真源（import 不复制）
        allowed = _VALID_TRANSITIONS.get(task.status)
        if allowed is None or target_status not in allowed:
            raise CommandValidationError(
                f"illegal task status transition {task.status.value} -> {target_status.value}",
                details={"from": task.status.value, "to": target_status.value},
            )

        stored: dict[str, Any] = {"task_id": str(task.id), "to_status": target_status.value}
        if payload.get("actual_minutes") is not None:
            stored["actual_minutes"] = int(payload["actual_minutes"])
        if payload.get("note") is not None:
            stored["note"] = str(payload["note"])[:2000]
        if payload.get("reason") is not None:
            stored["reason"] = str(payload["reason"])[:2000]

        before = _snapshot(task)
        after = dict(before)
        after["status"] = target_status.value
        risk_class, reversible = status_change_semantics(target_status)
        return PreparedCommand(
            command_type=self.command_type,
            subject_type="task",
            subject_id=str(task.id),
            subject_version_token=version_token(task.updated_at),
            payload=stored,
            diff=build_diff(before=before, after=after),
            summary=f"任务「{task.title}」状态 {before['status']} → {target_status.value}",
            risk_class=risk_class,
            reversible=reversible,
        )

    async def validate_subject(self, db: AsyncSession, *, proposal: ActionProposal) -> Task:
        task = await _load_user_task(db, task_id=proposal.subject_id, user_id=proposal.user_id, for_update=True)
        current_token = version_token(task.updated_at)
        if proposal.subject_version_token is not None and current_token != proposal.subject_version_token:
            from app.core.action_command import VersionConflictError

            raise VersionConflictError(
                "task was modified after this proposal was created (stale version)",
                details={
                    "subject_type": "task",
                    "subject_id": str(task.id),
                    "proposal_version_token": proposal.subject_version_token,
                    "current_version_token": current_token,
                    "hint": "refresh the proposal diff against current state and re-propose",
                },
            )
        return task

    async def execute(self, db: AsyncSession, *, proposal: ActionProposal) -> CommandEffects:
        task = await self.validate_subject(db, proposal=proposal)
        target_status = _resolve_status(proposal.payload.get("to_status"))
        before = _snapshot(task)
        payload = dict(proposal.payload or {})

        # belt-and-suspenders：执行前再验 FSM（版本 token 已保证无并发漂移）
        allowed = _VALID_TRANSITIONS.get(task.status)
        if allowed is None or target_status not in allowed:
            from app.core.action_command import VersionConflictError

            raise VersionConflictError(
                f"task state moved since proposal: {task.status.value} -> {target_status.value} now illegal",
                details={"from": task.status.value, "to": target_status.value},
            )

        # 路由到 TaskService 专用权威方法（状态迁移不走通用 update——TaskUpdate
        # 无 status 字段是房屋刻意设计：complete/pause/abandon 等各自携带全量
        # 副作用：plan 同步、galaxy spark、task.completed 事件等）。
        #
        # X-04 红线：actual_minutes 只透传实测值（payload 显式携带）；缺省传
        # None 由 TaskService.complete 从真实起止推算——**永不从 estimated 回填**。
        if target_status is TaskStatus.COMPLETED:
            raw_actual = payload.get("actual_minutes")
            actual_minutes = int(raw_actual) if raw_actual is not None else None
            updated = await TaskService.complete(db, task, actual_minutes, note=payload.get("note"))
        elif target_status is TaskStatus.IN_PROGRESS:
            if task.status is TaskStatus.PAUSED or task.status is TaskStatus.STUCK:
                updated = await TaskService.resume(db, task)
            else:
                updated = await TaskService.start(db, task)
        elif target_status is TaskStatus.PAUSED:
            updated = await TaskService.pause(db, task, reason=payload.get("reason"))
        elif target_status is TaskStatus.ABANDONED:
            updated = await TaskService.abandon(db, task, reason=payload.get("reason"))
        elif target_status is TaskStatus.STUCK:
            updated_task, _diagnosis = await TaskService.mark_stuck(db, task, stuck_point=payload.get("note"))
            updated = updated_task
        else:  # pragma: no cover — _VALID_TRANSITIONS 预筛已封闭词表
            raise CommandValidationError(f"unsupported target status {target_status!r}")

        after = _snapshot(updated)
        return CommandEffects(
            effects=[
                {
                    "kind": "task.status_changed",
                    "ref": f"task://{updated.id}",
                    "before": before.get("status"),
                    "after": after.get("status"),
                }
            ],
            subject_after=after,
            subject_version_token_after=version_token(updated.updated_at),
        )


class TaskUpdateFieldsCommand:
    """``task.update_fields`` —— 白名单字段批量修改提案（diff 可渲染）."""

    command_type = ActionCommandType.TASK_UPDATE_FIELDS.value

    async def prepare(self, db: AsyncSession, *, payload: dict[str, Any], user_id: Any) -> PreparedCommand:
        fields = payload.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise CommandValidationError("fields must be a non-empty object")
        illegal = sorted(set(fields) - TASK_FIELD_WHITELIST)
        if illegal:
            raise CommandValidationError(
                f"fields outside the proposal whitelist: {illegal}",
                details={"whitelist": sorted(TASK_FIELD_WHITELIST)},
            )

        task = await _load_user_task(db, task_id=payload.get("task_id"), user_id=user_id)
        try:
            normalized = _normalize_field_values(fields)
        except ValueError as exc:
            raise CommandValidationError(f"invalid field value: {exc}") from exc

        before = _snapshot(task)
        after = dict(before)
        for key, value in normalized.items():
            after[key] = value.isoformat() if isinstance(value, DateType) else value
        return PreparedCommand(
            command_type=self.command_type,
            subject_type="task",
            subject_id=str(task.id),
            subject_version_token=version_token(task.updated_at),
            payload={"task_id": str(task.id), "fields": {k: after.get(k) for k in normalized}},
            diff=build_diff(before=before, after=after),
            summary=f"任务「{task.title}」修改 {sorted(normalized)}",
            # 白名单字段修改可再改回（title/priority/due_date/…均为可逆编辑）
            risk_class="low",
            reversible=True,
        )

    async def validate_subject(self, db: AsyncSession, *, proposal: ActionProposal) -> Task:
        task = await _load_user_task(db, task_id=proposal.subject_id, user_id=proposal.user_id, for_update=True)
        current_token = version_token(task.updated_at)
        if proposal.subject_version_token is not None and current_token != proposal.subject_version_token:
            from app.core.action_command import VersionConflictError

            raise VersionConflictError(
                "task was modified after this proposal was created (stale version)",
                details={
                    "subject_type": "task",
                    "subject_id": str(task.id),
                    "proposal_version_token": proposal.subject_version_token,
                    "current_version_token": current_token,
                },
            )
        return task

    async def execute(self, db: AsyncSession, *, proposal: ActionProposal) -> CommandEffects:
        task = await self.validate_subject(db, proposal=proposal)
        before = _snapshot(task)
        fields = dict(proposal.payload.get("fields") or {})
        try:
            normalized = _normalize_field_values(fields)
        except ValueError as exc:
            raise CommandValidationError(f"invalid field value: {exc}") from exc
        update_in = TaskUpdate(**normalized)
        updated = await TaskService.update(db, task, update_in)
        after = _snapshot(updated)
        return CommandEffects(
            effects=[
                {
                    "kind": "task.fields_updated",
                    "ref": f"task://{updated.id}",
                    "changed_fields": sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k)),
                }
            ],
            subject_after=after,
            subject_version_token_after=version_token(updated.updated_at),
        )


class TaskCreateBatchCommand:
    """``task.create_batch`` —— 批量建任务提案（milestone 式推荐；无 subject）."""

    command_type = ActionCommandType.TASK_CREATE_BATCH.value

    async def prepare(self, db: AsyncSession, *, payload: dict[str, Any], user_id: Any) -> PreparedCommand:
        tasks = payload.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            raise CommandValidationError("tasks must be a non-empty list")
        if len(tasks) > 20:
            raise CommandValidationError("batch size exceeds 20")

        normalized_items: list[dict[str, Any]] = []
        for index, item in enumerate(tasks):
            if not isinstance(item, dict) or not str(item.get("title") or "").strip():
                raise CommandValidationError(f"tasks[{index}].title is required")
            normalized = dict(item)
            normalized["title"] = str(normalized["title"]).strip()[:255]
            normalized.setdefault("type", "learning")  # TaskCreate 必填；默认学习型
            normalized_items.append(normalized)

        # 契约预筛：TaskCreate pydantic 全量校验（类型/范围在此 422，不留到 commit）
        try:
            for item in normalized_items:
                TaskCreate(**item)
        except ValidationError as exc:
            raise CommandValidationError(
                f"invalid task spec: {exc.errors()[0].get('msg', 'validation failed')}"
            ) from exc

        after = {"tasks": [{"title": t["title"]} for t in normalized_items], "count": len(normalized_items)}
        return PreparedCommand(
            command_type=self.command_type,
            subject_type=None,
            subject_id=None,
            subject_version_token=None,
            payload={"tasks": normalized_items},
            diff=build_diff(before=None, after=after),
            summary=f"创建 {len(normalized_items)} 个任务："
            + "、".join(t["title"] for t in normalized_items[:3])
            + ("…" if len(normalized_items) > 3 else ""),
            risk_class="low",
            reversible=False,  # 建出的任务需要显式清理，不可一键回滚
        )

    async def validate_subject(self, db: AsyncSession, *, proposal: ActionProposal) -> None:
        return None  # 创建型命令无 subject / 无版本冲突面

    async def execute(self, db: AsyncSession, *, proposal: ActionProposal) -> CommandEffects:
        created_refs: list[dict[str, Any]] = []
        for item in proposal.payload.get("tasks", []):
            try:
                spec = TaskCreate(**item)
            except ValidationError as exc:
                raise CommandValidationError(f"invalid task spec at commit: {exc}") from exc
            task = await TaskService.create(db, spec, user_id=proposal.user_id)
            created_refs.append({"ref": f"task://{task.id}", "title": task.title})
        return CommandEffects(
            effects=[
                {"kind": "task.created_batch", "refs": [c["ref"] for c in created_refs], "count": len(created_refs)}
            ],
            subject_after={"created": created_refs},
            subject_version_token_after=None,
        )


def _normalize_field_values(fields: dict[str, Any]) -> dict[str, Any]:
    """白名单字段的类型归一（date ISO → date；其余原样交给 TaskUpdate 校验）."""
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        if key == "due_date" and isinstance(value, str):
            normalized[key] = DateType.fromisoformat(value)
        else:
            normalized[key] = value
    return normalized


#: 命令处理器注册表（封闭：与 ActionCommandType 一一对应；新增 = 契约变更）
COMMAND_HANDLERS: dict[str, Any] = {
    TaskUpdateStatusCommand.command_type: TaskUpdateStatusCommand(),
    TaskUpdateFieldsCommand.command_type: TaskUpdateFieldsCommand(),
    TaskCreateBatchCommand.command_type: TaskCreateBatchCommand(),
}


def get_command_handler(command_type: str) -> Any:
    handler = COMMAND_HANDLERS.get(str(command_type))
    if handler is None:
        raise CommandValidationError(
            f"unknown command_type {command_type!r} (closed vocabulary)",
            details={"known": sorted(COMMAND_HANDLERS)},
        )
    return handler
