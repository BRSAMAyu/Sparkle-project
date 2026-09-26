from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.kill_switch import is_enabled_mode, resolve_settings_mode
from app.routing.social_context_provider import FrozenSocialMention, FrozenSocialSnapshot, SocialContextProvider
from app.services.aurora_stage18_kill_switch_service import AuroraStage18KillSwitchService
from app.state_aggregator.service import StateAggregatorService


class AggregatorBackedSocialContextProvider(SocialContextProvider):
    """Stage 18 provider that preserves the Stage 17 prompt contract."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.aggregator = StateAggregatorService(db)
        self.kill_switches = AuroraStage18KillSwitchService()

    async def fetch(self, user_id, scope_hint: str | None = None) -> FrozenSocialSnapshot:
        del scope_hint
        if not await self.kill_switches.is_enabled("aggregator_enabled"):
            from app.routing.router_context_reader import RouterContextReader

            return await RouterContextReader(self.db).fetch_social_snapshot(user_id)
        state = await self.aggregator.get_user_state(
            user_id=user_id,
            required_fields=("recent_person_mentions", "commitment_summary"),
            expose_shadow=True,
        )
        mentions_value = state.recent_person_mentions.value if state.recent_person_mentions else None
        commitment_value = state.commitment_summary.value if state.commitment_summary else None
        mentions = [
            FrozenSocialMention(summary=item.summary, occurred_at=item.occurred_at)
            for item in (mentions_value.mentions if mentions_value else ())
        ]
        return FrozenSocialSnapshot(
            recent_person_mentions=mentions,
            pending_commitments_count=commitment_value.overdue_count if commitment_value else 0,
            relationship_count=mentions_value.relationship_count if mentions_value else 0,
        )

    async def fetch_social_snapshot(self, user_id):
        return await self.fetch(user_id=user_id, scope_hint="router_prompt")


def build_social_context_provider(db: AsyncSession) -> SocialContextProvider:
    # V3-FIX-186：选型判据走 V3-FIX-21 统一入口 resolve_settings_mode——
    # tri-state 设置 AURORA_STAGE18_AGGREGATOR_MODE 在场即唯一判据（off/shadow/live），
    # legacy bool SPARKLE_AGGREGATOR_ENABLED 只在设置缺席时兜底；
    # 直读 legacy bool 会让 stage18 off 仍选中本 provider（治理面与行为面分叉）。
    # builder 为同步面，按卡片口径读 settings 层三态（Redis 覆盖由 fetch 内
    # is_enabled 二道闸承接），与 AuroraStage18KillSwitchService 共用同一 binding。
    aggregator_mode = resolve_settings_mode(AuroraStage18KillSwitchService.BINDINGS["aggregator_enabled"])
    if is_enabled_mode(aggregator_mode) and settings.SPARKLE_ROUTER_USE_AGGREGATOR_PROVIDER:
        return AggregatorBackedSocialContextProvider(db)

    from app.routing.router_context_reader import RouterContextReader

    return RouterContextReader(db)
