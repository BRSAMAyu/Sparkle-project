"""V3-FIX-309：RequestValidator.sanitize_for_log 脱敏契约落地（红→绿实录）。

修前 orchestration/validator.py:47 的 SENSITIVE_PATTERNS 是与凭据词库同名
相撞的注入特征列表（正名归位为 XSS_PATTERNS），而真正名为"脱敏"的
sanitize_for_log 只做长度截断——凭据键值（含 JSON 形态）原样进日志面。

修后：先经 llm_secure_io.redact_secrets（词库内建自 llm_safety
SECRET_VALUE_PLACEHOLDER_EXEMPT 单一事实源）脱敏，再截断。
"""

from app.orchestration.validator import RequestValidator


class TestSanitizeForLogRedaction:
    def test_json_credential_redacted(self):
        validator = RequestValidator()

        sanitized = validator.sanitize_for_log('{"password": "hunter2hunter2"}')

        assert "hunter2hunter2" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_assignment_credential_redacted(self):
        validator = RequestValidator()

        sanitized = validator.sanitize_for_log("token=sk-live-abc123456789")

        assert "sk-live-abc123456789" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_placeholder_value_untouched(self):
        """占位符豁免随单一事实源生效：文档占位词不得被改写。"""
        validator = RequestValidator()

        sanitized = validator.sanitize_for_log('{"password": "<your-password>"}')

        assert sanitized == '{"password": "<your-password>"}'

    def test_truncation_contract_preserved(self):
        validator = RequestValidator()

        long_text = "x" * 300
        sanitized = validator.sanitize_for_log(long_text)

        assert sanitized == "x" * 200 + "..."

    def test_empty_and_short_passthrough(self):
        validator = RequestValidator()

        assert validator.sanitize_for_log("") == ""
        assert validator.sanitize_for_log("normal log line") == "normal log line"
