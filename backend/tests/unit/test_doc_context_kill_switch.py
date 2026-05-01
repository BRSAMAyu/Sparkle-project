from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.cache import cache_service
from app.services.aurora_doc_context_kill_switch_service import AuroraDocContextKillSwitchService


@pytest.mark.asyncio
async def test_doc_context_kill_switch_reads_shadow_setting(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_CONTEXT_INJECTION", True, raising=False)
    monkeypatch.setattr(settings, "AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE", "shadow", raising=False)

    assert await AuroraDocContextKillSwitchService().get_mode() == "shadow"


@pytest.mark.asyncio
async def test_doc_context_kill_switch_reads_redis_override(monkeypatch) -> None:
    fake_redis = AsyncMock()
    fake_redis.get.return_value = "live"
    monkeypatch.setattr(cache_service, "redis", fake_redis)
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_CONTEXT_INJECTION", True, raising=False)
    monkeypatch.setattr(settings, "AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE", "shadow", raising=False)

    assert await AuroraDocContextKillSwitchService().get_mode() == "live"


@pytest.mark.asyncio
async def test_doc_context_global_enable_overrides_to_off(monkeypatch) -> None:
    monkeypatch.setattr(cache_service, "redis", None)
    monkeypatch.setattr(settings, "ENABLE_DOCUMENT_CONTEXT_INJECTION", False, raising=False)
    monkeypatch.setattr(settings, "AURORA_DOC_CONTEXT_DOCUMENT_CONTEXT_INJECTION_MODE", "live", raising=False)

    assert await AuroraDocContextKillSwitchService().get_mode() == "off"
