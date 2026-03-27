"""
ExecutionRouter - 决定任务应由谁执行。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.execution_intent import ExecutionMode, ExecutionTargetEnv

HUMAN_ONLY_TASK_TYPES = frozenset({"LEARNING", "TRAINING", "REFLECTION"})
AGENT_ELIGIBLE_TASK_TYPES = frozenset({"PLANNING", "SOCIAL", "OCR"})

HUMAN_ONLY_KEYWORDS = frozenset(
    {
        "运动",
        "锻炼",
        "跑步",
        "健身",
        "转账",
        "付款",
        "汇款",
        "支付",
        "密码",
        "重置密码",
        "修改密码",
        "账号安全",
        "发消息",
        "发邮件",
        "发送",
    }
)


@dataclass
class RoutingDecision:
    """执行路由决策。"""

    execution_mode: ExecutionMode
    target_env: ExecutionTargetEnv | None = None
    reason: str = ""
    confidence: float = 0.0
    risk_flags: list[str] = field(default_factory=list)


class ExecutionRouter:
    """任务执行路由器。"""

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
        """Phase 0 仅做路由标注，不触发实际执行。"""
        normalized_task_type = self._normalize_task_type(task_type)
        normalized_goal = (goal or "").strip()
        risk_flags: list[str] = []

        if not self._openclaw_enabled:
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                reason="openclaw_disabled",
                confidence=1.0,
            )

        if normalized_task_type in HUMAN_ONLY_TASK_TYPES:
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                reason=f"task_type_excluded:{normalized_task_type.lower()}",
                confidence=1.0,
            )

        for keyword in HUMAN_ONLY_KEYWORDS:
            if keyword in normalized_goal:
                risk_flags.append(f"blocked_keyword:{keyword}")
                return RoutingDecision(
                    execution_mode=ExecutionMode.HUMAN,
                    reason=f"keyword_blocked:{keyword}",
                    confidence=1.0,
                    risk_flags=risk_flags,
                )

        if has_side_effects and not has_clear_criteria:
            risk_flags.append("side_effects_without_criteria")
            return RoutingDecision(
                execution_mode=ExecutionMode.HUMAN,
                reason="side_effects_no_criteria",
                confidence=0.9,
                risk_flags=risk_flags,
            )

        if normalized_task_type in AGENT_ELIGIBLE_TASK_TYPES and not has_side_effects:
            return RoutingDecision(
                execution_mode=ExecutionMode.AGENT,
                target_env=self._infer_target_env(normalized_goal, task_tags),
                reason="eligible_readonly_task",
                confidence=0.8,
            )

        if has_side_effects and has_clear_criteria:
            return RoutingDecision(
                execution_mode=ExecutionMode.HYBRID,
                target_env=self._infer_target_env(normalized_goal, task_tags),
                reason="side_effects_with_criteria",
                confidence=0.7,
                risk_flags=["requires_user_approval"],
            )

        return RoutingDecision(
            execution_mode=ExecutionMode.HUMAN,
            reason="default_conservative",
            confidence=0.5,
        )

    @staticmethod
    def _normalize_task_type(task_type: str) -> str:
        return (task_type or "").strip().upper()

    @staticmethod
    def _infer_target_env(goal: str, task_tags: list[str] | None = None) -> ExecutionTargetEnv | None:
        text = " ".join(filter(None, [goal, " ".join(task_tags or [])]))
        browser_keywords = {"浏览", "搜索", "网页", "打开", "登录", "邮件", "网站"}
        shell_keywords = {"脚本", "命令", "运行", "执行", "安装", "终端"}
        doc_keywords = {"文档", "整理", "摘要", "总结", "笔记", "PDF"}
        api_keywords = {"api", "接口", "请求", "webhook"}

        if any(keyword in text for keyword in browser_keywords):
            return ExecutionTargetEnv.BROWSER
        if any(keyword in text for keyword in shell_keywords):
            return ExecutionTargetEnv.SHELL
        if any(keyword.lower() in text.lower() for keyword in api_keywords):
            return ExecutionTargetEnv.API
        if any(keyword in text for keyword in doc_keywords):
            return ExecutionTargetEnv.DOCUMENT
        return None
