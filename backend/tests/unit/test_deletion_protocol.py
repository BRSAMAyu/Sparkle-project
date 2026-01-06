import pytest
from types import SimpleNamespace

from app.services.compliance.deletion_protocol import DeletionProtocol


@pytest.mark.asyncio
async def test_deletion_blocked_by_legal_hold(monkeypatch):
    protocol = DeletionProtocol(db=None)

    async def fake_is_hold_active(self, user_id):
        return True

    monkeypatch.setattr(protocol.legal_hold_service, "is_hold_active", fake_is_hold_active)
    result = await protocol.request_deletion(user_id="00000000-0000-0000-0000-000000000000")

    assert result.allowed is False
    assert result.reason == "LEGAL_HOLD_ACTIVE"


@pytest.mark.asyncio
async def test_deletion_triggers_crypto_erase(monkeypatch):
    protocol = DeletionProtocol(db=None)

    async def fake_is_hold_active(self, user_id):
        return False

    async def fake_destroy_key(self, user_id):
        return SimpleNamespace(id="cert-1")

    monkeypatch.setattr(protocol.legal_hold_service, "is_hold_active", fake_is_hold_active)
    monkeypatch.setattr(protocol.crypto_erase, "destroy_user_key", fake_destroy_key)

    result = await protocol.request_deletion(user_id="00000000-0000-0000-0000-000000000000")
    assert result.allowed is True
    assert result.certificate_id == "cert-1"
