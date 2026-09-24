from __future__ import annotations

import asyncio
import hashlib
import math
import random
import re
import time
from dataclasses import dataclass
from typing import TypedDict

from app.config import settings
from app.core.background_tasks import spawn_tracked
from app.core.kill_switch import normalize_mode, record_mode_gauge

_EMAIL_RE = re.compile(
    r"(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9._%+-])",
    flags=re.IGNORECASE,
)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
_CN_ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)|(?<!\d)\d{15}(?!\d)")
_BANK_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)")
_CN_NAME_LABEL_RE = re.compile(
    r"(?P<prefix>(?:姓名|名字)[:：]?\s*)(?P<value>[\u4e00-\u9fff]{2,4}|[A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3})"
)
_CN_NAME_SELF_RE = re.compile(r"(?P<prefix>(?:我叫|叫我)\s*)(?P<value>[\u4e00-\u9fff]{2,4})")
_EN_NAME_RE = re.compile(
    r"(?P<prefix>\b(?:my name is|name is|name:)\s+)(?P<value>[A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3})",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class PiiRedactionResult:
    text: str
    mode: str
    redacted: bool
    categories: tuple[str, ...]
    source_sha256: str

    def telemetry(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "redacted": self.redacted,
            "categories": list(self.categories),
            "source_sha256": self.source_sha256,
        }


def sha256_token(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class _ModeCache(TypedDict):
    value: str | None
    expires_at: float
    settings_seed: str | None


_MODE_CACHE: _ModeCache = {"value": None, "expires_at": 0.0, "settings_seed": None}
_MODE_TTL_SECONDS = 30.0


def _resolve_settings_mode() -> str:
    return normalize_mode(
        getattr(settings, "AURORA_PRIVACY_PII_REDACTION_MODE", "live"),
        fallback="live",
    )


def clear_mode_cache() -> None:
    """Reset the in-process kill-switch cache. Intended for tests."""
    _MODE_CACHE["value"] = None
    _MODE_CACHE["expires_at"] = 0.0
    _MODE_CACHE["settings_seed"] = None


async def _refresh_mode_cache_async() -> None:
    """Background refresh of the kill-switch mode cache.

    Failures leave the cache intact; the next caller will retry after TTL.
    """
    try:
        from app.services.aurora_privacy_kill_switch_service import (
            AuroraPrivacyKillSwitchService,
        )

        mode = await AuroraPrivacyKillSwitchService().get_mode()
    except Exception:
        return
    _MODE_CACHE["value"] = mode
    _MODE_CACHE["expires_at"] = time.monotonic() + _MODE_TTL_SECONDS


def _resolve_mode_safe() -> str:
    """Read the kill-switch mode without crashing on event-loop mismatch.

    SEC-4 / R2-04: the previous implementation called
    ``asyncio.get_event_loop().run_until_complete(...)`` which raises inside a
    running loop (Python 3.10+), forcing the entire LLM path into the silent
    settings fallback. We now:

    * Detect a running loop and **schedule** a background refresh, returning
      the cached value (or the settings fallback) immediately — never blocks
      the async caller.
    * In purely synchronous contexts (CLI, Celery, tests) run the async
      kill-switch helper to completion via ``asyncio.run``.
    """
    settings_mode = _resolve_settings_mode()
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            from app.services.aurora_privacy_kill_switch_service import (
                AuroraPrivacyKillSwitchService,
            )

            return asyncio.run(AuroraPrivacyKillSwitchService().get_mode())
        except Exception:
            return settings_mode

    # Inside an event loop — schedule a background refresh; return the last
    # known cached value (or the static settings fallback on cold start).
    # FF-CONVERGENCE（wt310）：裸 create_task 无强引用，刷新任务可能被 GC 回收
    # → 隐私模式刷新静默丢失（wt294 清单最高优先级之二）。
    spawn_tracked(_refresh_mode_cache_async(), name="aurora.privacy.refresh_mode_cache")
    cached = _MODE_CACHE.get("value")
    return str(cached) if cached else settings_mode


def pii_redaction_mode() -> str:
    """Current PII redaction mode (``off`` / ``shadow`` / ``live``).

    Safe to call from sync OR async contexts; uses a 30 s TTL cache so the
    hot LLM input path does not re-read Redis on every call. The cache is
    keyed on the current settings fallback as well, so a test monkey-patching
    ``AURORA_PRIVACY_PII_REDACTION_MODE`` automatically invalidates the cache
    on the next call.
    """
    now = time.monotonic()
    settings_seed = _resolve_settings_mode()
    cached = _MODE_CACHE.get("value")
    expires_at = float(_MODE_CACHE.get("expires_at") or 0.0)
    cached_seed = _MODE_CACHE.get("settings_seed")
    if cached is not None and now < expires_at and cached_seed == settings_seed:
        mode = str(cached)
    else:
        mode = _resolve_mode_safe()
        _MODE_CACHE["value"] = mode
        _MODE_CACHE["expires_at"] = now + _MODE_TTL_SECONDS
        _MODE_CACHE["settings_seed"] = settings_seed
    record_mode_gauge("privacy", "pii_redaction", mode)
    return mode


def _redact_pattern(text: str, pattern: re.Pattern[str], replacement: str, category: str, categories: set[str]) -> str:
    redacted, count = pattern.subn(replacement, text)
    if count:
        categories.add(category)
    return redacted


def _redact_name_pattern(text: str, pattern: re.Pattern[str], categories: set[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        categories.add("name")
        return f"{match.group('prefix')}[REDACTED_NAME]"

    return pattern.sub(replace, text)


def _redact_pii_text(text: str) -> tuple[str, tuple[str, ...]]:
    redacted = str(text or "")
    categories: set[str] = set()
    redacted = _redact_pattern(redacted, _EMAIL_RE, "[REDACTED_EMAIL]", "email", categories)
    redacted = _redact_pattern(redacted, _PHONE_RE, "[REDACTED_PHONE]", "phone", categories)
    redacted = _redact_pattern(redacted, _CN_ID_RE, "[REDACTED_CN_ID]", "cn_id", categories)
    redacted = _redact_pattern(redacted, _BANK_CARD_RE, "[REDACTED_BANK_CARD]", "bank_card", categories)
    redacted = _redact_name_pattern(redacted, _CN_NAME_LABEL_RE, categories)
    redacted = _redact_name_pattern(redacted, _CN_NAME_SELF_RE, categories)
    redacted = _redact_name_pattern(redacted, _EN_NAME_RE, categories)
    return redacted, tuple(sorted(categories))


def redact_pii_with_report(text: str) -> PiiRedactionResult:
    raw_text = str(text or "")
    mode = pii_redaction_mode()
    if mode == "off":
        return PiiRedactionResult(
            text=raw_text,
            mode=mode,
            redacted=False,
            categories=(),
            source_sha256="",
        )

    redacted_text, categories = _redact_pii_text(raw_text)
    return PiiRedactionResult(
        text=redacted_text,
        mode=mode,
        redacted=redacted_text != raw_text,
        categories=categories,
        source_sha256=sha256_token(raw_text) if categories else "",
    )


def redact_pii(text: str) -> str:
    mode = pii_redaction_mode()
    if mode == "off":
        return str(text or "")
    return redact_pii_with_report(text).text


def laplace_noise(
    value: float,
    epsilon: float = 0.3,
    *,
    sensitivity: float = 1.0,
    rng: random.Random | None = None,
) -> float:
    if epsilon <= 0:
        raise ValueError("epsilon must be > 0")
    if sensitivity <= 0:
        raise ValueError("sensitivity must be > 0")

    base_value = float(value)
    if not math.isfinite(base_value):
        raise ValueError("value must be finite")

    generator = rng or random.Random()
    u = generator.random() - 0.5
    if u == 0:
        return base_value

    scale = sensitivity / epsilon
    noise = -scale * math.copysign(math.log(1 - (2 * abs(u))), u)
    return base_value + noise
