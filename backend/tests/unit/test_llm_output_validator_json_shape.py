"""V3-FIX-309：LLMOutputValidator 凭据词库副本收口（红→绿实录）。

修前该类维护漂移的 SENSITIVE_PATTERNS 副本（llm_output_validator.py:47）：
凭据键值正则对 JSON 形态零命中、无占位符豁免。本类是 sanitize_llm_output
的二道闸，且被 community_shared_error_service（output_validator 单例）与
llm_security_wrapper 独立调用——redact_secrets 前置使主出口直接暴露面闭合
后，这些独立调用路径仍是漏检面。

修后：词库复用 app.core.llm_safety 的权威 SENSITIVE_PATTERNS
（CREDENTIAL_KEYVALUE_PATTERNS 单一事实源，import 而非复制），
JSON 形态红→绿、占位符豁免随源生效。
"""

from app.core.llm_output_validator import LLMOutputValidator, output_validator


class TestJsonShapeCredentialsDetected:
    """独立调用路径（不经 sanitize_llm_output/redact_secrets 前置）的 JSON 形态凭据必检。"""

    def test_json_credentials_detected(self):
        test_cases = [
            '{"username": "user", "password": "hunter2hunter2"}',
            '{"secret": "s3cr3t-value-99"}',
            '{"token": "tok_en-987654321"}',
        ]

        for text in test_cases:
            result = output_validator.validate(text)
            assert result.is_valid is False, text
            assert result.action == "sanitize", text
            assert len(result.violations) > 0, text
            assert "*" in result.sanitized_text, text

    def test_json_credentials_detected_strict_instance(self):
        validator = LLMOutputValidator(strict_mode=True)
        result = validator.validate('db_config = {"password": "hunter2hunter2"}')

        assert result.is_valid is False
        assert "*" in result.sanitized_text


class TestPlaceholderExemptFollowsSource:
    """占位符豁免随 llm_safety 源同步：文档/Schema 示例不得被误杀（wt597 F4 同款）。"""

    def test_placeholder_values_not_flagged(self):
        safe_samples = [
            '{"password": "***"}',
            '{"password": "<your-password>"}',
            '{"password": "${DB_PASSWORD}"}',
            '{"password": "{{ password }}"}',
            '{"password": null}',
            '{"password": "xxxxxxxx"}',
            '{"properties": {"password": {"type": "string"}}}',
            "password: your-password-here",
        ]

        for text in safe_samples:
            result = output_validator.validate(text)
            assert result.is_valid is True, f"占位符样例被误杀: {text} -> {result.violations}"


class TestOutputSideColloquialAndExtrasKept:
    """输出侧自有补充面（口语形/私钥块/系统路径）在收口后不丢。"""

    def test_colloquial_password_form_still_detected(self):
        result = output_validator.validate("管理员密码是: MySecretPass123")

        assert result.is_valid is False
        assert "*" in result.sanitized_text

    def test_private_key_block_still_detected(self):
        text = "私钥: -----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC..."
        result = output_validator.validate(text)

        assert result.is_valid is False
        assert "*" in result.sanitized_text

    def test_patterns_derived_not_copied(self):
        """词库单一事实源：凭据键值模式必须逐条来自 llm_safety 权威源。"""
        from app.core.llm_safety import CREDENTIAL_KEYVALUE_PATTERNS, LLMSafetyService

        own = [p for p, _ in LLMOutputValidator.SENSITIVE_PATTERNS]
        for source_pattern in CREDENTIAL_KEYVALUE_PATTERNS:
            assert source_pattern in own
        # 类列表 = 权威全表 + 输出侧补充
        assert own[: len(LLMSafetyService.SENSITIVE_PATTERNS)] == list(LLMSafetyService.SENSITIVE_PATTERNS)
