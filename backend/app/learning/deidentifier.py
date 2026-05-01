"""Strict PII and context deidentification for distilled strategies."""

from __future__ import annotations

import re
from dataclasses import dataclass

_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(东北|华北|华东|华南|西北|西南|北京|上海|广州|深圳|杭州|成都)"), ""),
    (re.compile(r"(大一|大二|大三|大四|研一|研二|研三)"), "学生"),
    (re.compile(r"(爸爸|妈妈|父亲|母亲|姐姐|哥哥|弟弟|妹妹|亲戚|叔叔|阿姨|男朋友|女朋友)"), "家人"),
    (re.compile(r"\b20\d{2}年\d{0,2}月?\d{0,2}日?\b"), "一段时间"),
    (re.compile(r"\b\d{11}\b"), "[已移除联系方式]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[已移除邮箱]"),
    (re.compile(r"\b\d{17}[\dXx]\b"), "[已移除身份标识]"),
)

_BLOCKING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{11}\b"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"\b\d{17}[\dXx]\b"),
    re.compile(r"(身份证|学号|手机号|邮箱)"),
)


@dataclass(frozen=True)
class DeidentificationResult:
    sanitized_text: str
    passed: bool
    markers_removed: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()


def deidentify_text(text: str) -> DeidentificationResult:
    """Remove high-risk personal details from distilled content."""

    raw_blocking = [pattern.pattern for pattern in _BLOCKING_PATTERNS if pattern.search(text)]
    sanitized = text
    removed: list[str] = []
    for pattern, replacement in _REPLACEMENTS:
        updated, count = pattern.subn(replacement, sanitized)
        if count:
            removed.append(pattern.pattern)
            sanitized = updated
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    blocked: list[str] = list(raw_blocking)
    for pattern in _BLOCKING_PATTERNS:
        if pattern.search(sanitized):
            blocked.append(pattern.pattern)
    return DeidentificationResult(
        sanitized_text=sanitized,
        passed=not blocked,
        markers_removed=tuple(removed),
        blocked_reasons=tuple(blocked),
    )
