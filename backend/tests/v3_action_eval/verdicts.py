"""X-10 · 判定器 —— 对每场景独立复算（不信执行器的自述结果）.

判定纪律（卡面「判定独立复算」「false success=0」）：
- **判定输入 ≠ 执行输出**：判定器用独立的 DB 会话重读真相行（task / proposal /
  run / transition / 账本），并用纯函数（allocation policy / run_steps 投影 /
  outcome capture 映射）重算预期，再与场景 expected 比对；
- **false success 判定**：凡场景声称「成功/完成/已授权执行」，必须同时被服务端
  真源确证（proposal COMMITTED ⇔ receipt 存在且命令域副作用落库；run SUCCEEDED
  ⇔ run 行终态+result_ref receipt；outcome POSITIVE ⇔ 终态事实确证）。声称与
  真源不一致 → false_success（判 fail 且计入全局 false_success 计数）；
- **high-risk auto=0**：在 allocation/authorization 全场景上按因子独立重判；
- 每条 check 附 expected/actual，失败保留原文（不粉饰）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.core.action_command import AuthorizationDeniedError
from app.core.outcome_ledger import (
    RUN_RECEIPT_OUTCOME_POLARITY,
    OutcomeSource,
    derive_outcome_id,
)
from app.core.run_steps import awaiting_step_projection, run_steps_wire
from app.models.action_proposal import ActionProposal, ActionProposalTransition
from app.models.agent_run import AgentRun, AgentRunTransition
from app.models.task import Task
from app.models.user import User
from app.services.action_allocation_policy import (
    AllocationFactors,
    _high_risk,
    _learning_guard_active,
    decide_allocation,
    vet_agent_offer,
)
from app.services.action_authorization import decide_authorization_mode
from app.services.outcome_capture_service import build_task_outcome_capture
from app.services.outcome_ledger_service import OutcomeLedgerService

from .dbfixture import ScenarioContext

VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_ERROR = "error"


@dataclass
class Verdict:
    """一个场景的判定结果（checks 全过 = pass；任何 fail/error 保留明细）。"""

    scenario_id: str
    verdict: str = VERDICT_PASS
    checks: list[dict[str, Any]] = field(default_factory=list)
    false_success: bool = False
    high_risk_auto: bool = False
    error_detail: str | None = None

    def add(self, check_id: str, passed: bool, *, expected: Any = None, actual: Any = None, detail: str = "") -> None:
        self.checks.append(
            {"id": check_id, "passed": bool(passed), "expected": expected, "actual": actual, "detail": detail}
        )
        if not passed:
            self.verdict = VERDICT_FAIL

    def payload(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "verdict": self.verdict,
            "false_success": self.false_success,
            "high_risk_auto": self.high_risk_auto,
            "error_detail": self.error_detail,
            "checks": self.checks,
        }


def _step_error(six: dict[str, Any], op_prefix: str) -> str | None:
    for step in six.get("execution", {}).get("steps", []):
        if step.get("op", "").startswith(op_prefix) and step.get("error"):
            return step["error"]
    return None


async def _fresh_task(ctx: ScenarioContext, task_id) -> Task | None:
    session = ctx.fresh_session()
    try:
        row = (await session.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
        return row
    finally:
        if session is not ctx.session:
            await session.close()


async def _fresh_proposals(ctx: ScenarioContext, user_id) -> list[ActionProposal]:
    session = ctx.fresh_session()
    try:
        rows = (
            (
                await session.execute(
                    select(ActionProposal).where(
                        ActionProposal.user_id == user_id, ActionProposal.deleted_at.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        return list(rows)
    finally:
        if session is not ctx.session:
            await session.close()


async def _fresh_proposal_transitions(ctx: ScenarioContext, proposal_id) -> list[ActionProposalTransition]:
    session = ctx.fresh_session()
    try:
        rows = (
            (
                await session.execute(
                    select(ActionProposalTransition).where(ActionProposalTransition.proposal_id == proposal_id)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)
    finally:
        if session is not ctx.session:
            await session.close()


async def _fresh_run(ctx: ScenarioContext, run_id) -> AgentRun | None:
    session = ctx.fresh_session()
    try:
        row = (await session.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one_or_none()
        return row
    finally:
        if session is not ctx.session:
            await session.close()


async def _fresh_run_transitions(ctx: ScenarioContext, run_id) -> list[AgentRunTransition]:
    session = ctx.fresh_session()
    try:
        rows = (
            (
                await session.execute(
                    select(AgentRunTransition).where(AgentRunTransition.run_id == run_id)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)
    finally:
        if session is not ctx.session:
            await session.close()


async def _ledger_entry_fresh(ctx: ScenarioContext, user_id, task_id):
    session = ctx.fresh_session()
    try:
        ledger = OutcomeLedgerService(session)
        page = await ledger.query(user_id=user_id, source=OutcomeSource.TASK_COMPLETION, limit=50)
        for entry in page.items:
            if str(entry.source_id) == str(task_id):
                return entry
        return None
    finally:
        if session is not ctx.session:
            await session.close()


# ---------------------------------------------------------------------------
# 全局检查（六元组完整性 / 意外异常 / zero-LLM）
# ---------------------------------------------------------------------------


def judge_common(scenario, six: dict[str, Any], verdict: Verdict) -> None:
    # 六元组完整性：键必须存在且非 None（空 dict 合法——如输入校验拒绝场景无授权决策可记）
    for key in ("decision", "execution", "result", "outcome", "latency", "cost"):
        verdict.add(f"six_tuple.{key}", six.get(key) is not None, expected="present", actual=six.get(key))
    unexpected = [
        s.get("op")
        for s in six.get("execution", {}).get("steps", [])
        if str(s.get("error", "")).startswith("unexpected:") or (s.get("ok") is False and not s.get("error"))
    ]
    verdict.add("execution.no_unexpected_error", not unexpected, expected=[], actual=unexpected)
    cost = six.get("cost") or {}
    verdict.add("cost.zero_llm", cost.get("llm_calls") == 0, expected=0, actual=cost.get("llm_calls"))


# ---------------------------------------------------------------------------
# family judges（独立复算）
# ---------------------------------------------------------------------------


def _allocation_invariant_checks(
    factors: AllocationFactors, decision, verdict: Verdict, recorded_mode: str | None = None
) -> None:
    """结构性不变式（按因子独立重判，与 fixture target 无关）：
    high-risk auto=0 / 学习不代写 / restricted=human / sensitive≠agent / embodiment≠agent。
    同时对**记录面**复核：执行器写下的 decision 若与不变式冲突（记录了 agent），
    同样判红并点亮 high_risk_auto 全局旗标——判定器同时看策略与记录两层。
    """
    if _high_risk(factors):
        verdict.high_risk_auto = verdict.high_risk_auto or decision.mode == "agent"
        verdict.add("invariant.high_risk_auto_zero", decision.mode != "agent", expected="!=agent", actual=decision.mode)
        verdict.add(
            "invariant.high_risk_requires_approval",
            decision.requires_human_approval is True,
            expected=True,
            actual=decision.requires_human_approval,
        )
        if recorded_mode == "agent":
            verdict.high_risk_auto = True
            verdict.add(
                "invariant.recorded_high_risk_auto",
                False,
                expected="!=agent",
                actual=recorded_mode,
                detail="recorded decision claims agent under high-risk factors",
            )
    if _learning_guard_active(factors):
        verdict.add("invariant.learning_guard_no_agent", decision.mode != "agent", expected="!=agent", actual=decision.mode)
        if recorded_mode == "agent":
            verdict.add(
                "invariant.recorded_learning_guard",
                False,
                expected="!=agent",
                actual=recorded_mode,
                detail="recorded decision claims agent under learning guard",
            )
    if factors.privacy == "restricted":
        verdict.add("invariant.restricted_human", decision.mode == "human", expected="human", actual=decision.mode)
        if recorded_mode is not None and recorded_mode != "human":
            verdict.add("invariant.recorded_restricted_human", False, expected="human", actual=recorded_mode)
    if factors.privacy == "sensitive":
        verdict.add("invariant.sensitive_no_agent", decision.mode != "agent", expected="!=agent", actual=decision.mode)
        if recorded_mode == "agent":
            verdict.add("invariant.recorded_sensitive_no_agent", False, expected="!=agent", actual=recorded_mode)
    if factors.embodiment_required is True:
        verdict.add("invariant.embodiment_no_agent", decision.mode != "agent", expected="!=agent", actual=decision.mode)
        if recorded_mode == "agent":
            verdict.add("invariant.recorded_embodiment_no_agent", False, expected="!=agent", actual=recorded_mode)


def judge_allocation(scenario, six: dict[str, Any], verdict: Verdict) -> None:
    factors = AllocationFactors.coerce(scenario.inputs.get("factors") or {})
    expected = scenario.expected
    decision = decide_allocation(factors)  # 独立复算
    recorded = six.get("decision") or {}

    verdict.add(
        "decision.deterministic_recompute",
        recorded.get("mode") == decision.mode and recorded.get("decision_id") is not None,
        expected=decision.mode,
        actual=recorded.get("mode"),
    )
    if "mode" in expected:
        verdict.add(
            "target.mode",
            decision.mode == expected.get("mode"),
            expected=expected.get("mode"),
            actual=decision.mode,
        )
    if "requires_human_approval" in expected:
        verdict.add(
            "target.requires_human_approval",
            decision.requires_human_approval == expected["requires_human_approval"],
            expected=expected["requires_human_approval"],
            actual=decision.requires_human_approval,
        )
    if "requires_user_authored_evidence" in expected:
        verdict.add(
            "target.requires_user_authored_evidence",
            decision.requires_user_authored_evidence == expected["requires_user_authored_evidence"],
            expected=expected["requires_user_authored_evidence"],
            actual=decision.requires_user_authored_evidence,
        )
    if "feasible_modes" in expected:
        verdict.add(
            "target.feasible_modes",
            list(decision.feasible_modes) == list(expected["feasible_modes"]),
            expected=expected["feasible_modes"],
            actual=list(decision.feasible_modes),
        )
    for reason in expected.get("why_contains", []):
        verdict.add(
            f"target.why[{reason}]",
            reason in decision.why,
            expected=True,
            actual=reason in decision.why,
        )
    if "offer_kind" in scenario.inputs:
        offer = vet_agent_offer(scenario.inputs["offer_kind"], factors, None)  # 独立复算
        verdict.add(
            "target.offer_allowed",
            offer.allowed == expected.get("offer_allowed"),
            expected=expected.get("offer_allowed"),
            actual=offer.allowed,
        )
        if expected.get("offer_reason"):
            verdict.add(
                "target.offer_reason",
                offer.reason == expected["offer_reason"],
                expected=expected["offer_reason"],
                actual=offer.reason,
            )
        if expected.get("offer_downgrade"):
            verdict.add(
                "target.offer_downgrade",
                offer.suggested_downgrade == expected["offer_downgrade"],
                expected=expected["offer_downgrade"],
                actual=offer.suggested_downgrade,
            )
        if "offer_requires_human_approval" in expected:
            verdict.add(
                "target.offer_requires_approval",
                offer.requires_human_approval == expected["offer_requires_human_approval"],
                expected=expected["offer_requires_human_approval"],
                actual=offer.requires_human_approval,
            )
        recorded_offer = (recorded.get("offer") or {})
        verdict.add(
            "decision.offer_recorded",
            recorded_offer.get("reason") == offer.reason,
            expected=offer.reason,
            actual=recorded_offer.get("reason"),
        )
    _allocation_invariant_checks(factors, decision, verdict, recorded_mode=recorded.get("mode"))


def judge_authorization(scenario, six: dict[str, Any], verdict: Verdict, ctx: ScenarioContext) -> None:
    inputs = scenario.inputs
    expected = scenario.expected
    path = inputs.get("path", "pure")

    if path == "pure":
        pure = dict(inputs.get("pure") or {})
        decision = decide_authorization_mode(  # 独立复算
            risk_class=pure.get("risk_class"),
            reversible=pure.get("reversible"),
            requires_human_approval=bool(pure.get("requires_human_approval")),
            user_auto_grant=bool(pure.get("user_auto_grant")),
        )
        verdict.add(
            "target.authorization_mode",
            decision.mode == expected.get("authorization_mode"),
            expected=expected.get("authorization_mode"),
            actual=decision.mode,
        )
        if expected.get("reason_contains"):
            reasons = decision.reason_codes
            verdict.add(
                "target.reason_codes",
                any(expected["reason_contains"] in r for r in reasons),
                expected=expected["reason_contains"],
                actual=reasons,
            )
        # high-risk 面：服务端投影 requires_human_approval=True 时 mode 永不 auto
        if pure.get("requires_human_approval"):
            verdict.high_risk_auto = verdict.high_risk_auto or decision.mode == "auto"
            verdict.add("invariant.approval_flag_never_auto", decision.mode != "auto", expected="!=auto", actual=decision.mode)
        return

    if path == "commit":
        confirmed = bool(inputs.get("confirmed"))
        mode = (inputs.get("authorization") or {}).get("mode")
        decision = decide_authorization_mode(risk_class="low", reversible=True, user_auto_grant=(mode == "auto"))
        recomputed_mode = decision.mode if mode == "auto" else "confirmation"
        verdict.add(
            "commit.mode_recompute",
            recomputed_mode == mode,
            expected=mode,
            actual=recomputed_mode,
        )
        if mode == "auto":
            verdict.add(
                "target.commit_allowed",
                expected.get("commit_allowed") is True,
                expected=True,
                actual=expected.get("commit_allowed"),
            )
        else:
            verdict.add(
                "target.commit_gate_fail_closed",
                expected.get("commit_allowed", False) == confirmed,
                expected=f"allowed={confirmed}",
                actual=expected.get("commit_allowed"),
            )
        if expected.get("missing_record_denied"):
            verdict.add(
                "target.missing_record_denied",
                six.get("result", {}).get("missing_record_denied") is True,
                expected=True,
                actual=six.get("result", {}).get("missing_record_denied"),
            )
        return

    # service path：DB 真相独立复核
    result = six.get("result") or {}
    mode = expected.get("authorization_mode")
    verdict.add(
        "target.authorization_mode",
        result.get("authorization_mode") == mode,
        expected=mode,
        actual=result.get("authorization_mode"),
    )

    async def _recheck() -> None:
        proposals = await _fresh_proposals(ctx, ctx.user.id)
        if not proposals:
            verdict.add("db.proposal_exists", False, expected=">=1", actual=0)
            return
        proposal = proposals[0]
        verdict.add(
            "db.proposal_authorization_mode",
            (proposal.authorization or {}).get("mode") == mode,
            expected=mode,
            actual=(proposal.authorization or {}).get("mode"),
        )
        status = proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status)
        verdict.add(
            "db.proposal_status",
            status == expected.get("proposal_status"),
            expected=expected.get("proposal_status"),
            actual=status,
        )
        task = await _fresh_task(ctx, proposal.subject_id) if proposal.subject_id else None
        if expected.get("proposal_status") == "COMMITTED":
            # false-success 面：声称已执行 ⇔ receipt 真在 + 副作用真落库
            receipt_ok = bool(proposal.receipt) and (proposal.receipt or {}).get("status") == "COMMITTED"
            verdict.add("db.receipt_present_on_commit", receipt_ok, expected=True, actual=bool(proposal.receipt))
            if task is not None and (proposal.payload or {}).get("fields"):
                fields = (proposal.payload or {}).get("fields") or {}
                applied = all(getattr(task, k, None) == v for k, v in fields.items())
                verdict.add("db.command_effects_applied", applied, expected=True, actual=applied)
        if expected.get("task_updated") is False:
            fields = (proposal.payload or {}).get("fields") or {}
            untouched = all(
                getattr(task, k, None) != v
                for k, v in fields.items()
                if task is not None and k != "task_id"
            )
            verdict.add(
                "db.confirmation_mode_did_not_execute",
                untouched,
                expected=True,
                actual=untouched,
            )
        if expected.get("task_status") and task is not None:
            task_status = task.status.value if hasattr(task.status, "value") else str(task.status)
            verdict.add("db.task_status", task_status == expected["task_status"], expected=expected["task_status"], actual=task_status)

    verdict._pending_db = _recheck  # runner 在事件循环内统一 await


def judge_proposal(scenario, six: dict[str, Any], verdict: Verdict, ctx: ScenarioContext) -> None:
    expected = scenario.expected
    result = six.get("result") or {}
    op = scenario.inputs["op"]

    if expected.get("error"):
        verdict.add(
            "target.error_class",
            result.get("error") == expected["error"],
            expected=expected["error"],
            actual=result.get("error"),
        )

    async def _recheck() -> None:
        proposals = await _fresh_proposals(ctx, ctx.user.id)
        if "proposals_count" in expected:
            verdict.add(
                "db.proposals_count",
                len(proposals) == expected["proposals_count"],
                expected=expected["proposals_count"],
                actual=len(proposals),
            )
        if expected.get("proposals_count") == 0:
            return
        if not proposals:
            verdict.add("db.proposal_exists", False, expected=">=1", actual=0)
            return
        proposal = proposals[0]
        status = proposal.status.value if hasattr(proposal.status, "value") else str(proposal.status)
        if expected.get("proposal_status"):
            verdict.add(
                "db.proposal_status",
                status == expected["proposal_status"],
                expected=expected["proposal_status"],
                actual=status,
            )
        if expected.get("proposal_status") == "COMMITTED":
            # false-success 面：receipt + 副作用独立确证
            receipt = proposal.receipt or {}
            verdict.add(
                "db.receipt_committed",
                receipt.get("status") == "COMMITTED",
                expected="COMMITTED",
                actual=receipt.get("status"),
            )
            task = await _fresh_task(ctx, proposal.subject_id) if proposal.subject_id else None
            if task is not None and expected.get("task_status"):
                task_status = task.status.value if hasattr(task.status, "value") else str(task.status)
                verdict.add("db.task_status", task_status == expected["task_status"], expected=expected["task_status"], actual=task_status)
        if expected.get("task_status") and op not in {"approve", "approve_twice"}:
            proposal_row = proposals[0]
            task = await _fresh_task(ctx, proposal_row.subject_id) if proposal_row.subject_id else None
            if task is not None:
                task_status = task.status.value if hasattr(task.status, "value") else str(task.status)
                verdict.add("db.task_status", task_status == expected["task_status"], expected=expected["task_status"], actual=task_status)
        if "transitions_count" in expected:
            transitions = await _fresh_proposal_transitions(ctx, proposals[0].id)
            verdict.add(
                "db.transitions_count",
                len(transitions) == expected["transitions_count"],
                expected=expected["transitions_count"],
                actual=len(transitions),
            )
        if expected.get("tasks_created") is not None:
            session = ctx.fresh_session()
            try:
                rows = (
                    (await session.execute(select(Task).where(Task.user_id == ctx.user.id, Task.deleted_at.is_(None))))
                    .scalars()
                    .all()
                )
                verdict.add(
                    "db.tasks_created",
                    len(list(rows)) == expected["tasks_created"],
                    expected=expected["tasks_created"],
                    actual=len(list(rows)),
                )
            finally:
                if session is not ctx.session:
                    await session.close()

    if result.get("proposal_status") == "COMPLETED" and expected.get("actual_minutes_not_estimated"):
        verdict.add(
            "target.actual_not_estimated",
            result.get("actual_minutes") != result.get("estimated_minutes")
            and (result.get("actual_minutes") or 0) <= expected.get("actual_minutes_max", 10**9),
            expected=f"<= {expected.get('actual_minutes_max')}",
            actual=result.get("actual_minutes"),
        )
    verdict._pending_db = _recheck


def judge_run_steps(scenario, six: dict[str, Any], verdict: Verdict, ctx: ScenarioContext) -> None:
    expected = scenario.expected
    result = six.get("result") or {}

    if expected.get("error"):
        verdict.add(
            "target.error_class",
            result.get("error") == expected["error"],
            expected=expected["error"],
            actual=result.get("error"),
        )
    if expected.get("error_expected"):
        verdict.add("target.error_raised", bool(result.get("error")), expected=True, actual=result.get("error"))

    async def _recheck() -> None:
        # 场景只有一个 run：取该用户全部 run 的最新一行（独立会话）
        session = ctx.fresh_session()
        try:
            rows = (
                (
                    await session.execute(
                        select(AgentRun)
                        .where(AgentRun.user_id == ctx.user.id, AgentRun.deleted_at.is_(None))
                        .order_by(AgentRun.created_at.desc())
                        .limit(1)
                    )
                )
                .scalars()
                .all()
            )
        finally:
            if session is not ctx.session:
                await session.close()
        if not rows:
            verdict.add("db.run_exists", False, expected=">=1", actual=0)
            return
        run = rows[0]
        status = run.status.value if hasattr(run.status, "value") else str(run.status)
        if expected.get("run_status"):
            verdict.add("db.run_status", status == expected["run_status"], expected=expected["run_status"], actual=status)
        if expected.get("terminal_reason"):
            verdict.add(
                "db.terminal_reason",
                run.terminal_reason == expected["terminal_reason"],
                expected=expected["terminal_reason"],
                actual=run.terminal_reason,
            )
        if expected.get("wait_kind"):
            verdict.add("db.wait_kind", run.wait_kind == expected["wait_kind"], expected=expected["wait_kind"], actual=run.wait_kind)

        steps = run.steps or []
        completions = {s.get("step_id"): (s.get("completion") or {}) for s in steps}
        for step_id, by in (expected.get("completions") or {}).items():
            actual_by = (completions.get(step_id) or {}).get("by")
            verdict.add(f"db.step_completed_by[{step_id}]", actual_by == by, expected=by, actual=actual_by)
        if expected.get("step_completed_s1"):
            actual_by = (completions.get("s1") or {}).get("by")
            verdict.add("db.step_completed_s1", actual_by == expected["step_completed_s1"], expected=expected["step_completed_s1"], actual=actual_by)
        if expected.get("step_completed_s2_by"):
            actual_by = (completions.get("s2") or {}).get("by")
            verdict.add("db.step_completed_s2_by", actual_by == expected["step_completed_s2_by"], expected=expected["step_completed_s2_by"], actual=actual_by)
        if "step_completed" in expected:
            any_done = any(completions.values())
            verdict.add("db.step_completed", any_done == expected["step_completed"], expected=expected["step_completed"], actual=any_done)
        if "wire_steps_count" in expected:
            wire = run_steps_wire(steps)  # 纯函数独立投影
            verdict.add(
                "db.wire_steps_count",
                len(wire) == expected["wire_steps_count"],
                expected=expected["wire_steps_count"],
                actual=len(wire),
            )
        if "wire_owner_first" in expected:
            wire = run_steps_wire(steps)
            owner = wire[0].get("owner") if wire else None
            verdict.add("db.wire_owner_first", owner == expected["wire_owner_first"], expected=expected["wire_owner_first"], actual=owner)
        if "wire_owner_second" in expected:
            wire = run_steps_wire(steps)
            owner = wire[1].get("owner") if len(wire) > 1 else None
            verdict.add("db.wire_owner_second", owner == expected["wire_owner_second"], expected=expected["wire_owner_second"], actual=owner)
        if "steps_total" in expected:
            verdict.add("db.steps_total", run.steps_total == expected["steps_total"], expected=expected["steps_total"], actual=run.steps_total)
        if "plan_owner_unchanged" in expected:
            first_owner = (steps[0] or {}).get("owner") if steps else None
            verdict.add(
                "db.plan_owner_unchanged",
                first_owner == expected["plan_owner_unchanged"],
                expected=expected["plan_owner_unchanged"],
                actual=first_owner,
            )

        transitions = await _fresh_run_transitions(ctx, run.id)
        resumed = [t for t in transitions if t.event_name == "run.user_resumed"]
        if "resume_count" in expected:
            verdict.add("db.resume_count", len(resumed) == expected["resume_count"], expected=expected["resume_count"], actual=len(resumed))
        if "user_resumed_events" in expected:
            events = [t for t in transitions if t.event_name == "run.user_resumed"]
            verdict.add(
                "db.user_resumed_events",
                len(events) == expected["user_resumed_events"],
                expected=expected["user_resumed_events"],
                actual=len(events),
            )
        if expected.get("event_step_completed"):
            # run.step_completed 是 outbox 进度事件（不改状态，不进 transitions 表）
            session2 = ctx.fresh_session()
            try:
                from sqlalchemy import text as sa_text

                outbox_rows = (
                    await session2.execute(
                        sa_text(
                            "SELECT id FROM event_outbox WHERE aggregate_id = :rid AND event_type = 'run.step_completed'"
                        ),
                        {"rid": str(run.id)},
                    )
                ).fetchall()
            finally:
                if session2 is not ctx.session:
                    await session2.close()
            verdict.add("db.step_completed_event", len(outbox_rows) >= 1, expected=">=1", actual=len(outbox_rows))

        projection = awaiting_step_projection(  # 独立复算（纯函数，不经 ORM helper）
            run_status=status,
            wait_kind=run.wait_kind,
            terminal_reason=run.terminal_reason,
            wait_expires_at=run.wait_expires_at,
            steps=steps,
        )
        if "awaiting_step_id" in expected:
            actual_id = projection.get("step_id") if projection else None
            verdict.add("db.awaiting_step_id", actual_id == expected["awaiting_step_id"], expected=expected["awaiting_step_id"], actual=actual_id)
        if "awaiting_state" in expected:
            actual_state = projection.get("state") if projection else None
            verdict.add("db.awaiting_state", actual_state == expected["awaiting_state"], expected=expected["awaiting_state"], actual=actual_state)
        if "awaiting_prompt" in expected:
            actual_prompt = projection.get("prompt") if projection else None
            verdict.add("db.awaiting_prompt", actual_prompt == expected["awaiting_prompt"], expected=expected["awaiting_prompt"], actual=actual_prompt)
        cold = (six.get("result") or {}).get("cold_start_awaiting")
        if expected.get("cold_start_ownership"):
            verdict.add(
                "db.cold_start_ownership",
                bool(cold) and cold.get("ownership") == expected["cold_start_ownership"],
                expected=expected["cold_start_ownership"],
                actual=(cold or {}).get("ownership"),
            )
        if expected.get("cold_start_prompt"):
            verdict.add(
                "db.cold_start_prompt",
                bool(cold) and cold.get("prompt") == expected["cold_start_prompt"],
                expected=expected["cold_start_prompt"],
                actual=(cold or {}).get("prompt"),
            )
        if "first_key_recorded" in expected:
            keys = [(c or {}).get("idempotency_key") for c in completions.values() if c]
            verdict.add(
                "db.first_key_first_wins",
                expected["first_key_recorded"] in keys,
                expected=expected["first_key_recorded"],
                actual=keys,
            )
        if "second_replay" in expected:
            verdict.add(
                "target.second_call_replay",
                result.get("second_replay") == expected["second_replay"],
                expected=expected["second_replay"],
                actual=result.get("second_replay"),
            )
        # owner 纪律独立复核：每条完成戳的 by 必须与步骤 owner 同侧
        for step in steps:
            completion = step.get("completion") or {}
            if not completion:
                continue
            owner = step.get("owner")
            by = completion.get("by")
            expected_by = "agent" if owner == "agent" else "user"
            verdict.add(
                f"db.owner_discipline[{step.get('step_id')}]",
                by == expected_by,
                expected=expected_by,
                actual=by,
            )

    verdict._pending_db = _recheck


def judge_outcome(scenario, six: dict[str, Any], verdict: Verdict, ctx: ScenarioContext) -> None:
    expected = scenario.expected
    result = six.get("result") or {}
    inputs = scenario.inputs

    if "outcome_polarity" in expected:
        verdict.add(
            "target.outcome_polarity",
            result.get("outcome_polarity") == expected["outcome_polarity"],
            expected=expected["outcome_polarity"],
            actual=result.get("outcome_polarity"),
        )
    if "run_outcome_polarity" in expected:
        verdict.add(
            "target.run_outcome_polarity",
            result.get("run_outcome_polarity") == expected["run_outcome_polarity"],
            expected=expected["run_outcome_polarity"],
            actual=result.get("run_outcome_polarity"),
        )
    if expected.get("never_positive"):
        verdict.add(
            "target.never_positive",
            result.get("run_outcome_polarity") != "positive",
            expected="!=positive",
            actual=result.get("run_outcome_polarity"),
        )
    if "ids_equal" in expected:
        verdict.add("target.derive_id_idempotent", result.get("ids_equal") is True, expected=True, actual=result.get("ids_equal"))
        verdict.add("target.id_prefix", str(result.get("id_prefix")) == expected.get("id_prefix"), expected=expected.get("id_prefix"), actual=result.get("id_prefix"))
    if "event_name" in expected:
        verdict.add("target.event_name", result.get("event_name") == expected["event_name"], expected=expected["event_name"], actual=result.get("event_name"))
    if "polarity" in expected:
        verdict.add("target.event_polarity", result.get("polarity") == expected["polarity"], expected=expected["polarity"], actual=result.get("polarity"))
    if expected.get("content_free"):
        payload = (six.get("outcome") or {}).get("event_payload") or {}
        allowed_prefixes = ("correlation_",)
        allowed_keys = {
            "event_type", "schema", "outcome_ledger_schema", "outcome_id", "outcome_key",
            "source", "source_id", "source_ref", "polarity", "user_id", "occurred_at",
        }
        clean = all(k in allowed_keys or any(k.startswith(p) for p in allowed_prefixes) for k in payload)
        verdict.add("target.payload_content_free", clean, expected=True, actual=sorted(payload.keys()))

    async def _recheck() -> None:
        # 独立复核：重读任务行 → 重算 capture 映射；账本用独立会话重查
        session = ctx.fresh_session()
        try:
            rows = (
                (
                    await session.execute(
                        select(Task).where(Task.user_id == ctx.user.id, Task.deleted_at.is_(None)).order_by(Task.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
        finally:
            if session is not ctx.session:
                await session.close()
        entry = await _ledger_entry_fresh(ctx, ctx.user.id, rows[0].id) if rows else None

        if "truth_class" in expected:
            actual_truth = entry.truth_class.value if entry else result.get("truth_class")
            verdict.add("db.ledger_truth_class", actual_truth == expected["truth_class"], expected=expected["truth_class"], actual=actual_truth)
        if expected.get("ledger_entry_present"):
            verdict.add("db.ledger_entry_present", entry is not None, expected=True, actual=entry is not None)
        if expected.get("outcome_captured") and rows:
            fresh_task = rows[0]
            try:
                capture = build_task_outcome_capture(fresh_task)  # 独立复算映射
                same = capture.outcome_id == result.get("outcome_id") or result.get("outcome_id") is None
                verdict.add("db.capture_mapping_recompute", same and capture.polarity.value == result.get("outcome_polarity", capture.polarity.value), expected="consistent", actual=capture.polarity.value)
            except ValueError:
                verdict.add("db.capture_mapping_recompute", False, expected="terminal task", actual=fresh_task.status.value if hasattr(fresh_task.status, "value") else str(fresh_task.status))
        if expected.get("declared_preserved"):
            verdict.add(
                "db.declared_preserved",
                result.get("declared_preserved") is True,
                expected=True,
                actual=result.get("declared_preserved"),
            )
        # run receipt 极性映射独立复核（封闭词表）
        if "run_outcome_polarity" in expected:
            terminal = inputs.get("run_terminal")
            recomputed = RUN_RECEIPT_OUTCOME_POLARITY.get(terminal)
            verdict.add(
                "db.run_receipt_polarity_map",
                recomputed is not None and recomputed.value == expected["run_outcome_polarity"],
                expected=expected["run_outcome_polarity"],
                actual=recomputed.value if recomputed else None,
            )
        if expected.get("run_receipt_materialized"):
            verdict.add(
                "db.run_receipt_materialized",
                result.get("run_receipt_materialized") is True,
                expected=True,
                actual=result.get("run_receipt_materialized"),
            )
        # false-success 面：POSITIVE outcome ⇔ 任务真为终态完成
        if expected.get("outcome_polarity") == "positive" and rows:
            fresh_task = rows[0]
            status = fresh_task.status.value if hasattr(fresh_task.status, "value") else str(fresh_task.status)
            verdict.add("db.positive_outcome_backed_by_completion", status == "COMPLETED", expected="COMPLETED", actual=status)
        if expected.get("outcome_polarity") == "negative" and rows:
            fresh_task = rows[0]
            status = fresh_task.status.value if hasattr(fresh_task.status, "value") else str(fresh_task.status)
            verdict.add("db.negative_outcome_backed_by_abandon", status == "ABANDONED", expected="ABANDONED", actual=status)

    verdict._pending_db = _recheck


def judge_journey(scenario, six: dict[str, Any], verdict: Verdict, ctx: ScenarioContext) -> None:
    expected = scenario.expected
    result = six.get("result") or {}

    async def _recheck() -> None:
        session = ctx.fresh_session()
        try:
            tasks = (
                (
                    await session.execute(
                        select(Task).where(Task.user_id == ctx.user.id, Task.deleted_at.is_(None)).order_by(Task.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
            run_rows = (
                (
                    await session.execute(
                        select(AgentRun)
                        .where(AgentRun.user_id == ctx.user.id, AgentRun.deleted_at.is_(None))
                        .order_by(AgentRun.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
        finally:
            if session is not ctx.session:
                await session.close()
        task = tasks[0] if tasks else None
        entry = await _ledger_entry_fresh(ctx, ctx.user.id, task.id) if task is not None else None

        if expected.get("task_status") and task is not None:
            status = task.status.value if hasattr(task.status, "value") else str(task.status)
            verdict.add("db.task_status", status == expected["task_status"], expected=expected["task_status"], actual=status)
        if "outcome_polarity" in expected:
            actual = entry.polarity.value if entry else result.get("outcome_polarity")
            verdict.add("db.outcome_polarity", actual == expected["outcome_polarity"], expected=expected["outcome_polarity"], actual=actual)

        if scenario.inputs["journey"] == "GJ04":
            if task is not None:
                from app.services.task_completion_evidence import RESCOPE_HISTORY_KEY

                history = (task.guide_json or {}).get(RESCOPE_HISTORY_KEY) or []
                verdict.add(
                    "db.rescope_history",
                    len(history) == expected.get("rescope_history", 1),
                    expected=expected.get("rescope_history", 1),
                    actual=len(history),
                )
                stuck_runtime = (task.guide_json or {}).get("stuck_runtime")
                verdict.add("db.stuck_recorded", bool(stuck_runtime) or result.get("stuck_recorded") is True, expected=True, actual=bool(stuck_runtime))
                verdict.add(
                    "db.actual_not_estimated",
                    task.actual_minutes is not None and task.actual_minutes != task.estimated_minutes,
                    expected="!=estimated",
                    actual=task.actual_minutes,
                )
        if scenario.inputs["journey"] == "GJ05":
            verdict.add(
                "db.study_record_echo",
                result.get("study_record_echo") is True,
                expected=True,
                actual=result.get("study_record_echo"),
            )
            if entry is not None:
                verdict.add(
                    "db.echo_evidence_attached",
                    any(e.role.value == "pipeline_echo" for e in entry.evidence),
                    expected=True,
                    actual=[e.role.value for e in entry.evidence],
                )
        if scenario.inputs["journey"] in {"GJ06", "GJ07"}:
            run_row = run_rows[0] if run_rows else None
            if run_row is not None:
                status = run_row.status.value if hasattr(run_row.status, "value") else str(run_row.status)
                verdict.add("db.run_status", status == expected.get("run_status"), expected=expected.get("run_status"), actual=status)
                verdict.add(
                    "db.receipt_ref_present",
                    bool((run_row.result_ref or {}).get("receipt_id")),
                    expected=True,
                    actual=bool((run_row.result_ref or {}).get("receipt_id")),
                )
                transitions = await _fresh_run_transitions(ctx, run_row.id)
                awaiting_approval = [t for t in transitions if t.to_status == "AWAITING_APPROVAL"]
                awaiting_user = [t for t in transitions if t.to_status == "AWAITING_USER"]
                if expected.get("approval_gate_visited"):
                    verdict.add(
                        "db.approval_gate_visited",
                        len(awaiting_approval) >= 1,
                        expected=">=1",
                        actual=len(awaiting_approval),
                    )
                    # high-risk auto=0 的 run 面：审批门前不得直接跳终态成功
                    verdict.high_risk_auto = verdict.high_risk_auto or (len(awaiting_approval) == 0)
                    verdict.add("invariant.high_risk_run_not_auto", len(awaiting_approval) >= 1, expected=">=1", actual=len(awaiting_approval))
                if expected.get("awaiting_visited"):
                    verdict.add(
                        "db.awaiting_user_visited",
                        len(awaiting_user) >= 1,
                        expected=">=1",
                        actual=len(awaiting_user),
                    )
                if "resume_count" in expected:
                    resumed = [t for t in transitions if t.event_name == "run.user_resumed"]
                    verdict.add("db.resume_exactly_once", len(resumed) == expected["resume_count"], expected=expected["resume_count"], actual=len(resumed))
                if "user_resumed_events" in expected:
                    events = [t for t in transitions if t.event_name == "run.user_resumed"]
                    verdict.add("db.user_resumed_events", len(events) == expected["user_resumed_events"], expected=expected["user_resumed_events"], actual=len(events))
                if "owner_sequence" in expected:
                    from app.core.run_steps import run_steps_wire as _wire

                    owners = [w.get("owner") for w in _wire(run_row.steps or [])]
                    verdict.add("db.owner_sequence", owners == expected["owner_sequence"], expected=expected["owner_sequence"], actual=owners)
            if expected.get("task_outcome_actual_via_receipt"):
                actual = bool(
                    entry is not None
                    and entry.truth_class.value == "actual"
                    and any(e.ref and e.ref.startswith("agent_run://") for e in entry.evidence)
                )
                verdict.add(
                    "db.task_outcome_actual_via_receipt",
                    actual,
                    expected=True,
                    actual={
                        "truth": entry.truth_class.value if entry else None,
                        "evidence": [e.ref for e in entry.evidence] if entry else [],
                    },
                )
            if result.get("double_confirm_replay") is not None:
                verdict.add(
                    "db.double_confirm_replayed",
                    result.get("double_confirm_replay") is True,
                    expected=True,
                    actual=result.get("double_confirm_replay"),
                )

    # allocation 决策（GJ06/GJ07）不变式复判
    decision = (six.get("decision") or {}).get("allocation")
    if decision is not None:
        if decision.get("requires_human_approval"):
            verdict.add(
                "invariant.journey_high_risk_flagged",
                six.get("decision", {}).get("requires_human_approval") is True,
                expected=True,
                actual=six.get("decision", {}).get("requires_human_approval"),
            )
    verdict._pending_db = _recheck


FAMILY_JUDGES = {
    "allocation": lambda scenario, six, verdict, ctx: judge_allocation(scenario, six, verdict),
    "authorization": judge_authorization,
    "proposal": judge_proposal,
    "run_steps": judge_run_steps,
    "outcome": judge_outcome,
    "journey": judge_journey,
}


async def judge_scenario(scenario, six: dict[str, Any], ctx: ScenarioContext) -> dict[str, Any]:
    """判定入口：公共检查 + 家族判定 + 独立 DB 复核（统一在此 await）。"""
    verdict = Verdict(scenario_id=scenario.scenario_id)
    try:
        judge_common(scenario, six, verdict)
        FAMILY_JUDGES[scenario.family](scenario, six, verdict, ctx)
        pending = getattr(verdict, "_pending_db", None)
        if pending is not None:
            await pending()
    except Exception as exc:  # noqa: BLE001 — 判定器自身异常如实记录为 error（非粉饰）
        verdict.verdict = VERDICT_ERROR
        verdict.error_detail = f"{type(exc).__name__}: {exc}"
    payload = verdict.payload()
    payload.pop("_pending_db", None)
    return payload
