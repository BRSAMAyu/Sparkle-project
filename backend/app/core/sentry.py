"""Sentry crash reporting initialization."""
from __future__ import annotations

from loguru import logger


def init_sentry(dsn: str, environment: str, traces_sample_rate: float = 0.1) -> None:
    if not dsn:
        logger.info("Sentry DSN not configured — crash reporting disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.redis import RedisIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            integrations=[
                FastApiIntegration(),
                RedisIntegration(),
                CeleryIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry initialized env={} traces_rate={}", environment, traces_sample_rate)
    except ImportError:
        logger.warning("sentry-sdk not installed — crash reporting disabled")
    except Exception as exc:
        logger.warning("Sentry init failed (non-fatal): {}", exc)
