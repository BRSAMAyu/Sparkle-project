from __future__ import annotations

import pytest

from app.aurora.privacy import redact_pii, redact_pii_with_report
from app.config import settings


@pytest.mark.parametrize(
    ("raw_text", "marker"),
    [
        ("请联系我：13812345678", "[REDACTED_PHONE]"),
        ("邮箱是 test.user@example.com", "[REDACTED_EMAIL]"),
        ("身份证 11010519491231002X", "[REDACTED_CN_ID]"),
        ("银行卡 6222021234567890123", "[REDACTED_BANK_CARD]"),
        ("手机号 +86 13912345678 和邮箱 foo@bar.com", "[REDACTED_PHONE]"),
        ("姓名：张三", "[REDACTED_NAME]"),
        ("my name is Ada Lovelace", "[REDACTED_NAME]"),
        ("我叫李雷，email is lilei@example.com, phone 13812345678", "[REDACTED_NAME]"),
    ],
)
def test_redact_pii_masks_sensitive_markers(raw_text: str, marker: str) -> None:
    result = redact_pii(raw_text)

    assert marker in result
    assert result != raw_text


@pytest.mark.parametrize(
    "raw_text",
    [
        "今天学习 90 分钟",
        "task:12345",
        "计划 ID abc:def",
        "example@localhost",
        "银行卡后四位 1234",
    ],
)
def test_redact_pii_preserves_non_pii_text(raw_text: str) -> None:
    assert redact_pii(raw_text) == raw_text


def test_redact_pii_shadow_returns_safe_text(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_PRIVACY_PII_REDACTION_MODE", "shadow", raising=False)
    raw_text = "我叫李雷，手机号是13812345678"
    result = redact_pii(raw_text)

    assert "[REDACTED_NAME]" in result
    assert "[REDACTED_PHONE]" in result
    assert "李雷" not in result
    assert "13812345678" not in result


def test_redact_pii_shadow_report_is_safe_for_telemetry(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_PRIVACY_PII_REDACTION_MODE", "shadow", raising=False)
    raw_text = "name: Jane Doe, 手机号 13812345678, 邮箱 jane@example.com"

    report = redact_pii_with_report(raw_text)
    telemetry = report.telemetry()

    assert report.text != raw_text
    assert report.source_sha256
    assert set(report.categories) == {"email", "name", "phone"}
    assert raw_text not in str(telemetry)
    assert "Jane Doe" not in str(telemetry)
    assert "13812345678" not in str(telemetry)
    assert "jane@example.com" not in str(telemetry)


def test_redact_pii_off_returns_original_text(monkeypatch) -> None:
    monkeypatch.setattr(settings, "AURORA_PRIVACY_PII_REDACTION_MODE", "off", raising=False)
    raw_text = "邮箱是 test.user@example.com"

    assert redact_pii(raw_text) == raw_text
