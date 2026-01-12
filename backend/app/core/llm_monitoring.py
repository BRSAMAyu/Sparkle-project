"""
LLM 监控与告警模块

功能:
1. Prometheus 指标收集
2. 安全事件追踪
3. 性能监控 (延迟、吞吐量)
4. 成本监控 (Token 使用、费用)
5. 告警规则定义

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import time
import logging
from typing import Optional, Dict, Any
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    start_http_server
)

logger = logging.getLogger(__name__)


# =============================================================================
# Prometheus 指标定义
# =============================================================================

# LLM 调用统计
LLM_CALLS_TOTAL = Counter(
    'llm_calls_total',
    'Total number of LLM calls',
    ['model', 'status', 'endpoint']  # success, error, timeout, blocked
)

LLM_TOKENS_TOTAL = Counter(
    'llm_tokens_total',
    'Total tokens consumed',
    ['model', 'token_type', 'source']  # input/output, chat/embedding/etc
)

LLM_LATENCY_SECONDS = Histogram(
    'llm_latency_seconds',
    'LLM call latency',
    ['model', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# 安全监控
SECURITY_EVENTS_TOTAL = Counter(
    'llm_security_events_total',
    'Total security events',
    ['event_type', 'severity']  # injection_attempt, quota_exceeded, sensitive_leak, xss
)

QUOTA_USAGE = Gauge(
    'llm_quota_usage',
    'Current quota usage per user',
    ['user_id']
)

QUOTA_LIMIT = Gauge(
    'llm_quota_limit',
    'Quota limit per user',
    ['user_id']
)

# 成本监控
ESTIMATED_COST_USD = Counter(
    'llm_estimated_cost_usd',
    'Estimated cost in USD',
    ['model', 'endpoint']
)

# 系统健康
ACTIVE_TASKS = Gauge(
    'llm_active_tasks',
    'Number of active LLM tasks'
)

TASK_FAILURES = Counter(
    'llm_task_failures_total',
    'Total task failures',
    ['task_type', 'error_type']
)

# 服务信息
LLM_SERVICE_INFO = Info('llm_service', 'LLM service configuration')


class LLMMonitor:
    """
    LLM 监控器 - 统一的监控和告警管理

    提供:
    - 自动指标收集装饰器
    - 安全事件记录
    - 性能追踪
    - 成本估算
    """

    def __init__(self, service_name: str = "sparkle-llm"):
        """
        初始化监控器

        Args:
            service_name: 服务名称
        """
        self.service_name = service_name
        self._setup_service_info()

        logger.info(f"LLMMonitor initialized for {service_name}")

    def _setup_service_info(self):
        """设置服务信息"""
        LLM_SERVICE_INFO.info({
            'service': self.service_name,
            'version': '1.0.0',
            'security_layer': 'enabled',
            'quota_enabled': 'true'
        })

    # =============================================================================
    # 装饰器 - 自动监控
    # =============================================================================

    @staticmethod
    def monitor_llm_call(model: str, endpoint: str = "chat"):
        """
        装饰器: 自动监控 LLM 调用

        使用示例:
            @LLMMonitor.monitor_llm_call(model="gpt-4", endpoint="chat")
            async def my_llm_function(messages):
                # 自动记录调用次数、延迟、状态
                return await llm_service.chat(messages)
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                status = "error"

                try:
                    result = await func(*args, **kwargs)
                    status = "success"
                    return result

                except Exception as e:
                    error_type = type(e).__name__
                    if "timeout" in str(e).lower():
                        status = "timeout"
                    elif "quota" in str(e).lower():
                        status = "blocked"
                    elif "rate" in str(e).lower():
                        status = "blocked"

                    # 记录任务失败
                    TASK_FAILURES.labels(
                        task_type="llm_call",
                        error_type=error_type
                    ).inc()

                    raise

                finally:
                    # 记录调用次数
                    LLM_CALLS_TOTAL.labels(
                        model=model,
                        status=status,
                        endpoint=endpoint
                    ).inc()

                    # 记录延迟
                    latency = time.time() - start_time
                    LLM_LATENCY_SECONDS.labels(
                        model=model,
                        endpoint=endpoint
                    ).observe(latency)

                    # 记录活跃任务
                    ACTIVE_TASKS.inc()
                    # 减少活跃任务 (延迟1ms后)
                    import asyncio
                    asyncio.create_task(self._decrement_active_tasks())

            return wrapper
        return decorator

    @staticmethod
    def monitor_token_usage(model: str, source: str = "chat"):
        """
        装饰器: 自动监控 Token 使用

        使用示例:
            @LLMMonitor.monitor_token_usage(model="gpt-4", source="chat")
            async def my_llm_function(messages):
                result = await llm_service.chat(messages)
                # 需要在函数内部调用 record_tokens()
                return result
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)

                # 假设函数返回包含 token 使用信息
                if isinstance(result, dict):
                    input_tokens = result.get('input_tokens', 0)
                    output_tokens = result.get('output_tokens', 0)

                    LLM_TOKENS_TOTAL.labels(
                        model=model,
                        token_type='input',
                        source=source
                    ).inc(input_tokens)

                    LLM_TOKENS_TOTAL.labels(
                        model=model,
                        token_type='output',
                        source=source
                    ).inc(output_tokens)

                    # 估算成本 (假设 GPT-4: $0.03/1K input, $0.06/1K output)
                    cost = (input_tokens / 1000 * 0.03) + (output_tokens / 1000 * 0.06)
                    ESTIMATED_COST_USD.labels(
                        model=model,
                        endpoint=source
                    ).inc(cost)

                return result

            return wrapper
        return decorator

    # =============================================================================
    # 安全事件记录
    # =============================================================================

    @staticmethod
    def record_security_event(
        event_type: str,
        severity: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        记录安全事件

        Args:
            event_type: 事件类型 (injection_attempt, quota_exceeded, sensitive_leak, xss)
            severity: 严重程度 (low, medium, high, critical)
            details: 详细信息
        """
        SECURITY_EVENTS_TOTAL.labels(
            event_type=event_type,
            severity=severity
        ).inc()

        log_msg = f"Security Event [{severity.upper()}] {event_type}"
        if details:
            log_msg += f" - {details}"

        if severity in ['high', 'critical']:
            logger.error(log_msg)
        else:
            logger.warning(log_msg)

    @staticmethod
    def record_injection_attempt(
        user_id: str,
        pattern: str,
        risk_score: float,
        details: Optional[str] = None
    ):
        """记录提示注入攻击尝试"""
        LLMMonitor.record_security_event(
            event_type='injection_attempt',
            severity='high' if risk_score > 0.7 else 'medium',
            details={
                'user_id': user_id,
                'pattern': pattern,
                'risk_score': risk_score,
                'details': details
            }
        )

    @staticmethod
    def record_quota_exceeded(
        user_id: str,
        usage: int,
        limit: int
    ):
        """记录配额超限"""
        LLMMonitor.record_security_event(
            event_type='quota_exceeded',
            severity='medium',
            details={
                'user_id': user_id,
                'usage': usage,
                'limit': limit,
                'percentage': round(usage / limit * 100, 2)
            }
        )

    @staticmethod
    def record_sensitive_leak(
        user_id: str,
        violation: str,
        severity: str = 'high'
    ):
        """记录敏感信息泄露"""
        LLMMonitor.record_security_event(
            event_type='sensitive_leak',
            severity=severity,
            details={
                'user_id': user_id,
                'violation': violation
            }
        )

    @staticmethod
    def record_xss_attempt(
        user_id: str,
        pattern: str
    ):
        """记录 XSS 攻击尝试"""
        LLMMonitor.record_security_event(
            event_type='xss',
            severity='critical',
            details={
                'user_id': user_id,
                'pattern': pattern
            }
        )

    # =============================================================================
    # 配额监控
    # =============================================================================

    @staticmethod
    def update_quota_metrics(user_id: str, current: int, limit: int):
        """
        更新配额指标

        Args:
            user_id: 用户ID
            current: 当前使用量
            limit: 配额限制
        """
        QUOTA_USAGE.labels(user_id=user_id).set(current)
        QUOTA_LIMIT.labels(user_id=user_id).set(limit)

    # =============================================================================
    # 性能指标
    # =============================================================================

    @staticmethod
    def record_performance_metric(
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        记录自定义性能指标

        Args:
            metric_name: 指标名称
            value: 指标值
            labels: 标签
        """
        # 这里可以扩展为自定义指标
        logger.debug(f"Performance metric: {metric_name} = {value} (labels: {labels})")

    # =============================================================================
    # 成本估算
    # =============================================================================

    @staticmethod
    def estimate_and_record_cost(
        model: str,
        input_tokens: int,
        output_tokens: int,
        endpoint: str = "chat"
    ) -> float:
        """
        估算并记录成本

        Args:
            model: 模型名称
            input_tokens: 输入 Token
            output_tokens: 输出 Token
            endpoint: 端点

        Returns:
            float: 估算成本 (USD)
        """
        # 定价表 (基于 OpenAI 2024 定价)
        pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002},
            'text-embedding-ada-002': {'input': 0.0001, 'output': 0.0},  # Embedding
        }

        # 默认定价
        default_input = 0.03
        default_output = 0.06

        input_price = pricing.get(model, {}).get('input', default_input)
        output_price = pricing.get(model, {}).get('output', default_output)

        cost = (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)

        # 记录到 Prometheus
        ESTIMATED_COST_USD.labels(
            model=model,
            endpoint=endpoint
        ).inc(cost)

        return cost

    # =============================================================================
    # 健康检查
    # =============================================================================

    @staticmethod
    def get_health_status() -> Dict[str, Any]:
        """
        获取当前健康状态

        Returns:
            Dict: 健康状态信息
        """
        # 这里可以从 Prometheus 或其他监控系统获取实时数据
        return {
            'service': 'llm-monitor',
            'status': 'healthy',
            'timestamp': time.time(),
            'metrics': {
                'active_tasks': ACTIVE_TASKS._value.get() if ACTIVE_TASKS._value else 0,
                'total_calls': LLM_CALLS_TOTAL._value.get() if LLM_CALLS_TOTAL._value else 0,
                'security_events': SECURITY_EVENTS_TOTAL._value.get() if SECURITY_EVENTS_TOTAL._value else 0,
            }
        }

    # =============================================================================
    # 内部方法
    # =============================================================================

    @staticmethod
    async def _decrement_active_tasks():
        """减少活跃任务计数"""
        await asyncio.sleep(0.001)  # 微小延迟
        ACTIVE_TASKS.dec()


# =============================================================================
# 启动监控服务器
# =============================================================================

def start_monitoring_server(port: int = 8000, host: str = '0.0.0.0'):
    """
    启动 Prometheus 指标服务器

    Args:
        port: 端口号
        host: 主机地址
    """
    try:
        start_http_server(port, addr=host)
        logger.info(f"Prometheus metrics server started on {host}:{port}")
        logger.info(f"Metrics available at: http://{host}:{port}/metrics")
        return True
    except Exception as e:
        logger.error(f"Failed to start monitoring server: {e}")
        return False


# =============================================================================
# 告警规则配置 (Prometheus)
# =============================================================================

ALERT_RULES = """
# Prometheus 告警规则配置

groups:
  - name: llm_security
    interval: 30s
    rules:
      # 高频提示注入攻击
      - alert: HighInjectionAttempts
        expr: rate(llm_security_events_total{event_type="injection_attempt"}[5m]) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "检测到高频提示注入攻击"
          description: "过去5分钟内检测到 {{ $value }} 次注入尝试"

      # 配额滥用
      - alert: LLMQuotaAbuse
        expr: rate(llm_calls_total{status="blocked"}[5m]) > 50
        for: 2m
        labels:
          severity: high
        annotations:
          summary: "大量配额超限请求"
          description: "每分钟 {{ $value }} 个请求被配额限制"

      # 成本异常
      - alert: CostSpike
        expr: rate(llm_estimated_cost_usd[5m]) > 10
        for: 5m
        labels:
          severity: high
        annotations:
          summary: "LLM 成本异常升高"
          description: "每分钟成本 ${{ $value }}"

      # 敏感信息泄露
      - alert: SensitiveDataLeak
        expr: increase(llm_security_events_total{event_type="sensitive_leak"}[10m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "检测到敏感信息泄露"
          description: "请立即检查相关用户和会话"

  - name: llm_performance
    interval: 30s
    rules:
      # 高延迟
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m])) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "LLM 调用延迟过高"
          description: "95分位延迟 {{ $value }}s"

      # 服务错误率
      - alert: HighErrorRate
        expr: rate(llm_calls_total{status="error"}[5m]) / rate(llm_calls_total[5m]) > 0.1
        for: 5m
        labels:
          severity: high
        annotations:
          summary: "LLM 服务错误率过高"
          description: "错误率 {{ $value | humanizePercentage }}"

  - name: llm_quota
    interval: 30s
    rules:
      # 用户配额即将耗尽
      - alert: QuotaWarning
        expr: llm_quota_usage / llm_quota_limit > 0.8
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "用户配额即将耗尽"
          description: "用户 {{ $labels.user_id }} 已使用 {{ $value | humanizePercentage }}"
"""


# =============================================================================
# 使用示例
# =============================================================================

if __name__ == "__main__":
    import asyncio

    # 启动监控服务器
    start_monitoring_server(port=8000)

    # 创建监控器实例
    monitor = LLMMonitor(service_name="sparkle-test")

    # 模拟 LLM 调用
    @LLMMonitor.monitor_llm_call(model="gpt-4", endpoint="chat")
    async def mock_llm_call(messages):
        await asyncio.sleep(0.1)  # 模拟延迟
        return {
            'input_tokens': 150,
            'output_tokens': 200,
            'response': "Mock response"
        }

    @LLMMonitor.monitor_token_usage(model="gpt-4", source="chat")
    async def mock_llm_with_tokens():
        await asyncio.sleep(0.1)
        return {
            'input_tokens': 150,
            'output_tokens': 200
        }

    async def demo():
        print("=== LLM 监控演示 ===\n")

        # 1. 记录安全事件
        print("1. 记录安全事件:")
        monitor.record_injection_attempt(
            user_id="user_123",
            pattern="ignore previous instructions",
            risk_score=0.85
        )
        monitor.record_quota_exceeded(
            user_id="user_456",
            usage=110000,
            limit=100000
        )
        monitor.record_sensitive_leak(
            user_id="user_789",
            violation="API Key detected"
        )

        # 2. 监控 LLM 调用
        print("\n2. 监控 LLM 调用:")
        result = await mock_llm_call([{"role": "user", "content": "test"}])
        print(f"   Result: {result}")

        # 3. 监控 Token 使用
        print("\n3. 监控 Token 使用:")
        tokens = await mock_llm_with_tokens()
        cost = monitor.estimate_and_record_cost(
            model="gpt-4",
            input_tokens=tokens['input_tokens'],
            output_tokens=tokens['output_tokens']
        )
        print(f"   Tokens: {tokens}")
        print(f"   Estimated cost: ${cost:.4f}")

        # 4. 更新配额指标
        print("\n4. 更新配额指标:")
        monitor.update_quota_metrics("user_123", 85000, 100000)
        monitor.update_quota_metrics("user_456", 110000, 100000)

        # 5. 获取健康状态
        print("\n5. 健康状态:")
        health = monitor.get_health_status()
        print(f"   {health}")

        print("\n=== 演示完成 ===")
        print("\n访问 http://localhost:8000/metrics 查看 Prometheus 指标")

    asyncio.run(demo())
