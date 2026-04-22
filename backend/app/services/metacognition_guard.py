from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.metrics import METACOG_DIAGNOSTIC_WORD_HIT_TOTAL


@dataclass(frozen=True)
class DiagnosticViolation:
    pattern_id: str
    matched_text: str
    source: str


_DIAGNOSTIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("identity_type", re.compile(r"你是[^。？！\n]{0,18}(型|人格|类型)")),
    ("belongs_type", re.compile(r"你属于[^。？！\n]{0,18}(型|人格|类型)")),
    ("personality_trait", re.compile(r"你的性格[^。？！\n]{0,20}")),
    (
        "diagnostic_tendency",
        re.compile(
            r"你(有|很|比较)?[^。？！\n]{0,12}(拖延|完美主义|焦虑|内向|外向)(倾向|人格|性格)?"
        ),
    ),
    ("absolute_always", re.compile(r"你总是[^。？！\n]{0,20}")),
    ("absolute_never", re.compile(r"你从不[^。？！\n]{0,20}")),
)


def scan_diagnostic_labels(
    text: str, *, source: str = "runtime"
) -> list[DiagnosticViolation]:
    violations: list[DiagnosticViolation] = []
    candidate = str(text or "").strip()
    if not candidate:
        return violations
    for pattern_id, pattern in _DIAGNOSTIC_PATTERNS:
        for match in pattern.finditer(candidate):
            violations.append(
                DiagnosticViolation(
                    pattern_id=pattern_id,
                    matched_text=match.group(0),
                    source=source,
                )
            )
    return violations


def scan_many(
    texts: list[str] | tuple[str, ...], *, source: str = "runtime"
) -> list[DiagnosticViolation]:
    violations: list[DiagnosticViolation] = []
    for text in texts:
        violations.extend(scan_diagnostic_labels(text, source=source))
    return violations


def record_metric(violations: list[DiagnosticViolation], *, source: str) -> None:
    if not violations:
        return
    METACOG_DIAGNOSTIC_WORD_HIT_TOTAL.labels(source=source).inc(len(violations))
