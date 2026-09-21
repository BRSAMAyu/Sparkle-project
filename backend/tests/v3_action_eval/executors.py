"""X-10 · 场景执行器 —— 每个场景走真实服务层 + 真实 DB，产出六元组.

纪律：
- **只调用真实服务**（ActionCommandService / AgentRunService / TaskService /
  allocation policy / outcome capture+ledger），零 LLM、零 mock 领域逻辑；
- 每个执行步记录 ``{op, ok, error, elapsed_ms}``（latency/cost 的原始事实面）；
- 执行器**不做判定**：判定在 ``verdicts.py``，对 DB 真相独立复算（执行结果
  只是六元组的记录面，不是证据面）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from app.core.action_command import (
    AuthorizationDeniedError,
    CommandValidationError,
    ProposalExpiredError,
    ProposalNotPendingError,
    VersionConflictError,
)
from app.core.outcome_ledger import OutcomeSource, derive_outcome_id
from app.core.run_state_machine import RunStatus, RunWaitKind
from app.models.focus import FocusSession
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.action_allocation_policy import (
    ActionAllocationPolicy,
    AllocationFactors,
    decide_allocation,
    vet_agent_offer,
)
from app.services.action_authorization import (
    authorize_commit,
    decide_authorization_mode,
    record_confirmation,
)
from app.services.action_command_service import ActionCommandService
from app.services.agent_run_service import (
    AgentRunService,
    InvalidResumeTargetError,
    RunNotAwaitingUserStepError,
    RunStepPlanConflictError,
)
from app.services.outcome_capture_service import (
    build_outcome_recorded_payload,
    build_run_receipt_outcome,
    build_task_outcome_capture,
)
from app.services.outcome_ledger_service import OutcomeLedgerService
from app.services.task_service import TaskService

from .dbfixture import ScenarioContext, backdate_proposal_expiry, seed_task

EXPECTED_ERROR_CLASSES: tuple[type[Exception], ...] = (
    AuthorizationDeniedError,
    CommandValidationError,
    ProposalExpiredError,
    ProposalNotPendingError,
    VersionConflictError,
    RunNotAwaitingUserStepError,
    RunStepPlanConflictError,
    InvalidResumeTargetError,
    ValueError,
)


@dataclass
class StepLog:
    """一次服务调用的执行记录（六元组 execution 面的原子）。"""

    op: str
    ok: bool
    error: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0

    def to_payload(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "ok": self.ok,
            "error": self.error,
            "detail": self.detail,
            "elapsed_ms": round(self.elapsed_ms, 3),
        }


@dataclass
class ScenarioRun:
    """一个场景的执行过程容器（executor 写入，runner 序列化）。"""

    steps: list[StepLog] = field(default_factory=list)
    decision: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)

    async def call(self, ctx: ScenarioContext, op: str, fn, *, expect_error: bool = False, **detail: Any):
        """执行一次服务调用（async/sync 均可）并记录（expected error 也算执行成功）。"""
        ctx.record_op(op)
        started = time.perf_counter()
        try:
            value = fn()
            if hasattr(value, "__await__"):
                value = await value
        except EXPECTED_ERROR_CLASSES as exc:  # noqa: BLE001 — 预期错误也是执行事实
            elapsed = (time.perf_counter() - started) * 1000
            self.steps.append(
                StepLog(
                    op=op,
                    ok=expect_error,
                    error=type(exc).__name__,
                    detail={"expected": expect_error, **detail},
                    elapsed_ms=elapsed,
                )
            )
            return exc
        except Exception as exc:  # noqa: BLE001 — 意外异常如实记录，判定阶段判 fail
            elapsed = (time.perf_counter() - started) * 1000
            self.steps.append(
                StepLog(op=op, ok=False, error=f"unexpected:{type(exc).__name__}", detail=detail, elapsed_ms=elapsed)
            )
            raise
        elapsed = (time.perf_counter() - started) * 1000
        self.steps.append(StepLog(op=op, ok=True, detail=detail, elapsed_ms=elapsed))
        return value


def _timed(fn):
    started = time.perf_counter()
    value = fn()
    return value, (time.perf_counter() - started) * 1000


# ---------------------------------------------------------------------------
# family: allocation
# ---------------------------------------------------------------------------


async def execute_allocation(scenario, ctx: ScenarioContext) -> ScenarioRun:
    run = ScenarioRun()
    factors_raw = dict(scenario.inputs.get("factors") or {})
    offer_kind = scenario.inputs.get("offer_kind")

    async def _decide():
        factors = AllocationFactors.coerce(factors_raw)
        decision = decide_allocation(factors)
        payload = {
            "decision_id": decision.decision_id(factors),
            **decision.to_dict(),
        }
        run.decision = payload
        if offer_kind is not None:
            stale_decision = None
            if scenario.inputs.get("stale_decision_requires_approval") is False:
                stale_decision = decide_allocation({})  # 陈旧/异因子决策旗标（错配防御样本）
            verdict = vet_agent_offer(offer_kind, factors, stale_decision)
            run.decision["offer"] = {
                "kind": offer_kind,
                "allowed": verdict.allowed,
                "reason": verdict.reason,
                "requires_human_approval": verdict.requires_human_approval,
                "suggested_downgrade": verdict.suggested_downgrade,
            }
        return decision

    await run.call(ctx, "decide_allocation", _decide)
    run.result = {"mode": run.decision.get("mode"), "offer": run.decision.get("offer")}
    run.outcome = {"kind": "decision_only", "deterministic": True}
    return run


# ---------------------------------------------------------------------------
# family: authorization
# ---------------------------------------------------------------------------


async def execute_authorization(scenario, ctx: ScenarioContext) -> ScenarioRun:
    run = ScenarioRun()
    path = scenario.inputs.get("path", "pure")

    if path == "pure":
        pure = dict(scenario.inputs.get("pure") or {})

        async def _decide():
            decision = decide_authorization_mode(
                risk_class=pure.get("risk_class"),
                reversible=pure.get("reversible"),
                requires_human_approval=bool(pure.get("requires_human_approval")),
                user_auto_grant=bool(pure.get("user_auto_grant")),
            )
            run.decision = dict(decision)
            return decision

        await run.call(ctx, "decide_authorization_mode", _decide)
        run.result = {"authorization_mode": run.decision.get("mode"), "reason_codes": run.decision.get("reason_codes")}
        run.outcome = {"kind": "authorization_decision"}
        return run

    if path == "commit":
        auth_input = dict(scenario.inputs.get("authorization") or {})

        async def _maybe_confirm():
            if scenario.inputs.get("confirmed"):
                return record_confirmation(auth_input, confirmed_by="user")
            return dict(auth_input)

        auth = await run.call(ctx, "record_confirmation_if_any", _maybe_confirm)
        allowed = await run.call(ctx, "authorize_commit", lambda: authorize_commit(auth))
        if isinstance(allowed, AuthorizationDeniedError):
            run.result = {"commit_allowed": False}
        else:
            run.result = {"commit_allowed": True, "commit_reason": allowed.get("commit_reason")}
        if scenario.inputs.get("also_missing_record"):

            async def _missing():
                return authorize_commit(None)

            missing = await run.call(ctx, "authorize_commit_missing_record", _missing, expect_error=True)
            run.result["missing_record_denied"] = isinstance(missing, AuthorizationDeniedError)
        run.decision = {"mode": auth_input.get("mode"), "confirmed": bool(scenario.inputs.get("confirmed"))}
        run.outcome = {"kind": "commit_gate"}
        return run

    # service path：真实 ActionCommandService（授权输入服务端自查）
    auto_grant = bool(scenario.inputs.get("user_auto_grant"))
    execute_if_authorized = bool(scenario.inputs.get("execute_if_authorized"))
    command = dict(scenario.inputs.get("command") or {})
    task = await seed_task(ctx, scenario.inputs.get("seed_task"))

    async def _create():
        return await ActionCommandService(ctx.session).create_proposal(
            user_id=ctx.user.id,
            command_type=command["type"],
            payload=_command_payload(command, task),
            source="task",
            execute_if_authorized=execute_if_authorized,
        )

    created = await run.call(ctx, "create_proposal", _create)
    proposal = created.proposal
    run.decision = dict(proposal.authorization or {})
    final = await _refresh_proposal(ctx, proposal.id)
    run.result = {
        "authorization_mode": (final.authorization or {}).get("mode"),
        "proposal_status": final.status if isinstance(final.status, str) else final.status.value,
        "task_status": await _task_status(ctx, task),
        "task_title": await _task_field(ctx, task, "title"),
        "receipt_present": bool(final.receipt),
    }
    run.outcome = {"kind": "authorization_service_path", "executed": run.result["proposal_status"] == "COMMITTED"}
    return run


# ---------------------------------------------------------------------------
# family: proposal lifecycle
# ---------------------------------------------------------------------------


def _command_payload(command: dict[str, Any], task: Task | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": command.get("type")}
    if command["type"] == "task.update_status":
        return {"task_id": str(task.id), "to_status": command["to_status"]}
    if command["type"] == "task.update_fields":
        return {"task_id": str(task.id), "fields": dict(command["fields"])}
    if command["type"] == "task.create_batch":
        return {"tasks": list(command["tasks"])}
    raise ValueError(f"unknown command type {command.get('type')!r}")


async def _refresh_proposal(ctx: ScenarioContext, proposal_id) -> Any:
    from sqlalchemy import select as _select

    from app.models.action_proposal import ActionProposal

    row = (
        await ctx.session.execute(_select(ActionProposal).where(ActionProposal.id == proposal_id))
    ).scalar_one()
    await ctx.session.refresh(row)
    return row


async def _task_row(ctx: ScenarioContext, task: Task | None) -> Task | None:
    if task is None:
        return None
    await ctx.session.refresh(task)
    return task


async def _task_status(ctx: ScenarioContext, task: Task | None) -> str | None:
    row = await _task_row(ctx, task)
    if row is None:
        return None
    return row.status.value if hasattr(row.status, "value") else str(row.status)


async def _task_field(ctx: ScenarioContext, task: Task | None, name: str):
    row = await _task_row(ctx, task)
    return getattr(row, name) if row is not None else None


async def _count_proposals(ctx: ScenarioContext) -> int:
    from app.models.action_proposal import ActionProposal

    rows = (
        await ctx.session.execute(
            select(ActionProposal).where(ActionProposal.user_id == ctx.user.id, ActionProposal.deleted_at.is_(None))
        )
    ).scalars().all()
    return len(list(rows))


async def _count_transitions(ctx: ScenarioContext, proposal_id) -> int:
    from app.models.action_proposal import ActionProposalTransition

    rows = (
        await ctx.session.execute(
            select(ActionProposalTransition).where(ActionProposalTransition.proposal_id == proposal_id)
        )
    ).scalars().all()
    return len(list(rows))


async def execute_proposal(scenario, ctx: ScenarioContext) -> ScenarioRun:
    run = ScenarioRun()
    op = scenario.inputs["op"]
    command = dict(scenario.inputs.get("command") or {})
    key = scenario.inputs.get("idempotency_key")
    task = await seed_task(ctx, scenario.inputs.get("seed_task"))
    service = ActionCommandService(ctx.session)
    proposal = None
    result: dict[str, Any] = {}

    if op in {"approve", "approve_twice"}:
        created = await run.call(
            ctx,
            "create_proposal",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
                idempotency_key=key,
            ),
        )
        proposal = created.proposal
        result["created"] = created.created
        first = await run.call(
            ctx, "approve", lambda: service.approve(proposal.id, user_id=ctx.user.id, actor="user")
        )
        result["first_applied"] = first.applied
        if op == "approve_twice":
            second = await run.call(
                ctx,
                "approve_replay",
                lambda: service.approve(proposal.id, user_id=ctx.user.id, actor="user"),
                expect_error=False,
            )
            result["second_applied"] = second.applied
            result["second_already_committed"] = second.already_committed
            result["transitions_count"] = await _count_transitions(ctx, proposal.id)
    elif op in {"create_twice_same_key", "create_conflicting_key"}:
        payload = _command_payload(command, task)
        second_payload = (
            _command_payload(dict(scenario.inputs["second_command"]), task)
            if op == "create_conflicting_key"
            else payload
        )
        first = await run.call(
            ctx,
            "create_proposal_first",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=payload,
                source="task",
                idempotency_key=key,
            ),
        )
        proposal = first.proposal
        result["first_created"] = first.created
        second = await run.call(
            ctx,
            "create_proposal_second",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=second_payload,
                source="task",
                idempotency_key=key,
            ),
        )
        result["second_created"] = second.created
        result["proposals_count"] = await _count_proposals(ctx)
    elif op == "reject":
        created = await run.call(
            ctx,
            "create_proposal",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
            ),
        )
        proposal = created.proposal
        rejected = await run.call(
            ctx, "reject", lambda: service.reject(proposal.id, user_id=ctx.user.id, reason=None)
        )
        result["applied"] = rejected.applied
    elif op == "cancel_twice":
        created = await run.call(
            ctx,
            "create_proposal",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
            ),
        )
        proposal = created.proposal
        cancelled = await run.call(ctx, "cancel", lambda: service.cancel(proposal.id, user_id=ctx.user.id))
        result["first_applied"] = cancelled.applied
        again = await run.call(ctx, "cancel_replay", lambda: service.cancel(proposal.id, user_id=ctx.user.id))
        result["second_applied"] = again.applied
    elif op == "expire_then_approve":
        created = await run.call(
            ctx,
            "create_proposal",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
                ttl_seconds=60,
            ),
        )
        proposal = created.proposal
        await run.call(
            ctx,
            "backdate_expiry_clock",
            lambda: backdate_proposal_expiry(ctx, proposal.id, seconds=120),
        )
        expired = await run.call(
            ctx,
            "approve_expired",
            lambda: service.approve(proposal.id, user_id=ctx.user.id, actor="user"),
            expect_error=True,
        )
        result["error"] = type(expired).__name__ if isinstance(expired, Exception) else None
    elif op == "sweep":
        created = await run.call(
            ctx,
            "create_proposal",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
                ttl_seconds=60,
            ),
        )
        proposal = created.proposal
        await run.call(
            ctx,
            "backdate_expiry_clock",
            lambda: backdate_proposal_expiry(ctx, proposal.id, seconds=120),
        )
        result["sweep_count"] = await run.call(
            ctx, "expire_stale_proposals", lambda: service.expire_stale_proposals(user_id=ctx.user.id)
        )
    elif op == "version_conflict":
        created = await run.call(
            ctx,
            "create_proposal",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
            ),
        )
        proposal = created.proposal
        interfere = dict(scenario.inputs.get("interfere") or {})
        fresh_task = await _task_row(ctx, task)
        if interfere.get("op") == "pause":
            await run.call(
                ctx,
                "interfere_pause",
                lambda: TaskService.pause(ctx.session, fresh_task, reason=interfere.get("reason")),
            )
        conflict = await run.call(
            ctx,
            "approve_stale",
            lambda: service.approve(proposal.id, user_id=ctx.user.id, actor="user"),
            expect_error=True,
        )
        result["error"] = type(conflict).__name__ if isinstance(conflict, Exception) else None
    elif op == "approve_after_reject":
        created = await run.call(
            ctx,
            "create_proposal",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
            ),
        )
        proposal = created.proposal
        await run.call(ctx, "reject", lambda: service.reject(proposal.id, user_id=ctx.user.id, reason=None))
        denied = await run.call(
            ctx,
            "approve_terminal",
            lambda: service.approve(proposal.id, user_id=ctx.user.id, actor="user"),
            expect_error=True,
        )
        result["error"] = type(denied).__name__ if isinstance(denied, Exception) else None
    elif op == "whitelist_violation":
        violation = await run.call(
            ctx,
            "create_proposal_whitelist_violation",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type=command["type"],
                payload=_command_payload(command, task),
                source="task",
            ),
            expect_error=True,
        )
        result["error"] = type(violation).__name__ if isinstance(violation, Exception) else None
        result["proposals_count"] = await _count_proposals(ctx)
    else:  # pragma: no cover — fixture 封闭集
        raise ValueError(f"unknown proposal op {op!r}")

    if proposal is not None:
        final = await _refresh_proposal(ctx, proposal.id)
        result["proposal_status"] = final.status if isinstance(final.status, str) else final.status.value
        result["receipt_present"] = bool(final.receipt)
        receipt_effects = (final.receipt or {}).get("effects")
        result["receipt_effects_count"] = len(receipt_effects) if isinstance(receipt_effects, list) else 0
        result["subjectless"] = final.subject_id is None
    result["task_status"] = await _task_status(ctx, task)
    result["task_title"] = await _task_field(ctx, task, "title")
    completed_row = await _task_row(ctx, task)
    result["actual_minutes"] = getattr(completed_row, "actual_minutes", None) if completed_row else None
    result["estimated_minutes"] = getattr(completed_row, "estimated_minutes", None) if completed_row else None
    if op in {"approve", "approve_twice"} and completed_row is not None and result.get("proposal_status") == "COMPLETED":
        created_count = (
            await ctx.session.execute(
                select(Task).where(Task.user_id == ctx.user.id, Task.deleted_at.is_(None))
            )
        ).scalars().all()
        result["tasks_created"] = len(list(created_count))
    run.decision = dict(proposal.authorization or {}) if proposal is not None else {}
    run.result = result
    run.outcome = {
        "kind": "proposal_terminal_state",
        "terminal_reached": result.get("proposal_status") in {"COMMITTED", "REJECTED", "CANCELLED", "EXPIRED"},
        "false_success_risk": result.get("proposal_status") == "COMMITTED"
        and result.get("task_status") not in {None, "COMPLETED", "PENDING", "PAUSED"}
        and command.get("type") == "task.update_status",
    }
    return run


# ---------------------------------------------------------------------------
# family: run steps（X-07）
# ---------------------------------------------------------------------------

_DEFAULT_TWO_STEP_PLAN = [
    {
        "step_id": "s1",
        "ordinal": 1,
        "owner": "agent",
        "completion_condition": {"kind": "agent_output"},
    },
    {
        "step_id": "s2",
        "ordinal": 2,
        "owner": "human",
        "completion_condition": {"kind": "user_confirmation"},
    },
]


async def _count_run_transitions(ctx: ScenarioContext, run_id, event_name: str | None = None) -> int:
    from app.models.agent_run import AgentRunTransition

    stmt = select(AgentRunTransition).where(AgentRunTransition.run_id == run_id)
    if event_name is not None:
        stmt = stmt.where(AgentRunTransition.event_name == event_name)
    rows = (await ctx.session.execute(stmt)).scalars().all()
    return len(list(rows))


async def execute_run_steps(scenario, ctx: ScenarioContext) -> ScenarioRun:
    run = ScenarioRun()
    service = AgentRunService(ctx.session)
    steps_spec = scenario.inputs.get("steps") or _DEFAULT_TWO_STEP_PLAN
    run.decision = {
        "step_plan": [
            {"step_id": s["step_id"], "owner": s["owner"], "completion": s.get("completion_condition", {})}
            for s in steps_spec
        ]
    }
    created = await run.call(
        ctx,
        "create_run",
        lambda: service.create_run(
            user_id=ctx.user.id,
            objective=f"X-10 {scenario.scenario_id}",
            kind="execution",
            steps=[dict(s) for s in steps_spec],
        ),
    )
    agent_run = created.run
    result: dict[str, Any] = {}
    user_step_replay: dict[str, Any] = {}
    first_user_complete_step: str | None = None

    for op_spec in scenario.inputs.get("ops", []):
        op = op_spec["op"]
        expect_error = bool(op_spec.get("expect_error"))
        if op == "define":
            await run.call(ctx, "define_run_steps", lambda: service.define_run_steps(agent_run.id, steps=steps_spec))
        elif op == "define_same":
            await run.call(
                ctx,
                "define_run_steps_replay",
                lambda: service.define_run_steps(agent_run.id, steps=steps_spec),
            )
        elif op == "define_conflict":
            conflict_steps = [dict(s) for s in op_spec.get("steps", [])]
            conflict = await run.call(
                ctx,
                "define_run_steps_conflict",
                lambda: service.define_run_steps(agent_run.id, steps=conflict_steps),
                expect_error=True,
            )
            result["error"] = type(conflict).__name__ if isinstance(conflict, Exception) else None
        elif op == "start":
            await run.call(
                ctx,
                "transition_running",
                lambda: service.transition(agent_run.id, RunStatus.RUNNING, user_id=ctx.user.id, actor="system"),
            )
        elif op == "agent_complete":
            done = await run.call(
                ctx,
                "complete_agent_step",
                lambda: service.complete_agent_step(
                    agent_run.id,
                    step_id=op_spec["step_id"],
                    user_id=ctx.user.id,
                    artifact_refs=op_spec.get("artifacts"),
                ),
                expect_error=expect_error,
            )
            if isinstance(done, Exception):
                result["error"] = type(done).__name__
        elif op == "await":
            wait_expires = None
            if op_spec.get("wait_expires_offset_sec") is not None:
                wait_expires = datetime.now(UTC).replace(tzinfo=None) + timedelta(
                    seconds=float(op_spec["wait_expires_offset_sec"])
                )
            awaited = await run.call(
                ctx,
                "await_user_step",
                lambda: service.await_user_step(
                    agent_run.id,
                    step_id=op_spec["step_id"],
                    user_id=ctx.user.id,
                    prompt=op_spec.get("prompt"),
                    wait_expires_at=wait_expires,
                ),
                expect_error=expect_error,
            )
            if isinstance(awaited, Exception):
                result["error"] = type(awaited).__name__
        elif op == "user_complete":
            done = await run.call(
                ctx,
                "complete_user_step",
                lambda: service.complete_user_step(
                    agent_run.id,
                    step_id=op_spec["step_id"],
                    user_id=ctx.user.id,
                    idempotency_key=op_spec["idempotency_key"],
                    action=op_spec.get("action", "confirm"),
                    note=op_spec.get("note"),
                ),
                expect_error=expect_error,
            )
            if isinstance(done, Exception):
                result["error"] = type(done).__name__
            else:
                if first_user_complete_step is None:
                    first_user_complete_step = op_spec["step_id"]
                    result["applied"] = done.applied
                else:
                    user_step_replay = {"replay": done.replay, "applied": done.applied}
        elif op == "cancel":
            await run.call(
                ctx,
                "cancel_run",
                lambda: service.cancel(agent_run.id, user_id=ctx.user.id, reason=op_spec.get("reason", "user_cancelled")),
            )
        elif op == "sweep":
            sweep = await run.call(ctx, "recover_stale_runs", lambda: service.recover_stale_runs())
            result["sweep_actions"] = [a.get("kind") for a in sweep.get("actions", [])]
        elif op == "resume_bad_target":
            bad = await run.call(
                ctx,
                "resume_forbidden_target",
                lambda: service.resume(
                    agent_run.id, user_id=ctx.user.id, to_status=op_spec.get("to_status", "SUCCEEDED")
                ),
                expect_error=True,
            )
            result["error"] = type(bad).__name__ if isinstance(bad, Exception) else None
        elif op == "cold_start_read":
            # 冷启动：新 session（同引擎新连接）+ 新 service 实例，零内存态推导
            cold_service = AgentRunService(ctx.fresh_session())
            projection = await run.call(
                ctx,
                "cold_start_get_run",
                lambda: cold_service.get_run(agent_run.id, user_id=ctx.user.id),
            )
            cold_payload = projection.to_dict()
            result["cold_start_awaiting"] = cold_payload.get("awaiting_step")
        else:  # pragma: no cover
            raise ValueError(f"unknown run op {op!r}")

    final = await service.get_run(agent_run.id, user_id=ctx.user.id)
    payload = final.to_dict()
    result["run_status"] = payload["status"]
    result["terminal_reason"] = payload.get("terminal_reason")
    result["wait_kind"] = payload.get("wait_kind")
    result["resume_count"] = await _count_run_transitions(ctx, agent_run.id, "run.user_resumed")
    result["user_resumed_events"] = await _count_run_transitions(ctx, agent_run.id, "run.user_resumed")
    completions = {s["step_id"]: (s.get("completion") or {}) for s in final.steps or []}
    if "s1" in completions:
        result["step_completed_s1"] = (completions["s1"] or {}).get("by")
        result["step_completed_s1_key"] = (completions["s1"] or {}).get("idempotency_key")
    if "s2" in completions:
        result["step_completed_s2_by"] = (completions["s2"] or {}).get("by")
    step_done = [bool((s.get("completion") or {})) for s in final.steps or []]
    result["step_completed"] = any(step_done)
    result["plan_owner_unchanged"] = (final.steps or [{}])[0].get("owner")
    awaiting = payload.get("awaiting_step")
    result["awaiting_step_id"] = awaiting.get("step_id") if awaiting else None
    result["awaiting_state"] = awaiting.get("state") if awaiting else None
    result["awaiting_prompt"] = awaiting.get("prompt") if awaiting else None
    if user_step_replay:
        result["second_replay"] = user_step_replay.get("replay")
        result["second_applied"] = user_step_replay.get("applied")
    if first_user_complete_step is not None:
        completion = completions.get(first_user_complete_step) or {}
        result["first_key_recorded"] = completion.get("idempotency_key")
    run.result = result
    run.outcome = {
        "kind": "run_step_state",
        "awaiting_projection": awaiting,
        "resume_exactly_once": result["resume_count"] == 1,
    }
    return run


# ---------------------------------------------------------------------------
# family: outcome（X-08）
# ---------------------------------------------------------------------------


async def _seed_knowledge_node(ctx: ScenarioContext) -> Any:
    node = KnowledgeNode(name=f"X-10 node {uuid4().hex[:8]}", importance_level=2, is_seed=False)
    ctx.session.add(node)
    await ctx.session.commit()
    await ctx.session.refresh(node)
    ctx.extras["_knowledge_node_id"] = node.id
    return node


async def _ledger_task_entry(ctx: ScenarioContext, task_id) -> Any:
    ledger = OutcomeLedgerService(ctx.session)
    page = await ledger.query(user_id=ctx.user.id, source=OutcomeSource.TASK_COMPLETION, limit=50)
    for entry in page.items:
        if str(entry.source_id) == str(task_id):
            return entry
    return None


async def execute_outcome(scenario, ctx: ScenarioContext) -> ScenarioRun:
    run = ScenarioRun()
    op = scenario.inputs["op"]
    result: dict[str, Any] = {}
    task = None

    if op == "complete_task":
        spec = dict(scenario.inputs.get("seed_task") or {})
        declared = spec.get("completion_evidence")
        task = await seed_task(ctx, spec)
        complete = dict(scenario.inputs.get("complete") or {})
        evidence = None
        if declared:
            # 场景 o02：完成时用户再次提供同声明（ref 不可解析）——声明面
            evidence = [
                {"evidence_kind": d["evidence_kind"], "ref": d.get("ref"), "description": d.get("description")}
                for d in declared
            ]
        completed = await run.call(
            ctx,
            "task_service_complete",
            lambda: TaskService.complete(
                ctx.session, task, complete.get("actual_minutes"), evidence=evidence
            ),
        )
        capture, ms = _timed(lambda: build_task_outcome_capture(completed))
        run.steps.append(StepLog(op="build_task_outcome_capture", ok=True, elapsed_ms=ms))
        result.update(
            {
                "outcome_id": capture.outcome_id,
                "outcome_polarity": capture.polarity.value,
                "outcome_captured": True,
            }
        )
        entry = await run.call(ctx, "ledger_query", lambda: _ledger_task_entry(ctx, task.id))
        result["ledger_entry_present"] = entry is not None
        result["truth_class"] = entry.truth_class.value if entry is not None else None
        result["declared_preserved"] = bool(completed.completion_evidence)
        run.decision = {"terminal_action": "complete", "provided_evidence": bool(evidence)}
    elif op == "complete_with_run":
        task = await seed_task(ctx, scenario.inputs.get("seed_task"))
        run_svc = AgentRunService(ctx.session)
        agent_run = (
            await run.call(
                ctx,
                "create_run",
                lambda: run_svc.create_run(
                    user_id=ctx.user.id,
                    objective="X-10 receipt evidence run",
                    kind="execution",
                    task_id=task.id,
                ),
            )
        ).run
        await run.call(
            ctx,
            "run_to_succeeded",
            lambda: _drive_run_terminal(run_svc, agent_run.id, ctx.user.id, "SUCCEEDED"),
        )
        complete = dict(scenario.inputs.get("complete") or {})
        await run.call(
            ctx,
            "task_service_complete",
            lambda: TaskService.complete(ctx.session, task, complete.get("actual_minutes")),
        )
        final_task = await _task_row(ctx, task)
        capture, ms = _timed(lambda: build_task_outcome_capture(final_task))
        run.steps.append(StepLog(op="build_task_outcome_capture", ok=True, elapsed_ms=ms))
        result["outcome_polarity"] = capture.polarity.value
        entry = await run.call(ctx, "ledger_query", lambda: _ledger_task_entry(ctx, task.id))
        result["truth_class"] = entry.truth_class.value if entry is not None else None
        result["run_receipt_materialized"] = bool(
            entry is not None
            and any(e.ref and e.ref.startswith("agent_run://") for e in entry.evidence)
        )
        run.decision = {"terminal_action": "complete_with_run_receipt"}
    elif op == "complete_with_focus":
        task = await seed_task(ctx, scenario.inputs.get("seed_task"))
        focus_minutes = int(scenario.inputs.get("focus_minutes") or 0)
        now = datetime.now(UTC).replace(tzinfo=None)
        ctx.session.add(
            FocusSession(
                user_id=ctx.user.id,
                task_id=task.id,
                start_time=now - timedelta(minutes=focus_minutes),
                end_time=now,
                duration_minutes=focus_minutes,
            )
        )
        await ctx.session.commit()
        complete = dict(scenario.inputs.get("complete") or {})
        await run.call(
            ctx,
            "task_service_complete",
            lambda: TaskService.complete(ctx.session, task, complete.get("actual_minutes")),
        )
        entry = await run.call(ctx, "ledger_query", lambda: _ledger_task_entry(ctx, task.id))
        result["truth_class"] = entry.truth_class.value if entry is not None else None
        result["outcome_polarity"] = entry.polarity.value if entry is not None else None
        run.decision = {"terminal_action": "complete_with_focus_observation"}
    elif op == "abandon_task":
        task = await seed_task(ctx, scenario.inputs.get("seed_task"))
        abandon = dict(scenario.inputs.get("abandon") or {})
        abandoned = await run.call(
            ctx,
            "task_service_abandon",
            lambda: TaskService.abandon(ctx.session, task, reason=abandon.get("reason", "x10")),
        )
        capture, ms = _timed(lambda: build_task_outcome_capture(abandoned))
        run.steps.append(StepLog(op="build_task_outcome_capture", ok=True, elapsed_ms=ms))
        result["outcome_polarity"] = capture.polarity.value
        result["outcome_captured"] = True
        entry = await run.call(ctx, "ledger_query", lambda: _ledger_task_entry(ctx, task.id))
        result["ledger_entry_present"] = entry is not None
        result["truth_class"] = entry.truth_class.value if entry is not None else None
        run.decision = {"terminal_action": "abandon"}
    elif op == "terminalize_run":
        run_svc = AgentRunService(ctx.session)
        spec = dict(scenario.inputs.get("seed_run") or {})
        agent_run = (
            await run.call(
                ctx,
                "create_run",
                lambda: run_svc.create_run(user_id=ctx.user.id, objective=spec.get("objective", "X-10"), kind="execution"),
            )
        ).run
        terminal = scenario.inputs.get("run_terminal", "FAILED")
        await run.call(
            ctx,
            f"run_to_{str(terminal).lower()}",
            lambda: _drive_run_terminal(run_svc, agent_run.id, ctx.user.id, terminal),
        )
        fresh = await run_svc.get_run(agent_run.id, user_id=ctx.user.id)
        capture, ms = _timed(lambda: build_run_receipt_outcome(fresh))
        run.steps.append(StepLog(op="build_run_receipt_outcome", ok=True, elapsed_ms=ms))
        result["run_outcome_polarity"] = capture.polarity.value
        result["never_positive"] = capture.polarity.value != "positive"
        run.decision = {"terminal_action": f"run_{str(terminal).lower()}"}
    elif op == "derive_id_twice":
        source_id = uuid4()
        first, ms1 = _timed(lambda: derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=source_id))
        second, ms2 = _timed(lambda: derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=source_id))
        run.steps.append(StepLog(op="derive_outcome_id", ok=True, elapsed_ms=ms1 + ms2))
        result["ids_equal"] = first == second
        result["id_prefix"] = first[:5]
        run.decision = {"terminal_action": "idempotency_probe"}
    elif op == "build_event_payload":
        task = await seed_task(ctx, scenario.inputs.get("seed_task"))
        complete = dict(scenario.inputs.get("complete") or {})
        completed = await run.call(
            ctx,
            "task_service_complete",
            lambda: TaskService.complete(ctx.session, task, complete.get("actual_minutes")),
        )
        capture, ms = _timed(lambda: build_task_outcome_capture(completed))
        payload, ms2 = _timed(lambda: build_outcome_recorded_payload(capture))
        run.steps.append(StepLog(op="build_outcome_recorded_payload", ok=True, elapsed_ms=ms + ms2))
        result["event_name"] = payload.get("event_type")
        result["polarity"] = payload.get("polarity")
        result["content_free"] = _payload_is_content_free(payload)
        run.decision = {"terminal_action": "event_payload_probe"}
        run.outcome["event_payload"] = payload
    else:  # pragma: no cover
        raise ValueError(f"unknown outcome op {op!r}")

    run.result = result
    if not run.outcome:
        run.outcome = {"kind": "outcome_capture", "ledger_entry_present": result.get("ledger_entry_present")}
    return run


def _payload_is_content_free(payload: dict[str, Any]) -> bool:
    """事件载荷内容纪律：只允许 ids/极性/引用/schema 键（无结果本体、无用户内容）。"""
    allowed_prefixes = ("correlation_",)
    allowed_keys = {
        "event_type",
        "schema",
        "outcome_ledger_schema",
        "outcome_id",
        "outcome_key",
        "source",
        "source_id",
        "source_ref",
        "polarity",
        "user_id",
        "occurred_at",
    }
    for key in payload:
        if key in allowed_keys or any(key.startswith(prefix) for prefix in allowed_prefixes):
            continue
        return False
    return True


async def _drive_run_terminal(
    service: AgentRunService,
    run_id,
    user_id,
    terminal: str,
):
    """QUEUED → RUNNING → 终态（真实状态机合法路径；审批等待由 journey 显式走）。"""
    await service.transition(run_id, RunStatus.RUNNING, user_id=user_id, actor="system")
    await service.transition(
        run_id,
        RunStatus(terminal),
        user_id=user_id,
        actor="system",
        reason="completed" if terminal == "SUCCEEDED" else "failed",
        result_ref={"receipt_id": str(uuid4()), "status": terminal, "effects": [{"kind": "x10.probe"}]}
        if terminal == "SUCCEEDED"
        else None,
    )


# ---------------------------------------------------------------------------
# family: journey（GJ04-07）
# ---------------------------------------------------------------------------


async def execute_journey(scenario, ctx: ScenarioContext) -> ScenarioRun:
    run = ScenarioRun()
    journey = scenario.inputs["journey"]
    result: dict[str, Any] = {"journey": journey}
    service = ActionCommandService(ctx.session)
    run_svc = AgentRunService(ctx.session)

    if journey == "GJ04":
        task = await seed_task(ctx, scenario.inputs.get("seed_task"))
        stuck = await run.call(
            ctx,
            "mark_stuck",
            lambda: TaskService.mark_stuck(ctx.session, task, stuck_point=scenario.inputs.get("stuck_point")),
        )
        result["stuck_recorded"] = stuck[0].status.value == "STUCK"
        rescoped = await run.call(
            ctx,
            "rescope",
            lambda: TaskService.rescope(
                ctx.session, stuck[0], dict(scenario.inputs.get("rescope") or {}), reason="一次澄清后缩小范围"
            ),
        )
        from app.services.task_completion_evidence import RESCOPE_HISTORY_KEY

        result["rescope_history"] = len((rescoped.guide_json or {}).get(RESCOPE_HISTORY_KEY) or [])
        result["rescope_fields_applied"] = rescoped.estimated_minutes == (scenario.inputs.get("rescope") or {}).get(
            "estimated_minutes"
        )
        # 恢复语义：rescope 只改口径不改状态（STUCK），恢复执行须显式 resume（真实 FSM 边）
        resumed_task = await run.call(ctx, "resume_from_stuck", lambda: TaskService.resume(ctx.session, rescoped))
        complete = dict(scenario.inputs.get("complete") or {})
        completed = await run.call(
            ctx,
            "complete",
            lambda: TaskService.complete(ctx.session, resumed_task, complete.get("actual_minutes")),
        )
        result["task_status"] = completed.status.value
        result["actual_minutes_not_estimated"] = completed.actual_minutes != completed.estimated_minutes
        capture, ms = _timed(lambda: build_task_outcome_capture(completed))
        run.steps.append(StepLog(op="build_task_outcome_capture", ok=True, elapsed_ms=ms))
        result["outcome_polarity"] = capture.polarity.value
        entry = await run.call(ctx, "ledger_query", lambda: _ledger_task_entry(ctx, task.id))
        result["truth_class"] = entry.truth_class.value if entry is not None else None
        run.decision = {"allocation_mode": "human", "journey": "GJ04", "clarifications": 1}
    elif journey in {"GJ05", "GJ06", "GJ07"}:
        spec = dict(scenario.inputs.get("seed_task") or {})
        if journey == "GJ05":
            await run.call(ctx, "seed_knowledge_node", lambda: _seed_knowledge_node(ctx))
        task = await seed_task(ctx, spec)

        if journey == "GJ05":
            complete = dict(scenario.inputs.get("complete") or {})
            completed = await run.call(
                ctx,
                "complete_with_evidence",
                lambda: TaskService.complete(
                    ctx.session, task, complete.get("actual_minutes"), evidence=complete.get("evidence")
                ),
            )
            record = (completed.guide_json or {}).get("completion_evidence_record") or []
            latest = record[-1] if record else {}
            result["evidence_fulfilled"] = latest.get("fulfilled") is True
            echo_rows = (
                await ctx.session.execute(
                    select(StudyRecord).where(StudyRecord.task_id == task.id, StudyRecord.record_type == "task_complete")
                )
            ).scalars().all()
            result["study_record_echo"] = len(list(echo_rows)) >= 1
            capture, ms = _timed(lambda: build_task_outcome_capture(completed))
            run.steps.append(StepLog(op="build_task_outcome_capture", ok=True, elapsed_ms=ms))
            result["outcome_polarity"] = capture.polarity.value
            result["task_status"] = completed.status.value
            entry = await run.call(ctx, "ledger_query", lambda: _ledger_task_entry(ctx, task.id))
            result["ledger_entry_present"] = entry is not None
            result["echo_attached"] = any(e.role.value == "pipeline_echo" for e in entry.evidence) if entry else False
            run.decision = {"allocation_mode": "human", "journey": "GJ05"}
            run.result = result
            run.outcome = {
                "kind": "journey_outcome",
                "polarity": result.get("outcome_polarity"),
                "truth_class": entry.truth_class.value if entry else None,
            }
            return run

        # GJ06 / GJ07：agent/hybrid 闭环（allocation → run → 审批/交棒 → receipt → 命令路径完成 → outcome）
        # run 接管执行的前提语义：任务已开工（PENDING → COMPLETED 在任务 FSM 非法边）
        task = await run.call(ctx, "task_start", lambda: TaskService.start(ctx.session, task))
        factors = (
            {
                "task_type": spec.get("type", "PLANNING"),
                "cognitive_ownership": "delegated" if journey == "GJ06" else "shared",
                "tool_advantage": "high",
                "risk_class": scenario.inputs["run"].get("risk_class", "low"),
                "reversible": scenario.inputs["run"].get("risk_class") != "high",
            }
        )
        decision, ms = _timed(lambda: decide_allocation(AllocationFactors.coerce(factors)))
        run.steps.append(StepLog(op="decide_allocation", ok=True, elapsed_ms=ms))
        run.decision = {
            "allocation": decision.to_dict(),
            "journey": journey,
            "requires_human_approval": decision.requires_human_approval,
        }

        run_spec = dict(scenario.inputs.get("run") or {})
        steps = run_spec.get("steps")
        created = await run.call(
            ctx,
            "create_run",
            lambda: run_svc.create_run(
                user_id=ctx.user.id,
                objective=run_spec.get("objective", f"X-10 {journey}"),
                kind="execution",
                task_id=task.id,
                risk_class=run_spec.get("risk_class"),
                steps=[dict(s) for s in steps] if steps else None,
            ),
        )
        agent_run = created.run

        if journey == "GJ06":
            # 审批门：RUNNING → AWAITING_APPROVAL（wait_kind=approval）→ resume(EXECUTING)
            await run.call(
                ctx,
                "run_running",
                lambda: run_svc.transition(agent_run.id, RunStatus.RUNNING, user_id=ctx.user.id, actor="system"),
            )
            await run.call(
                ctx,
                "run_awaiting_approval",
                lambda: run_svc.transition(
                    agent_run.id,
                    RunStatus.AWAITING_APPROVAL,
                    user_id=ctx.user.id,
                    actor="system",
                    wait_kind=RunWaitKind.APPROVAL,
                    details={"reason": "high risk run requires human approval"},
                ),
            )
            result["approval_gate_visited"] = True
            await run.call(
                ctx,
                "approve_resume",
                lambda: run_svc.resume(agent_run.id, user_id=ctx.user.id, to_status=RunStatus.EXECUTING),
            )
            result["resume_count"] = await _count_run_transitions(ctx, agent_run.id, "run.user_resumed")
        else:
            # GJ07：agent prep → 编排层显式 await 交棒 → awaiting user → 幂等 resume → agent check
            await run.call(
                ctx,
                "run_running",
                lambda: run_svc.transition(agent_run.id, RunStatus.RUNNING, user_id=ctx.user.id, actor="system"),
            )
            await run.call(
                ctx,
                "agent_prep_complete",
                lambda: run_svc.complete_agent_step(
                    agent_run.id,
                    step_id="j7-s1-prep",
                    user_id=ctx.user.id,
                    artifact_refs=[{"scheme": "action_proposal", "ref": "gj07-outline"}],
                ),
            )
            await run.call(
                ctx,
                "await_user_step",
                lambda: run_svc.await_user_step(
                    agent_run.id,
                    step_id="j7-s2-decide",
                    user_id=ctx.user.id,
                    prompt="Agent 已备好提纲，请确认并补写结论",
                ),
            )
            result["awaiting_visited"] = True
            confirmed = await run.call(
                ctx,
                "user_confirm_resume",
                lambda: run_svc.complete_user_step(
                    agent_run.id,
                    step_id="j7-s2-decide",
                    user_id=ctx.user.id,
                    idempotency_key="x10:gj07:confirm",
                    note="结论已补写",
                ),
            )
            result["resumed"] = confirmed.resumed
            if scenario.inputs.get("double_confirm"):
                replay = await run.call(
                    ctx,
                    "user_confirm_replay",
                    lambda: run_svc.complete_user_step(
                        agent_run.id,
                        step_id="j7-s2-decide",
                        user_id=ctx.user.id,
                        idempotency_key="x10:gj07:confirm-retry",
                    ),
                )
                result["double_confirm_replay"] = replay.replay
            await run.call(
                ctx,
                "agent_check_complete",
                lambda: run_svc.complete_agent_step(
                    agent_run.id,
                    step_id="j7-s3-check",
                    user_id=ctx.user.id,
                    artifact_refs=[{"scheme": "action_proposal", "ref": "gj07-final"}],
                ),
            )
            result["resume_count"] = await _count_run_transitions(ctx, agent_run.id, "run.user_resumed")
            result["user_resumed_events"] = result["resume_count"]

        receipt_id = str(uuid4())
        succeeded = await run.call(
            ctx,
            "run_succeed_with_receipt",
            lambda: run_svc.transition(
                agent_run.id,
                RunStatus.SUCCEEDED,
                user_id=ctx.user.id,
                actor="system",
                reason="completed",
                result_ref={"receipt_id": receipt_id, "status": "SUCCEEDED", "effects": [{"kind": "report.generated"}]},
            ),
        )
        result["run_status"] = succeeded.run.status.value
        result["receipt_ref_present"] = bool((succeeded.run.result_ref or {}).get("receipt_id"))
        fresh_run = await run_svc.get_run(agent_run.id, user_id=ctx.user.id)
        receipt_capture, ms = _timed(lambda: build_run_receipt_outcome(fresh_run))
        run.steps.append(StepLog(op="build_run_receipt_outcome", ok=True, elapsed_ms=ms))
        result["run_outcome_polarity"] = receipt_capture.polarity.value

        # 命令路径完成任务（不可逆终态命令必须经用户确认——授权门）
        propose = await run.call(
            ctx,
            "propose_task_complete",
            lambda: service.create_proposal(
                user_id=ctx.user.id,
                command_type="task.update_status",
                payload={"task_id": str(task.id), "to_status": "COMPLETED"},
                source="task",
                run_id=agent_run.id,
            ),
        )
        result["task_complete_authorization_mode"] = (propose.proposal.authorization or {}).get("mode")
        await run.call(
            ctx,
            "approve_task_complete",
            lambda: service.approve(propose.proposal.id, user_id=ctx.user.id, actor="user"),
        )
        final_task = await _task_row(ctx, task)
        result["task_status"] = final_task.status.value

        capture, ms = _timed(lambda: build_task_outcome_capture(final_task))
        run.steps.append(StepLog(op="build_task_outcome_capture", ok=True, elapsed_ms=ms))
        result["outcome_polarity"] = capture.polarity.value
        entry = await run.call(ctx, "ledger_query", lambda: _ledger_task_entry(ctx, task.id))
        result["task_outcome_actual_via_receipt"] = (
            entry is not None and entry.truth_class.value == "actual" and any(
                e.ref and e.ref.startswith("agent_run://") for e in entry.evidence
            )
        )
        result["truth_class"] = entry.truth_class.value if entry is not None else None
        result["owner_sequence"] = [s["owner"] for s in (steps or [])]
        run.outcome = {
            "kind": "journey_outcome",
            "polarity": result.get("outcome_polarity"),
            "run_receipt_polarity": result.get("run_outcome_polarity"),
            "truth_class": result.get("truth_class"),
        }
    else:  # pragma: no cover — fixture 封闭集
        raise ValueError(f"unknown journey {journey!r}")

    run.result = result
    if not run.outcome:
        run.outcome = {"kind": "journey_outcome"}
    return run


EXECUTORS = {
    "allocation": execute_allocation,
    "authorization": execute_authorization,
    "proposal": execute_proposal,
    "run_steps": execute_run_steps,
    "outcome": execute_outcome,
    "journey": execute_journey,
}
