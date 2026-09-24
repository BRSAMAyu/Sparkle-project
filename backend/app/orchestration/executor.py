from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from loguru import logger
from pydantic import ValidationError

from app.config import settings
from app.core.business_metrics import COMPENSATION_TRIGGERED
from app.core.event_bus import event_bus
from app.core.event_types import (
    TOOL_EXECUTION_COMPLETED,
    TOOL_EXECUTION_FAILED,
    TOOL_EXECUTION_STARTED,
    TOOL_EXECUTION_TIMED_OUT,
)
from app.core.failure_semantics import (
    DEFAULT_MAX_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY_SECONDS,
    DEFAULT_RETRY_MAX_DELAY_SECONDS,
    FailureKind,
    retry_decision,
)

if TYPE_CHECKING:
    from app.core.failure_semantics import FailureClassification
from app.core.llm_secure_io import refresh_llm_safety_mode, sanitize_exception_message
from app.core.metrics import TOOL_EXECUTION_COUNT
from app.db.session import AsyncSessionLocal
from app.models.agent_tool_call import AgentToolCall
from app.services.tool_history_service import ToolHistoryService
from app.tools.base import TOOL_RUNTIME_CONTEXT_KEY, ToolResult
from app.tools.metadata import (
    PermissionDecision,
    ToolMetadata,
    canonical_args_hash,
    decide_tool_permission,
)
from app.tools.registry import tool_registry

if TYPE_CHECKING:
    from app.orchestration.schemas import ExecutablePlan, ToolCallSpec

#: X-06 · run 权威会话工厂（权限/预算读取用**独立会话**，避免在调用方事务中途
#: commit）。测试以 sqlite 测试引擎 monkeypatch 本符号（X-05 service 测试同法）。
_agent_run_session_factory = AsyncSessionLocal

#: X-09 · 账本两阶段收敛会话工厂（失败路径 rollback 后复查/收敛账本行，用独立
#: 会话提交——不制造调用方事务边界；测试 monkeypatch 同上）。
_ledger_session_factory = AsyncSessionLocal


@dataclass
class _CallGuard:
    """一次工具调用的安全闸门结果（rejected 非空 = 不执行工具）。"""

    tool_name: str
    decision: PermissionDecision | None = None
    metadata: ToolMetadata | None = None
    idempotency_key: str | None = None
    args_hash: str = ""
    run_id: str | None = None
    ledger: AgentToolCall | None = None
    replay_result: ToolResult | None = None
    rejected: ToolResult | None = None

    def reject(self, *, error_type: str, message: str) -> None:
        self.rejected = ToolResult(
            success=False,
            tool_name=self.tool_name,
            error_type=error_type,
            error_message=message,
        )

    def reject_permission(self, tool_name: str, reason: str) -> None:
        self.reject(
            error_type="PermissionDenied",
            message=f"Tool '{tool_name}' denied by permission decision ({reason}); "
            "grants come from the tool registry and server-declared permissions only",
        )

    async def finalize(
        self,
        db_session: Any,
        result: ToolResult,
        execution_time_ms: int | None,
    ) -> None:
        """账本收敛（succeeded/failed + 结果 dump；与工具写入同事务提交）。"""
        if self.ledger is None:
            return
        try:
            self.ledger.status = "succeeded" if result.success else "failed"
            self.ledger.result = result.model_dump(mode="json")
            self.ledger.execution_time_ms = execution_time_ms
            self.ledger.error_type = result.error_type
            self.ledger.error_message = (result.error_message or None) if not result.success else None
            self.ledger.finished_at = datetime.now(UTC).replace(tzinfo=None)
            db_session.add(self.ledger)
        except Exception as exc:  # noqa: BLE001 — 账本收敛失败不吞工具结果
            logger.warning("tool call ledger finalize failed tool={} error={!r}", self.tool_name, exc)

    async def resolve_after_failure(
        self,
        *,
        error_type: str,
        error_message: str | None,
    ) -> str:
        """X-09 · 失败路径的账本两阶段收敛（FIX-40 P2-3 收编）.

        背景：内部 commit 工具（persona/plan_state/theater 等）会在执行中途把
        账本 in_progress 行**提前落库**——executor 失败路径 rollback 对已提交行
        无效，账本行将永久停在 in_progress（同 key 重放被恒拒 = key 中毒）。

        收敛语义（rollback 之后调用，用独立会话按**账本行 id** 复查）：

        - 行不存在（随事务回滚）→ ``"none"``：无任何持久效果残留，失败调用
          可安全自动重试；
        - 行仍为 in_progress（内部 commit 提前落库）→ 置 ``interrupted``
          （+error/finished_at）并提交 → ``"unknown"``：效果不可核实，重试必须
          换新幂等键（duplicate side effect=0 的账本根基）；
        - 行已收敛（succeeded/failed/interrupted）→ ``"unknown"``（保守：该行
          曾独立提交过，执行中断后其结论不可作为重放依据）。
        """
        if self.ledger is None:
            return "none"
        ledger_id = getattr(self.ledger, "id", None)
        if ledger_id is None:
            return "none"
        try:
            async with _ledger_session_factory() as session:
                from sqlalchemy import select

                row = (
                    await session.execute(select(AgentToolCall).where(AgentToolCall.id == ledger_id))
                ).scalar_one_or_none()
                if row is None:
                    return "none"
                if row.status != "in_progress":
                    return "unknown"
                row.status = "interrupted"
                row.error_type = (error_type or "Interrupted")[:100]
                row.error_message = (error_message or "execution interrupted before outcome was recorded")[:2000]
                row.finished_at = datetime.now(UTC).replace(tzinfo=None)
                session.add(row)
                await session.commit()
                logger.warning(
                    "tool call ledger resolved to interrupted (two-phase, FIX-40 P2-3): "
                    "tool={} key={} ledger_id={} error_type={}",
                    self.tool_name,
                    self.idempotency_key,
                    ledger_id,
                    error_type,
                )
                return "unknown"
        except Exception as exc:  # noqa: BLE001 — 收敛失败不影响失败结果返回；恢复 sweep 兜底
            logger.error(
                "tool call ledger two-phase resolve failed tool={} ledger_id={} error={!r}",
                self.tool_name,
                ledger_id,
                exc,
            )
            return "unknown"

    async def record_usage(self, user_id: str) -> None:
        """run 维度 usage 记账（tool_calls+1、cost+metadata 估计）。"""
        if self.run_id is None or self.metadata is None:
            return
        try:
            from app.services.agent_run_service import AgentRunService

            async with _agent_run_session_factory() as run_session:
                await AgentRunService(run_session).record_run_usage(
                    self.run_id,
                    user_id=user_id,
                    tool_calls=1,
                    cost_usd=self.metadata.cost_usd,
                )
        except Exception as exc:  # noqa: BLE001 — 记账失败不吞工具结果（下次闸门仍会拦超限）
            logger.warning("run usage recording failed run_id={} error={!r}", self.run_id, exc)


@dataclass
class StepResult:
    """Result of executing a single DAG step."""

    step_id: str
    tool_name: str
    tool_result: ToolResult
    duration_ms: int = 0
    output_key: str | None = None
    output_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanExecutionResult:
    """Aggregate result of executing an entire plan via DAG layers."""

    plan_id: str
    step_results: list[StepResult] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    execution_layers_completed: int = 0
    total_layers: int = 0
    aborted: bool = False
    abort_reason: str | None = None
    # X-09：run 预算已超限（后续层不再发起；FIX-40 P3-6——切断而非硬顶兜底）。
    budget_exceeded: bool = False
    # 演示缺陷 ❌#4：确认门（requires_confirmation 且用户未批准）中断的是
    # 「等待确认」而非「执行失败」。置位后聊天层把中断文案路由为面向用户
    # 的自然话术，开发者诊断（abort_reason）只进日志与内部 metadata。
    awaiting_user_confirmation: bool = False


_MAX_TOOL_CALLS_PER_REQUEST = 20
_DAG_LAYER_MAX_CONCURRENCY = 10

#: 确认门结构化错误码（演示缺陷 ❌#4）：requires_confirmation 且用户未批准时
#: 工具不执行。这是「等待确认」语义，不是执行失败——计划层据此路由文案。
CONFIRMATION_REQUIRED_ERROR_TYPE = "ConfirmationRequired"

# ---------------------------------------------------------------------------
# X-09 · 失败语义接线（确定性映射 + 重试参数；模块级常量供测试 monkeypatch）
# ---------------------------------------------------------------------------

#: executor error_type（闸门/超时/异常路径的结构化错误码）→ FailureKind 封闭
#: 映射。**只看 error_type，不看 message 文案**（文案变化不得改变终态语义）。
_ERROR_TYPE_TO_FAILURE_KIND: dict[str, FailureKind] = {
    "TimeoutError": FailureKind.TOOL_TIMEOUT,
    "BudgetExceeded": FailureKind.BUDGET_EXCEEDED,
    "BudgetGateUnavailable": FailureKind.TOOL_EXCEPTION,
    "PermissionDenied": FailureKind.PERMISSION_DENIED,
    "IdempotencyKeyRequired": FailureKind.IDEMPOTENCY_KEY_REQUIRED,
    "IdempotencyConflict": FailureKind.IDEMPOTENCY_CONFLICT,
    "IdempotencyArgsMismatch": FailureKind.IDEMPOTENCY_ARGS_MISMATCH,
    "IdempotencyInterrupted": FailureKind.IDEMPOTENCY_INTERRUPTED,
    "ValidationError": FailureKind.VALIDATION_ERROR,
    "ToolNotFound": FailureKind.UNKNOWN_TOOL,
    "ConfirmationRequired": FailureKind.CONFIRMATION_REQUIRED,
}

#: 暂态网络/基础设施异常类型名前缀（generic Exception 路径 error_type=
#: type(e).__name__ 的确定性归并；网络分区 chaos 场景的可重试判据）。
_TRANSIENT_EXCEPTION_PREFIXES: tuple[str, ...] = (
    "Connection",
    "ConnectTimeout",
    "ReadTimeout",
    "WriteTimeout",
    "ServerDisconnected",
    "ClientConnector",
    "TemporaryFailure",
    "RateLimit",
)


def failure_kind_for_error_type(error_type: str | None) -> FailureKind:
    """executor 错误码 → FailureKind（确定性；未知码 → TOOL_REPORTED_FAILURE）.

    未知错误码一律 ``TOOL_REPORTED_FAILURE``（暂态族）——最终可重试性仍由
    side_effect_state 裁决（unknown 则升格 UNKNOWN_OUTCOME），不会误放行。
    """
    code = str(error_type or "").strip()
    if not code:
        return FailureKind.TOOL_REPORTED_FAILURE
    if code in _ERROR_TYPE_TO_FAILURE_KIND:
        return _ERROR_TYPE_TO_FAILURE_KIND[code]
    if any(code.startswith(prefix) for prefix in _TRANSIENT_EXCEPTION_PREFIXES):
        return FailureKind.NETWORK_UNREACHABLE
    return FailureKind.TOOL_REPORTED_FAILURE


def classify_tool_result_failure(
    result: ToolResult,
    *,
    tool_effect: str | None,
) -> FailureClassification:
    """失败 ToolResult → :class:`FailureClassification`（分类器接线）."""
    from app.core.failure_semantics import classify_execution_failure

    return classify_execution_failure(
        failure_kind=failure_kind_for_error_type(result.error_type),
        error_type=result.error_type,
        tool_effect=tool_effect,
        side_effect_state=result.side_effect_state,
    )


class ToolExecutor:
    """
    工具执行器
    负责解析 LLM 的工具调用请求并执行
    """

    @staticmethod
    async def _notify_execution_observer(execution_observer: Any | None, payload: dict[str, Any]) -> None:
        if not execution_observer:
            return
        result = execution_observer(payload)
        if inspect.isawaitable(result):
            await result

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _tool_timeout_seconds(tool: Any) -> float:
        timeout = getattr(tool, "timeout_seconds", None)
        if timeout is None:
            timeout = getattr(settings, "TOOL_EXECUTION_TIMEOUT_SECONDS", 120.0)
        if timeout is None:
            timeout_value = 120.0
        else:
            try:
                timeout_value = float(timeout)
            except (TypeError, ValueError):
                timeout_value = 120.0
        return timeout_value if timeout_value > 0 else 120.0

    @staticmethod
    def _accepts_kwarg(func: Any, name: str) -> bool:
        """按签名探测 func 是否接受关键字参数 name（含 **kwargs 通配）。

        背景（V3-FIX-13 / D-15-7）：executor 曾无条件向 tool.execute() 传
        locale=，签名未声明的工具（现存 25 个注册工具中 23 个）全部
        TypeError。改为探测后再传，缺省形参的工具不再被打挂。
        """
        try:
            signature = inspect.signature(func)
        except (TypeError, ValueError):
            return False
        param = signature.parameters.get(name)
        if param is not None:
            return param.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())

    @staticmethod
    async def _publish_tool_event(event_type: str, payload: dict[str, Any]) -> None:
        try:
            await event_bus.publish(
                event_type,
                {
                    "event_type": event_type,
                    **payload,
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to publish tool execution event {event_type}: {exc}")

    @staticmethod
    def _dump_params(validated_params: Any, fallback: dict[str, Any]) -> dict[str, Any]:
        if hasattr(validated_params, "model_dump"):
            try:
                dumped = validated_params.model_dump()
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
        if hasattr(validated_params, "__dict__"):
            try:
                dumped = dict(validated_params)
                if isinstance(dumped, dict):
                    return dumped
            except Exception:
                pass
        return fallback

    @staticmethod
    def _quote_bareword_values(raw: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            prefix, token, suffix = match.groups()
            if token in {"true", "false", "null"}:
                return f"{prefix}{token}{suffix}"
            return f'{prefix}"{token}"{suffix}'

        return re.sub(r"(:\s*)([A-Za-z_][A-Za-z0-9_-]*)(\s*[,}])", _replace, raw)

    @classmethod
    def _coerce_arguments(cls, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if raw is None:
            return {}
        if not isinstance(raw, str):
            return {}

        text = raw.strip()
        if not text:
            return {}

        candidates = [
            text,
            text.replace("'", '"'),
            cls._quote_bareword_values(text),
            cls._quote_bareword_values(text.replace("'", '"')),
        ]
        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

        logger.warning(f"Failed to parse tool call arguments as JSON: {text[:200]}")
        return {"_parse_error": "arguments were not valid JSON", "_raw_preview": text[:500]}

    @staticmethod
    def _session_info_mapping(db_session: Any) -> dict[str, Any] | None:
        sync_session = getattr(db_session, "sync_session", None)
        info = getattr(sync_session, "info", None)
        if isinstance(info, dict):
            return info
        info = getattr(db_session, "info", None)
        if isinstance(info, dict):
            return info
        return None

    # ------------------------------------------------------------------
    # X-06 · 工具调用安全闸门（权限/幂等/预算/账本——代码强制，非提示词层）
    # ------------------------------------------------------------------

    @staticmethod
    def _structured_context(runtime_context: dict[str, Any] | None) -> dict[str, Any]:
        """只取 runtime_context 的**服务端结构化键**（权限判定输入空间）。

        权限判定与预算检查只消费本方法返回的结构化字段；对话内容
        （``current_user_message`` 等不可信文本）永不进入判定输入——这是
        prompt injection 无法扩权的构造性保证（SECURITY_PRIVACY.md）。
        """
        if not isinstance(runtime_context, dict):
            return {}
        keys = ("allowed_tools", "run_permissions", "run_id", "user_approved", "locale")
        return {k: runtime_context[k] for k in keys if k in runtime_context}

    async def _authorize_and_begin_call(
        self,
        *,
        tool: Any,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        db_session: Any,
        tool_call_id: str | None,
        idempotency_key: str | None,
        runtime_context: dict[str, Any] | None,
    ) -> _CallGuard:
        """权限判定 + side-effect 幂等 + run 预算闸门 + 账本开行。

        返回 :class:`_CallGuard`——``rejected`` 非空即拒绝/重放（调用方直接
        返回该 ToolResult，不执行工具）；否则 ``ledger`` 为已开账本行
        （in_progress，与工具写入同事务），执行完成后调 ``finalize``。

        闸门顺序（fail-closed）：
        1. 元数据：registry 是唯一真源；缺失（未注册/被拒注册）→ 拒绝；
        2. 权限：registry 元数据 + run 契约（run_id 存在时以 AgentRun 行为
           权威，否则取 runtime_context 的服务端结构化授权）；
        3. 幂等：side-effect（effect=write）必须有 key（显式 idempotency_key
           或 tool_call_id），缺失即拒绝；同 key 已记录 → 重放（不重复执行）；
        4. 预算：run_id 存在时 AgentRunService.enforce_budget（超限 → run
           落 BUDGET_EXCEEDED 明确终态，本次调用拒绝）。
        """
        guard = _CallGuard(tool_name=tool_name)
        ctx = self._structured_context(runtime_context)

        # 1. 元数据（registry fail-closed 的执行侧兜底复查）
        metadata = tool_registry.get_tool_metadata(tool_name)
        if metadata is None:
            guard.reject_permission(tool_name, "metadata_missing")
            return guard

        # 2. 权限判定（run 行权威 > 服务端结构化授权 > 代码冻结默认授权集）
        run_row = None
        run_id = ctx.get("run_id")
        if run_id:
            run_row = await self._load_run_row(str(run_id), str(user_id))
        if run_row is not None:
            run_permissions = run_row.permissions if isinstance(run_row.permissions, dict) else {}
            decision = decide_tool_permission(
                tool_name=tool_name,
                metadata=metadata,
                allowed_tools=run_row.allowed_tools or None,
                granted_permissions=run_permissions.get("granted"),
                denied_permissions=run_permissions.get("denied"),
            )
        else:
            run_permissions = ctx.get("run_permissions")
            run_permissions = run_permissions if isinstance(run_permissions, dict) else {}
            decision = decide_tool_permission(
                tool_name=tool_name,
                metadata=metadata,
                allowed_tools=ctx.get("allowed_tools"),
                granted_permissions=run_permissions.get("granted"),
                denied_permissions=run_permissions.get("denied"),
            )
        if not decision.allowed:
            guard.reject_permission(tool_name, decision.reason)
            return guard
        guard.decision = decision

        # 3. side-effect 幂等（effect=write 强制 key；同 key 重放恰一次）
        key = (str(idempotency_key).strip() if idempotency_key else None) or tool_call_id or None
        guard.idempotency_key = key
        if metadata.is_side_effect and not key:
            guard.reject(
                error_type="IdempotencyKeyRequired",
                message=f"Tool '{tool_name}' has side effects; an idempotency key (or tool_call_id) is required",
            )
            return guard

        args_hash = canonical_args_hash(arguments)
        guard.args_hash = args_hash
        guard.metadata = metadata

        if key:
            existing = await self._find_ledger_row(db_session, user_id, tool_name, key)
            if existing is not None:
                if existing.args_hash and existing.args_hash != args_hash:
                    guard.reject(
                        error_type="IdempotencyArgsMismatch",
                        message=(
                            f"Idempotency key '{key}' was already used with different arguments for tool '{tool_name}'"
                        ),
                    )
                    return guard
                if existing.status == "in_progress":
                    guard.reject(
                        error_type="IdempotencyConflict",
                        message=(
                            f"Previous attempt with idempotency key '{key}' is still in progress "
                            f"for tool '{tool_name}'; side effect not re-executed"
                        ),
                    )
                    return guard
                if existing.status == "interrupted":
                    # X-09：前次调用中断且效果不可核实（崩溃/超时两阶段收敛后的
                    # 账本行）。同 key 重放恒拒（duplicate side effect=0）；重试
                    # 必须换新幂等键——那是显式决策，不是自动行为。
                    guard.reject(
                        error_type="IdempotencyInterrupted",
                        message=(
                            f"Previous attempt with idempotency key '{key}' for tool '{tool_name}' "
                            "was interrupted and its side-effect outcome could not be verified; "
                            "retrying requires a NEW idempotency key (this key will never re-execute)"
                        ),
                    )
                    return guard
                # succeeded/failed：返回已记录结果——同 key 重放恰一次执行
                guard.replay_result = self._rebuild_result(existing)
                return guard

        # 4. run 预算闸门（超限 → BUDGET_EXCEEDED 明确终态 + 本次拒绝）
        if run_row is not None:
            from app.services.agent_run_service import AgentRunService, BudgetExceededError

            try:
                async with _agent_run_session_factory() as run_session:
                    await AgentRunService(run_session).enforce_budget(
                        run_row.id, user_id=user_id, prospective_tool_calls=1
                    )
            except BudgetExceededError as exc:
                guard.reject(error_type="BudgetExceeded", message=str(exc))
                return guard
            except Exception as exc:  # noqa: BLE001 — 预算基础设施故障 → fail-closed
                logger.error("run budget gate failed (fail-closed) tool={} error={!r}", tool_name, exc)
                guard.reject(error_type="BudgetGateUnavailable", message="run budget gate unavailable; call rejected")
                return guard
            guard.run_id = str(run_row.id)

        # 账本开行（与工具写入同事务：提交即「已发生且已记账」）
        try:
            ledger = AgentToolCall(
                user_id=uuid.UUID(str(user_id)),
                run_id=uuid.UUID(str(guard.run_id)) if guard.run_id else None,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                idempotency_key=key,
                args_hash=args_hash,
                permission_decision=decision.to_dict(),
                status="in_progress",
                started_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db_session.add(ledger)
            await db_session.flush()
            guard.ledger = ledger
        except Exception as exc:  # noqa: BLE001 — 并发同 key 撞唯一索引等 → fail-closed
            logger.warning("tool call ledger begin failed (fail-closed) tool={} error={!r}", tool_name, exc)
            await self._safe_rollback(db_session)
            guard.reject(
                error_type="IdempotencyConflict",
                message=f"Concurrent duplicate call for tool '{tool_name}' detected; side effect not re-executed",
            )
        return guard

    async def _load_run_row(self, run_id: str, user_id: str) -> Any:
        """加载 AgentRun 权威行（权限/预算的 DB 真源；独立会话避免嵌套事务）。"""
        try:
            from app.services.agent_run_service import AgentRunService, RunNotFoundError

            async with _agent_run_session_factory() as run_session:
                return await AgentRunService(run_session).get_run(run_id, user_id=user_id)
        except RunNotFoundError:
            logger.warning("run context references unknown run_id={} (permission falls back to context grants)", run_id)
            return None
        except Exception as exc:  # noqa: BLE001 — run 权威不可读 → 视为无 run 上下文（context 授权兜底）
            logger.error("run authority load failed run_id={} error={!r}", run_id, exc)
            return None

    @staticmethod
    async def _find_ledger_row(db_session: Any, user_id: str, tool_name: str, key: str) -> AgentToolCall | None:
        from sqlalchemy import select

        try:
            stmt = (
                select(AgentToolCall)
                .where(
                    AgentToolCall.user_id == uuid.UUID(str(user_id)),
                    AgentToolCall.tool_name == tool_name,
                    AgentToolCall.idempotency_key == key,
                )
                # X-09：populate_existing 绕过 identity map 陈旧视图——同一长会话
                # （chat 轨道单 db_session 多轮工具调用）内的重放必须看到**已提交**
                # 的账本真相（另一会话/两阶段收敛写入的 interrupted/succeeded），
                # 而不是本会话构造时的 in_progress 残影。
                .execution_options(populate_existing=True)
            )
            return cast("AgentToolCall | None", ((await db_session.execute(stmt)).scalar_one_or_none()))
        except Exception as exc:  # noqa: BLE001 — 账本不可读 → fail-closed（无账本不执行 side effect）
            logger.error("tool call ledger read failed tool={} key={} error={!r}", tool_name, key, exc)
            raise

    @staticmethod
    def _rebuild_result(ledger: AgentToolCall) -> ToolResult:
        """从账本行重建 ToolResult（重放返回体；损坏行退化为显式冲突拒绝）。"""
        try:
            payload = ledger.result or {}
            return ToolResult.model_validate(payload)
        except Exception:
            return ToolResult(
                success=False,
                tool_name=ledger.tool_name,
                error_type="IdempotencyConflict",
                error_message="Recorded result for this idempotency key is unreadable; side effect not re-executed",
            )

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        db_session: Any | None,
        progress_callback: Any | None = None,
        tool_call_id: str | None = None,
        compensation_call: dict[str, Any] | None = None,
        runtime_context: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> ToolResult:
        """
        执行单个工具调用并记录执行历史

        Args:
            tool_name: 工具名称
            arguments: LLM 提供的参数（JSON）
            user_id: 用户 ID
            db_session: 数据库会话
            progress_callback: 进度回调
            tool_call_id: 工具调用 ID
            idempotency_key: X-06 幂等键（side-effect 工具缺省回落 tool_call_id；
                两者皆缺且 effect=write → IdempotencyKeyRequired 拒绝）

        Returns:
            ToolResult: 执行结果
        """
        await refresh_llm_safety_mode()
        if db_session is None:
            async with AsyncSessionLocal() as session:
                return await self._execute_tool_call_with_session(
                    tool_name=tool_name,
                    arguments=arguments,
                    user_id=user_id,
                    db_session=session,
                    progress_callback=progress_callback,
                    tool_call_id=tool_call_id,
                    owns_session=True,
                    compensation_call=compensation_call,
                    runtime_context=runtime_context,
                    idempotency_key=idempotency_key,
                )

        return await self._execute_tool_call_with_session(
            tool_name=tool_name,
            arguments=arguments,
            user_id=user_id,
            db_session=db_session,
            progress_callback=progress_callback,
            tool_call_id=tool_call_id,
            owns_session=False,
            compensation_call=compensation_call,
            runtime_context=runtime_context,
            idempotency_key=idempotency_key,
        )

    async def _execute_tool_call_with_session(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        user_id: str,
        db_session: Any,
        progress_callback: Any | None,
        tool_call_id: str | None,
        owns_session: bool,
        compensation_call: dict[str, Any] | None,
        runtime_context: dict[str, Any] | None,
        idempotency_key: str | None = None,
    ) -> ToolResult:
        tool = tool_registry.get_tool(tool_name)
        session_info = self._session_info_mapping(db_session)
        previous_runtime_context = session_info.get(TOOL_RUNTIME_CONTEXT_KEY) if session_info is not None else None
        if session_info is not None and runtime_context:
            session_info[TOOL_RUNTIME_CONTEXT_KEY] = dict(runtime_context)

        try:
            if not tool:
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="not_found").inc()
                error_result = ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=f"未知工具: {tool_name}",
                    error_type="ToolNotFound",
                    suggestion="请检查工具名称是否正确",
                )
                await self._publish_tool_event(
                    TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "error_message": error_result.error_message,
                        "error_type": "ToolNotFound",
                        "timestamp": self._utcnow_iso(),
                    },
                )
                await self._record_tool_execution(
                    db_session,
                    user_id,
                    tool_name,
                    False,
                    error_message=f"未知工具: {tool_name}",
                    error_type="ToolNotFound",
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                return error_result

            try:
                validated_params = tool.parameters_schema(**arguments)
            except ValidationError as e:
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="validation_error").inc()
                validation_error = ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=sanitize_exception_message(
                        f"参数验证失败: {str(e)}",
                        fallback="参数验证失败，请检查输入格式。",
                    ),
                    suggestion="请检查参数格式是否正确",
                )
                await self._publish_tool_event(
                    TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "error_message": validation_error.error_message,
                        "error_type": "ValidationError",
                        "timestamp": self._utcnow_iso(),
                    },
                )
                await self._record_tool_execution(
                    db_session,
                    user_id,
                    tool_name,
                    False,
                    error_message=f"参数验证失败: {str(e)}",
                    error_type="ValidationError",
                    input_args=arguments,
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                return validation_error

            start_time = time.time()
            executed_tool = False
            compensation_spec = self._parse_compensation_call(compensation_call)
            timeout_seconds = self._tool_timeout_seconds(tool)

            # Enforce requires_confirmation before execution
            if getattr(tool, "requires_confirmation", False):
                approved = (runtime_context or {}).get("user_approved", False)
                if not approved:
                    # 演示缺陷 ❌#4：error_message/suggestion 会进 tool_result 帧
                    # 被用户看到——保持面向用户的话术，不用开发者英文术语。
                    return ToolResult(
                        success=False,
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        error_message=f"「{tool_name}」这一步需要你确认后才能执行。",
                        suggestion="确认这个操作后我们马上继续。",
                        error_type=CONFIRMATION_REQUIRED_ERROR_TYPE,
                    )

            # X-06 · 安全闸门链：权限判定 → side-effect 幂等 → run 预算 → 账本开行
            # （代码强制；判定输入只有 registry 元数据与服务端结构化授权，
            # 与对话内容无关——prompt injection 无法扩权）。
            guard = await self._authorize_and_begin_call(
                tool=tool,
                tool_name=tool_name,
                arguments=arguments,
                user_id=user_id,
                db_session=db_session,
                tool_call_id=tool_call_id,
                idempotency_key=idempotency_key,
                runtime_context=runtime_context,
            )
            if guard.rejected is not None:
                rejected = guard.rejected
                rejected.tool_call_id = tool_call_id
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="denied").inc()
                await self._publish_tool_event(
                    TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "error_message": rejected.error_message,
                        "error_type": rejected.error_type,
                        "timestamp": self._utcnow_iso(),
                    },
                )
                await self._record_tool_execution(
                    db_session,
                    user_id,
                    tool_name,
                    False,
                    error_message=rejected.error_message,
                    error_type=rejected.error_type,
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                return rejected
            if guard.replay_result is not None:
                replay = guard.replay_result
                replay.tool_call_id = tool_call_id
                logger.info(
                    "tool call replay (idempotent, side effect not repeated): tool={} key={}",
                    tool_name,
                    guard.idempotency_key,
                )
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="idempotent_replay").inc()
                await self._publish_tool_event(
                    TOOL_EXECUTION_COMPLETED if replay.success else TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "idempotent_replay": True,
                        "success": replay.success,
                        "timestamp": self._utcnow_iso(),
                    },
                )
                return replay

            await self._publish_tool_event(
                TOOL_EXECUTION_STARTED,
                {
                    "user_id": str(user_id),
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "timeout_seconds": timeout_seconds,
                    "timestamp": self._utcnow_iso(),
                },
            )

            try:
                executed_tool = True
                # Extract locale from runtime_context for localized prompts
                locale = "en"
                if runtime_context and isinstance(runtime_context, dict):
                    locale = runtime_context.get("locale", "en")

                # 按工具 execute() 签名探测后再传扩展 kwargs（V3-FIX-13 / D-15-7）
                execute_kwargs: dict[str, Any] = {"tool_call_id": tool_call_id}
                if self._accepts_kwarg(tool.execute, "locale"):
                    execute_kwargs["locale"] = locale

                if getattr(tool, "is_long_running", False) and progress_callback:
                    if self._accepts_kwarg(tool.execute, "progress_callback"):
                        execute_kwargs["progress_callback"] = progress_callback
                    execution_coro = tool.execute(
                        validated_params,
                        user_id,
                        db_session,
                        **execute_kwargs,
                    )
                else:
                    execution_coro = tool.execute(
                        validated_params,
                        user_id,
                        db_session,
                        **execute_kwargs,
                    )
                result = await asyncio.wait_for(execution_coro, timeout=timeout_seconds)
                if result.tool_call_id is None:
                    result.tool_call_id = tool_call_id
                if not result.success:
                    result.error_message = sanitize_exception_message(result.error_message)
                    if result.suggestion:
                        result.suggestion = sanitize_exception_message(
                            result.suggestion,
                            fallback="请稍后重试。",
                        )

                execution_time_ms = int((time.time() - start_time) * 1000)
                TOOL_EXECUTION_COUNT.labels(
                    tool_name=tool_name,
                    status="success" if result.success else "failed",
                ).inc()

                await self._record_tool_execution(
                    db_session=db_session,
                    user_id=user_id,
                    tool_name=tool_name,
                    success=result.success,
                    execution_time_ms=execution_time_ms,
                    error_message=result.error_message,
                    tool_category=getattr(tool, "category", None),
                    input_args=self._dump_params(validated_params, arguments),
                    output_summary=result.suggestion or str(result.data)[:200] if result.data else None,
                    use_separate_session=not owns_session,
                )
                # X-06 账本收敛（succeeded/failed + 结果 dump；与工具写入同事务）
                await guard.finalize(db_session, result, execution_time_ms)
                await self._commit_if_owned(db_session, owns_session)
                # X-06 run 维度 usage 记账（tool_calls+1 / cost+metadata 估计）
                await guard.record_usage(user_id)

                if not result.success:
                    await self._publish_tool_event(
                        TOOL_EXECUTION_FAILED,
                        {
                            "user_id": str(user_id),
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "duration_ms": execution_time_ms,
                            "error_message": result.error_message,
                            "error_type": result.error_type,
                            "timestamp": self._utcnow_iso(),
                        },
                    )
                    await self._maybe_execute_compensation(
                        compensation_spec=compensation_spec,
                        user_id=user_id,
                        db_session=db_session,
                        owns_session=owns_session,
                        reason="tool_failed",
                        runtime_context=runtime_context,
                        tool_call_id=tool_call_id,
                    )
                else:
                    await self._publish_tool_event(
                        TOOL_EXECUTION_COMPLETED,
                        {
                            "user_id": str(user_id),
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "duration_ms": execution_time_ms,
                            "success": True,
                            "timestamp": self._utcnow_iso(),
                        },
                    )

                return result
            except TimeoutError:
                execution_time_ms = int((time.time() - start_time) * 1000)
                timeout_message = f"工具执行超时（>{timeout_seconds:.0f}s）"
                logger.error(f"Tool execution timeout: {tool_name} after {timeout_seconds}s")
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="timeout").inc()
                await self._safe_rollback(db_session)
                # X-09 两阶段收敛：rollback 后账本行若仍存在（内部 commit 提前
                # 落库）→ interrupted；side_effect_state 随结果透传给分类器。
                side_effect_state = await guard.resolve_after_failure(
                    error_type="TimeoutError", error_message=timeout_message
                )
                await self._record_tool_execution(
                    db_session=db_session,
                    user_id=user_id,
                    tool_name=tool_name,
                    success=False,
                    execution_time_ms=execution_time_ms,
                    error_message=timeout_message,
                    error_type="TimeoutError",
                    input_args=self._dump_params(validated_params, arguments),
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                await self._publish_tool_event(
                    TOOL_EXECUTION_TIMED_OUT,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "duration_ms": execution_time_ms,
                        "timeout_seconds": timeout_seconds,
                        "error_message": timeout_message,
                        "timestamp": self._utcnow_iso(),
                    },
                )
                if executed_tool:
                    await self._maybe_execute_compensation(
                        compensation_spec=compensation_spec,
                        user_id=user_id,
                        db_session=db_session,
                        owns_session=owns_session,
                        reason="tool_timeout",
                        runtime_context=runtime_context,
                        tool_call_id=tool_call_id,
                    )
                return ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=timeout_message,
                    error_type="TimeoutError",
                    side_effect_state=side_effect_state,
                    suggestion="请稍后重试，或缩小本次工具执行范围",
                )
            except Exception as e:
                execution_time_ms = int((time.time() - start_time) * 1000)
                safe_error = sanitize_exception_message(str(e))
                logger.opt(exception=e).error(f"Tool execution error: {tool_name} - {str(e)}")
                TOOL_EXECUTION_COUNT.labels(tool_name=tool_name, status="error").inc()
                await self._safe_rollback(db_session)
                # X-09 两阶段收敛（同 TimeoutError 路径；FIX-40 P2-3）.
                side_effect_state = await guard.resolve_after_failure(
                    error_type=type(e).__name__, error_message=safe_error
                )
                await self._record_tool_execution(
                    db_session=db_session,
                    user_id=user_id,
                    tool_name=tool_name,
                    success=False,
                    execution_time_ms=execution_time_ms,
                    error_message=str(e),
                    error_type=type(e).__name__,
                    input_args=arguments,
                    use_separate_session=not owns_session,
                )
                await self._commit_if_owned(db_session, owns_session)
                await self._publish_tool_event(
                    TOOL_EXECUTION_FAILED,
                    {
                        "user_id": str(user_id),
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "duration_ms": execution_time_ms,
                        "error_message": safe_error,
                        "error_type": type(e).__name__,
                        "timestamp": self._utcnow_iso(),
                    },
                )
                if executed_tool:
                    await self._maybe_execute_compensation(
                        compensation_spec=compensation_spec,
                        user_id=user_id,
                        db_session=db_session,
                        owns_session=owns_session,
                        reason="tool_exception",
                        runtime_context=runtime_context,
                        tool_call_id=tool_call_id,
                    )
                return ToolResult(
                    success=False,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    error_message=safe_error,
                    error_type=type(e).__name__,
                    side_effect_state=side_effect_state,
                    suggestion="请稍后重试或联系支持",
                )
        finally:
            if session_info is not None:
                if previous_runtime_context is None:
                    session_info.pop(TOOL_RUNTIME_CONTEXT_KEY, None)
                else:
                    session_info[TOOL_RUNTIME_CONTEXT_KEY] = previous_runtime_context

    async def _record_tool_execution(
        self,
        db_session: Any,
        user_id: str,
        tool_name: str,
        success: bool,
        execution_time_ms: int | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        tool_category: str | None = None,
        input_args: dict[str, Any] | None = None,
        output_summary: str | None = None,
        use_separate_session: bool = False,
    ) -> None:
        """
        记录工具执行到数据库

        Args:
            db_session: 数据库会话
            user_id: 用户ID
            tool_name: 工具名称
            success: 是否成功
            execution_time_ms: 执行时间（毫秒）
            error_message: 错误信息
            error_type: 错误类型
            tool_category: 工具类别
            input_args: 输入参数
            output_summary: 输出摘要
        """
        # 转换user_id为UUID（如果需要）
        try:
            user_id_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        except ValueError:
            logger.warning(f"Invalid user_id for history recording: {user_id}")
            return

        if use_separate_session:
            async with AsyncSessionLocal() as history_session:
                try:
                    history_service = ToolHistoryService(history_session)
                    await history_service.record_tool_execution(
                        user_id=user_id_uuid,
                        tool_name=tool_name,
                        success=success,
                        execution_time_ms=execution_time_ms,
                        error_message=error_message,
                        error_type=error_type,
                        tool_category=tool_category,
                        input_args=input_args,
                        output_summary=output_summary,
                    )
                    await history_session.commit()
                except Exception as e:
                    await history_session.rollback()
                    logger.warning(f"Failed to record tool execution history: {e}")
            return

        try:
            history_service = ToolHistoryService(db_session)
            await history_service.record_tool_execution(
                user_id=user_id_uuid,
                tool_name=tool_name,
                success=success,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
                error_type=error_type,
                tool_category=tool_category,
                input_args=input_args,
                output_summary=output_summary,
            )
            await db_session.flush()
        except Exception as e:
            logger.warning(f"Failed to record tool execution history: {e}")
            await self._safe_rollback(db_session)

    async def _commit_if_owned(self, db_session: Any, owns_session: bool) -> None:
        if not owns_session:
            return
        try:
            await db_session.commit()
        except Exception as e:
            logger.warning(f"Failed to commit tool execution session: {e}")
            await self._safe_rollback(db_session)

    async def _safe_rollback(self, db_session: Any) -> None:
        if not db_session or not hasattr(db_session, "rollback"):
            return
        try:
            await db_session.rollback()
        except Exception as e:
            logger.warning(f"Failed to rollback tool execution session: {e}")

    def _parse_compensation_call(self, compensation_call: dict[str, Any] | None) -> tuple[str, dict[str, Any]] | None:
        if not compensation_call or not isinstance(compensation_call, dict):
            return None
        tool_name = compensation_call.get("name") or compensation_call.get("tool_name") or compensation_call.get("tool")
        args = (
            compensation_call.get("params") or compensation_call.get("arguments") or compensation_call.get("args") or {}
        )
        if not tool_name:
            return None
        if isinstance(args, str):
            args = self._coerce_arguments(args)
        if not isinstance(args, dict):
            args = {}
        return tool_name, args

    async def _maybe_execute_compensation(
        self,
        *,
        compensation_spec: tuple[str, dict[str, Any]] | None,
        user_id: str,
        db_session: Any,
        owns_session: bool,
        reason: str,
        runtime_context: dict[str, Any] | None = None,
        tool_call_id: str | None = None,
    ) -> None:
        if not compensation_spec:
            return
        tool_name, arguments = compensation_spec
        COMPENSATION_TRIGGERED.labels(reason=reason).inc()
        # X-06：补偿调用本身是 side effect——确定性幂等键（同一失败调用的补偿
        # 重放恰一次；无原始 call id 时退化为参数哈希）。
        compensation_key = (
            f"compensation:{tool_call_id}:{tool_name}"
            if tool_call_id
            else f"compensation:{tool_name}:{canonical_args_hash(arguments)}"
        )
        try:
            await self._execute_tool_call_with_session(
                tool_name=tool_name,
                arguments=arguments,
                user_id=user_id,
                db_session=db_session,
                progress_callback=None,
                tool_call_id=None,
                owns_session=owns_session,
                compensation_call=None,
                runtime_context=runtime_context,
                idempotency_key=compensation_key,
            )
        except Exception as e:
            logger.warning(f"Compensation tool failed: {tool_name} - {e}")

    async def execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        user_id: str,
        db_session: Any | None,
        runtime_context: dict[str, Any] | None = None,
    ) -> list[ToolResult]:
        """
        批量执行工具调用（按顺序）

        Args:
            tool_calls: 工具调用列表，格式为 OpenAI function_call

        Returns:
            List[ToolResult]: 执行结果列表
        """
        results = []
        capped_calls = tool_calls[:_MAX_TOOL_CALLS_PER_REQUEST]
        if len(tool_calls) > _MAX_TOOL_CALLS_PER_REQUEST:
            logger.warning(f"Tool calls capped from {len(tool_calls)} to {_MAX_TOOL_CALLS_PER_REQUEST}")
        for call in capped_calls:
            arguments = self._coerce_arguments(call["function"].get("arguments"))
            result = await self.execute_tool_call(
                tool_name=call["function"]["name"],
                arguments=arguments,
                user_id=user_id,
                db_session=db_session,
                tool_call_id=call.get("id"),
                compensation_call=(call.get("compensation_call") or call.get("function", {}).get("compensation_call")),
                runtime_context=runtime_context,
            )
            results.append(result)
            # X-09 · budget 终态切断批量循环（FIX-40 P3-6）：run 已 BUDGET_EXCEEDED
            # 时不再发起后续工具调用（此前靠 20 次硬顶兜底）。
            if result.error_type == "BudgetExceeded":
                logger.warning(
                    "tool call batch cut at {}/{} after run budget exceeded (tool={})",
                    len(results),
                    len(capped_calls),
                    call["function"]["name"],
                )
                break
        return results

    # ------------------------------------------------------------------
    # DAG-aware plan execution
    # ------------------------------------------------------------------

    async def execute_plan(
        self,
        plan: ExecutablePlan,
        user_id: str,
        db_session: Any | None,
        progress_callback: Any | None = None,
        execution_observer: Any | None = None,
        runtime_context: dict[str, Any] | None = None,
    ) -> PlanExecutionResult:
        """Execute an ExecutablePlan respecting DAG layer ordering.

        Steps within a layer run concurrently (asyncio.gather).
        Output from earlier steps is propagated to dependent steps
        via ``output_key`` → parameter substitution.

        If a *required* step fails, execution is aborted and remaining
        layers are skipped.

        Falls back to sequential execution when no ``execution_order``
        is defined (backward compatible).
        """
        layers = plan.get_execution_layers()
        result = PlanExecutionResult(
            plan_id=plan.plan_id,
            total_layers=len(layers),
        )

        # Shared output store: step_id -> output_data
        output_store: dict[str, dict[str, Any]] = {}

        for layer_idx, layer in enumerate(layers):
            if not layer:
                continue

            # Resolve parameter placeholders from output_store
            resolved_layer = self._resolve_layer_params(layer, output_store)
            layer_number = layer_idx + 1

            await self._notify_execution_observer(
                execution_observer,
                {
                    "event": "layer_start",
                    "layer_index": layer_idx,
                    "layer_number": layer_number,
                    "total_layers": len(layers),
                    "step_ids": [tc.id for tc in resolved_layer],
                    "tool_names": [tc.name for tc in resolved_layer],
                },
            )

            # Execute steps within this layer concurrently (bounded)
            semaphore = asyncio.Semaphore(_DAG_LAYER_MAX_CONCURRENCY)

            # B023: 经默认参绑定本层 semaphore——gather 虽在同层迭代内被 await
            # （现行行为已正确），显式绑定消除闭包后期绑定隐患，防后续重构
            # （如把 gather 移出层循环）时静默绑到末轮信号量。
            async def _bounded_step(
                tc_item: Any,
                sem: asyncio.Semaphore = semaphore,
            ) -> Any:
                async with sem:
                    return await self._execute_step(
                        tc_item,
                        user_id,
                        db_session,
                        progress_callback,
                        runtime_context=runtime_context,
                    )

            step_results = await asyncio.gather(
                *(_bounded_step(tc) for tc in resolved_layer),
                return_exceptions=True,
            )

            # Process results
            layer_aborted = False
            for tc, sr in zip(resolved_layer, step_results, strict=False):
                if isinstance(sr, BaseException):
                    sr = StepResult(
                        step_id=tc.id,
                        tool_name=tc.name,
                        tool_result=ToolResult(
                            success=False,
                            tool_name=tc.name,
                            error_message=str(sr),
                        ),
                    )

                result.step_results.append(sr)
                result.tool_results.append(sr.tool_result)

                await self._notify_execution_observer(
                    execution_observer,
                    {
                        "event": "step_completed",
                        "layer_index": layer_idx,
                        "layer_number": layer_number,
                        "step_id": sr.step_id,
                        "tool_name": sr.tool_name,
                        "success": sr.tool_result.success,
                        "duration_ms": sr.duration_ms,
                    },
                )

                # Store output for downstream steps
                if sr.output_key and sr.tool_result.success:
                    output_store[sr.step_id] = sr.output_data

                # Check required step failure
                criteria = tc.success_criteria
                is_required = criteria.required if criteria else True
                if not sr.tool_result.success and is_required:
                    layer_aborted = True

            result.execution_layers_completed = layer_idx + 1

            await self._notify_execution_observer(
                execution_observer,
                {
                    "event": "layer_end",
                    "layer_index": layer_idx,
                    "layer_number": layer_number,
                    "total_layers": len(layers),
                    "aborted": layer_aborted,
                    "completed_steps": len(resolved_layer),
                },
            )

            # X-09 · budget 终态切断 DAG 循环（FIX-40 P3-6）：任一步因 BUDGET_EXCEEDED
            # 被拒 → 不再启动后续层（剩余步骤全部跳过，非静默：结果里保留拒绝原因）。
            if any(sr.tool_result.error_type == "BudgetExceeded" for sr in result.step_results):
                result.budget_exceeded = True
                result.aborted = True
                result.abort_reason = f"Run budget exceeded in layer {layer_idx}"
                logger.warning(
                    "Plan {} cut at layer {}: run budget exceeded; remaining layers skipped",
                    plan.plan_id,
                    layer_idx,
                )
                await self._notify_execution_observer(
                    execution_observer,
                    {
                        "event": "execution_aborted",
                        "layer_index": layer_idx,
                        "layer_number": layer_number,
                        "reason": result.abort_reason,
                    },
                )
                break

            if layer_aborted:
                result.aborted = True
                # 演示缺陷 ❌#4：确认门（ConfirmationRequired）不是执行失败——
                # 是「等待用户批准」。置 awaiting_user_confirmation 让聊天层把
                # 用户可见文案路由为自然话术；开发者诊断（含 layer 细节）只进
                # 日志，不进聊天文本。
                confirmation_gate_hit = any(
                    (sr.tool_result.error_type or "") == CONFIRMATION_REQUIRED_ERROR_TYPE for sr in result.step_results
                )
                if confirmation_gate_hit:
                    result.awaiting_user_confirmation = True
                    result.abort_reason = (
                        f"Confirmation-required step paused at layer {layer_idx} (awaiting user approval)"
                    )
                    logger.warning(
                        "Plan {} paused at layer {}: confirmation-required tool awaits user approval",
                        plan.plan_id,
                        layer_idx,
                    )
                else:
                    result.abort_reason = f"Required step failed in layer {layer_idx}"
                    logger.warning(
                        "Plan {} aborted at layer {}: required step failed",
                        plan.plan_id,
                        layer_idx,
                    )
                await self._notify_execution_observer(
                    execution_observer,
                    {
                        "event": "execution_aborted",
                        "layer_index": layer_idx,
                        "layer_number": layer_number,
                        "reason": result.abort_reason,
                        "awaiting_user_confirmation": result.awaiting_user_confirmation,
                    },
                )
                break

        await self._notify_execution_observer(
            execution_observer,
            {
                "event": "execution_end",
                "plan_id": plan.plan_id,
                "total_layers": len(layers),
                "layers_completed": result.execution_layers_completed,
                "aborted": result.aborted,
                "abort_reason": result.abort_reason,
                "steps_total": len(result.step_results),
            },
        )

        return result

    async def _execute_step(
        self,
        spec: ToolCallSpec,
        user_id: str,
        db_session: Any | None,
        progress_callback: Any | None,
        runtime_context: dict[str, Any] | None = None,
    ) -> StepResult:
        """Execute a single ToolCallSpec and return StepResult.

        X-09 · 有界确定性重试（卡面工作项 5）：失败结果先过三族分类器——
        RETRYABLE 且 side_effect_state=none（账本随事务回滚，无效果残留）时按
        指数退避重试，上限 :data:`DEFAULT_MAX_RETRY_ATTEMPTS`；超限即死信
        （保留最后一次失败结果，由 run 层落明确终态）。UNKNOWN/PERMANENT 族
        与 BUDGET_EXCEEDED 恒不重试。

        键语义：重试以**派生 tool_call_id**（``{spec.id}:retry:{n}``）开新账本
        行——原 id 的账本历史不被改写（同 id 重放仍恰一次，X-06 守卫零弱化）；
        side_effect_state=unknown 的失败根本不进入重试（unknown 族），新键
        重试只发生在旧账本已回滚（nothing happened）的可证明安全场景。
        """
        start = time.time()
        metadata = tool_registry.get_tool_metadata(spec.name)
        tool_effect = metadata.effect.value if metadata is not None else None

        attempt = 1
        retries = 0
        tool_result = await self.execute_tool_call(
            tool_name=spec.name,
            arguments=spec.params,
            user_id=user_id,
            db_session=db_session,
            progress_callback=progress_callback,
            tool_call_id=spec.id,
            compensation_call=spec.compensation_call,
            runtime_context=runtime_context,
        )
        while not tool_result.success:
            classification = classify_tool_result_failure(tool_result, tool_effect=tool_effect)
            should_retry, delay = retry_decision(
                classification,
                attempt=attempt,
                max_attempts=DEFAULT_MAX_RETRY_ATTEMPTS,
                base_delay_seconds=DEFAULT_RETRY_BASE_DELAY_SECONDS,
                max_delay_seconds=DEFAULT_RETRY_MAX_DELAY_SECONDS,
            )
            if not should_retry:
                if classification.retryable:
                    logger.warning(
                        "step {} (tool {}) dead-lettered after {} attempt(s): {}",
                        spec.id,
                        spec.name,
                        attempt,
                        tool_result.error_type,
                    )
                break
            logger.info(
                "retrying step {} (tool {}) attempt {}->{} in {:.3f}s (family={}, side_effect={})",
                spec.id,
                spec.name,
                attempt,
                attempt + 1,
                delay,
                classification.family.value,
                classification.side_effect_state,
            )
            await asyncio.sleep(delay)
            attempt += 1
            retries += 1
            tool_result = await self.execute_tool_call(
                tool_name=spec.name,
                arguments=spec.params,
                user_id=user_id,
                db_session=db_session,
                progress_callback=progress_callback,
                tool_call_id=f"{spec.id}:retry:{attempt}",
                compensation_call=spec.compensation_call,
                runtime_context=runtime_context,
            )
        duration_ms = int((time.time() - start) * 1000)
        if retries and tool_result.success:
            tool_result = tool_result.model_copy(update={"data": {**(tool_result.data or {}), "retries": retries}})

        # Extract output_data from result for downstream propagation
        output_data: dict[str, Any] = {}
        if spec.output_key and tool_result.success and tool_result.data:
            if isinstance(tool_result.data, dict):
                output_data = tool_result.data
            else:
                output_data = {"_value": tool_result.data}

        return StepResult(
            step_id=spec.id,
            tool_name=spec.name,
            tool_result=tool_result,
            duration_ms=duration_ms,
            output_key=spec.output_key,
            output_data=output_data,
        )

    @staticmethod
    def _resolve_layer_params(
        layer: list[ToolCallSpec],
        output_store: dict[str, dict[str, Any]],
    ) -> list[ToolCallSpec]:
        """Substitute placeholder params with outputs from completed steps.

        If a step's param value matches a pattern like
        ``"$ref:step_id:key"`` or is exactly ``"$ref:step_id"``,
        replace it with the corresponding value from output_store.
        Also handles the common case where ``depends_on`` lists a step
        whose output contains the needed ID (e.g. plan_id, task_id).
        """
        if not output_store:
            return layer

        for tc in layer:
            for dep_id in tc.depends_on:
                if dep_id not in output_store:
                    continue
                dep_output = output_store[dep_id]
                # Auto-inject matching keys from dependency output
                for param_key, param_val in list(tc.params.items()):
                    # Explicit $ref placeholder
                    if isinstance(param_val, str) and param_val.startswith("$ref:"):
                        parts = param_val.split(":", 2)
                        ref_step = parts[1] if len(parts) > 1 else ""
                        ref_key = parts[2] if len(parts) > 2 else param_key
                        if ref_step == dep_id and ref_key in dep_output:
                            tc.params[param_key] = dep_output[ref_key]
                    # Auto-fill: if param value looks like a placeholder
                    # (empty or __pending__) and dep has the key
                    elif param_val in ("", "__pending__") and param_key in dep_output:
                        tc.params[param_key] = dep_output[param_key]

        return layer
