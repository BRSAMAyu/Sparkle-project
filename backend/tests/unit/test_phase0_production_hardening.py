from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from app.config import settings
from app.config.settings import Settings
from app.core.email_service import EmailService


def _production_settings(**overrides):
    values = {
        "ENVIRONMENT": "production",
        "DEBUG": False,
        "JWT_SECRET": "phase0_secret_value_with_more_than_32_chars",
        "DATABASE_URL": "postgresql+asyncpg://postgres:secret@sparkle_db:5432/sparkle",
        "POSTGRES_PASSWORD": "postgres_secret",
        "REDIS_PASSWORD": "redis_secret",
        "INTERNAL_API_KEY": "test-internal-api-key",
        "MINIO_ACCESS_KEY": "minio_access",
        "MINIO_SECRET_KEY": "minio_secret",
        "LLM_API_KEY": "llm_secret",
        "PRODUCTION_URL": "https://sparkle.example.com",
        "BACKEND_CORS_ORIGINS": "",
        "SMTP_HOST": "smtp.example.com",
        "SMTP_USER": "smtp_user",
        "SMTP_PASSWORD": "smtp_secret",
        "EMAIL_FROM": "no-reply@example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_cors_defaults_to_https_production_url():
    cfg = _production_settings(BACKEND_CORS_ORIGINS="")

    assert cfg.BACKEND_CORS_ORIGINS == ["https://sparkle.example.com"]


def test_production_cors_rejects_non_https_origin():
    with pytest.raises(ValueError, match="BACKEND_CORS_ORIGINS must contain only HTTPS"):
        _production_settings(BACKEND_CORS_ORIGINS="http://sparkle.example.com")


def test_email_enabled_defaults_by_environment():
    prod = _production_settings()
    dev = Settings(ENVIRONMENT="development", JWT_SECRET="dev_secret_value_with_more_than_32_chars")

    assert prod.EMAIL_ENABLED is True
    assert dev.EMAIL_ENABLED is False


@pytest.mark.asyncio
async def test_email_service_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", False)

    service = EmailService()

    assert await service.send_verification_email("user@example.com", "123456") is False


@pytest.mark.asyncio
async def test_email_service_requires_smtp_host_and_sender(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "EMAIL_FROM", "")

    service = EmailService()

    assert await service.send_password_reset_email("user@example.com", "reset-token") is False


@pytest.mark.asyncio
async def test_email_service_sends_with_starttls(monkeypatch):
    sent_messages = []

    class FakeSMTP:
        instances = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.login_args = None
            FakeSMTP.instances.append(self)

        async def connect(self):
            return None

        async def login(self, username, password):
            self.login_args = (username, password)

        async def send_message(self, message):
            sent_messages.append(message)

        async def quit(self):
            return None

    monkeypatch.setitem(sys.modules, "aiosmtplib", SimpleNamespace(SMTP=FakeSMTP))
    monkeypatch.setattr(settings, "EMAIL_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USER", "smtp_user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "smtp_secret")
    monkeypatch.setattr(settings, "EMAIL_FROM", "no-reply@example.com")
    monkeypatch.setattr(settings, "EMAIL_FROM_NAME", "Sparkle")

    service = EmailService()

    assert await service.send_verification_email("user@example.com", "123456", username="Ada") is True
    assert FakeSMTP.instances[0].kwargs["use_tls"] is False
    assert FakeSMTP.instances[0].kwargs["start_tls"] is True
    assert FakeSMTP.instances[0].login_args == ("smtp_user", "smtp_secret")
    assert sent_messages[0]["To"] == "user@example.com"
    assert sent_messages[0]["From"] == "Sparkle <no-reply@example.com>"
