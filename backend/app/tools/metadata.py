"""X-06 · Tool Capability Metadata Contract —— 工具能力边界的单一真源.

对应 v3/07_tasks/cards/X-06.md 工作项 1 + SECURITY_PRIVACY.md「tool capability
allowlist / prompt injection 不能升级 tool permission」+ AGENT_RUNTIME.md §4
Tool Call 契约（normalized args hash / idempotency_key / permission decision）。

设计（对齐 run_state_machine.py 的 core 层风格）：

- 本模块 **stdlib-only、零 IO**（不 import app.*），可被 tools / orchestration /
  services / 测试无环引用；
- 封闭词表 ×3：:class:`ToolEffect`（read/write）、:class:`ToolRiskLevel`
  （low/medium/high）、:data:`TOOL_PERMISSION_VOCABULARY`（9 个 agent 工具能力）。
  扩词表属契约变更，需过两位 reviewer（X-05 冻结声明同款）；
- **fail-closed 注册**：每个 BaseTool 子类必须显式声明 effect/risk/reversible/
  required_permission/cost_usd 五元数据；缺失/越词表 → :class:`ToolMetadataError`
  → 注册表拒绝注册（DynamicToolRegistry.register_tool）；
- **权限判定是纯函数**：:func:`decide_tool_permission` 只吃结构化输入
  （registry 元数据 + 服务端声明的 grants/allowlist），**永不接触对话内容**
  ——system/user/tool-output 三来源的注入文本无法进入判定输入，这是注入免疫
  的构造性保证（acceptance 1 的机制根源）；
- 默认授权 :data:`DEFAULT_AGENT_TOOL_GRANTS` 是**代码冻结的 allowlist**（保持
  既有 chat 行为零回归）；显式 ``granted`` 集合**替换**默认集且不可越过
  :data:`PERMISSION_CEILING`（调用方 bug 也不能铸出天花板外的能力）；
  ``denied`` 恒为否决（显式回收恒赢）。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any, Iterable

__all__ = [
    "ToolEffect",
    "ToolRiskLevel",
    "TOOL_PERMISSION_VOCABULARY",
    "ToolMetadata",
    "ToolMetadataError",
    "PermissionDecision",
    "PermissionDenyReason",
    "PERMISSION_CEILING",
    "DEFAULT_AGENT_TOOL_GRANTS",
    "validate_tool_metadata",
    "tool_metadata_from_attributes",
    "decide_tool_permission",
    "canonical_args_hash",
    "required_metadata_fields",
]

#: 工具元数据必填字段（fail-closed 校验清单；全部必须**显式**声明）。
required_metadata_fields = ("effect", "risk", "reversible", "required_permission", "cost_usd")


class ToolEffect(StrEnum):
    """工具效果类别（side-effect 判定的唯一依据）。

    - READ：不改变任何持久状态（纯读取/计算）；重放无害。
    - WRITE：改变持久状态（DB 行/外部副作用）；调用必须携带 idempotency key，
      且同 key 重放不得重复执行 side effect（X-06 工作项 2）。
    """

    READ = "read"
    WRITE = "write"


class ToolRiskLevel(StrEnum):
    """风险等级（SECURITY_PRIVACY.md：high-risk side effect 需显式批准）。

    与 BaseTool.requires_confirmation 对齐：risk=high 的 WRITE 工具应在类上
    同时声明 ``requires_confirmation = True``（executor 两道闸都强制）。
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


#: agent 工具能力封闭词表（9 项）。扩词表 = 契约变更（两位 reviewer）。
#: 语义按数据域划分；外部资源消耗（LLM/搜索）单列，便于预算与授权治理。
TOOL_PERMISSION_VOCABULARY: frozenset[str] = frozenset(
    {
        "task.read",  # 读任务/计划状态
        "task.write",  # 创建/修改/批处理任务
        "plan.write",  # 创建计划、按计划生成任务
        "memory.read",  # 读个人画像/记忆/材料/行为模式
        "memory.write",  # 写成长笔记/关系笔记/画像修正
        "growth.read",  # 读策略态/情境简报/干预记录
        "growth.write",  # 调整成长策略态/记录干预反馈
        "llm.use",  # 消耗 LLM tokens 的计算型工具
        "web.search",  # 外部 web 检索
    }
)

#: 可授权能力天花板：任何显式 granted 集合先与它求交（fail-closed）。
PERMISSION_CEILING: frozenset[str] = TOOL_PERMISSION_VOCABULARY

#: 默认授权（代码冻结的 allowlist，保持既有 chat 工具行为零回归）。
#: 注意：新增能力词不会自动出现在此集合——新能力默认**拒绝**，需显式修此常量。
DEFAULT_AGENT_TOOL_GRANTS: frozenset[str] = frozenset(TOOL_PERMISSION_VOCABULARY)


class ToolMetadataError(ValueError):
    """工具元数据缺失/非法 → 注册表拒绝注册（fail-closed；ValueError 子类）。"""


@dataclass(frozen=True)
class ToolMetadata:
    """单个工具的能力元数据（注册表唯一真源的物化形态）。

    - ``cost_usd``：单次调用成本估计（USD，order-of-magnitude 估计值），
      供 run budget 的 cost 维度记账；纯 DB 工具为 0。
    - ``reversible``：是否存在补偿路径（AGENT_RUNTIME.md §6 语义）。
    """

    name: str
    effect: ToolEffect
    risk: ToolRiskLevel
    reversible: bool
    required_permission: str
    cost_usd: float

    @property
    def is_side_effect(self) -> bool:
        """是否 side-effect 工具（WRITE ⇒ 强制 idempotency key）。"""
        return self.effect is ToolEffect.WRITE

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "effect": self.effect.value,
            "risk": self.risk.value,
            "reversible": bool(self.reversible),
            "required_permission": self.required_permission,
            "cost_usd": float(self.cost_usd),
        }


def _norm_permission(value: Any) -> str:
    return str(value).strip()


def validate_tool_metadata(tool: Any) -> list[str]:
    """校验工具对象的五元数据；返回 issue 列表（空 = 通过）。

    fail-closed 语义：**任何**字段缺失/越词表/类型非法都产出 issue，
    由注册表决定拒绝注册（ToolMetadataError）。
    """
    name = getattr(tool, "name", None) or type(tool).__name__
    issues: list[str] = []

    effect = getattr(tool, "effect", None)
    try:
        ToolEffect(effect)
    except ValueError:
        issues.append(f"{name}: missing or invalid 'effect' (must be one of {sorted(e.value for e in ToolEffect)})")

    risk = getattr(tool, "risk", None)
    try:
        ToolRiskLevel(risk)
    except ValueError:
        issues.append(f"{name}: missing or invalid 'risk' (must be one of {sorted(r.value for r in ToolRiskLevel)})")

    reversible = getattr(tool, "reversible", None)
    if not isinstance(reversible, bool):
        issues.append(f"{name}: missing or non-bool 'reversible'")

    permission = getattr(tool, "required_permission", None)
    if _norm_permission(permission) not in TOOL_PERMISSION_VOCABULARY:
        issues.append(
            f"{name}: missing or unknown 'required_permission' {permission!r} "
            f"(closed vocabulary: {sorted(TOOL_PERMISSION_VOCABULARY)})"
        )

    cost = getattr(tool, "cost_usd", None)
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
        issues.append(f"{name}: missing or invalid 'cost_usd' (must be a non-negative number)")

    return issues


def tool_metadata_from_attributes(tool: Any) -> ToolMetadata:
    """从工具对象物化元数据；不合法即抛 ToolMetadataError（fail-closed）。"""
    issues = validate_tool_metadata(tool)
    if issues:
        raise ToolMetadataError("; ".join(issues))
    return ToolMetadata(
        name=str(tool.name),
        effect=ToolEffect(tool.effect),
        risk=ToolRiskLevel(tool.risk),
        reversible=bool(tool.reversible),
        required_permission=_norm_permission(tool.required_permission),
        cost_usd=float(tool.cost_usd),
    )


class PermissionDenyReason(StrEnum):
    """权限否决的封闭归因（审计/测试用；decision.reason 取值域）。"""

    UNKNOWN_TOOL = "unknown_tool"
    METADATA_MISSING = "metadata_missing"
    NOT_IN_ALLOWED_TOOLS = "not_in_allowed_tools"
    PERMISSION_NOT_GRANTED = "permission_not_granted"
    PERMISSION_EXPLICITLY_DENIED = "permission_explicitly_denied"


@dataclass(frozen=True)
class PermissionDecision:
    """一次工具调用的权限判定结果（AGENT_RUNTIME.md §4 permission decision）。

    allowed=False 时 reason ∈ :class:`PermissionDenyReason`。判定输入只有
    registry 元数据与服务端结构化授权——对话内容不在输入空间（注入免疫）。
    """

    allowed: bool
    tool_name: str
    reason: str
    granted_via: str | None = None  # default_grants | explicit_grants | run_contract

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "tool_name": self.tool_name,
            "reason": self.reason,
            "granted_via": self.granted_via,
        }


def decide_tool_permission(
    *,
    tool_name: str,
    metadata: ToolMetadata | None,
    allowed_tools: Iterable[str] | None = None,
    granted_permissions: Iterable[str] | None = None,
    denied_permissions: Iterable[str] | None = None,
    default_grants: frozenset[str] = DEFAULT_AGENT_TOOL_GRANTS,
) -> PermissionDecision:
    """权限判定（纯函数；executor 的唯一判定入口）。

    规则顺序（全部 fail-closed）：

    1. 元数据缺失 → METADATA_MISSING（注册表 fail-closed 的兜底复查）；
    2. ``allowed_tools`` 非空且不含该工具 → NOT_IN_ALLOWED_TOOLS
       （run contract 的工具级白名单，X-05 AgentRun.allowed_tools）；
    3. ``denied_permissions`` 命中 → PERMISSION_EXPLICITLY_DENIED（显式回收恒赢）；
    4. 有效授权集 = default_grants（granted 缺省时）或 granted ∩ CEILING；
       required_permission 不在其中 → PERMISSION_NOT_GRANTED。

    注入免疫：本函数签名只有结构化参数——调用方（executor）只传 registry
    元数据与服务端授权结构，永不传对话文本（见 executor._decide_permission）。
    """
    if metadata is None or metadata.name != str(tool_name):
        return PermissionDecision(
            allowed=False,
            tool_name=str(tool_name),
            reason=PermissionDenyReason.METADATA_MISSING.value,
        )

    if allowed_tools is not None:
        allowed = {str(t) for t in allowed_tools}
        if metadata.name not in allowed:
            return PermissionDecision(
                allowed=False,
                tool_name=metadata.name,
                reason=PermissionDenyReason.NOT_IN_ALLOWED_TOOLS.value,
            )

    denied = {_norm_permission(p) for p in (denied_permissions or ()) if _norm_permission(p)}
    if metadata.required_permission in denied:
        return PermissionDecision(
            allowed=False,
            tool_name=metadata.name,
            reason=PermissionDenyReason.PERMISSION_EXPLICITLY_DENIED.value,
        )

    if granted_permissions is None:
        effective, granted_via = set(default_grants), "default_grants"
    else:
        effective = {_norm_permission(p) for p in granted_permissions} & PERMISSION_CEILING
        granted_via = "explicit_grants"

    if metadata.required_permission not in effective:
        return PermissionDecision(
            allowed=False,
            tool_name=metadata.name,
            reason=PermissionDenyReason.PERMISSION_NOT_GRANTED.value,
            granted_via=granted_via,
        )
    return PermissionDecision(allowed=True, tool_name=metadata.name, reason="granted", granted_via=granted_via)


def canonical_args_hash(arguments: dict[str, Any] | None) -> str:
    """参数规范化哈希（AGENT_RUNTIME.md §4 normalized args hash）。

    键排序 + 稳定 JSON → sha256；非 JSON-serializable 值退化 str()（工具参数
    均为 pydantic 验证后的标量/容器，正常路径不走退化）。
    """
    import json

    try:
        canonical = json.dumps(arguments or {}, sort_keys=True, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        canonical = repr(sorted((arguments or {}).items(), key=lambda kv: str(kv[0])))
    return sha256(canonical.encode("utf-8")).hexdigest()
