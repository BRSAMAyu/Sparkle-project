"""
Core: relationship — Aurora low-stimulation policy (A-07 / AURORA_V3 §7).

Turns the existing low-stimulation setting into a real Aurora behavior
policy for the proactive surfaces (comeback nudge first):

- 用户 explicit setting 最高优先：``aurora_stimulation_mode`` 显式偏好
  （``low`` / ``standard``）无条件覆盖自动判定，双向覆盖——显式 ``standard``
  时即使信号偏高也不衰减，显式 ``low`` 时即使信号平静也衰减。
- ``auto``（默认档）行为完全保持现状（standard）：引擎侧当前不消费任何
  情绪/负荷信号做自动降档；后续接入信号时必须走显式授权的数字预算，
  **不做任何心理诊断**（不推断"焦虑/状态不好"，不做诊断性表述）。

输出是行为面预算（推送与否/抑制窗口/文案强度），不是对用户的判断。
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

STIMULATION_STANDARD = "standard"
STIMULATION_LOW = "low"

# 显式偏好值（aurora_stimulation_mode）。auto = 不表态，交给自动判定。
EXPLICIT_MODE_AUTO = "auto"
EXPLICIT_MODE_LOW = "low"
EXPLICIT_MODE_STANDARD = "standard"

VALID_STIMULATION_MODES = {
    EXPLICIT_MODE_AUTO,
    EXPLICIT_MODE_LOW,
    EXPLICIT_MODE_STANDARD,
}

# 默认抑制窗口（小时）——与 comeback_nudge_task 既有 _has_recent_notification 口径一致。
DEFAULT_NUDGE_SUPPRESS_HOURS = 24
# 低刺激档主动建议频率衰减：抑制窗口 ×3（24h → 72h）。
LOW_STIMULATION_NUDGE_SUPPRESS_HOURS = 72
# P-06 低刺激档 quiet hours 加宽（分钟）：允许集 = 原窗允许 ∩ 加宽窗允许，
# 即有效抑制窗 = 原窗 ∪ 各端外扩——低刺激默认更保守的交集语义。
LOW_STIMULATION_QUIET_EXTENSION_MINUTES = 60
# P-06 低刺激档默认日上限：仅当用户未显式设置 daily_cap 时生效
# （用户 explicit setting 最高优先，显式值不被压低）。
LOW_STIMULATION_DAILY_CAP = 2


@dataclass(slots=True, frozen=True)
class StimulationPolicy:
    """Behavioral budget derived from the explicit setting (never a diagnosis)."""

    level: str = STIMULATION_STANDARD
    #: 主动建议是否推送（低刺激档降为仅应用内，不主动打扰）。
    allow_proactive_push: bool = True
    #: 主动建议重复抑制窗口（小时）——低刺激档拉长 = 降低主动频率。
    proactive_suppress_hours: int = DEFAULT_NUDGE_SUPPRESS_HOURS
    #: 庆祝/敦促强度：低刺激档去压力化标题，正文保持事实性。
    quiet_title: bool = False
    #: 透传给客户端的档位标记（移动端据此走安静呈现）。
    payload_tag: str = ""

    def to_payload(self) -> dict[str, object]:
        return {
            "level": self.level,
            "allow_proactive_push": self.allow_proactive_push,
            "proactive_suppress_hours": self.proactive_suppress_hours,
            "quiet_title": self.quiet_title,
        }


#: auto 档当前无引擎侧信号源——保守落 standard，行为与历史完全一致。
_POLICY_STANDARD = StimulationPolicy(level=STIMULATION_STANDARD)
_POLICY_LOW = StimulationPolicy(
    level=STIMULATION_LOW,
    allow_proactive_push=False,
    proactive_suppress_hours=LOW_STIMULATION_NUDGE_SUPPRESS_HOURS,
    quiet_title=True,
    payload_tag=STIMULATION_LOW,
)


def resolve_stimulation_policy(explicit_mode: str | None) -> StimulationPolicy:
    """Resolve the behavioral policy from the user's explicit setting.

    显式档双向覆盖：``low`` → 永远衰减；``standard`` → 永不衰减；
    ``auto``/未知/缺省 → 保持现状（standard）。绝不由内容推断心理状态。
    """
    mode = (explicit_mode or "").strip().lower()
    if mode == EXPLICIT_MODE_LOW:
        return _POLICY_LOW
    if mode == EXPLICIT_MODE_STANDARD:
        return _POLICY_STANDARD
    if mode not in ("", EXPLICIT_MODE_AUTO):
        logger.warning(
            "Unknown aurora_stimulation_mode {!r}; falling back to standard", explicit_mode
        )
    return _POLICY_STANDARD


def apply_policy_to_nudge(
    policy: StimulationPolicy,
    *,
    title: str,
    content: str,
) -> tuple[str, str]:
    """Return the (title, content) for a comeback nudge under the policy.

    低刺激档：标题去敦促/等待压力，改中性事实性表述；正文保持引擎的
    事实性 comeback 消息（那里已做过陈旧任务诚实化）。显式 standard 档
    行为零变化。
    """
    if not policy.quiet_title:
        return title, content
    quiet_title = "你的学习计划状态"
    return quiet_title, content
