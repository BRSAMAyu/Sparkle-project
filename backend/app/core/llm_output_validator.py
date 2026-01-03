"""
LLM 输出验证与过滤模块

功能:
1. 敏感信息泄露检测
2. 恶意指令过滤
3. 输出长度限制
4. HTML/JS 注入防护
5. 内容合规性检查

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import re
import logging
from typing import Tuple, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    sanitized_text: str
    violations: List[str]
    action: str  # "allow", "block", "sanitize"


class LLMOutputValidator:
    """
    LLM 输出验证器 - 确保输出内容安全合规

    防护层级:
    1. 敏感信息检测 (密码、密钥、金融信息)
    2. 恶意指令过滤 (删除、格式化等危险操作)
    3. 代码注入防护 (HTML/JS/脚本)
    4. 长度限制 (防止无限生成)
    5. 内容合规性 (暴力、色情、仇恨言论)
    """

    # 敏感信息泄露模式
    SENSITIVE_PATTERNS = [
        # 密钥类 (高风险)
        (r"api[_-]?key\s*[:：]\s*[A-Za-z0-9]{20,}", "API Key 泄露"),
        (r"secret\s*[:：]\s*[A-Za-z0-9]{20,}", "Secret 泄露"),
        (r"token\s*[:：]\s*[A-Za-z0-9]{20,}", "Token 泄露"),
        (r"password\s*[:：]\s*\S{8,}", "密码泄露"),
        (r"private[_-]?key\s*[:：]\s*-----BEGIN", "私钥泄露"),

        # 金融类 (高风险)
        (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "信用卡号"),
        (r"\b\d{3}[- ]?\d{2}[- ]?\d{4}\b", "美国 SSN"),
        (r"\b\d{16}\b", "16位数字 (可能是卡号)"),

        # 个人身份信息 (中风险)
        (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "邮箱地址"),
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP 地址"),
        (r"1[3-9]\d{9}", "中国手机号"),
        (r"\b\d{18}\b", "身份证号"),

        # 系统信息 (低风险)
        (r"/etc/(passwd|shadow)", "系统密码文件路径"),
        (r"C:\\\\Windows\\\\", "Windows 系统路径"),
        (r"/root/", "Linux root 目录"),
    ]

    # 恶意指令模式
    MALICIOUS_PATTERNS = [
        (r"delete\s+(all|database|table|file)", "删除操作"),
        (r"drop\s+(table|database)", "删除结构"),
        (r"format\s+[cC]:", "格式化磁盘"),
        (r"rm\s+-rf\s+/", "强制删除根目录"),
        (r"mkfs\s+", "格式化命令"),
        (r"shutdown\s+", "关机命令"),
        (r"reboot\s+", "重启命令"),
        (r"kill\s+-9\s+", "强制杀进程"),
    ]

    # 代码注入模式
    CODE_INJECTION_PATTERNS = [
        (r"<script[^>]*>.*?</script>", "Script 标签"),
        (r"javascript:", "JavaScript 协议"),
        (r"on\w+\s*=", "HTML 事件处理器"),
        (r"<iframe[^>]*>", "Iframe 嵌入"),
        (r"<object[^>]*>", "Object 嵌入"),
        (r"<embed[^>]*>", "Embed 嵌入"),
        (r"vbscript:", "VBScript"),
        (r"data:text/html", "Data URL"),
        (r"eval\s*\(", "eval 函数"),
        (r"exec\s*\(", "exec 函数"),
        (r"Function\s*\(", "Function 构造"),
    ]

    # 内容合规性模式 (需要人工审核)
    COMPLIANCE_PATTERNS = [
        (r"暴力|杀|死|伤害", "暴力内容"),
        (r"色情|性|裸", "色情内容"),
        (r"歧视|仇恨|种族", "仇恨言论"),
        (r"炸弹|恐怖|袭击", "恐怖内容"),
    ]

    # 输出长度限制
    MAX_OUTPUT_LENGTH = 10000  # 字符

    # 允许的最大代码块数量
    MAX_CODE_BLOCKS = 10

    def __init__(self, strict_mode: bool = True):
        """
        初始化验证器

        Args:
            strict_mode: 严格模式 (更激进的过滤)
        """
        self.strict_mode = strict_mode

        # 预编译正则
        self._compiled_patterns = {
            'sensitive': [(re.compile(p, re.IGNORECASE), desc) for p, desc in self.SENSITIVE_PATTERNS],
            'malicious': [(re.compile(p, re.IGNORECASE), desc) for p, desc in self.MALICIOUS_PATTERNS],
            'code': [(re.compile(p, re.IGNORECASE), desc) for p, desc in self.CODE_INJECTION_PATTERNS],
            'compliance': [(re.compile(p, re.IGNORECASE), desc) for p, desc in self.COMPLIANCE_PATTERNS],
        }

        logger.info(f"LLMOutputValidator initialized (strict_mode={strict_mode})")

    def validate(self, text: str, context: Optional[Dict] = None) -> ValidationResult:
        """
        验证 LLM 输出

        Args:
            text: LLM 原始输出
            context: 上下文信息 (如用户ID、会话ID等)

        Returns:
            ValidationResult: 验证结果
        """
        if not text or not isinstance(text, str):
            return ValidationResult(True, "", [], "allow")

        violations = []
        sanitized_text = text
        action = "allow"

        # Layer 1: 长度限制
        if len(text) > self.MAX_OUTPUT_LENGTH:
            violations.append(f"输出过长: {len(text)} > {self.MAX_OUTPUT_LENGTH}")
            sanitized_text = text[:self.MAX_OUTPUT_LENGTH] + "... [截断]"
            action = "sanitize"

        # Layer 2: 敏感信息泄露检测
        sensitive_result = self._detect_sensitive_info(sanitized_text)
        if sensitive_result.detected:
            violations.extend(sensitive_result.violations)
            sanitized_text = sensitive_result.sanitized_text
            action = "sanitize" if action == "allow" else action

            # 如果是严格模式且检测到高风险信息,直接阻断
            if self.strict_mode and sensitive_result.high_risk:
                action = "block"

        # Layer 3: 恶意指令过滤
        malicious_result = self._filter_malicious_instructions(sanitized_text)
        if malicious_result.detected:
            violations.extend(malicious_result.violations)
            sanitized_text = malicious_result.sanitized_text
            action = "block"  # 恶意指令必须阻断

        # Layer 4: 代码注入防护
        code_result = self._filter_code_injection(sanitized_text)
        if code_result.detected:
            violations.extend(code_result.violations)
            sanitized_text = code_result.sanitized_text
            action = "sanitize" if action == "allow" else action

        # Layer 5: 内容合规性检查 (可选,可配置)
        if self.strict_mode:
            compliance_result = self._check_compliance(sanitized_text)
            if compliance_result.detected:
                violations.extend(compliance_result.violations)
                # 合规性问题通常需要人工审核
                action = "sanitize"

        # Layer 6: 代码块数量检查
        code_block_count = sanitized_text.count("```")
        if code_block_count > self.MAX_CODE_BLOCKS * 2:  # 每个代码块需要 ```
            violations.append(f"代码块过多: {code_block_count//2} > {self.MAX_CODE_BLOCKS}")
            action = "sanitize"

        # 记录安全事件
        if violations:
            logger.warning(
                f"LLM输出安全事件 - Context: {context}, "
                f"Action: {action}, Violations: {violations}"
            )

        is_valid = action != "block"

        return ValidationResult(
            is_valid=is_valid,
            sanitized_text=sanitized_text,
            violations=violations,
            action=action
        )

    def _detect_sensitive_info(self, text: str) -> 'DetectionResult':
        """检测敏感信息泄露"""
        violations = []
        sanitized_text = text
        high_risk = False

        for pattern, description in self._compiled_patterns['sensitive']:
            matches = pattern.findall(sanitized_text)
            if matches:
                for match in matches:
                    # 部分遮蔽
                    if isinstance(match, tuple):
                        match_str = match[0] if isinstance(match, tuple) else match
                    else:
                        match_str = match

                    masked = self._mask_sensitive(match_str)
                    sanitized_text = sanitized_text.replace(match_str, masked)
                    violations.append(f"{description}: {masked}")
                    high_risk = True  # 敏感信息都是高风险

        return DetectionResult(
            detected=len(violations) > 0,
            violations=violations,
            sanitized_text=sanitized_text,
            high_risk=high_risk
        )

    def _filter_malicious_instructions(self, text: str) -> 'DetectionResult':
        """过滤恶意指令"""
        violations = []
        sanitized_text = text

        for pattern, description in self._compiled_patterns['malicious']:
            matches = pattern.findall(sanitized_text)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match_str = match[0]
                    else:
                        match_str = match

                    # 替换为警告
                    warning = f"[{description}_FILTERED]"
                    sanitized_text = sanitized_text.replace(match_str, warning)
                    violations.append(description)

        return DetectionResult(
            detected=len(violations) > 0,
            violations=violations,
            sanitized_text=sanitized_text,
            high_risk=True  # 恶意指令都是高风险
        )

    def _filter_code_injection(self, text: str) -> 'DetectionResult':
        """过滤代码注入"""
        violations = []
        sanitized_text = text

        for pattern, description in self._compiled_patterns['code']:
            matches = pattern.findall(sanitized_text)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match_str = match[0]
                    else:
                        match_str = match

                    # 替换为警告
                    warning = f"[{description}_FILTERED]"
                    sanitized_text = sanitized_text.replace(match_str, warning)
                    violations.append(description)

        return DetectionResult(
            detected=len(violations) > 0,
            violations=violations,
            sanitized_text=sanitized_text,
            high_risk=True  # 代码注入都是高风险
        )

    def _check_compliance(self, text: str) -> 'DetectionResult':
        """检查内容合规性"""
        violations = []
        sanitized_text = text

        for pattern, description in self._compiled_patterns['compliance']:
            matches = pattern.findall(sanitized_text)
            if matches:
                violations.append(f"潜在违规: {description}")

        return DetectionResult(
            detected=len(violations) > 0,
            violations=violations,
            sanitized_text=sanitized_text,
            high_risk=False  # 需要人工审核
        )

    def _mask_sensitive(self, text: str) -> str:
        """遮蔽敏感信息"""
        length = len(text)
        if length <= 4:
            return "*" * length
        elif length <= 10:
            return text[:2] + "*" * (length - 4) + text[-2:]
        else:
            return text[:4] + "*" * (length - 8) + text[-4:]

    def truncate_if_needed(self, text: str, max_length: Optional[int] = None) -> str:
        """
        如果需要则截断文本

        Args:
            text: 文本
            max_length: 最大长度 (默认使用 MAX_OUTPUT_LENGTH)

        Returns:
            str: 截断后的文本
        """
        max_len = max_length or self.MAX_OUTPUT_LENGTH
        if len(text) <= max_len:
            return text

        return text[:max_len] + "... [内容已截断]"

    def sanitize_html(self, text: str) -> str:
        """
        HTML 安全转义 (用于需要显示 HTML 的场景)

        Args:
            text: 包含 HTML 的文本

        Returns:
            str: 转义后的安全 HTML
        """
        import html

        # 转义 HTML 特殊字符
        escaped = html.escape(text)

        # 但保留代码块标记
        escaped = escaped.replace("<code>", "<code>")
        escaped = escaped.replace("</code>", "</code>")
        escaped = escaped.replace("<pre>", "<pre>")
        escaped = escaped.replace("</pre>", "</pre>")

        return escaped

    def get_security_stats(self) -> dict:
        """获取验证器统计信息"""
        return {
            "max_output_length": self.MAX_OUTPUT_LENGTH,
            "max_code_blocks": self.MAX_CODE_BLOCKS,
            "strict_mode": self.strict_mode,
            "sensitive_patterns": len(self.SENSITIVE_PATTERNS),
            "malicious_patterns": len(self.MALICIOUS_PATTERNS),
            "code_injection_patterns": len(self.CODE_INJECTION_PATTERNS),
            "compliance_patterns": len(self.COMPLIANCE_PATTERNS),
        }


@dataclass
class DetectionResult:
    """内部检测结果"""
    detected: bool
    violations: List[str]
    sanitized_text: str
    high_risk: bool


# 单例实例
output_validator = LLMOutputValidator()


# 使用示例
if __name__ == "__main__":
    # 测试用例
    test_cases = [
        # 正常输出
        "这是一个正常的回答，包含一些有用的信息。",

        # 敏感信息泄露
        "根据您的要求，API密钥是 sk-1234567890abcdef1234567890abcdef，密码是 MyPassword123",

        # 恶意指令
        "为了修复问题，请执行: rm -rf /var/lib 数据库需要删除所有表: DROP TABLE users;",

        # 代码注入
        "<script>alert('xss')</script> 请访问这个链接: javascript:alert('test')",

        # 超长输出
        "这是一个很长的回答。" * 5000,

        # 混合问题
        "API key: sk-123 <script>alert(1)</script> rm -rf /",
    ]

    validator = LLMOutputValidator(strict_mode=True)

    for i, test in enumerate(test_cases, 1):
        result = validator.validate(test, context={"test_id": i})
        print(f"\n测试 {i}:")
        print(f"  输入: {test[:60]}...")
        print(f"  是否有效: {result.is_valid}")
        print(f"  操作: {result.action}")
        print(f"  违规: {result.violations}")
        print(f"  净化后: {result.sanitized_text[:60]}...")
