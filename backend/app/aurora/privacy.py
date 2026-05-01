from __future__ import annotations

import hashlib
import math
import random
import re
from dataclasses import dataclass

from app.config import settings
from app.core.kill_switch import normalize_mode

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


def pii_redaction_mode() -> str:
    return normalize_mode(
        getattr(settings, "AURORA_PRIVACY_PII_REDACTION_MODE", "live"),
        fallback="live",
    )


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
