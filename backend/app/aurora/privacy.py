from __future__ import annotations

import hashlib
import math
import random
import re

_EMAIL_RE = re.compile(
    r"(?<![A-Z0-9._%+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![A-Z0-9._%+-])",
    flags=re.IGNORECASE,
)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
_CN_ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)|(?<!\d)\d{15}(?!\d)")
_BANK_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,19}(?!\d)")


def sha256_token(value: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def redact_pii(text: str) -> str:
    redacted = str(text or "")
    redacted = _EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
    redacted = _PHONE_RE.sub("[REDACTED_PHONE]", redacted)
    redacted = _CN_ID_RE.sub("[REDACTED_CN_ID]", redacted)
    redacted = _BANK_CARD_RE.sub("[REDACTED_BANK_CARD]", redacted)
    return redacted


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
