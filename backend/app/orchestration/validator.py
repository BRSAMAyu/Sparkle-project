"""
Request Validator
请求验证器，负责输入验证和清理
"""
import re
from typing import Optional, Tuple
from loguru import logger
from dataclasses import dataclass

from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.token_tracker import TokenTracker


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    error_message: Optional[str] = None
    sanitized_data: Optional[dict] = None


class RequestValidator:
    """
    请求验证器
    负责验证和清理输入数据
    """
    
    # 最大输入长度限制
    MAX_MESSAGE_LENGTH = 2000
    MAX_SESSION_ID_LENGTH = 100
    MAX_USER_ID_LENGTH = 100
    MAX_REQUEST_ID_LENGTH = 100
    
    # 最小输入长度
    MIN_MESSAGE_LENGTH = 1
    
    # 正则模式
    PATTERN_SESSION_ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
    PATTERN_USER_ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
    PATTERN_REQUEST_ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
    
    # 敏感词过滤（简单示例）
    SENSITIVE_PATTERNS = [
        re.compile(r'<script.*?>', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'onclick=', re.IGNORECASE),
        re.compile(r'onerror=', re.IGNORECASE),
    ]
    
    def __init__(self, redis_client=None, daily_quota: int = 100000):
        """
        初始化 RequestValidator

        Args:
            redis_client: Redis 客户端（用于配额检查）
            daily_quota: 每日 Token 配额限制
        """
        self.redis = redis_client
        self.daily_quota = daily_quota
        self.token_tracker = TokenTracker(redis_client) if redis_client else None
        logger.info(f"RequestValidator initialized with daily_quota={daily_quota}")

    async def validate_chat_request(self, request: agent_service_pb2.ChatRequest) -> ValidationResult:
        """
        验证 ChatRequest
        
        Args:
            request: gRPC 请求
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            # 1. 验证用户 ID
            if not request.user_id:
                return ValidationResult(False, "user_id is required")
            
            if len(request.user_id) > self.MAX_USER_ID_LENGTH:
                return ValidationResult(False, f"user_id exceeds max length {self.MAX_USER_ID_LENGTH}")
            
            if not self.PATTERN_USER_ID.match(request.user_id):
                return ValidationResult(False, "user_id contains invalid characters")
            
            # 2. 验证会话 ID
            if not request.session_id:
                return ValidationResult(False, "session_id is required")
            
            if len(request.session_id) > self.MAX_SESSION_ID_LENGTH:
                return ValidationResult(False, f"session_id exceeds max length {self.MAX_SESSION_ID_LENGTH}")
            
            if not self.PATTERN_SESSION_ID.match(request.session_id):
                return ValidationResult(False, "session_id contains invalid characters")
            
            # 3. 验证请求 ID
            if not request.request_id:
                return ValidationResult(False, "request_id is required")
            
            if len(request.request_id) > self.MAX_REQUEST_ID_LENGTH:
                return ValidationResult(False, f"request_id exceeds max length {self.MAX_REQUEST_ID_LENGTH}")
            
            if not self.PATTERN_REQUEST_ID.match(request.request_id):
                return ValidationResult(False, "request_id contains invalid characters")
            
            # 4. 验证输入内容
            if request.HasField("message"):
                message = request.message
                result = self.validate_message(message)
                if not result.is_valid:
                    return result
                
            elif request.HasField("tool_result"):
                tool_result = request.tool_result
                result = self.validate_tool_result(tool_result)
                if not result.is_valid:
                    return result
            
            else:
                return ValidationResult(False, "Either message or tool_result must be provided")
            
            # 5. 验证用户配置（可选）
            if request.HasField("config"):
                result = self.validate_config(request.config)
                if not result.is_valid:
                    return result
            
            # 6. 配额检查（如果启用了 Redis）
            if self.token_tracker:
                quota_check = await self.token_tracker.check_quota(
                    user_id=request.user_id,
                    daily_limit=self.daily_quota
                )

                if not quota_check["within_quota"]:
                    error_msg = (
                        f"Daily token quota exceeded. "
                        f"Used: {quota_check['used']}/{quota_check['limit']} tokens "
                        f"({quota_check['percentage']}). "
                        f"Please try again tomorrow or upgrade your plan."
                    )
                    logger.warning(
                        f"Quota exceeded for user {request.user_id}: "
                        f"{quota_check['used']}/{quota_check['limit']}"
                    )
                    return ValidationResult(False, error_msg)

                # 记录配额使用情况到日志
                logger.debug(
                    f"Quota check passed for user {request.user_id}: "
                    f"{quota_check['used']}/{quota_check['limit']} "
                    f"({quota_check['percentage']})"
                )

            return ValidationResult(True, sanitized_data={
                "user_id": request.user_id,
                "session_id": request.session_id,
                "request_id": request.request_id,
            })

        except Exception as e:
            logger.error(f"Error validating request: {e}")
            return ValidationResult(False, f"Validation error: {str(e)}")

    def validate_message(self, message: str) -> ValidationResult:
        """
        验证消息内容
        
        Args:
            message: 消息文本
            
        Returns:
            ValidationResult: 验证结果
        """
        # 1. 长度验证
        if not message or len(message.strip()) == 0:
            return ValidationResult(False, "Message cannot be empty")
        
        if len(message) > self.MAX_MESSAGE_LENGTH:
            return ValidationResult(False, f"Message exceeds max length {self.MAX_MESSAGE_LENGTH}")
        
        if len(message) < self.MIN_MESSAGE_LENGTH:
            return ValidationResult(False, f"Message must be at least {self.MIN_MESSAGE_LENGTH} character")
        
        # 2. 清理和检查敏感内容
        cleaned = self._sanitize_text(message)
        
        # 3. 检查是否包含恶意内容
        if self._contains_malicious_content(cleaned):
            return ValidationResult(False, "Message contains potentially malicious content")
        
        # 4. 检查是否只是空白字符
        if not cleaned.strip():
            return ValidationResult(False, "Message cannot be only whitespace")
        
        return ValidationResult(True, sanitized_data={"message": cleaned})

    def validate_tool_result(self, tool_result: agent_service_pb2.ToolResult) -> ValidationResult:
        """
        验证工具执行结果
        
        Args:
            tool_result: 工具结果
            
        Returns:
            ValidationResult: 验证结果
        """
        # 1. 验证工具名称
        if not tool_result.tool_name:
            return ValidationResult(False, "tool_name is required")
        
        if len(tool_result.tool_name) > 100:
            return ValidationResult(False, "tool_name too long")
        
        # 2. 验证工具调用 ID
        if not tool_result.tool_call_id:
            return ValidationResult(False, "tool_call_id is required")
        
        # 3. 验证结果 JSON
        if not tool_result.result_json:
            return ValidationResult(False, "result_json is required")
        
        # 尝试解析 JSON 以验证格式
        try:
            import json
            parsed = json.loads(tool_result.result_json)
            
            # 限制 JSON 大小
            if len(tool_result.result_json) > 10000:
                return ValidationResult(False, "result_json too large")
            
            return ValidationResult(True, sanitized_data={
                "tool_call_id": tool_result.tool_call_id,
                "tool_name": tool_result.tool_name,
                "result_json": tool_result.result_json,
                "is_error": tool_result.is_error,
                "error_message": tool_result.error_message if tool_result.error_message else None
            })
            
        except json.JSONDecodeError:
            return ValidationResult(False, "result_json is not valid JSON")

    def validate_config(self, config: agent_service_pb2.ChatConfig) -> ValidationResult:
        """
        验证聊天配置
        
        Args:
            config: 配置对象
            
        Returns:
            ValidationResult: 验证结果
        """
        # 1. 验证模型名称（如果提供）
        if config.model and len(config.model) > 100:
            return ValidationResult(False, "model name too long")
        
        # 2. 验证温度值
        if config.HasField("temperature"):
            if config.temperature < 0.0 or config.temperature > 2.0:
                return ValidationResult(False, "temperature must be between 0.0 and 2.0")
        
        # 3. 验证最大 token 数
        if config.HasField("max_tokens"):
            if config.max_tokens <= 0 or config.max_tokens > 8192:
                return ValidationResult(False, "max_tokens must be between 1 and 8192")
        
        return ValidationResult(True)

    def validate_session_id(self, session_id: str) -> ValidationResult:
        """
        验证会话 ID 格式
        
        Args:
            session_id: 会话 ID
            
        Returns:
            ValidationResult: 验证结果
        """
        if not session_id:
            return ValidationResult(False, "session_id is required")
        
        if len(session_id) > self.MAX_SESSION_ID_LENGTH:
            return ValidationResult(False, f"session_id exceeds max length {self.MAX_SESSION_ID_LENGTH}")
        
        if not self.PATTERN_SESSION_ID.match(session_id):
            return ValidationResult(False, "session_id contains invalid characters, use only alphanumeric, hyphen, underscore")
        
        return ValidationResult(True)

    def validate_user_id(self, user_id: str) -> ValidationResult:
        """
        验证用户 ID 格式
        
        Args:
            user_id: 用户 ID
            
        Returns:
            ValidationResult: 验证结果
        """
        if not user_id:
            return ValidationResult(False, "user_id is required")
        
        if len(user_id) > self.MAX_USER_ID_LENGTH:
            return ValidationResult(False, f"user_id exceeds max length {self.MAX_USER_ID_LENGTH}")
        
        if not self.PATTERN_USER_ID.match(user_id):
            return ValidationResult(False, "user_id contains invalid characters")
        
        return ValidationResult(True)

    def _sanitize_text(self, text: str) -> str:
        """
        清理文本，移除危险内容
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理后的文本
        """
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def _contains_malicious_content(self, text: str) -> bool:
        """
        检查是否包含恶意内容
        
        Args:
            text: 文本内容
            
        Returns:
            bool: 是否包含恶意内容
        """
        text_lower = text.lower()
        
        # 检查敏感模式
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern.search(text):
                logger.warning(f"Detected potentially malicious content: {pattern.pattern}")
                return True
        
        # 检查 SQL 注入特征
        sql_keywords = ['select ', 'insert ', 'update ', 'delete ', 'drop ', 'union ']
        for keyword in sql_keywords:
            if keyword in text_lower:
                # 进一步检查是否是恶意意图
                if re.search(rf'\b{keyword}\b.*?from\b', text_lower, re.IGNORECASE):
                    logger.warning(f"Detected potential SQL injection: {keyword}")
                    return True
        
        return False

    def sanitize_for_log(self, text: str) -> str:
        """
        为日志记录清理文本（脱敏）
        
        Args:
            text: 原始文本
            
        Returns:
            str: 脱敏后的文本
        """
        if not text:
            return ""
        
        # 限制日志长度
        if len(text) > 200:
            return text[:200] + "..."
        
        return text