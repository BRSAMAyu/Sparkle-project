"""Pre-dispatch risk assessment for OpenClaw execution intents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RiskSignal:
    code: str
    label: str
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "label": self.label,
            "snippet": self.snippet,
        }


@dataclass(frozen=True)
class RiskAssessment:
    level: str
    reasons: list[str] = field(default_factory=list)
    forced_confirm: bool = False
    contains_sensitive_data: bool = False
    blocked: bool = False
    blocked_reason: str | None = None
    blocked_signals: list[RiskSignal] = field(default_factory=list)
    sensitive_signals: list[RiskSignal] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "reasons": list(self.reasons),
            "forced_confirm": self.forced_confirm,
            "contains_sensitive_data": self.contains_sensitive_data,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "blocked_signals": [item.to_dict() for item in self.blocked_signals],
            "sensitive_signals": [item.to_dict() for item in self.sensitive_signals],
        }


class ExecutionRiskAssessor:
    """Assess whether an execution requires additional confirmation."""

    BLOCKED_COMMAND_RULES = (
        (
            "shell.rm_recursive_rootish",
            "删除目录/强制递归删除",
            r"\brm\s+(-[a-zA-Z]*[rf][a-zA-Z]*\s+)(/|~|\.{1,2}/|/tmp|/var|/Users|/home)",
        ),
        ("database.drop_table", "删除数据库表", r"\bdrop\s+table\b"),
        ("git.force_push", "强制推送历史重写", r"\bgit\s+push\s+--force(?:-with-lease)?\b"),
        ("disk.raw_write", "磁盘原始写入", r"\bdd\s+if="),
        ("disk.format", "格式化磁盘", r"\bmkfs(?:\.[a-z0-9_+-]+)?\b"),
        ("system.shutdown", "关机/重启系统", r"\b(?:shutdown|reboot|halt|poweroff)\b"),
        ("shell.fork_bomb", "fork bomb", r":\(\)\s*\{"),
    )
    HIGH_RISK_PATTERNS = (
        r"\bdelete\b",
        r"\bremove\b",
        r"\bformat\b",
        r"\bpurchase\b",
        r"\bbuy\b",
        r"\btransfer\b",
        r"\bsend\b",
        r"\bupload\b",
        r"\binstall\b",
    )
    SENSITIVE_RULES = (
        ("secret.password", "密码/口令", r"\b(?:password|passwd|口令|密码)\b"),
        ("secret.api_key", "API Key", r"\bapi[_-]?key\b"),
        ("secret.token", "访问令牌", r"\b(?:access[_-]?token|refresh[_-]?token|bearer\s+[a-z0-9._-]+)\b"),
        ("secret.credential", "凭证/密钥", r"\b(?:secret|credential|private key|ssh-rsa|ssh-ed25519)\b"),
        ("secret.openai_key", "OpenAI 风格密钥", r"\bsk-[a-zA-Z0-9]{16,}\b"),
        ("secret.aws_access_key", "AWS Access Key", r"\bAKIA[0-9A-Z]{16}\b"),
        ("secret.jwt", "JWT", r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+\b"),
        ("secret.credit_card", "疑似银行卡号", r"\b(?:\d[ -]*?){13,19}\b"),
    )

    def assess(
        self,
        *,
        intent_goal: str,
        instructions: list[str] | None,
        policy: dict[str, Any] | None,
        target_env: str | None = None,
    ) -> RiskAssessment:
        combined_text = "\n".join(
            [
                str(intent_goal or "").strip(),
                *[str(item or "").strip() for item in list(instructions or [])],
            ]
        ).strip()
        lowered = combined_text.lower()
        reasons: list[str] = []
        blocked_signals = self._collect_signals(lowered, self.BLOCKED_COMMAND_RULES)
        sensitive_signals = self._collect_signals(lowered, self.SENSITIVE_RULES)

        if blocked_signals:
            primary = blocked_signals[0]
            return RiskAssessment(
                level="critical",
                reasons=["irreversible_operation_detected", primary.code],
                forced_confirm=True,
                contains_sensitive_data=bool(sensitive_signals),
                blocked=True,
                blocked_reason=f"该指令包含不可逆高危操作（{primary.label}），出于安全考虑已被 Sparkle 拦截。",
                blocked_signals=blocked_signals,
                sensitive_signals=sensitive_signals,
            )

        contains_sensitive_data = bool(sensitive_signals)
        if contains_sensitive_data:
            reasons.append("contains_sensitive_data")

        forced_confirm = False
        level = "low"
        if any(re.search(pattern, lowered) for pattern in self.HIGH_RISK_PATTERNS):
            level = "high"
            forced_confirm = True
            reasons.append("high_risk_keywords")

        policy_payload = dict(policy or {})
        allowed_tools = {str(item).strip().lower() for item in list(policy_payload.get("allowed_tools") or [])}
        if target_env == "shell" or "exec" in allowed_tools:
            if level == "low":
                level = "medium"
            reasons.append("shell_execution")
        if target_env == "browser" and {"browser", "write_summary"} & allowed_tools == {"browser"}:
            reasons.append("browser_interaction")
        if contains_sensitive_data and level in {"low", "medium"}:
            level = "high"
            forced_confirm = True

        return RiskAssessment(
            level=level,
            reasons=reasons,
            forced_confirm=forced_confirm,
            contains_sensitive_data=contains_sensitive_data,
            blocked_signals=blocked_signals,
            sensitive_signals=sensitive_signals,
        )

    @staticmethod
    def _collect_signals(text: str, rules: tuple[tuple[str, str, str], ...]) -> list[RiskSignal]:
        signals: list[RiskSignal] = []
        for code, label, pattern in rules:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match is None:
                continue
            snippet = match.group(0).strip()
            signals.append(
                RiskSignal(
                    code=code,
                    label=label,
                    snippet=snippet[:120] if snippet else None,
                )
            )
        return signals
