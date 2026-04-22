from __future__ import annotations

import pytest

from app.services.aurora_stage31_idiographic_kill_switch_service import (
    AuroraStage31IdiographicKillSwitchService,
)


@pytest.mark.asyncio
async def test_kill_switch_auto_downgrades_live_mode_on_high_disconfirm_rate() -> None:
    service = AuroraStage31IdiographicKillSwitchService()
    original_mode = await service.get_mode()

    try:
        await service.set_mode("live")
        downgraded = await service.auto_downgrade_on_disconfirm_rate(0.31)

        assert downgraded == "shadow"
        assert await service.get_mode() == "shadow"
    finally:
        await service.set_mode(original_mode)
