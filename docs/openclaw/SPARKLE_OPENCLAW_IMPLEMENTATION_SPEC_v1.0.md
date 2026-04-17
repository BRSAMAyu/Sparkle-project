# Sparkle x OpenClaw Integration — Implementation Specification v1.0

> **Status**: Approved Architecture Spec
> **Author**: Chief Architect (Claude Opus 4.6)
> **Date**: 2026-03-27
> **Scope**: Phase 0 (Protocol & Trust Foundation) + Phase 1 (PoC) + Phase 2-3 Interface Contracts
> **Principle**: Zero-invasion to existing production chain

---

## Table of Contents

1. [Design Principles & Safety Guarantees](#1-design-principles--safety-guarantees)
2. [Phase 0: Data Models & DB Migration](#2-phase-0-data-models--db-migration)
3. [Phase 0: Execution Router](#3-phase-0-execution-router)
4. [Phase 0: Trust Engine](#4-phase-0-trust-engine)
5. [Phase 0: Event Types Extension](#5-phase-0-event-types-extension)
6. [Phase 0: Task Model Extension](#6-phase-0-task-model-extension)
7. [Phase 0: Configuration Extension](#7-phase-0-configuration-extension)
8. [Phase 1: OpenClaw Adapter](#8-phase-1-openclaw-adapter)
9. [Phase 1: Execution Service](#9-phase-1-execution-service)
10. [Phase 1: REST API — Executions](#10-phase-1-rest-api--executions)
11. [Phase 1: Mobile — Handoff Button & Status Display](#11-phase-1-mobile--handoff-button--status-display)
12. [Phase 2: Execution Ingestor (Interface Contract)](#12-phase-2-execution-ingestor-interface-contract)
13. [Phase 3: Profile Feedback Loop (Interface Contract)](#13-phase-3-profile-feedback-loop-interface-contract)
14. [File Manifest & Dependency Graph](#14-file-manifest--dependency-graph)
15. [Verification Checklist](#15-verification-checklist)
16. [Appendix: OpenClaw API Quick Reference](#16-appendix-openclaw-api-quick-reference)

---

## 1. Design Principles & Safety Guarantees

### 1.1 Zero-Invasion Contract

Every new component MUST satisfy ALL of the following:

```
1. ADDITIVE ONLY — New files only; existing files receive only additive changes
   (new fields with defaults, new imports, new route registrations)

2. FEATURE FLAG GATED — All OpenClaw behavior behind settings.OPENCLAW_ENABLED (default: False)
   When False, the system behaves EXACTLY as before

3. NO IMPORT SIDE EFFECTS — New modules import existing ones; existing modules
   NEVER import new OpenClaw modules (except models/__init__.py registration)

4. EXISTING TESTS UNCHANGED — All existing tests must pass without modification.
   New tests go in new test files only

5. SOFT SCHEMA — New DB columns are ALL nullable with defaults;
   no NOT NULL constraints on existing tables
```

### 1.2 Adapter Pattern

```
Existing System                        New Integration Layer
┌──────────────────┐                  ┌──────────────────────┐
│ ChatOrchestrator │ ─── unchanged ──→│                      │
│ ToolExecutor     │                  │                      │
│ LangGraphPlanner │                  │  (Does NOT import    │
│ EventBus         │ ◄── events ─────│   these modules)     │
│ PlanStateService │ ◄── reads ──────│                      │
│ AdaptiveReplanner│ ◄── events ─────│                      │
└──────────────────┘                  └──────────────────────┘
         ▲                                      │
         │                                      │
    (existing)                             (new, additive)
         │                                      │
┌──────────────────┐                  ┌──────────────────────┐
│ Task model       │ ◄── new field ──│ ExecutionIntent model │
│ models/__init__  │ ◄── new export ─│ ExecutionRecord model │
│ event_types.py   │ ◄── new events ─│ ExecutionRouter       │
│ router.py        │ ◄── new route ──│ ExecutionTrustEngine  │
│ settings.py      │ ◄── new config ─│ OpenClawAdapter       │
└──────────────────┘                  │ ExecutionService      │
                                      │ executions.py (API)   │
                                      └──────────────────────┘
```

### 1.3 Data Flow Invariant

```
OpenClaw Result → ResultParser → TrustEngine.evaluate() → ExecutionRecord (always)
                                      │
                                      ├─ RAW → STOP (no further writes)
                                      ├─ VALIDATED → Task status + PlanExecutionRecord
                                      └─ TRUSTED → Behavior signals + Profile
```

**This invariant is NON-NEGOTIABLE.** No code path may write OpenClaw results to Task status, PlanState, or behavior signals without passing through TrustEngine.

---

## 2. Phase 0: Data Models & DB Migration

### 2.1 ExecutionIntent Model

**File**: `backend/app/models/execution_intent.py` (NEW)

```python
"""
ExecutionIntent — 面向外部执行器的结构化任务协议
"""
from __future__ import annotations

import enum
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

# JSONB with SQLite fallback (matches project convention)
JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ExecutionMode(str, enum.Enum):
    """任务执行模式"""
    HUMAN = "human"          # 纯人工执行（当前默认）
    AGENT = "agent"          # 委派给外部执行器
    HYBRID = "hybrid"        # 人机协同


class ExecutorType(str, enum.Enum):
    """执行器类型"""
    MANUAL = "manual"        # 用户手动（当前默认）
    OPENCLAW = "openclaw"    # OpenClaw 执行器
    # 未来可扩展: BROWSER_USE = "browser_use"


class ExecutionTargetEnv(str, enum.Enum):
    """执行目标环境"""
    BROWSER = "browser"      # 浏览器操作
    SHELL = "shell"          # 命令行/脚本
    API = "api"              # API 调用
    DOCUMENT = "document"    # 文档处理
    HUMAN = "human"          # 人类世界动作


class ExecutionIntentStatus(str, enum.Enum):
    """执行意图生命周期状态"""
    DRAFT = "draft"                          # 已生成，未确认
    READY = "ready"                          # 用户已确认，待分发
    DISPATCHED = "dispatched"                # 已发送给执行器
    RUNNING = "running"                      # 执行中
    WAITING_APPROVAL = "waiting_approval"    # 等待用户审批
    SUCCEEDED = "succeeded"                  # 成功完成
    PARTIAL = "partial"                      # 部分完成
    FAILED = "failed"                        # 失败
    CANCELED = "canceled"                    # 用户取消
    TIMED_OUT = "timed_out"                  # 超时
    HANDED_BACK = "handed_back"              # 回退给用户手动完成


class TrustLevel(str, enum.Enum):
    """执行结果信任等级"""
    RAW = "raw"              # 原始结果，未校验
    VALIDATED = "validated"  # 通过 schema + 合理性校验
    TRUSTED = "trusted"      # 用户确认 或 自动信任（高历史成功率）


class ExecutionIntent(BaseModel):
    """
    面向执行层的标准任务协议

    关键设计：
    - 每个 intent 与一个 task 1:1 绑定
    - idempotency_key 防重复触发
    - trust_level 控制结果写入范围
    - policy 控制安全边界
    """
    __tablename__ = "execution_intents"

    # === Foreign Keys ===
    plan_id = Column(GUID(), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # === Routing Decision ===
    execution_mode = Column(
        Enum(ExecutionMode, name="execution_mode_enum", create_constraint=False),
        nullable=False,
        default=ExecutionMode.HUMAN,
    )
    executor = Column(
        Enum(ExecutorType, name="executor_type_enum", create_constraint=False),
        nullable=False,
        default=ExecutorType.MANUAL,
    )

    # === Execution Specification ===
    goal = Column(Text, nullable=False)                         # 结构化目标描述
    instructions = Column(JSONBCompat, nullable=False, default=list)  # 约束指令列表
    target_env = Column(
        Enum(ExecutionTargetEnv, name="execution_target_env_enum", create_constraint=False),
        nullable=True,
    )
    policy = Column(JSONBCompat, nullable=False, default=dict)  # 安全策略
    success_criteria = Column(JSONBCompat, nullable=False, default=dict)  # 成功判定标准
    result_contract = Column(JSONBCompat, nullable=False, default=dict)   # 结果格式约束
    timeout_seconds = Column(Integer, nullable=False, default=300)

    # === Lifecycle ===
    status = Column(
        Enum(ExecutionIntentStatus, name="execution_intent_status_enum", create_constraint=False),
        nullable=False,
        default=ExecutionIntentStatus.DRAFT,
        index=True,
    )

    # === Trust ===
    trust_level = Column(
        Enum(TrustLevel, name="trust_level_enum", create_constraint=False),
        nullable=False,
        default=TrustLevel.RAW,
    )

    # === Traceability ===
    external_run_id = Column(String(255), nullable=True, index=True)   # OpenClaw runId
    idempotency_key = Column(String(255), nullable=False, unique=True) # plan_id:task_id:version
    error_category = Column(String(100), nullable=True)                # 失败归因分类
    error_message = Column(Text, nullable=True)

    # === Timestamps ===
    dispatched_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # === Relationships ===
    task = relationship("Task", backref="execution_intents", foreign_keys=[task_id])
    plan = relationship("Plan", backref="execution_intents", foreign_keys=[plan_id])
    user = relationship("User", backref="execution_intents", foreign_keys=[user_id])

    __table_args__ = (
        Index("idx_exec_intent_user_status", "user_id", "status"),
        Index("idx_exec_intent_task", "task_id"),
        Index("idx_exec_intent_created", "created_at"),
        Index("idx_exec_intent_external_run", "external_run_id"),
    )

    def __repr__(self):
        return f"<ExecutionIntent(task_id={self.task_id}, status={self.status}, executor={self.executor})>"

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "plan_id": str(self.plan_id) if self.plan_id else None,
            "task_id": str(self.task_id),
            "user_id": str(self.user_id),
            "execution_mode": self.execution_mode.value if self.execution_mode else None,
            "executor": self.executor.value if self.executor else None,
            "goal": self.goal,
            "instructions": self.instructions,
            "target_env": self.target_env.value if self.target_env else None,
            "policy": self.policy,
            "success_criteria": self.success_criteria,
            "result_contract": self.result_contract,
            "timeout_seconds": self.timeout_seconds,
            "status": self.status.value if self.status else None,
            "trust_level": self.trust_level.value if self.trust_level else None,
            "external_run_id": self.external_run_id,
            "idempotency_key": self.idempotency_key,
            "error_category": self.error_category,
            "error_message": self.error_message,
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
```

### 2.2 ExecutionRecord Model

**File**: `backend/app/models/execution_record.py` (NEW)

```python
"""
ExecutionRecord — OpenClaw 执行结果的原始记录
设计原则：先存后判，所有结果都先落库，再由 TrustEngine 决定写入范围
"""
from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import relationship

from app.models.base import GUID, BaseModel

JSONBCompat = JSONB().with_variant(JSON(), "sqlite")


class ExecutionRecord(BaseModel):
    """
    外部执行器的原始结果记录

    与 PlanExecutionRecord 的区别：
    - PlanExecutionRecord 记录的是 Sparkle 内部 ToolExecutor 的执行反馈
    - ExecutionRecord 记录的是外部执行器（OpenClaw）的原始结果
    - ExecutionRecord 经过 TrustEngine 评估后，VALIDATED 级别的数据才会被写入 PlanExecutionRecord
    """
    __tablename__ = "execution_records"

    # === Foreign Keys ===
    execution_intent_id = Column(
        GUID(), ForeignKey("execution_intents.id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True,  # 1:1 with intent
    )
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(GUID(), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)

    # === Executor Metadata ===
    executor_type = Column(String(50), nullable=False, default="openclaw")
    external_run_id = Column(String(255), nullable=True)

    # === Raw Result ===
    raw_response = Column(JSONBCompat, nullable=False, default=dict)  # OpenClaw 原始响应
    parsed_output = Column(JSONBCompat, nullable=True)                # 解析后的结构化输出
    artifacts = Column(JSONBCompat, nullable=False, default=list)     # 产物列表 (screenshots, files, etc.)

    # === Quality Assessment ===
    trust_level = Column(String(20), nullable=False, default="raw")   # raw / validated / trusted
    validation_passed = Column(Integer, nullable=True)                # schema 校验通过的字段数
    validation_total = Column(Integer, nullable=True)                 # schema 校验总字段数
    quality_score = Column(Float, nullable=True)                      # 0.0 - 1.0

    # === Execution Metrics ===
    duration_ms = Column(Integer, nullable=True)
    token_usage = Column(JSONBCompat, nullable=True)                  # {input_tokens, output_tokens}
    tool_calls_count = Column(Integer, nullable=True, default=0)
    approval_requested = Column(Integer, nullable=True, default=0)    # 审批请求次数

    # === Error Info ===
    error_category = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)

    # === Timestamps ===
    execution_started_at = Column(DateTime, nullable=True)
    execution_completed_at = Column(DateTime, nullable=True)

    # === Relationships ===
    execution_intent = relationship("ExecutionIntent", backref="execution_record", uselist=False)
    user = relationship("User", backref="execution_records")

    __table_args__ = (
        Index("idx_exec_record_user", "user_id"),
        Index("idx_exec_record_intent", "execution_intent_id"),
        Index("idx_exec_record_trust", "trust_level"),
        Index("idx_exec_record_created", "created_at"),
    )

    def __repr__(self):
        return (
            f"<ExecutionRecord(intent_id={self.execution_intent_id}, "
            f"trust={self.trust_level}, score={self.quality_score})>"
        )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "execution_intent_id": str(self.execution_intent_id),
            "user_id": str(self.user_id),
            "task_id": str(self.task_id) if self.task_id else None,
            "executor_type": self.executor_type,
            "external_run_id": self.external_run_id,
            "parsed_output": self.parsed_output,
            "artifacts": self.artifacts,
            "trust_level": self.trust_level,
            "quality_score": self.quality_score,
            "duration_ms": self.duration_ms,
            "error_category": self.error_category,
            "error_message": self.error_message,
            "execution_started_at": self.execution_started_at.isoformat() if self.execution_started_at else None,
            "execution_completed_at": self.execution_completed_at.isoformat() if self.execution_completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
```

### 2.3 Alembic Migration

**File**: `backend/alembic/versions/oc001_add_execution_intent_and_record.py` (NEW)

```python
"""add execution_intent and execution_record tables, extend tasks

Revision ID: oc001a2b3c4d5
Revises: e8f1a2b3c4d5
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "oc001a2b3c4d5"
down_revision = "e8f1a2b3c4d5"  # <-- MUST match current head. Verify with: alembic heads
branch_labels = None
depends_on = None


def _is_postgres(conn) -> bool:
    return conn.dialect.name == "postgresql"


def upgrade() -> None:
    conn = op.get_bind()
    is_pg = _is_postgres(conn)
    json_type = postgresql.JSONB if is_pg else sa.JSON

    # --- execution_intents table ---
    op.create_table(
        "execution_intents",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column("plan_id", sa.CHAR(36), sa.ForeignKey("plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("task_id", sa.CHAR(36), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("execution_mode", sa.String(20), nullable=False, server_default="human"),
        sa.Column("executor", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("goal", sa.Text, nullable=False),
        sa.Column("instructions", json_type(), nullable=False, server_default="[]"),
        sa.Column("target_env", sa.String(20), nullable=True),
        sa.Column("policy", json_type(), nullable=False, server_default="{}"),
        sa.Column("success_criteria", json_type(), nullable=False, server_default="{}"),
        sa.Column("result_contract", json_type(), nullable=False, server_default="{}"),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="300"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("trust_level", sa.String(20), nullable=False, server_default="raw"),
        sa.Column("external_run_id", sa.String(255), nullable=True),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("error_category", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("dispatched_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_exec_intent_user_status", "execution_intents", ["user_id", "status"])
    op.create_index("idx_exec_intent_task", "execution_intents", ["task_id"])
    op.create_index("idx_exec_intent_created", "execution_intents", ["created_at"])
    op.create_index("idx_exec_intent_external_run", "execution_intents", ["external_run_id"])
    op.create_index("idx_exec_intent_plan", "execution_intents", ["plan_id"])

    # --- execution_records table ---
    op.create_table(
        "execution_records",
        sa.Column("id", sa.CHAR(36), primary_key=True, nullable=False),
        sa.Column("execution_intent_id", sa.CHAR(36),
                  sa.ForeignKey("execution_intents.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("user_id", sa.CHAR(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task_id", sa.CHAR(36), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("executor_type", sa.String(50), nullable=False, server_default="openclaw"),
        sa.Column("external_run_id", sa.String(255), nullable=True),
        sa.Column("raw_response", json_type(), nullable=False, server_default="{}"),
        sa.Column("parsed_output", json_type(), nullable=True),
        sa.Column("artifacts", json_type(), nullable=False, server_default="[]"),
        sa.Column("trust_level", sa.String(20), nullable=False, server_default="raw"),
        sa.Column("validation_passed", sa.Integer, nullable=True),
        sa.Column("validation_total", sa.Integer, nullable=True),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("token_usage", json_type(), nullable=True),
        sa.Column("tool_calls_count", sa.Integer, nullable=True, server_default="0"),
        sa.Column("approval_requested", sa.Integer, nullable=True, server_default="0"),
        sa.Column("error_category", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("execution_started_at", sa.DateTime, nullable=True),
        sa.Column("execution_completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_exec_record_user", "execution_records", ["user_id"])
    op.create_index("idx_exec_record_intent", "execution_records", ["execution_intent_id"])
    op.create_index("idx_exec_record_trust", "execution_records", ["trust_level"])
    op.create_index("idx_exec_record_created", "execution_records", ["created_at"])

    # --- Extend tasks table: add execution_mode column ---
    # NULLABLE with default — zero impact on existing data
    op.add_column(
        "tasks",
        sa.Column("execution_mode", sa.String(20), nullable=True, server_default=None),
    )


def downgrade() -> None:
    op.drop_column("tasks", "execution_mode")
    op.drop_table("execution_records")
    op.drop_table("execution_intents")
```

### 2.4 Model Registration

**Additions to** `backend/app/models/__init__.py`:

```python
# --- Add these imports (at appropriate alphabetical position) ---
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionRecord,        # Note: if you put ExecutionRecord in its own file, import from there
    ExecutorType,
    ExecutionTargetEnv,
    TrustLevel,
)
from app.models.execution_record import ExecutionRecord

# --- Add to __all__ list (in the "# Plan Execution" section) ---
    # Execution Intent (OpenClaw Integration)
    "ExecutionIntent",
    "ExecutionIntentStatus",
    "ExecutionMode",
    "ExecutorType",
    "ExecutionTargetEnv",
    "TrustLevel",
    "ExecutionRecord",
```

---

## 3. Phase 0: Execution Router

**File**: `backend/app/core/execution_router.py` (NEW)

```python
"""
ExecutionRouter — 决定任务应该由谁执行

设计原则：
- Phase 0 只做分类标注，不触发实际外部执行
- 只在 OPENCLAW_ENABLED=True 时返回 AGENT/HYBRID
- 默认保守：宁可返回 HUMAN 也不误判为 AGENT
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.models.execution_intent import ExecutionMode, ExecutionTargetEnv

logger = logging.getLogger(__name__)


# === 硬性排除规则 ===

# 这些任务类型永远不能交给 AI 执行
HUMAN_ONLY_TASK_TYPES = frozenset({
    "learning",      # 学习型 — 用户需要亲自完成才有意义
    "training",      # 训练型
    "reflection",    # 反思型
})

# 这些关键词出现在任务目标中时，强制人工
HUMAN_ONLY_KEYWORDS = frozenset({
    "运动", "锻炼", "跑步", "健身",              # 物理世界
    "转账", "付款", "汇款", "支付",              # 金融操作
    "密码", "重置密码", "修改密码", "账号安全",   # 安全敏感
    "发消息", "发邮件", "发送",                   # 对外通信
})

# 允许 AI 执行的目标环境
AGENT_CAPABLE_ENVS = frozenset({
    ExecutionTargetEnv.BROWSER,
    ExecutionTargetEnv.SHELL,
    ExecutionTargetEnv.API,
    ExecutionTargetEnv.DOCUMENT,
})

# 允许 AI 执行的任务类型
AGENT_ELIGIBLE_TASK_TYPES = frozenset({
    "planning",     # 规划辅助
    "social",       # 社交信息整理（只读）
    "ocr",          # 文档识别
})


@dataclass
class RoutingDecision:
    """路由决策结果"""
    execution_mode: ExecutionMode
    target_env: ExecutionTargetEnv | None = None
    reason: str = ""
    confidence: float = 0.0
    risk_flags: list[str] = field(default_factory=list)


class ExecutionRouter:
    """
    任务执行路由器

    Usage:
        router = ExecutionRouter(openclaw_enabled=settings.OPENCLAW_ENABLED)
        decision = router.classify(task_type="ocr", goal="整理今天的未读邮件")
    """

    def __init__(self, openclaw_enabled: bool = False):
        self._openclaw_enabled = openclaw_enabled

    def classify(
        self,
        *,
        task_type: str,
        goal: str,
        has_side_effects: bool = False,
        has_clear_criteria: bool = False,
        task_tags: list[str] | None = None,
    ) -> RoutingDecision:
        """
        对任务进行执行模式分类

        Args:
            task_type: TaskType 枚举值 (str)
            goal: 任务目标描述
            has_side_effects: 任务是否有副作用（写入、修改、发送）
            has_clear_criteria: 是否有明确的成功判定标准
            task_tags: 任务标签

        Returns:
            RoutingDecision
        """
        risk_flags: list[str] = []

        # Rule 1: Feature flag check
        if not self._openclaw_enabled:
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                reason="openclaw_disabled",
                confidence=1.0,
            )

        # Rule 2: Hard exclusion by task type
        if task_type in HUMAN_ONLY_TASK_TYPES:
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                reason=f"task_type_excluded:{task_type}",
                confidence=1.0,
            )

        # Rule 3: Hard exclusion by keyword
        for keyword in HUMAN_ONLY_KEYWORDS:
            if keyword in goal:
                risk_flags.append(f"blocked_keyword:{keyword}")
                return RoutingDecision(
                    execution_mode=ExecutionMode.HUMAN,
                    reason=f"keyword_blocked:{keyword}",
                    confidence=1.0,
                    risk_flags=risk_flags,
                )

        # Rule 4: Side effects without clear criteria → HUMAN
        if has_side_effects and not has_clear_criteria:
            risk_flags.append("side_effects_without_criteria")
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                reason="side_effects_no_criteria",
                confidence=0.9,
                risk_flags=risk_flags,
            )

        # Rule 5: Eligible task type + no side effects → AGENT
        if task_type in AGENT_ELIGIBLE_TASK_TYPES and not has_side_effects:
            target_env = self._infer_target_env(goal)
            return RoutingDecision(
                execution_mode=ExecutionMode.AGENT,
                target_env=target_env,
                reason="eligible_readonly_task",
                confidence=0.8,
            )

        # Rule 6: Side effects + clear criteria → HYBRID
        if has_side_effects and has_clear_criteria:
            target_env = self._infer_target_env(goal)
            return RoutingDecision(
                execution_mode=ExecutionMode.HYBRID,
                target_env=target_env,
                reason="side_effects_with_criteria",
                confidence=0.7,
                risk_flags=["requires_user_approval"],
            )

        # Default: HUMAN
        return RoutingDecision(
            execution_mode=ExecutionMode.HUMAN,
            reason="default_conservative",
            confidence=0.5,
        )

    @staticmethod
    def _infer_target_env(goal: str) -> ExecutionTargetEnv | None:
        """从目标描述推断执行环境"""
        browser_keywords = {"浏览", "搜索", "网页", "打开", "登录", "邮件", "网站"}
        shell_keywords = {"脚本", "命令", "运行", "执行", "安装"}
        doc_keywords = {"文档", "整理", "摘要", "总结", "笔记", "PDF"}

        for kw in browser_keywords:
            if kw in goal:
                return ExecutionTargetEnv.BROWSER
        for kw in shell_keywords:
            if kw in goal:
                return ExecutionTargetEnv.SHELL
        for kw in doc_keywords:
            if kw in goal:
                return ExecutionTargetEnv.DOCUMENT

        return None
```

---

## 4. Phase 0: Trust Engine

**File**: `backend/app/core/execution_trust.py` (NEW)

```python
"""
ExecutionTrustEngine — 三级信任评估引擎

核心职责：
- 评估 OpenClaw 返回结果的信任等级
- 决定结果可以写入哪些数据层
- 防止数据污染

信任等级流转：
  RAW → (schema 校验 + 合理性检查) → VALIDATED → (用户确认 OR 自动提升) → TRUSTED
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# === 自动提升阈值 ===
AUTO_TRUST_MIN_HISTORY = 5         # 最少需要 N 次成功历史
AUTO_TRUST_SUCCESS_RATE = 0.85     # 同类任务成功率阈值
AUTO_TRUST_MIN_QUALITY = 0.7       # 最低质量分


@dataclass
class TrustEvaluation:
    """信任评估结果"""
    trust_level: str                    # "raw" | "validated" | "trusted"
    validation_passed: int = 0          # 通过的校验项数
    validation_total: int = 0           # 总校验项数
    quality_score: float = 0.0          # 0.0 - 1.0
    reasons: list[str] = field(default_factory=list)
    blocked_fields: list[str] = field(default_factory=list)  # 被拦截的异常字段

    @property
    def can_update_task(self) -> bool:
        """VALIDATED 及以上可更新 Task 状态"""
        return self.trust_level in ("validated", "trusted")

    @property
    def can_update_plan_record(self) -> bool:
        """VALIDATED 及以上可写入 PlanExecutionRecord"""
        return self.trust_level in ("validated", "trusted")

    @property
    def can_emit_behavior_signals(self) -> bool:
        """仅 TRUSTED 可写入行为信号和画像"""
        return self.trust_level == "trusted"


class ExecutionTrustEngine:
    """
    三级信任评估引擎

    Usage:
        engine = ExecutionTrustEngine()
        evaluation = engine.evaluate(
            raw_result=openclaw_response,
            success_criteria=intent.success_criteria,
            result_contract=intent.result_contract,
            executor_history=history_stats,
        )
    """

    def evaluate(
        self,
        *,
        raw_result: dict[str, Any],
        success_criteria: dict[str, Any],
        result_contract: dict[str, Any],
        executor_history: dict[str, Any] | None = None,
        user_confirmed: bool = False,
    ) -> TrustEvaluation:
        """
        评估执行结果的信任等级

        Args:
            raw_result: OpenClaw 返回的原始结果
            success_criteria: ExecutionIntent 中定义的成功标准
            result_contract: ExecutionIntent 中定义的结果格式约束
            executor_history: 该用户同类任务的历史执行统计
            user_confirmed: 用户是否已显式确认结果

        Returns:
            TrustEvaluation
        """
        reasons: list[str] = []
        blocked_fields: list[str] = []

        # Step 1: Basic sanity check
        if not raw_result:
            return TrustEvaluation(
                trust_level="raw",
                reasons=["empty_result"],
            )

        # Step 2: Content safety check
        safety_issues = self._check_content_safety(raw_result)
        if safety_issues:
            blocked_fields.extend(safety_issues)
            reasons.append(f"safety_blocked:{len(safety_issues)}_fields")
            return TrustEvaluation(
                trust_level="raw",
                blocked_fields=blocked_fields,
                reasons=reasons,
            )

        # Step 3: Schema validation against result_contract
        v_passed, v_total = self._validate_schema(raw_result, result_contract)

        # Step 4: Success criteria check
        criteria_met = self._check_success_criteria(raw_result, success_criteria)

        # Step 5: Calculate quality score
        quality_score = self._calculate_quality(
            validation_ratio=v_passed / max(v_total, 1),
            criteria_met=criteria_met,
            raw_result=raw_result,
        )

        # Step 6: Determine trust level
        if v_total > 0 and v_passed < v_total * 0.5:
            # Less than 50% schema match → RAW
            trust_level = "raw"
            reasons.append("schema_validation_below_50pct")
        elif not criteria_met:
            # Success criteria not met → RAW
            trust_level = "raw"
            reasons.append("success_criteria_not_met")
        elif quality_score < 0.3:
            trust_level = "raw"
            reasons.append("quality_too_low")
        else:
            # Basic validation passed → VALIDATED
            trust_level = "validated"
            reasons.append("schema_and_criteria_passed")

            # Check for auto-promotion to TRUSTED
            if user_confirmed:
                trust_level = "trusted"
                reasons.append("user_confirmed")
            elif self._can_auto_promote(executor_history, quality_score):
                trust_level = "trusted"
                reasons.append("auto_promoted_by_history")

        return TrustEvaluation(
            trust_level=trust_level,
            validation_passed=v_passed,
            validation_total=v_total,
            quality_score=quality_score,
            reasons=reasons,
            blocked_fields=blocked_fields,
        )

    def _check_content_safety(self, result: dict[str, Any]) -> list[str]:
        """检查结果中是否包含敏感/异常内容"""
        issues: list[str] = []
        result_str = str(result).lower()

        # Check for potential credential leaks
        sensitive_patterns = [
            "password", "secret", "api_key", "token",
            "credit_card", "ssn", "social_security",
        ]
        for pattern in sensitive_patterns:
            if pattern in result_str:
                issues.append(f"sensitive_content:{pattern}")

        # Check for injection attempts
        injection_patterns = ["<script", "javascript:", "eval(", "exec("]
        for pattern in injection_patterns:
            if pattern in result_str:
                issues.append(f"injection_attempt:{pattern}")

        return issues

    def _validate_schema(
        self,
        result: dict[str, Any],
        contract: dict[str, Any],
    ) -> tuple[int, int]:
        """
        校验结果是否符合 result_contract 定义的 schema

        Returns:
            (passed_count, total_count)
        """
        required_fields = contract.get("required_fields", [])
        if not required_fields:
            return (0, 0)  # No contract defined, skip validation

        passed = 0
        total = len(required_fields)

        for field_name in required_fields:
            if field_name in result and result[field_name] is not None:
                passed += 1

        return (passed, total)

    def _check_success_criteria(
        self,
        result: dict[str, Any],
        criteria: dict[str, Any],
    ) -> bool:
        """检查是否满足成功标准"""
        criteria_type = criteria.get("type")

        if not criteria_type:
            return True  # No criteria defined, assume success

        if criteria_type == "structured_output":
            required = criteria.get("required_fields", [])
            return all(
                field_name in result and result[field_name] is not None
                for field_name in required
            )

        if criteria_type == "contains_text":
            expected = criteria.get("expected_text", "")
            output_text = str(result.get("output", ""))
            return expected.lower() in output_text.lower()

        if criteria_type == "non_empty":
            output = result.get("output") or result.get("parsed_output")
            return bool(output)

        # Unknown criteria type → conservative pass
        logger.warning(f"Unknown success criteria type: {criteria_type}")
        return True

    def _calculate_quality(
        self,
        *,
        validation_ratio: float,
        criteria_met: bool,
        raw_result: dict[str, Any],
    ) -> float:
        """
        计算结果质量分 (0.0 - 1.0)

        权重：
        - Schema 校验比例: 40%
        - 成功标准是否满足: 30%
        - 结果丰富度: 30%
        """
        schema_score = validation_ratio * 0.4
        criteria_score = 0.3 if criteria_met else 0.0

        # Richness: check if result has meaningful content
        output = raw_result.get("output") or raw_result.get("parsed_output") or {}
        if isinstance(output, dict):
            richness = min(len(output) / 5.0, 1.0) * 0.3  # Normalize by 5 fields
        elif isinstance(output, str):
            richness = min(len(output) / 200.0, 1.0) * 0.3  # Normalize by 200 chars
        else:
            richness = 0.1  # Minimal score for non-empty

        return round(schema_score + criteria_score + richness, 3)

    def _can_auto_promote(
        self,
        history: dict[str, Any] | None,
        current_quality: float,
    ) -> bool:
        """
        判断是否可以自动提升到 TRUSTED

        条件（全部满足）：
        1. 至少 N 次同类任务历史
        2. 历史成功率 >= 阈值
        3. 当前质量分 >= 阈值
        """
        if not history:
            return False

        total_runs = history.get("total_runs", 0)
        success_rate = history.get("success_rate", 0.0)

        if total_runs < AUTO_TRUST_MIN_HISTORY:
            return False
        if success_rate < AUTO_TRUST_SUCCESS_RATE:
            return False
        if current_quality < AUTO_TRUST_MIN_QUALITY:
            return False

        return True
```

---

## 5. Phase 0: Event Types Extension

**Additions to** `backend/app/core/event_types.py`:

```python
# ============================================================
# Execution Delegation Events (OpenClaw Integration)
# ============================================================

class ExecutionDelegated(Event):
    """用户选择将任务委派给 AI 执行"""

    def __init__(
        self,
        user_id: str,
        task_id: str,
        plan_id: str | None,
        execution_intent_id: str,
        execution_mode: str,
        executor: str,
        target_env: str | None,
        timestamp: datetime | None = None,
    ):
        self.user_id = user_id
        self.task_id = task_id
        self.plan_id = plan_id
        self.execution_intent_id = execution_intent_id
        self.execution_mode = execution_mode
        self.executor = executor
        self.target_env = target_env
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "event_type": "execution.delegated",
            "user_id": self.user_id,
            "task_id": self.task_id,
            "plan_id": self.plan_id,
            "execution_intent_id": self.execution_intent_id,
            "execution_mode": self.execution_mode,
            "executor": self.executor,
            "target_env": self.target_env,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionStatusChanged(Event):
    """外部执行状态变更"""

    def __init__(
        self,
        user_id: str,
        execution_intent_id: str,
        task_id: str,
        old_status: str,
        new_status: str,
        trust_level: str | None = None,
        timestamp: datetime | None = None,
    ):
        self.user_id = user_id
        self.execution_intent_id = execution_intent_id
        self.task_id = task_id
        self.old_status = old_status
        self.new_status = new_status
        self.trust_level = trust_level
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "event_type": "execution.status_changed",
            "user_id": self.user_id,
            "execution_intent_id": self.execution_intent_id,
            "task_id": self.task_id,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "trust_level": self.trust_level,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionResultIngested(Event):
    """外部执行结果已被摄取和评估"""

    def __init__(
        self,
        user_id: str,
        execution_intent_id: str,
        execution_record_id: str,
        task_id: str,
        trust_level: str,
        quality_score: float,
        success: bool,
        error_category: str | None = None,
        timestamp: datetime | None = None,
    ):
        self.user_id = user_id
        self.execution_intent_id = execution_intent_id
        self.execution_record_id = execution_record_id
        self.task_id = task_id
        self.trust_level = trust_level
        self.quality_score = quality_score
        self.success = success
        self.error_category = error_category
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "event_type": "execution.result_ingested",
            "user_id": self.user_id,
            "execution_intent_id": self.execution_intent_id,
            "execution_record_id": self.execution_record_id,
            "task_id": self.task_id,
            "trust_level": self.trust_level,
            "quality_score": self.quality_score,
            "success": self.success,
            "error_category": self.error_category,
            "timestamp": self.timestamp.isoformat(),
        }


class ExecutionHandedBack(Event):
    """用户取回了委派中的任务"""

    def __init__(
        self,
        user_id: str,
        execution_intent_id: str,
        task_id: str,
        reason: str | None = None,
        progress_at_handback: float = 0.0,
        timestamp: datetime | None = None,
    ):
        self.user_id = user_id
        self.execution_intent_id = execution_intent_id
        self.task_id = task_id
        self.reason = reason
        self.progress_at_handback = progress_at_handback
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "event_type": "execution.handed_back",
            "user_id": self.user_id,
            "execution_intent_id": self.execution_intent_id,
            "task_id": self.task_id,
            "reason": self.reason,
            "progress_at_handback": self.progress_at_handback,
            "timestamp": self.timestamp.isoformat(),
        }
```

---

## 6. Phase 0: Task Model Extension

**Addition to** `backend/app/models/task.py`:

Only ONE additive change — a nullable column with no default impact:

```python
# Add this column to the Task class, after the existing 'tool_result_id' field:

    # === OpenClaw Integration (Phase 0) ===
    # Nullable, no impact on existing queries or behavior
    execution_mode = Column(String(20), nullable=True, default=None)
    # Values: None (legacy) | "human" | "agent" | "hybrid"
```

**Impact Assessment**: This column is nullable with no server_default. All existing Task creation code continues to work because the field defaults to `None`. No existing query filters on this column. The alembic migration handles the ALTER TABLE.

---

## 7. Phase 0: Configuration Extension

**Additions to** `backend/app/config/settings.py`:

```python
    # === OpenClaw Integration ===
    OPENCLAW_ENABLED: bool = False                          # Master feature flag
    OPENCLAW_GATEWAY_URL: str = ""                          # e.g., "http://127.0.0.1:18789"
    OPENCLAW_AUTH_TOKEN: str = ""                            # Bearer token
    OPENCLAW_DEFAULT_AGENT_ID: str = ""                     # Default agent ID
    OPENCLAW_DEFAULT_TIMEOUT_SECONDS: int = 300             # 5 minutes
    OPENCLAW_MAX_CONCURRENT_RUNS: int = 3                   # Per user
    OPENCLAW_TRUST_AUTO_PROMOTE_MIN_HISTORY: int = 5        # Auto-trust threshold
    OPENCLAW_TRUST_AUTO_PROMOTE_SUCCESS_RATE: float = 0.85  # Auto-trust threshold
```

---

## 8. Phase 1: OpenClaw Adapter

**Directory**: `backend/app/adapters/openclaw/` (NEW)

### 8.1 Config

**File**: `backend/app/adapters/openclaw/config.py`

```python
"""OpenClaw adapter configuration"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


@dataclass(frozen=True)
class OpenClawConfig:
    enabled: bool = False
    gateway_url: str = ""
    auth_token: str = ""
    default_agent_id: str = ""
    default_timeout_seconds: int = 300
    max_concurrent_runs: int = 3

    @classmethod
    def from_settings(cls) -> OpenClawConfig:
        return cls(
            enabled=settings.OPENCLAW_ENABLED,
            gateway_url=settings.OPENCLAW_GATEWAY_URL.rstrip("/"),
            auth_token=settings.OPENCLAW_AUTH_TOKEN,
            default_agent_id=settings.OPENCLAW_DEFAULT_AGENT_ID,
            default_timeout_seconds=settings.OPENCLAW_DEFAULT_TIMEOUT_SECONDS,
            max_concurrent_runs=settings.OPENCLAW_MAX_CONCURRENT_RUNS,
        )
```

### 8.2 Intent Translator

**File**: `backend/app/adapters/openclaw/intent_translator.py`

```python
"""
IntentTranslator — 将 ExecutionIntent 转换为 OpenClaw API 请求

Phase 1 使用 POST /v1/responses (同步 HTTP)
Phase 2 可扩展为 Gateway WebSocket RPC
"""
from __future__ import annotations

from typing import Any

from app.models.execution_intent import ExecutionIntent


class IntentTranslator:
    """
    将 Sparkle ExecutionIntent 翻译为 OpenClaw /v1/responses 请求体

    翻译规则：
    - intent.goal + intent.instructions → 合成为 input message
    - intent.policy → 注入到 instructions (system prompt)
    - intent.timeout_seconds → 映射为 OpenClaw timeout (目前通过 instructions 约束)
    - intent.target_env → 提示 OpenClaw 使用哪类工具
    """

    def translate(
        self,
        intent: ExecutionIntent,
        *,
        agent_id: str = "",
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """
        生成 OpenClaw /v1/responses 请求体

        Returns:
            dict 可直接作为 POST body
        """
        # Build the user message
        user_message = self._build_user_message(intent)

        # Build system instructions (policy + constraints)
        system_instructions = self._build_system_instructions(intent)

        # Build request
        request: dict[str, Any] = {
            "model": model_override or f"openclaw/{agent_id}" if agent_id else "openclaw",
            "input": user_message,
            "instructions": system_instructions,
            "stream": False,  # Phase 1: synchronous for simplicity
        }

        # Session key for traceability
        request["user"] = f"sparkle:{intent.user_id}:{intent.task_id}"

        return request

    def _build_user_message(self, intent: ExecutionIntent) -> str:
        """构建发送给 OpenClaw 的用户消息"""
        parts = [f"## Task Goal\n{intent.goal}"]

        if intent.instructions:
            constraints = "\n".join(f"- {i}" for i in intent.instructions)
            parts.append(f"\n## Constraints\n{constraints}")

        if intent.success_criteria:
            criteria_type = intent.success_criteria.get("type", "")
            required_fields = intent.success_criteria.get("required_fields", [])
            if required_fields:
                fields_str = ", ".join(required_fields)
                parts.append(
                    f"\n## Expected Output\n"
                    f"Type: {criteria_type}\n"
                    f"Required fields: {fields_str}"
                )

        if intent.result_contract:
            artifact_types = intent.result_contract.get("artifact_types", [])
            if artifact_types:
                parts.append(f"\n## Output Format\nProvide results as: {', '.join(artifact_types)}")

        return "\n".join(parts)

    def _build_system_instructions(self, intent: ExecutionIntent) -> str:
        """构建系统级约束指令"""
        lines = [
            "You are executing a delegated task from Sparkle AI Learning Assistant.",
            f"Task environment: {intent.target_env.value if intent.target_env else 'general'}",
            f"Time limit: {intent.timeout_seconds} seconds",
        ]

        policy = intent.policy or {}

        # Domain restrictions
        allowed_domains = policy.get("allowed_domains", [])
        if allowed_domains:
            lines.append(f"ONLY access these domains: {', '.join(allowed_domains)}")

        # Tool restrictions
        allowed_tools = policy.get("allowed_tools", [])
        if allowed_tools:
            lines.append(f"ONLY use these tools: {', '.join(allowed_tools)}")

        # Exec policy
        if not policy.get("allow_exec", False):
            lines.append("DO NOT execute shell commands or scripts.")

        # Safety
        lines.extend([
            "DO NOT send messages, emails, or make purchases.",
            "DO NOT modify account settings or passwords.",
            "If you encounter a login prompt or CAPTCHA, STOP and report it.",
            "Return results in a structured format.",
        ])

        return "\n".join(lines)
```

### 8.3 Result Parser

**File**: `backend/app/adapters/openclaw/result_parser.py`

```python
"""
ResultParser — 将 OpenClaw 响应解析为 Sparkle 标准化结果
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ResultParser:
    """
    解析 OpenClaw /v1/responses 的响应

    OpenClaw Response Format (simplified):
    {
        "id": "resp_xxx",
        "output": [
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "..."}]},
            {"type": "function_call", ...},
        ],
        "usage": {"input_tokens": N, "output_tokens": N},
        "status": "completed" | "failed" | ...
    }
    """

    def parse(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        """
        解析 OpenClaw 响应为标准化结果

        Returns:
            {
                "success": bool,
                "output": str,                # 合并后的文本输出
                "parsed_output": dict | None, # 尝试解析的结构化输出
                "artifacts": list[dict],      # 产物列表
                "tool_calls_count": int,
                "token_usage": dict | None,
                "error_message": str | None,
                "raw_status": str,
            }
        """
        try:
            status = raw_response.get("status", "unknown")
            output_items = raw_response.get("output", [])
            usage = raw_response.get("usage")

            # Extract text content
            text_parts: list[str] = []
            tool_calls_count = 0
            artifacts: list[dict] = []

            for item in output_items:
                item_type = item.get("type", "")

                if item_type == "message":
                    content_blocks = item.get("content", [])
                    for block in content_blocks:
                        if block.get("type") == "output_text":
                            text_parts.append(block.get("text", ""))

                elif item_type == "function_call":
                    tool_calls_count += 1

            output_text = "\n".join(text_parts).strip()

            # Try to parse structured output from text
            parsed_output = self._try_parse_structured(output_text)

            success = status in ("completed",) and bool(output_text)

            return {
                "success": success,
                "output": output_text,
                "parsed_output": parsed_output,
                "artifacts": artifacts,
                "tool_calls_count": tool_calls_count,
                "token_usage": usage,
                "error_message": None if success else f"status={status}, no_output={not output_text}",
                "raw_status": status,
            }

        except Exception as e:
            logger.exception("Failed to parse OpenClaw response")
            return {
                "success": False,
                "output": "",
                "parsed_output": None,
                "artifacts": [],
                "tool_calls_count": 0,
                "token_usage": None,
                "error_message": str(e),
                "raw_status": "parse_error",
            }

    def _try_parse_structured(self, text: str) -> dict[str, Any] | None:
        """尝试从文本中提取结构化输出（JSON）"""
        import json

        # Try direct JSON parse
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to find JSON block in markdown
        if "```json" in text:
            try:
                start = text.index("```json") + 7
                end = text.index("```", start)
                return json.loads(text[start:end].strip())
            except (ValueError, json.JSONDecodeError):
                pass

        return None
```

### 8.4 HTTP Client

**File**: `backend/app/adapters/openclaw/client.py`

```python
"""
OpenClawClient — HTTP client for OpenClaw /v1/responses API

Phase 1: Synchronous HTTP (POST /v1/responses, stream=false)
Phase 2: Can be extended with SSE streaming or Gateway WebSocket
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.adapters.openclaw.config import OpenClawConfig

logger = logging.getLogger(__name__)

# Timeout: connect=10s, read=configured, write=10s, pool=5s
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_WRITE_TIMEOUT = 10.0
DEFAULT_POOL_TIMEOUT = 5.0


class OpenClawClient:
    """
    OpenClaw HTTP API Client

    Usage:
        config = OpenClawConfig.from_settings()
        client = OpenClawClient(config)
        response = await client.execute(request_body)
    """

    def __init__(self, config: OpenClawConfig):
        self._config = config
        self._base_url = config.gateway_url

    async def execute(
        self,
        request_body: dict[str, Any],
        *,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """
        执行 OpenClaw /v1/responses 请求

        Args:
            request_body: IntentTranslator 生成的请求体
            timeout_seconds: 覆盖默认超时

        Returns:
            OpenClaw 原始响应 dict

        Raises:
            OpenClawError: 连接/超时/认证错误
            OpenClawExecutionError: 执行失败
        """
        if not self._config.enabled:
            raise OpenClawError("OpenClaw integration is disabled")

        if not self._base_url:
            raise OpenClawError("OpenClaw gateway URL is not configured")

        read_timeout = float(timeout_seconds or self._config.default_timeout_seconds)

        url = f"{self._base_url}/v1/responses"
        headers = {
            "Authorization": f"Bearer {self._config.auth_token}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(
            connect=DEFAULT_CONNECT_TIMEOUT,
            read=read_timeout + 30.0,  # Buffer beyond execution timeout
            write=DEFAULT_WRITE_TIMEOUT,
            pool=DEFAULT_POOL_TIMEOUT,
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as http:
                response = await http.post(url, json=request_body, headers=headers)

            if response.status_code == 401:
                raise OpenClawError("Authentication failed — check OPENCLAW_AUTH_TOKEN")

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise OpenClawRateLimited(f"Rate limited, retry after {retry_after}s")

            if response.status_code >= 500:
                raise OpenClawError(f"OpenClaw server error: {response.status_code}")

            if response.status_code >= 400:
                error_body = response.json() if response.content else {}
                error_msg = error_body.get("error", {}).get("message", response.text)
                raise OpenClawExecutionError(f"Request failed: {error_msg}")

            return response.json()

        except httpx.TimeoutException:
            raise OpenClawTimeout(
                f"OpenClaw execution timed out after {read_timeout}s"
            )
        except httpx.ConnectError:
            raise OpenClawError(
                f"Cannot connect to OpenClaw at {self._base_url} — is the gateway running?"
            )

    async def health_check(self) -> bool:
        """检查 OpenClaw 可用性"""
        if not self._config.enabled or not self._base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as http:
                resp = await http.get(f"{self._base_url}/v1/models")
                return resp.status_code == 200
        except Exception:
            return False


# === Exception Hierarchy ===

class OpenClawError(Exception):
    """Base OpenClaw error"""
    pass

class OpenClawTimeout(OpenClawError):
    """Execution timed out"""
    pass

class OpenClawRateLimited(OpenClawError):
    """Rate limited by OpenClaw"""
    pass

class OpenClawExecutionError(OpenClawError):
    """Execution failed"""
    pass
```

### 8.5 Package Init

**File**: `backend/app/adapters/__init__.py` (NEW, empty)
**File**: `backend/app/adapters/openclaw/__init__.py` (NEW)

```python
"""OpenClaw adapter package"""
from app.adapters.openclaw.client import OpenClawClient, OpenClawError, OpenClawTimeout
from app.adapters.openclaw.config import OpenClawConfig
from app.adapters.openclaw.intent_translator import IntentTranslator
from app.adapters.openclaw.result_parser import ResultParser

__all__ = [
    "OpenClawClient",
    "OpenClawConfig",
    "OpenClawError",
    "OpenClawTimeout",
    "IntentTranslator",
    "ResultParser",
]
```

---

## 9. Phase 1: Execution Service

**File**: `backend/app/services/execution_service.py` (NEW)

```python
"""
ExecutionService — 执行编排服务

核心职责：
1. 创建 ExecutionIntent
2. 调度到 OpenClaw
3. 接收结果 → TrustEngine 评估 → 分级写入
4. 生命周期管理（取消、超时、回退）

安全约束：
- 所有操作都验证 user_id 归属
- 所有结果必须经过 TrustEngine
- feature flag 关闭时所有方法返回 disabled 状态
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.openclaw import OpenClawClient, OpenClawConfig, IntentTranslator, ResultParser
from app.adapters.openclaw.client import OpenClawError, OpenClawTimeout
from app.config import settings
from app.core.execution_router import ExecutionRouter, RoutingDecision
from app.core.execution_trust import ExecutionTrustEngine, TrustEvaluation
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_record import ExecutionRecord
from app.models.task import Task

logger = logging.getLogger(__name__)


class ExecutionService:
    """
    Usage:
        service = ExecutionService(db=db_session)
        result = await service.handoff_to_openclaw(task_id=..., user_id=...)
    """

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
    ):
        self._db = db
        self._redis = redis
        self._router = ExecutionRouter(openclaw_enabled=settings.OPENCLAW_ENABLED)
        self._trust_engine = ExecutionTrustEngine()
        self._config = OpenClawConfig.from_settings()
        self._client = OpenClawClient(self._config) if self._config.enabled else None
        self._translator = IntentTranslator()
        self._parser = ResultParser()

    # =================================================================
    # Public API
    # =================================================================

    async def classify_task(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
    ) -> RoutingDecision:
        """
        对任务进行执行模式分类（不触发执行）

        Returns:
            RoutingDecision
        """
        task = await self._get_user_task(task_id, user_id)
        return self._router.classify(
            task_type=task.type.value if task.type else "",
            goal=task.title or "",
            has_side_effects=False,  # TODO: Phase 2 — infer from task content
            has_clear_criteria=False,
        )

    async def create_intent(
        self,
        *,
        task_id: UUID,
        user_id: UUID,
        goal: str | None = None,
        instructions: list[str] | None = None,
        policy: dict[str, Any] | None = None,
        success_criteria: dict[str, Any] | None = None,
        result_contract: dict[str, Any] | None = None,
    ) -> ExecutionIntent:
        """
        创建 ExecutionIntent（状态: DRAFT）

        用户确认后再调用 dispatch()
        """
        task = await self._get_user_task(task_id, user_id)
        decision = self._router.classify(
            task_type=task.type.value if task.type else "",
            goal=goal or task.title or "",
        )

        plan_id = task.plan_id

        # Build idempotency key
        idempotency_key = f"{plan_id or 'noplan'}:{task_id}:{uuid.uuid4().hex[:8]}"

        intent = ExecutionIntent(
            plan_id=plan_id,
            task_id=task_id,
            user_id=user_id,
            execution_mode=decision.execution_mode,
            executor=ExecutorType.OPENCLAW if decision.execution_mode != ExecutionMode.HUMAN else ExecutorType.MANUAL,
            goal=goal or task.title or "",
            instructions=instructions or [],
            target_env=decision.target_env,
            policy=policy or self._default_policy(),
            success_criteria=success_criteria or {"type": "non_empty"},
            result_contract=result_contract or {},
            timeout_seconds=self._config.default_timeout_seconds,
            status=ExecutionIntentStatus.DRAFT,
            trust_level=TrustLevel.RAW,
            idempotency_key=idempotency_key,
        )

        self._db.add(intent)
        await self._db.flush()
        await self._db.refresh(intent)
        return intent

    async def dispatch(
        self,
        *,
        intent_id: UUID,
        user_id: UUID,
    ) -> ExecutionIntent:
        """
        确认并分发 ExecutionIntent 到 OpenClaw

        完整流程:
        1. 状态从 DRAFT/READY → DISPATCHED
        2. 调用 OpenClaw /v1/responses
        3. 解析结果
        4. TrustEngine 评估
        5. 创建 ExecutionRecord
        6. 根据信任等级更新 Task 状态
        7. 返回更新后的 intent

        Raises:
            ValueError: intent 不存在或不属于该用户
            OpenClawError: 执行失败
        """
        intent = await self._get_user_intent(intent_id, user_id)

        if intent.status not in (ExecutionIntentStatus.DRAFT, ExecutionIntentStatus.READY):
            raise ValueError(f"Intent {intent_id} is in status {intent.status}, cannot dispatch")

        if not self._client:
            raise OpenClawError("OpenClaw is not enabled")

        # 1. Update status
        intent.status = ExecutionIntentStatus.DISPATCHED
        intent.dispatched_at = datetime.now(timezone.utc)
        await self._db.flush()

        try:
            # 2. Translate and execute
            request_body = self._translator.translate(
                intent,
                agent_id=self._config.default_agent_id,
            )

            intent.status = ExecutionIntentStatus.RUNNING
            await self._db.flush()

            raw_response = await self._client.execute(
                request_body,
                timeout_seconds=intent.timeout_seconds,
            )

            # 3. Parse result
            parsed = self._parser.parse(raw_response)

            # 4. Trust evaluation
            evaluation = self._trust_engine.evaluate(
                raw_result=parsed,
                success_criteria=intent.success_criteria or {},
                result_contract=intent.result_contract or {},
                executor_history=None,  # TODO: Phase 3 — load history
            )

            # 5. Create ExecutionRecord
            record = ExecutionRecord(
                execution_intent_id=intent.id,
                user_id=user_id,
                task_id=intent.task_id,
                executor_type="openclaw",
                external_run_id=raw_response.get("id"),
                raw_response=raw_response,
                parsed_output=parsed.get("parsed_output"),
                artifacts=parsed.get("artifacts", []),
                trust_level=evaluation.trust_level,
                validation_passed=evaluation.validation_passed,
                validation_total=evaluation.validation_total,
                quality_score=evaluation.quality_score,
                duration_ms=None,  # TODO: calculate from timestamps
                token_usage=parsed.get("token_usage"),
                tool_calls_count=parsed.get("tool_calls_count", 0),
            )
            self._db.add(record)

            # 6. Update intent
            intent.external_run_id = raw_response.get("id")
            intent.trust_level = TrustLevel(evaluation.trust_level)
            intent.status = (
                ExecutionIntentStatus.SUCCEEDED if parsed.get("success")
                else ExecutionIntentStatus.PARTIAL if parsed.get("output")
                else ExecutionIntentStatus.FAILED
            )
            intent.completed_at = datetime.now(timezone.utc)

            if not parsed.get("success"):
                intent.error_category = "execution_failed"
                intent.error_message = parsed.get("error_message")

            await self._db.flush()
            return intent

        except OpenClawTimeout:
            intent.status = ExecutionIntentStatus.TIMED_OUT
            intent.error_category = "timeout"
            intent.error_message = f"Timed out after {intent.timeout_seconds}s"
            intent.completed_at = datetime.now(timezone.utc)
            await self._db.flush()
            return intent

        except OpenClawError as e:
            intent.status = ExecutionIntentStatus.FAILED
            intent.error_category = "adapter_error"
            intent.error_message = str(e)
            intent.completed_at = datetime.now(timezone.utc)
            await self._db.flush()
            return intent

    async def cancel(
        self,
        *,
        intent_id: UUID,
        user_id: UUID,
    ) -> ExecutionIntent:
        """取消执行"""
        intent = await self._get_user_intent(intent_id, user_id)
        if intent.status in (
            ExecutionIntentStatus.SUCCEEDED,
            ExecutionIntentStatus.FAILED,
            ExecutionIntentStatus.CANCELED,
        ):
            raise ValueError(f"Intent {intent_id} is already terminal: {intent.status}")

        intent.status = ExecutionIntentStatus.CANCELED
        intent.completed_at = datetime.now(timezone.utc)
        await self._db.flush()
        return intent

    async def hand_back(
        self,
        *,
        intent_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> ExecutionIntent:
        """将任务回退给用户手动完成"""
        intent = await self._get_user_intent(intent_id, user_id)
        intent.status = ExecutionIntentStatus.HANDED_BACK
        intent.error_category = "user_handback"
        intent.error_message = reason
        intent.completed_at = datetime.now(timezone.utc)
        await self._db.flush()
        return intent

    async def get_intent(
        self,
        *,
        intent_id: UUID,
        user_id: UUID,
    ) -> ExecutionIntent | None:
        """获取单个 intent"""
        return await self._get_user_intent(intent_id, user_id)

    async def list_intents(
        self,
        *,
        user_id: UUID,
        task_id: UUID | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[ExecutionIntent]:
        """列出用户的 execution intents"""
        query = (
            select(ExecutionIntent)
            .where(ExecutionIntent.user_id == user_id)
            .where(ExecutionIntent.deleted_at.is_(None))
        )
        if task_id:
            query = query.where(ExecutionIntent.task_id == task_id)
        if status:
            query = query.where(ExecutionIntent.status == status)
        query = query.order_by(ExecutionIntent.created_at.desc()).limit(limit)

        result = await self._db.execute(query)
        return list(result.scalars().all())

    # =================================================================
    # Private Helpers
    # =================================================================

    async def _get_user_task(self, task_id: UUID, user_id: UUID) -> Task:
        result = await self._db.execute(
            select(Task)
            .where(Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None))
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError(f"Task {task_id} not found for user {user_id}")
        return task

    async def _get_user_intent(self, intent_id: UUID, user_id: UUID) -> ExecutionIntent:
        result = await self._db.execute(
            select(ExecutionIntent)
            .where(
                ExecutionIntent.id == intent_id,
                ExecutionIntent.user_id == user_id,
                ExecutionIntent.deleted_at.is_(None),
            )
        )
        intent = result.scalar_one_or_none()
        if not intent:
            raise ValueError(f"ExecutionIntent {intent_id} not found for user {user_id}")
        return intent

    @staticmethod
    def _default_policy() -> dict[str, Any]:
        return {
            "approval_policy": "require_for_side_effects",
            "allowed_domains": [],
            "allowed_tools": ["browser", "read"],
            "allow_exec": False,
        }
```

---

## 10. Phase 1: REST API — Executions

**File**: `backend/app/api/v1/executions.py` (NEW)

```python
"""
Executions API — OpenClaw 执行管理接口

路由前缀: /executions
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.user import User
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])


# === Request Models ===

class HandoffRequest(BaseModel):
    """任务委派请求"""
    goal: str | None = Field(None, description="覆盖任务标题的执行目标")
    instructions: list[str] | None = Field(None, description="附加约束指令")
    policy: dict[str, Any] | None = Field(None, description="安全策略覆盖")
    success_criteria: dict[str, Any] | None = Field(None, description="成功标准")
    result_contract: dict[str, Any] | None = Field(None, description="结果格式约束")


class HandbackRequest(BaseModel):
    """取回任务请求"""
    reason: str | None = Field(None, description="取回原因")


# === Response Models ===

class ExecutionIntentResponse(BaseModel):
    """ExecutionIntent 响应"""
    id: str
    task_id: str
    plan_id: str | None
    execution_mode: str
    executor: str
    status: str
    trust_level: str
    external_run_id: str | None
    goal: str
    error_category: str | None
    error_message: str | None
    dispatched_at: str | None
    completed_at: str | None
    created_at: str


class ClassifyResponse(BaseModel):
    """分类结果响应"""
    execution_mode: str
    target_env: str | None
    reason: str
    confidence: float
    risk_flags: list[str]


class ExecutionRecordResponse(BaseModel):
    """执行记录响应"""
    id: str
    trust_level: str
    quality_score: float | None
    parsed_output: dict | None
    artifacts: list
    duration_ms: int | None
    error_category: str | None
    error_message: str | None


# === Endpoints ===

@router.get("/health")
async def execution_health():
    """检查 OpenClaw 集成状态"""
    return {
        "openclaw_enabled": settings.OPENCLAW_ENABLED,
        "gateway_url": settings.OPENCLAW_GATEWAY_URL if settings.OPENCLAW_ENABLED else None,
    }


@router.post("/tasks/{task_id}/classify", response_model=ClassifyResponse)
async def classify_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """对任务进行执行模式分类（不触发执行）"""
    service = ExecutionService(db=db)
    decision = await service.classify_task(task_id=task_id, user_id=current_user.id)
    return ClassifyResponse(
        execution_mode=decision.execution_mode.value,
        target_env=decision.target_env.value if decision.target_env else None,
        reason=decision.reason,
        confidence=decision.confidence,
        risk_flags=decision.risk_flags,
    )


@router.post("/tasks/{task_id}/handoff", response_model=ExecutionIntentResponse)
async def handoff_task(
    task_id: UUID,
    request: HandoffRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    将任务委派给 AI 执行

    完整流程：创建 intent → 分发到 OpenClaw → 返回结果
    """
    if not settings.OPENCLAW_ENABLED:
        raise HTTPException(status_code=503, detail="OpenClaw integration is not enabled")

    service = ExecutionService(db=db)

    try:
        # Create intent
        intent = await service.create_intent(
            task_id=task_id,
            user_id=current_user.id,
            goal=request.goal,
            instructions=request.instructions,
            policy=request.policy,
            success_criteria=request.success_criteria,
            result_contract=request.result_contract,
        )

        # Dispatch immediately
        intent = await service.dispatch(
            intent_id=intent.id,
            user_id=current_user.id,
        )

        await db.commit()
        return _to_response(intent)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.get("/{intent_id}", response_model=ExecutionIntentResponse)
async def get_execution(
    intent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取执行状态"""
    service = ExecutionService(db=db)
    try:
        intent = await service.get_intent(intent_id=intent_id, user_id=current_user.id)
        return _to_response(intent)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tasks/{task_id}/intents")
async def list_task_executions(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出任务的所有执行记录"""
    service = ExecutionService(db=db)
    intents = await service.list_intents(user_id=current_user.id, task_id=task_id)
    return [_to_response(i) for i in intents]


@router.post("/{intent_id}/cancel", response_model=ExecutionIntentResponse)
async def cancel_execution(
    intent_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消执行"""
    service = ExecutionService(db=db)
    try:
        intent = await service.cancel(intent_id=intent_id, user_id=current_user.id)
        await db.commit()
        return _to_response(intent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{intent_id}/handback", response_model=ExecutionIntentResponse)
async def handback_execution(
    intent_id: UUID,
    request: HandbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """将任务回退给用户手动完成"""
    service = ExecutionService(db=db)
    try:
        intent = await service.hand_back(
            intent_id=intent_id,
            user_id=current_user.id,
            reason=request.reason,
        )
        await db.commit()
        return _to_response(intent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# === Helpers ===

def _to_response(intent) -> ExecutionIntentResponse:
    d = intent.to_dict()
    return ExecutionIntentResponse(
        id=d["id"],
        task_id=d["task_id"],
        plan_id=d.get("plan_id"),
        execution_mode=d["execution_mode"],
        executor=d["executor"],
        status=d["status"],
        trust_level=d["trust_level"],
        external_run_id=d.get("external_run_id"),
        goal=d["goal"],
        error_category=d.get("error_category"),
        error_message=d.get("error_message"),
        dispatched_at=d.get("dispatched_at"),
        completed_at=d.get("completed_at"),
        created_at=d["created_at"],
    )
```

### Route Registration

**Addition to** `backend/app/api/v1/router.py`:

```python
# Add import (alphabetical position):
from app.api.v1 import executions

# Add route registration (after tasks):
api_router.include_router(executions.router, prefix="/executions", tags=["executions"])
```

---

## 11. Phase 1: Mobile — Handoff Button & Status Display

### 11.1 API Endpoint Definition

**Addition to** `mobile/lib/core/network/api_endpoints.dart`:

```dart
  // === Execution (OpenClaw) ===
  static String classifyTask(String taskId) => '/executions/tasks/$taskId/classify';
  static String handoffTask(String taskId) => '/executions/tasks/$taskId/handoff';
  static String execution(String intentId) => '/executions/$intentId';
  static String taskExecutions(String taskId) => '/executions/tasks/$taskId/intents';
  static String cancelExecution(String intentId) => '/executions/$intentId/cancel';
  static String handbackExecution(String intentId) => '/executions/$intentId/handback';
  static const String executionHealth = '/executions/health';
```

### 11.2 Execution Models

**File**: `mobile/lib/features/task/data/models/execution_intent_model.dart` (NEW)

```dart
import 'package:json_annotation/json_annotation.dart';

part 'execution_intent_model.g.dart';

enum ExecutionIntentStatus {
  draft, ready, dispatched, running, waitingApproval,
  succeeded, partial, failed, canceled, timedOut, handedBack,
}

@JsonSerializable()
class ExecutionIntentModel {
  final String id;
  @JsonKey(name: 'task_id')
  final String taskId;
  @JsonKey(name: 'plan_id')
  final String? planId;
  @JsonKey(name: 'execution_mode')
  final String executionMode;
  final String executor;
  final String status;
  @JsonKey(name: 'trust_level')
  final String trustLevel;
  @JsonKey(name: 'external_run_id')
  final String? externalRunId;
  final String goal;
  @JsonKey(name: 'error_category')
  final String? errorCategory;
  @JsonKey(name: 'error_message')
  final String? errorMessage;
  @JsonKey(name: 'dispatched_at')
  final String? dispatchedAt;
  @JsonKey(name: 'completed_at')
  final String? completedAt;
  @JsonKey(name: 'created_at')
  final String createdAt;

  const ExecutionIntentModel({
    required this.id,
    required this.taskId,
    this.planId,
    required this.executionMode,
    required this.executor,
    required this.status,
    required this.trustLevel,
    this.externalRunId,
    required this.goal,
    this.errorCategory,
    this.errorMessage,
    this.dispatchedAt,
    this.completedAt,
    required this.createdAt,
  });

  factory ExecutionIntentModel.fromJson(Map<String, dynamic> json) =>
      _$ExecutionIntentModelFromJson(json);

  Map<String, dynamic> toJson() => _$ExecutionIntentModelToJson(this);

  bool get isTerminal => [
    'succeeded', 'failed', 'canceled', 'timed_out', 'handed_back',
  ].contains(status);

  bool get isRunning => ['dispatched', 'running', 'waiting_approval'].contains(status);
}
```

### 11.3 UI Integration Point

The handoff button should be added to `TaskExecutionScreen` as a conditional widget in the bottom controls area. Show ONLY when:

1. `settings.OPENCLAW_ENABLED == true` (check via `/executions/health`)
2. Task status is `PENDING` or `IN_PROGRESS`
3. No active execution intent exists for this task

```
┌─────────────────────────────────────┐
│  Task Execution Screen              │
│  ┌───────────────────────────────┐  │
│  │ ... existing content ...      │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌───────────────────────────────┐  │
│  │ 🤖 交给 AI 执行               │  │  ← NEW (conditional)
│  │ [分类: 浏览器任务 | 信心: 80%] │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌──────────┐  ┌──────────────┐    │
│  │  放弃    │  │   完成任务    │    │  ← existing
│  └──────────┘  └──────────────┘    │
└─────────────────────────────────────┘
```

Execution status display:

```
┌─────────────────────────────────────┐
│  AI 执行中...                       │
│  ├─ 状态: 运行中                    │
│  ├─ 已用时: 45s                     │
│  └─ [取消] [取回自己做]              │
└─────────────────────────────────────┘

  OR (completed):

┌─────────────────────────────────────┐
│  ✅ AI 执行完成                     │
│  ├─ 信任等级: VALIDATED             │
│  ├─ 质量评分: 0.82                  │
│  ├─ 结果摘要: ...                   │
│  └─ [确认结果] [不满意，自己做]      │
└─────────────────────────────────────┘
```

---

## 12. Phase 2: Execution Ingestor (Interface Contract)

Phase 2 的 Ingestor 需要实现以下接口。Phase 1 由 `ExecutionService.dispatch()` 内联处理简化版本。

```python
class ExecutionIngestor:
    """
    Phase 2 完整实现需满足的接口合约

    所有 OpenClaw 结果必须经过此组件，不允许旁路
    """

    async def ingest(
        self,
        *,
        intent: ExecutionIntent,
        raw_result: dict[str, Any],
        user_confirmed: bool = False,
    ) -> ExecutionRecord:
        """
        摄取并评估执行结果

        写入规则：
        - ALWAYS: 创建 ExecutionRecord
        - VALIDATED+: 更新 Task 状态, 创建 PlanExecutionRecord
        - TRUSTED only: 发布行为信号, 更新画像
        """
        ...

    async def confirm_result(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
    ) -> ExecutionRecord:
        """
        用户确认结果 → 提升信任等级到 TRUSTED

        触发：
        - 更新 record.trust_level
        - 发布 ExecutionResultIngested 事件 (trusted)
        - 写入行为信号
        """
        ...

    async def reject_result(
        self,
        *,
        record_id: UUID,
        user_id: UUID,
        reason: str | None = None,
    ) -> None:
        """
        用户拒绝结果

        触发：
        - 回滚 Task 状态（如果已更新）
        - 发布 ExecutionHandedBack 事件
        - 记录拒绝反馈到 PlanState.feedback_log
        """
        ...
```

---

## 13. Phase 3: Profile Feedback Loop (Interface Contract)

Phase 3 需要在以下现有组件中**新增**处理逻辑（非替换）：

### 13.1 BehaviorSignalCollector Extension

```python
# New handler method (added to existing class):
async def handle_execution_result_event(self, event: dict) -> None:
    """
    处理 execution.result_ingested 事件

    仅当 trust_level == "trusted" 时触发
    """
    ...
```

### 13.2 AdaptiveReplanner Extension

```python
# New pattern triggers (added to CognitivePatternTrigger._map_pattern):
NEW_PATTERNS = {
    "delegation_aversion": {
        "trigger": "handed_back_rate > 0.6 in last 10 delegations",
        "adjustment": PlanParameterAdjustment(
            parameter="suggest_delegation",
            value=False,
            reason="User frequently takes back delegated tasks",
        ),
    },
    "delegation_trust_building": {
        "trigger": "consecutive_openclaw_success >= 5",
        "adjustment": PlanParameterAdjustment(
            parameter="auto_delegate_eligible_types",
            value="expanded",
            reason="Consistent execution success, expanding eligible task types",
        ),
    },
}
```

### 13.3 New Event Handler Registration

```python
# New subscription in event bus consumer (Phase 3):
await event_bus.subscribe(
    stream="sparkle_events",
    group_name="execution_feedback",
    consumer_name="execution_consumer",
    callback=handle_execution_events,
)

async def handle_execution_events(event: dict) -> None:
    event_type = event.get("event_type")
    if event_type == "execution.result_ingested":
        if event.get("trust_level") == "trusted":
            await behavior_collector.handle_execution_result_event(event)
            await replanner.on_execution_completed(event)
    elif event_type == "execution.handed_back":
        await behavior_collector.handle_execution_handback_event(event)
```

---

## 14. File Manifest & Dependency Graph

### 14.1 Phase 0 — New Files

| File | Type | Dependencies |
|------|------|-------------|
| `backend/app/models/execution_intent.py` | Model | `base.py` |
| `backend/app/models/execution_record.py` | Model | `base.py`, `execution_intent.py` |
| `backend/app/core/execution_router.py` | Logic | `execution_intent.py` (enums only) |
| `backend/app/core/execution_trust.py` | Logic | None (pure logic) |
| `backend/alembic/versions/oc001_...py` | Migration | None |

### 14.2 Phase 0 — Modified Files (additive only)

| File | Change | Risk |
|------|--------|------|
| `backend/app/models/__init__.py` | Add imports + __all__ entries | None — additive |
| `backend/app/models/task.py` | Add `execution_mode` Column | None — nullable |
| `backend/app/core/event_types.py` | Add 4 new Event classes | None — additive |
| `backend/app/config/settings.py` | Add OPENCLAW_* settings | None — defaults safe |

### 14.3 Phase 1 — New Files

| File | Type | Dependencies |
|------|------|-------------|
| `backend/app/adapters/__init__.py` | Package | None |
| `backend/app/adapters/openclaw/__init__.py` | Package | sub-modules |
| `backend/app/adapters/openclaw/config.py` | Config | `settings.py` |
| `backend/app/adapters/openclaw/client.py` | HTTP Client | `config.py`, `httpx` |
| `backend/app/adapters/openclaw/intent_translator.py` | Translator | `execution_intent.py` |
| `backend/app/adapters/openclaw/result_parser.py` | Parser | None |
| `backend/app/services/execution_service.py` | Service | router, trust, adapter, models |
| `backend/app/api/v1/executions.py` | API | `execution_service.py` |

### 14.4 Phase 1 — Modified Files

| File | Change | Risk |
|------|--------|------|
| `backend/app/api/v1/router.py` | Add `executions` import + route | None — additive |
| `mobile/lib/core/network/api_endpoints.dart` | Add endpoint strings | None — additive |
| New Flutter files for models + UI | New files | None — new features |

### 14.5 Dependency Graph

```
settings.py (config)
  ↓
execution_intent.py ← execution_record.py
  ↓                       ↓
execution_router.py    execution_trust.py
  ↓                       ↓
  └───────┐    ┌──────────┘
          ↓    ↓
    execution_service.py ← openclaw/adapter
          ↓
    executions.py (API)
          ↓
    router.py (registration)
```

---

## 15. Verification Checklist

### Phase 0 Complete When:

- [ ] `alembic upgrade head` succeeds without error
- [ ] `alembic downgrade -1` successfully rolls back
- [ ] All existing tests pass (`cd backend && pytest`)
- [ ] `ExecutionIntent` and `ExecutionRecord` can be created via ORM
- [ ] `ExecutionRouter.classify()` returns HUMAN for all task types when `OPENCLAW_ENABLED=False`
- [ ] `ExecutionRouter.classify()` returns HUMAN for learning/training/reflection types when enabled
- [ ] `ExecutionTrustEngine.evaluate()` returns "raw" for empty results
- [ ] `ExecutionTrustEngine.evaluate()` returns "validated" for well-formed results
- [ ] `ExecutionTrustEngine.evaluate()` blocks results with sensitive content patterns
- [ ] Task model change has zero impact on existing task creation/completion flows

### Phase 1 Complete When:

- [ ] `POST /api/v1/executions/tasks/{id}/classify` returns classification
- [ ] `POST /api/v1/executions/tasks/{id}/handoff` creates intent + dispatches to OpenClaw
- [ ] OpenClaw result is parsed and stored as ExecutionRecord
- [ ] TrustEngine correctly evaluates result trust level
- [ ] `GET /api/v1/executions/{id}` returns intent status
- [ ] Cancel and handback endpoints work correctly
- [ ] Feature flag `OPENCLAW_ENABLED=False` returns 503 for handoff
- [ ] All existing tests still pass
- [ ] Mobile handoff button appears conditionally
- [ ] Mobile execution status display works

---

## 16. Appendix: OpenClaw API Quick Reference

### POST /v1/responses (Phase 1)

```bash
curl -X POST http://127.0.0.1:18789/v1/responses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openclaw/default",
    "input": "Search for recent AI news and summarize top 3",
    "instructions": "Only access news websites. Return structured JSON.",
    "stream": false,
    "user": "sparkle:user123:task456"
  }'
```

Response:
```json
{
  "id": "resp_abc123",
  "output": [
    {
      "type": "message",
      "role": "assistant",
      "content": [{"type": "output_text", "text": "..."}]
    }
  ],
  "usage": {"input_tokens": 150, "output_tokens": 500},
  "status": "completed"
}
```

### POST /hooks/agent (Alternative, not used in Phase 1)

```bash
curl -X POST http://127.0.0.1:18789/hooks/agent \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "message": "...",
    "agentId": "sparkle-executor",
    "timeoutSeconds": 300,
    "deliver": false
  }'
```

### Gateway WebSocket RPC (Phase 2)

```json
{"type": "req", "id": 1, "method": "agent", "params": {"message": "...", "agentId": "..."}}
// → {"type": "res", "id": 1, "ok": true, "payload": {"runId": "run_xxx", "acceptedAt": "..."}}

{"type": "req", "id": 2, "method": "agent.wait", "params": {"runId": "run_xxx"}}
// → {"type": "res", "id": 2, "ok": true, "payload": {"status": "completed", "output": "..."}}
```

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-27 | Initial specification |

---

**End of Specification**
