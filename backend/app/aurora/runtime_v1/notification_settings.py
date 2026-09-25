"""
Core: execution / cognitive
Stage: Aurora Runtime v1 — Unified Notification Settings Resolution (P-06)

**统一通知负担解析点**（Notification Burden / Quiet / Low-stimulation 终局）。

P-06 之前，三处散装开关互不相通：
1. quiet hours —— ``NotificationPreferences`` 表（/notification-center/preferences
   可写），但 P-01 抑制链只读 env 旋钮，用户设置不生效；
2. daily cap —— ``UserPreferencesCenter.explicit["daily_cap"]`` 同样只被展示
   消费，通知路径从不据此限量；
3. low stimulation —— A-07 ``aurora_stimulation_mode`` 只衰减 nudge 重复窗口
   与推送，不与 quiet/cap 联动。

本模块把三者收束到**一个解析函数**，产出一个
:class:`EffectiveNotificationPolicy` 供全部出口（comeback nudge、aurora wake
投递、P-01 事件管线）一致消费。硬约束：

- **零新真源**：只读既有存储——``NotificationPreferences`` 表（quiet 窗）、
  ``UserPreferencesCenter.explicit``（daily_cap / aurora_stimulation_mode /
  enable_interventions）、``PreferenceConsumptionService.get_notification_config``
  的既有合并语义。零新表、零新键、零迁移。
- **mute 复用 P-03**：建议级静音/冷却仍由
  :class:`~app.services.proactive_suggestion_service.ProactiveSuggestionFeedbackService`
  判定，本模块只透传（``suggestion_suppressed``），绝不重建。
- **低刺激更保守（交集语义）**：显式 ``low`` 档下，**生效中**的 quiet 窗
  （用户窗，未开启时取平台基线窗）两端各外扩
  :data:`~app.aurora.runtime_v1.stimulation_policy.LOW_STIMULATION_QUIET_EXTENSION_MINUTES`
  分钟——允许时刻 = 原窗允许 ∩ 加宽窗允许。低刺激档不凭空造 quiet：生效窗
  不存在（用户未开启且平台旋钮关闭）时行为与既有完全一致；用户未显式设置
  daily_cap 时默认下调到
  :data:`~app.aurora.runtime_v1.stimulation_policy.LOW_STIMULATION_DAILY_CAP`
  （显式值最高优先，不被压低）。
- **cap 以通知账本计数**：当日已发数从真实 ``Notification`` 行（用户本地日
  界）统计——与实际触达同源，不是 mock 计数；``daily_cap=0`` = 用户关停，
  任何时刻都抑制。
- **fail-closed**：真源读不到时抛
  :class:`NotificationSettingsUnavailable`，由调用方按「宁可少发不可误发」
  处理（P-01 R2 P1-1 / WT378-03 同哲学）——绝不以缺省值放行。

输出是行为面预算（窗口/上限/档位），不是对用户的判断；不做任何心理推断。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.suppression import (
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    in_quiet_window,
)
from app.aurora.runtime_v1.stimulation_policy import (
    LOW_STIMULATION_DAILY_CAP,
    LOW_STIMULATION_QUIET_EXTENSION_MINUTES,
    StimulationPolicy,
    resolve_stimulation_policy,
)

__all__ = [
    "EffectiveNotificationPolicy",
    "BurdenDecision",
    "NotificationSettingsResolver",
    "NotificationSettingsUnavailable",
    "widen_quiet_window",
]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class NotificationSettingsUnavailable(RuntimeError):
    """统一设置真源读失败——调用方必须 fail-closed（宁可少发不可误发）。"""


def widen_quiet_window(window: tuple[str, str], minutes: int) -> tuple[str, str]:
    """quiet 窗两端各外扩 ``minutes`` 分钟（mod 24h，跨午夜回绕）。"""

    def parse(hhmm: str) -> int:
        hour, minute = hhmm.split(":")
        return int(hour) * 60 + int(minute)

    def render(total: int) -> str:
        total %= 24 * 60
        return f"{total // 60:02d}:{total % 60:02d}"

    start = (parse(window[0]) - minutes) % (24 * 60)
    end = (parse(window[1]) + minutes) % (24 * 60)
    return render(start), render(end)


@dataclass(frozen=True, slots=True)
class EffectiveNotificationPolicy:
    """统一解析后的行为面预算（全部出口消费同一份，不是三处散装）。"""

    #: A-07 显式档位（auto/low/standard）。
    stimulation_mode: str
    #: A-07 行为策略（推送许可/重复抑制窗口/去敦促标题）。
    stimulation: StimulationPolicy
    #: 生效 quiet 窗（低刺激档为加宽后的窗；``None`` = 无 quiet 抑制）。
    quiet_window: tuple[str, str] | None
    #: 用户/平台基线窗（未加宽；供展示与低刺激档加宽语义核验）。
    base_quiet_window: tuple[str, str] | None
    quiet_source: str = "none"
    #: 生效日上限（``0`` = 用户关停）。
    daily_cap: int = 0
    daily_cap_source: str = "default"
    #: 主动面（intervention 通知）总开关。
    interventions_enabled: bool = True
    #: quiet 判定时区（IANA 名）。
    timezone: str = "Asia/Shanghai"

    def quiet_suppresses(self, now: datetime) -> bool:
        if self.quiet_window is None:
            return False
        return in_quiet_window(now, self.quiet_window, self.timezone)

    @property
    def allow_proactive_push(self) -> bool:
        """A-07 档位：低刺激档不主动推送（仅入应用内通知中心）。"""
        return self.stimulation.allow_proactive_push

    @property
    def proactive_suppress_hours(self) -> int:
        """A-07 档位：重复建议抑制窗口（小时）。"""
        return self.stimulation.proactive_suppress_hours

    def to_payload(self) -> dict[str, Any]:
        return {
            "stimulation_mode": self.stimulation_mode,
            "quiet_window": list(self.quiet_window) if self.quiet_window else None,
            "quiet_source": self.quiet_source,
            "daily_cap": self.daily_cap,
            "daily_cap_source": self.daily_cap_source,
            "interventions_enabled": self.interventions_enabled,
            "allow_proactive_push": self.stimulation.allow_proactive_push,
            "timezone": self.timezone,
        }


@dataclass(frozen=True, slots=True)
class BurdenDecision:
    """负担闸门裁决（quiet → cap 固定顺序，与 SUPPRESSION_STEPS 对齐）。"""

    allowed: bool
    reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "reason": self.reason, "details": dict(self.details)}


class NotificationSettingsResolver:
    """读既有真源 → 解析统一策略 → 供各出口一致消费。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- resolve ----------------------------------------------------------

    async def resolve(self, user_id: str | UUID, *, now: datetime | None = None) -> EffectiveNotificationPolicy:
        """解析统一通知策略。真源读失败抛 :class:`NotificationSettingsUnavailable`。"""
        try:
            explicit = await self._read_explicit(user_id)
            merged_notification = await self._read_merged_notification_config(user_id)
            stimulation_mode = await self._read_stimulation_mode(user_id)
        except NotificationSettingsUnavailable:
            raise
        except Exception as exc:
            raise NotificationSettingsUnavailable(f"notification settings read failed: {exc!r}") from exc

        policy = resolve_stimulation_policy(stimulation_mode)
        timezone_name = str(explicit.get("timezone") or merged_notification.get("timezone") or "Asia/Shanghai")

        # --- quiet hours：用户窗 → 平台基线窗；低刺激档在生效窗上加宽（交集语义） ---
        # 低刺激档不凭空造 quiet：生效窗 = 用户窗（开启时）或平台基线窗
        # （env 旋钮开启时），低刺激档把它两端各外扩——允许时刻 = 原窗允许
        # ∩ 加宽窗允许。平台旋钮关闭且用户未开启时无 quiet（与既有行为一致，
        # 不引入时钟依赖）。
        user_quiet: tuple[str, str] | None = None
        quiet_origin = "none"
        if merged_notification.get("quiet_hours_enabled"):
            start = str(merged_notification.get("quiet_hours_start") or DEFAULT_QUIET_START)
            end = str(merged_notification.get("quiet_hours_end") or DEFAULT_QUIET_END)
            user_quiet = (start, end)
            quiet_origin = "user"
        elif self._platform_quiet_enabled():
            user_quiet = (proactive_config.PROACTIVE_QUIET_START, proactive_config.PROACTIVE_QUIET_END)
            quiet_origin = "platform_default"

        quiet_source = quiet_origin
        effective_quiet: tuple[str, str] | None = user_quiet
        if policy.level == "low" and user_quiet is not None:
            effective_quiet = widen_quiet_window(user_quiet, LOW_STIMULATION_QUIET_EXTENSION_MINUTES)

        # --- daily cap：用户显式值最高优先；低刺激档仅下调缺省值 ---
        raw_cap = explicit.get("daily_cap")
        if raw_cap is None:
            daily_cap = (
                LOW_STIMULATION_DAILY_CAP if policy.level == "low" else int(proactive_config.PROACTIVE_DAILY_CAP)
            )
            cap_source = "default"
        else:
            try:
                daily_cap = max(0, int(raw_cap))
            except (TypeError, ValueError):
                daily_cap = int(proactive_config.PROACTIVE_DAILY_CAP)
                cap_source = "default"
            else:
                cap_source = "user"

        return EffectiveNotificationPolicy(
            stimulation_mode=stimulation_mode,
            stimulation=policy,
            quiet_window=effective_quiet,
            base_quiet_window=user_quiet,
            quiet_source=quiet_source,
            daily_cap=daily_cap,
            daily_cap_source=cap_source,
            interventions_enabled=bool(merged_notification.get("enable_interventions", True)),
            timezone=self._safe_timezone(timezone_name),
        )

    # -- burden gate -------------------------------------------------------

    async def evaluate_burden(self, user_id: str | UUID, *, now: datetime | None = None) -> BurdenDecision:
        """quiet → cap 确定性闸门（首个命中即短路）。"""
        moment = now or _utcnow()
        policy = await self.resolve(user_id, now=moment)

        if policy.quiet_suppresses(moment):
            return BurdenDecision(
                False,
                "quiet_hours",
                {"window": list(policy.quiet_window or ()), "timezone": policy.timezone},
            )

        count = await self.daily_count(user_id, now=moment, timezone_name=policy.timezone)
        if count >= policy.daily_cap:
            return BurdenDecision(False, "daily_cap", {"count": count, "cap": policy.daily_cap})
        return BurdenDecision(True, None, {"count": count, "cap": policy.daily_cap})

    # -- P-03 mute 透传（勿重建） -------------------------------------------

    async def suggestion_suppressed(
        self, user_id: str | UUID, suggestion_type: str, *, now: datetime | None = None
    ) -> dict[str, str] | None:
        """建议级静音/冷却判定——直接复用 P-03 真源服务。"""
        from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

        return await ProactiveSuggestionFeedbackService(self.db).get_suppression(user_id, suggestion_type, now=now)

    # -- ledger ------------------------------------------------------------

    async def daily_count(
        self, user_id: str | UUID, *, now: datetime | None = None, timezone_name: str | None = None
    ) -> int:
        """当日（用户本地日界）已发通知数——从真实 ``Notification`` 行统计。"""
        from app.models.notification import Notification

        moment = now or _utcnow()
        tz = ZoneInfo(self._safe_timezone(timezone_name or "Asia/Shanghai"))
        try:
            local_day_start = (
                moment.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            )
        except (ValueError, OverflowError):
            local_day_start = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        day_start_utc = local_day_start.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.created_at >= day_start_utc,
                Notification.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one_or_none() or 0)

    # -- readers（逐项隔离，读失败统一上抛由 resolve 收口） -------------------

    async def _read_explicit(self, user_id: str | UUID) -> dict[str, Any]:
        """读 raw explicit（不经 _fill_defaults——需要区分「未设置」）。"""
        from app.models.user_preferences import UserPreferencesCenter

        result = await self.db.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id))
        row = result.scalar_one_or_none()
        if row is None:
            return {}
        explicit = row.explicit
        return dict(explicit) if isinstance(explicit, dict) else {}

    async def _read_merged_notification_config(self, user_id: str | UUID) -> dict[str, Any]:
        """quiet 窗 / interventions 开关——复用既有合并语义（explicit 镜像 ∪ 表行）。"""
        from app.services.preference_consumption_service import PreferenceConsumptionService

        service = PreferenceConsumptionService(self.db)
        return await service.get_notification_config(UUID(str(user_id)))

    async def _read_stimulation_mode(self, user_id: str | UUID) -> str:
        """A-07 显式档位（同一真源键 aurora_stimulation_mode）。"""
        from app.aurora.runtime_v1.user_preferences import AuroraUserPreferencesService

        prefs = await AuroraUserPreferencesService(self.db).get(user_id)
        return str(prefs.get("aurora_stimulation_mode") or "auto")

    @staticmethod
    def _platform_quiet_enabled() -> bool:
        return bool(getattr(proactive_config, "PROACTIVE_QUIET_HOURS_ENABLED", False))

    @staticmethod
    def _safe_timezone(name: str) -> str:
        try:
            ZoneInfo(str(name or "Asia/Shanghai"))
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            return "Asia/Shanghai"
        return str(name or "Asia/Shanghai")


def local_quiet_probe(now_utc: datetime, timezone_name: str) -> time:
    """测试辅助：UTC naive 时刻 → 本地 wall-clock time。"""
    tz = ZoneInfo(timezone_name)
    return now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).time()


def make_db_settings_provider(session_factory: Any) -> Any:
    """为 P-01 事件管线构造 per-user 统一设置提供器（每事件独立会话）。

    返回 ``async (user_id) -> {"quiet_window", "daily_cap", "timezone"}``；
    解析失败原样上抛，由管线侧回退管线旋钮（env 保守基线）。
    """

    async def _provider(user_id: str) -> dict[str, Any] | None:
        async with session_factory() as session:
            policy = await NotificationSettingsResolver(session).resolve(user_id)
            return {
                "quiet_window": policy.quiet_window,
                "daily_cap": policy.daily_cap,
                "timezone": policy.timezone,
            }

    return _provider
