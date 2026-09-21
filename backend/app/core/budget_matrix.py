"""
Core: <cognitive|execution>
Phase: plan
Stage: O-07

O-07 · Run 预算派生矩阵 —— budget by user/plan/run/tier 的「run × user-tier」面。

定位（非平行真源，只是薄派生层）：
- **user 面真源**：网关 QuotaService 日额度（``llm_tokens:{uid}:{date}``）+
  引擎 ``app/core/llm_quota.LLMCostGuard``（同键面）；判级真源
  ``app/core/entitlement.py``（users.entitlement，未知一律 free，宁降不升）。
- **plan 面真源**：``app/services/execution_preference_service``（execution_budget
  日/月 token 限额，``execution_service.dispatch`` 处强制 + 超限显式阻断）。
- **run 面真源**：X-06 ``agent_run_service`` budget 契约（limits/usage 四维，
  fail-closed 校验 + BUDGET_EXCEEDED 明确终态 + executor 每调用闸门）。
- **tier 面真源**：``app/core/cost_controller`` 按类目日预算熔断（llm/rag/
  aurora/glm_batch 分桶）。

缺的只有一块：**run 创建时未显式携带 budget → 无限额（unlimited）**——
失控 run 的成本面没有兜底。本模块按 entitlement 派生四维 run 预算默认值
（``derive_default_run_budget``），由 ``AgentRunService.create_run`` 在
budget 缺省时接线（``RUN_BUDGET_DEFAULTS_ENABLED`` 可关）。派生值全部经
X-06 既有 ``normalize_budget`` 校验——本模块不引入第二套预算形状或词表。
"""

from __future__ import annotations

import json
import logging

from app.core.entitlement import ENTITLEMENT_FREE, normalize_entitlement

_logger = logging.getLogger(__name__)

#: O-07 · run 预算派生语义版本（默认值变更需 bump 并过 reviewer）。
RUN_BUDGET_MATRIX_VERSION = "run_budget_matrix.v1"

#: 四维限额键（与 agent_run_service.BUDGET_LIMIT_WORDS 同词表；此处只做
#: 派生，不复制校验——最终仍过 normalize_budget 单一校验面）。
_RUN_BUDGET_LIMIT_KEYS: frozenset[str] = frozenset(
    {"max_total_tokens", "max_cost_usd", "max_tool_calls", "max_duration_seconds"}
)

#: entitlement → settings 键（未知 entitlement 落 free：宁降不升，与
#: entitlement.py「未知/缺失一律 free」同一 fail-safe 方向）。
_ENTITLEMENT_TO_SETTINGS_KEY = {
    ENTITLEMENT_FREE: "RUN_BUDGET_LIMITS_FREE_JSON",
    "pro": "RUN_BUDGET_LIMITS_PRO_JSON",
}


def _parse_limits_json(raw: str | None, *, label: str) -> dict[str, float]:
    """解析限额 JSON（确定性；垃圾输入 → 空映射 → 无该维限额）。"""
    if not raw or not str(raw).strip():
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        _logger.warning("budget_matrix: %s is not valid JSON; ignoring (raw hidden)", label)
        return {}
    if not isinstance(parsed, dict):
        _logger.warning("budget_matrix: %s is not a JSON object; ignoring", label)
        return {}
    limits: dict[str, float] = {}
    for key, value in parsed.items():
        if key not in _RUN_BUDGET_LIMIT_KEYS:
            _logger.warning("budget_matrix: ignoring unknown run budget limit %r in %s", key, label)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            _logger.warning("budget_matrix: ignoring non-positive limit %r in %s", key, label)
            continue
        limits[key] = float(value)
    return limits


def derive_default_run_budget(entitlement: object | None) -> dict[str, dict[str, float]]:
    """按用户 entitlement 派生 run 预算默认值（canonical budget 形状的 limits 面）。

    返回 ``{"limits": {…}}``（usage 由 X-06 ``normalize_budget`` 补零）；任何
    配置缺失/垃圾值只收敛该维（不整体失败）——派生是 best-effort 收紧，不是
    可用性闸门。
    """
    normalized = normalize_entitlement(entitlement)
    settings_key = _ENTITLEMENT_TO_SETTINGS_KEY.get(normalized, "RUN_BUDGET_LIMITS_FREE_JSON")

    from app.config import settings

    raw = str(getattr(settings, settings_key, "") or "")
    limits = _parse_limits_json(raw, label=settings_key)
    if not limits:
        _logger.warning(
            "budget_matrix: no usable run budget limits for entitlement=%r (settings key %s empty); "
            "run stays unlimited this creation",
            normalized,
            settings_key,
        )
    return {"limits": limits}


def derive_default_run_budget_if_enabled(entitlement: object | None) -> dict[str, dict[str, float]] | None:
    """``RUN_BUDGET_DEFAULTS_ENABLED=False`` 时返回 None（保持旧行为 unlimited）。"""
    from app.config import settings

    if not bool(getattr(settings, "RUN_BUDGET_DEFAULTS_ENABLED", True)):
        return None
    return derive_default_run_budget(entitlement)
