# Phase 3: 成本控制、上下文管理与性能压榨

## 📋 任务概述

基于对现有架构的深入分析，Phase 3 将重点解决三个核心问题：
1. **上下文窗口管理** - 防止 Token 爆炸和上下文溢出
2. **用户画像缓存优化** - 降低数据库压力
3. **Token 计量与限流** - 成本控制和防滥用

---

## 🎯 优先级任务清单

| 优先级 | 任务 | 目的 | 复杂度 | 预计文件修改 |
|--------|------|------|--------|--------------|
| **P0** | 实现 ContextPruner (上下文修剪器) | 防止 Token 爆炸和上下文溢出 | ⭐⭐⭐ | 3-4 个文件 |
| **P1** | UserService 增加 Redis 缓存 | 降低数据库压力，提升响应速度 | ⭐⭐ | 2 个文件 |
| **P1** | Token 计量与限流系统 | 成本控制，防止滥用 | ⭐⭐ | 3 个文件 |
| **P2** | 慢速工具的流式反馈优化 | 提升用户体验 (UX) | ⭐⭐⭐ | 2 个文件 |
| **P3** | Prometheus 监控接入 | 看到 QPS、延迟和错误率 | ⭐ | 2 个文件 |

---

## 🚀 详细实施方案

### P0: ContextPruner (上下文修剪器) - **最紧迫**

#### 问题分析
当前架构在 `_build_user_context()` 中直接查询数据库，但**没有对聊天历史进行修剪**。随着对话变长：
- 每次请求都会加载完整历史记录
- Prompt 无限膨胀 → Token 成本指数增长
- 最终超过 LLM 上下文限制 (128k tokens)

#### 解决方案：实现 ContextPruner 组件

**文件 1: `/Users/a/code/sparkle-flutter/backend/app/orchestration/context_pruner.py`** (新建)
```python
class ContextPruner:
    """
    上下文修剪器 - 管理和优化 LLM 上下文窗口

    策略:
    - Sliding Window: 只保留最近 N 轮对话
    - Summarization: 超过阈值时触发总结
    - Token Counting: 精确计算 token 数量
    """

    def __init__(self, redis_client, max_history_messages: int = 10, summary_threshold: int = 20):
        self.redis = redis_client
        self.max_history_messages = max_history_messages
        self.summary_threshold = summary_threshold

    async def get_pruned_history(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """获取修剪后的聊天历史"""
        # 1. 从 Redis 获取历史
        history = await self._load_chat_history(session_id)

        # 2. 如果历史记录很少，直接返回
        if len(history) <= self.max_history_messages:
            return {"messages": history, "summary": None}

        # 3. 检查是否需要总结
        if len(history) > self.summary_threshold:
            return await self._get_summarized_history(session_id, history, user_id)

        # 4. 使用滑动窗口
        return {"messages": history[-self.max_history_messages:], "summary": None}

    async def _get_summarized_history(self, session_id: str, history: List[Dict], user_id: str) -> Dict[str, Any]:
        """使用 LLM 总结历史对话"""
        # 检查缓存
        cache_key = f"summary:{session_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return {"messages": history[-5:], "summary": cached}

        # 触发异步总结任务
        await self._trigger_summary(session_id, history, user_id)

        # 返回最近几条消息作为 fallback
        return {"messages": history[-5:], "summary": None}

    async def _trigger_summary(self, session_id: str, history: List[Dict], user_id: str):
        """异步触发总结任务"""
        # 将任务推送到队列
        task = {
            "session_id": session_id,
            "history": history[:-5],  # 总结除最近5条外的所有历史
            "user_id": user_id,
            "timestamp": time.time()
        }
        await self.redis.rpush("queue:summarization", json.dumps(task))

    async def _load_chat_history(self, session_id: str) -> List[Dict]:
        """从 Redis 加载聊天历史"""
        cache_key = f"chat:history:{session_id}"
        messages = await self.redis.lrange(cache_key, 0, -1)
        return [json.loads(m) for m in messages]
```

**文件 2: `/Users/a/code/sparkle-flutter/backend/app/orchestration/summarization_worker.py`** (新建)
```python
class SummarizationWorker:
    """后台总结任务处理器"""

    async def process_summarization_queue(self):
        """从队列消费总结任务"""
        while True:
            task_data = await self.redis.blpop("queue:summarization", timeout=0)
            if task_data:
                task = json.loads(task_data[1])
                await self._summarize_history(task)

    async def _summarize_history(self, task: Dict):
        """使用 LLM 生成历史总结"""
        # 构建总结提示词
        prompt = self._build_summary_prompt(task["history"])

        # 调用 LLM
        summary = await llm_service.generate_summary(prompt)

        # 保存到 Redis
        cache_key = f"summary:{task['session_id']}"
        await self.redis.setex(cache_key, 3600, summary)  # 1小时TTL
```

**文件 3: `/Users/a/code/sparkle-flutter/backend/app/orchestration/orchestrator.py`** (修改)
```python
# 在 process_stream 方法中插入 ContextPruner

# Step 5: Build User Context + Prune History
await self._update_state(session_id, STATE_THINKING, "Building user context and pruning history...")
user_context_data = await self._build_user_context(user_id, active_db)

# 新增：获取修剪后的历史
pruned_history = await self.context_pruner.get_pruned_history(session_id, user_id)

# Step 7: Build Prompt (包含历史)
base_system_prompt = build_system_prompt(
    user_context_data,
    conversation_history=pruned_history  # 传递修剪后的历史
)
```

**文件 4: `/Users/a/code/sparkle-flutter/backend/app/orchestration/prompts.py`** (修改)
```python
def build_system_prompt(user_context_data: Dict, conversation_history: Dict = None) -> str:
    """构建系统提示词，包含修剪后的历史"""
    prompt = "..."

    # 添加历史总结
    if conversation_history and conversation_history.get("summary"):
        prompt += f"\n\n## 前情提要\n{conversation_history['summary']}"

    # 添加最近对话
    if conversation_history and conversation_history.get("messages"):
        prompt += "\n\n## 最近对话\n"
        for msg in conversation_history["messages"]:
            role = "用户" if msg["role"] == "user" else "助手"
            prompt += f"{role}: {msg['content']}\n"

    return prompt
```

---

### P1: UserService Redis 缓存 (Cache-Aside 模式)

#### 问题分析
当前 `UserService` 每次调用都直接查询数据库：
- `get_context()` → 查询 User + PushPreference
- `get_analytics_summary()` → 查询 User
- `get_preferences()` → 查询 User + PushPreference

在高并发下，数据库成为瓶颈。

#### 解决方案：Cache-Aside 模式

**文件 1: `/Users/a/code/sparkle-flutter/backend/app/services/user_service.py`** (修改)

```python
from app.core.cache import cache_service

class UserService:
    def __init__(self, db_session: AsyncSession, redis_client=None):
        self.db = db_session
        self.redis = redis_client or cache_service.redis
        logger.info("UserService initialized")

    async def get_context(self, user_id: UUID) -> Optional[UserContext]:
        """获取用户上下文（带缓存）"""
        cache_key = f"user:context:{user_id}"

        # 1. Cache Lookup
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return pickle.loads(cached)

        # 2. Database Query
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        push_pref = await self._get_push_preference(user_id)

        # 3. Build Context
        context = UserContext(
            user_id=str(user_id),
            nickname=user.nickname or user.username,
            timezone=push_pref.timezone if push_pref else "Asia/Shanghai",
            language="zh-CN",
            is_pro=user.flame_level >= 3,
            preferences={
                "depth_preference": user.depth_preference,
                "curiosity_preference": user.curiosity_preference,
                "flame_level": user.flame_level,
                "flame_brightness": user.flame_brightness,
            },
            active_slots=push_pref.active_slots if push_pref else None,
            daily_cap=push_pref.daily_cap if push_pref else 5,
            persona_type=push_pref.persona_type if push_pref else "coach",
        )

        # 4. Cache Write (TTL 30 minutes)
        if self.redis:
            await self.redis.setex(cache_key, 1800, pickle.dumps(context))

        return context

    async def get_analytics_summary(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """获取用户分析摘要（带缓存）"""
        cache_key = f"user:analytics:{user_id}"

        # 1. Cache Lookup
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # 2. Database Query
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        # 3. Build Summary
        is_active = user.last_login_at is not None
        flame_level = user.flame_level

        if flame_level >= 5:
            engagement = "very_high"
        elif flame_level >= 3:
            engagement = "high"
        elif flame_level >= 2:
            engagement = "medium"
        else:
            engagement = "low"

        summary = {
            "is_active": is_active,
            "active_level": "active" if is_active else "inactive",
            "engagement_level": engagement,
            "flame_level": flame_level,
            "flame_brightness": user.flame_brightness,
            "depth_preference": user.depth_preference,
            "curiosity_preference": user.curiosity_preference,
            "registration_source": user.registration_source,
        }

        # 4. Cache Write (TTL 30 minutes)
        if self.redis:
            await self.redis.setex(cache_key, 1800, json.dumps(summary))

        return summary

    async def invalidate_user_cache(self, user_id: UUID):
        """使用户缓存失效（在用户更新资料时调用）"""
        if not self.redis:
            return

        keys = [
            f"user:context:{user_id}",
            f"user:analytics:{user_id}",
            f"user:preferences:{user_id}",
            f"user:stats:{user_id}",
        ]

        await self.redis.delete(*keys)
        logger.info(f"Invalidated cache for user {user_id}")

    async def update_user_profile(self, user_id: UUID, updates: Dict) -> bool:
        """更新用户资料并使缓存失效"""
        try:
            # 1. 更新数据库
            user = await self.get_user_by_id(user_id)
            if not user:
                return False

            for key, value in updates.items():
                setattr(user, key, value)

            await self.db.commit()

            # 2. 使缓存失效
            await self.invalidate_user_cache(user_id)

            return True
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            await self.db.rollback()
            return False
```

**文件 2: `/Users/a/code/sparkle-flutter/backend/app/orchestration/orchestrator.py`** (修改)
```python
# 在 _build_user_context 方法中传递 redis_client

async def _build_user_context(self, user_id: str, db_session: AsyncSession) -> Dict[str, Any]:
    try:
        # 传递 redis_client 给 UserService
        user_service = UserService(db_session, self.redis)

        user_context = await user_service.get_context(uuid.UUID(user_id))
        analytics = await user_service.get_analytics_summary(uuid.UUID(user_id))

        # ... rest of the code
```

---

### P1: Token 计量与限流系统

#### 问题分析
当前系统：
- ✅ Go Gateway 有 Quota 扣减机制
- ✅ ChatMessage 模型有 `tokens_used` 字段
- ❌ Python 层没有追踪 Token 使用量
- ❌ 没有实时配额检查
- ❌ 没有详细的 Token 使用记录

#### 解决方案：完整 Token 追踪 + 配额检查

**文件 1: `/Users/a/code/sparkle-flutter/backend/app/orchestration/token_tracker.py`** (新建)
```python
class TokenTracker:
    """Token 使用量追踪器"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def record_usage(
        self,
        user_id: str,
        session_id: str,
        request_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4"
    ):
        """记录 Token 使用量"""
        total_tokens = prompt_tokens + completion_tokens

        # 1. 记录到 Redis 队列（异步持久化）
        usage_record = {
            "user_id": user_id,
            "session_id": session_id,
            "request_id": request_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model": model,
            "timestamp": time.time()
        }

        await self.redis.rpush("queue:billing", json.dumps(usage_record))

        # 2. 更新用户当日累计
        today = datetime.now().strftime("%Y-%m-%d")
        daily_key = f"user:daily_tokens:{user_id}:{today}"
        await self.redis.incrby(daily_key, total_tokens)
        await self.redis.expire(daily_key, 86400)  # 24小时过期

        # 3. 更新会话累计
        session_key = f"session:tokens:{session_id}"
        await self.redis.incrby(session_key, total_tokens)

        return total_tokens

    async def get_daily_usage(self, user_id: str) -> int:
        """获取用户今日 Token 使用量"""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"user:daily_tokens:{user_id}:{today}"
        result = await self.redis.get(key)
        return int(result) if result else 0

    async def check_quota(self, user_id: str, daily_limit: int = 100000) -> bool:
        """检查用户是否超出配额"""
        used = await self.get_daily_usage(user_id)
        return used < daily_limit

    async def get_usage_breakdown(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """获取用户 Token 使用明细"""
        breakdown = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            key = f"user:daily_tokens:{user_id}:{date}"
            usage = await self.redis.get(key)
            breakdown[date] = int(usage) if usage else 0

        return breakdown
```

**文件 2: `/Users/a/code/sparkle-flutter/backend/app/orchestration/validator.py`** (修改)
```python
class RequestValidator:
    """请求验证器（增强版）"""

    def __init__(self, redis_client=None):
        self.redis = redis_client

    async def validate_chat_request(self, request, user_id: str) -> ValidationResult:
        """验证聊天请求"""
        # 现有验证...

        # 新增：配额检查
        if self.redis:
            token_tracker = TokenTracker(self.redis)
            quota_ok = await token_tracker.check_quota(user_id)

            if not quota_ok:
                return ValidationResult(
                    is_valid=False,
                    error_message="Daily token quota exceeded. Please try again tomorrow."
                )

        return ValidationResult(is_valid=True)
```

**文件 3: `/Users/a/code/sparkle-flutter/backend/app/orchestration/orchestrator.py`** (修改)
```python
# 在 process_stream 中集成 Token 追踪

class ChatOrchestrator:
    def __init__(self, db_session, redis_client):
        # ... existing init
        self.token_tracker = TokenTracker(redis_client) if redis_client else None

    async def process_stream(self, request, db_session, context_data):
        # ... existing code

        full_response = ""
        tool_execution_results = []
        total_prompt_tokens = 0
        total_completion_tokens = 0

        # Call LLM Service
        async for chunk in llm_service.chat_stream_with_tools(...):
            if chunk.type == "text":
                full_response += chunk.content
                yield agent_service_pb2.ChatResponse(...)

            # 新增：追踪 Token 使用
            elif chunk.type == "usage":
                total_prompt_tokens += chunk.prompt_tokens
                total_completion_tokens += chunk.completion_tokens

                # 发送 Token 使用统计给客户端
                yield agent_service_pb2.ChatResponse(
                    response_id=f"resp_{uuid.uuid4()}",
                    created_at=int(datetime.now().timestamp()),
                    request_id=request_id,
                    usage=agent_service_pb2.Usage(
                        prompt_tokens=chunk.prompt_tokens,
                        completion_tokens=chunk.completion_tokens,
                        total_tokens=chunk.prompt_tokens + chunk.completion_tokens
                    )
                )

        # 最终：记录总 Token 使用量
        if self.token_tracker:
            await self.token_tracker.record_usage(
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens
            )
```

**文件 4: `/Users/a/code/sparkle-flutter/backend/app/services/billing_worker.py`** (新建)
```python
class BillingWorker:
    """异步计费任务处理器"""

    async def process_billing_queue(self):
        """从队列消费计费记录并持久化到数据库"""
        while True:
            record_data = await self.redis.blpop("queue:billing", timeout=0)
            if record_data:
                record = json.loads(record_data[1])
                await self._persist_to_db(record)

    async def _persist_to_db(self, record: Dict):
        """持久化到数据库"""
        # 使用 SQLAlchemy 插入 TokenUsage 记录
        # 可以聚合多条记录减少数据库写入
        pass
```

---

### P2: 慢速工具的流式反馈优化

#### 问题分析
当前工具执行是同步的：
- 如果工具执行需要 30 秒，WebSocket 连接可能超时
- 用户看不到进度，体验差

#### 解决方案：心跳机制 + 进度更新

**文件 1: `/Users/a/code/sparkle-flutter/backend/app/orchestration/executor.py`** (修改)
```python
class ToolExecutor:
    """增强版工具执行器"""

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict,
        user_id: str,
        db_session,
        progress_callback: Optional[Callable] = None
    ) -> ToolResult:
        """执行工具调用，支持进度回调"""
        tool = tool_registry.get_tool(tool_name)
        validated_params = tool.parameters_schema(**arguments)

        # 如果是长时间任务，启动进度报告
        if tool.is_long_running:
            # 启动后台任务
            task_id = str(uuid.uuid4())
            asyncio.create_task(
                self._execute_long_running_tool(
                    tool, validated_params, user_id, db_session,
                    task_id, progress_callback
                )
            )

            # 立即返回任务 ID
            return ToolResult(
                success=True,
                tool_name=tool_name,
                data={"task_id": task_id, "status": "started"},
                is_async=True
            )
        else:
            # 短任务直接执行
            result = await tool.execute(validated_params, user_id, db_session)
            return result

    async def _execute_long_running_tool(
        self, tool, params, user_id, db_session,
        task_id, progress_callback
    ):
        """执行长时间运行的工具"""
        try:
            # 每隔 5 秒发送一次进度更新
            for i in range(1, 6):  # 模拟进度
                if progress_callback:
                    await progress_callback(
                        task_id=task_id,
                        progress=i * 20,
                        message=f"Processing step {i}/5..."
                    )
                await asyncio.sleep(1)  # 模拟工作

            # 执行实际工具
            result = await tool.execute(params, user_id, db_session)

            # 发送完成通知
            if progress_callback:
                await progress_callback(
                    task_id=task_id,
                    progress=100,
                    message="Completed",
                    result=result
                )

        except Exception as e:
            if progress_callback:
                await progress_callback(
                    task_id=task_id,
                    progress=0,
                    message=f"Failed: {str(e)}",
                    error=True
                )
```

**文件 2: `/Users/a/code/sparkle-flutter/backend/app/orchestration/orchestrator.py`** (修改)
```python
# 在 process_stream 中处理异步工具

async def process_stream(self, request, db_session, context_data):
    # ... existing code

    # Step 8: LLM Generation with Dynamic Tools
    async for chunk in llm_service.chat_stream_with_tools(...):
        if chunk.type == "text":
            # ... existing

        elif chunk.type == "tool_call_end":
            # 执行工具
            tool_result = await self.tool_executor.execute_tool_call(
                tool_name=chunk.tool_name,
                arguments=chunk.full_arguments,
                user_id=user_id,
                db_session=active_db,
                progress_callback=self._send_progress_update  # 传递回调
            )

            if tool_result.is_async:
                # 异步工具：发送任务 ID，结束当前流
                yield agent_service_pb2.ChatResponse(
                    response_id=f"resp_{uuid.uuid4()}",
                    request_id=request_id,
                    status_update=agent_service_pb2.AgentStatus(
                        state=agent_service_pb2.AgentStatus.ASYNC_TOOL,
                        details=f"Long-running task started: {tool_result.data['task_id']}"
                    ),
                    tool_call=agent_service_pb2.ToolCall(
                        id=chunk.tool_call_id,
                        name=tool_name,
                        arguments=json.dumps(chunk.full_arguments),
                        task_id=tool_result.data["task_id"]
                    )
                )
                return  # 结束流，等待客户端轮询或 WebSocket 推送

            else:
                # 同步工具：继续流
                tool_execution_results.append(tool_result)
                yield agent_service_pb2.ChatResponse(...)

    # ... rest of code

async def _send_progress_update(self, task_id: str, progress: int, message: str, **kwargs):
    """发送进度更新到 WebSocket"""
    # 这个方法需要访问 WebSocket 连接
    # 可能需要通过状态管理器或事件总线来实现
    update = {
        "type": "tool_progress",
        "task_id": task_id,
        "progress": progress,
        "message": message,
        **kwargs
    }
    # 推送到 Redis 队列，由 WebSocket handler 消费
    await self.redis.rpush(f"ws:updates:{task_id}", json.dumps(update))
```

---

### P3: Prometheus 监控接入

#### 解决方案：基础监控指标

**文件 1: `/Users/a/code/sparkle-flutter/backend/app/core/metrics.py`** (新建)
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry

# 创建注册表
registry = CollectorRegistry()

# 定义指标
REQUEST_COUNT = Counter(
    'chat_requests_total',
    'Total number of chat requests',
    ['method', 'status'],
    registry=registry
)

REQUEST_DURATION = Histogram(
    'chat_request_duration_seconds',
    'Request duration in seconds',
    ['method'],
    registry=registry
)

ACTIVE_SESSIONS = Gauge(
    'active_sessions',
    'Number of active sessions',
    registry=registry
)

TOKEN_USAGE = Counter(
    'tokens_consumed_total',
    'Total tokens consumed',
    ['model', 'type'],  # type: prompt/completion
    registry=registry
)

TOOL_EXECUTION_COUNT = Counter(
    'tool_executions_total',
    'Total tool executions',
    ['tool_name', 'status'],
    registry=registry
)

DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    registry=registry
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Cache hits and misses',
    ['cache_type', 'hit'],  # hit: true/false
    registry=registry
)
```

**文件 2: `/Users/a/code/sparkle-flutter/backend/app/orchestration/orchestrator.py`** (修改)
```python
from app.core.metrics import REQUEST_COUNT, REQUEST_DURATION, TOKEN_USAGE

class ChatOrchestrator:
    async def process_stream(self, request, db_session, context_data):
        timer = REQUEST_DURATION.labels(method="chat").time()

        with timer():
            try:
                REQUEST_COUNT.labels(method="chat", status="started").inc()

                # ... existing code

                # Track token usage
                if total_completion_tokens > 0:
                    TOKEN_USAGE.labels(model="gpt-4", type="prompt").inc(total_prompt_tokens)
                    TOKEN_USAGE.labels(model="gpt-4", type="completion").inc(total_completion_tokens)

                REQUEST_COUNT.labels(method="chat", status="success").inc()

            except Exception:
                REQUEST_COUNT.labels(method="chat", status="error").inc()
                raise
```

**文件 3: `/Users/a/code/sparkle-flutter/backend/gateway/internal/handler/metrics.go`** (新建)
```go
package handler

import (
    "github.com/gin-gonic/gin"
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

func MetricsHandler() gin.HandlerFunc {
    h := promhttp.Handler()
    return func(c *gin.Context) {
        h.ServeHTTP(c.Writer, c.Request)
    }
}
```

---

## 📊 实施顺序建议

### Day 1: P0 - ContextPruner
1. 创建 `context_pruner.py`
2. 创建 `summarization_worker.py`
3. 修改 `orchestrator.py` 集成 ContextPruner
4. 修改 `prompts.py` 支持历史总结

### Day 2: P1 - UserService 缓存
1. 修改 `user_service.py` 添加 Cache-Aside
2. 修改 `orchestrator.py` 传递 redis_client
3. 测试缓存命中率

### Day 3: P1 - Token 计量
1. 创建 `token_tracker.py`
2. 修改 `validator.py` 添加配额检查
3. 修改 `orchestrator.py` 集成 Token 追踪
4. 创建 `billing_worker.py`

### Day 4: P2 - 慢速工具优化
1. 修改 `executor.py` 添加进度回调
2. 修改 `orchestrator.py` 处理异步工具

### Day 5: P3 - 监控接入
1. 创建 `metrics.py`
2. 在关键位置埋点
3. 配置 Prometheus + Grafana

---

## 🔍 关键文件路径总结

| 模块 | 文件路径 | 操作类型 |
|------|----------|----------|
| ContextPruner | `backend/app/orchestration/context_pruner.py` | 新建 |
| Summarization Worker | `backend/app/orchestration/summarization_worker.py` | 新建 |
| Token Tracker | `backend/app/orchestration/token_tracker.py` | 新建 |
| Billing Worker | `backend/app/services/billing_worker.py` | 新建 |
| Metrics | `backend/app/core/metrics.py` | 新建 |
| Orchestrator | `backend/app/orchestration/orchestrator.py` | 修改 |
| UserService | `backend/app/services/user_service.py` | 修改 |
| Validator | `backend/app/orchestration/validator.py` | 修改 |
| Executor | `backend/app/orchestration/executor.py` | 修改 |
| Prompts | `backend/app/orchestration/prompts.py` | 修改 |
| Gateway Metrics | `backend/gateway/internal/handler/metrics.go` | 新建 |

---

## ✅ 验收标准

### ContextPruner
- [ ] 历史消息超过 10 条时自动截断
- [ ] 超过 20 条时触发异步总结
- [ ] 总结结果缓存 1 小时
- [ ] Token 使用量减少 50%+

### UserService 缓存
- [ ] 缓存命中率 > 80%
- [ ] 数据库查询减少 70%+
- [ ] 用户资料更新后缓存自动失效
- [ ] 响应时间 < 50ms (缓存命中)

### Token 计量
- [ ] 每次请求记录 Token 使用量
- [ ] 配额超限自动拦截
- [ ] 支持每日/每月配额查询
- [ ] 计费数据异步持久化

### 慢速工具优化
- [ ] 长任务每 5 秒发送进度更新
- [ ] WebSocket 不超时断开
- [ ] 用户能看到实时进度

### 监控
- [ ] Prometheus 暴露 /metrics 端点
- [ ] Grafana 仪表盘显示 QPS、延迟、错误率
- [ ] Token 使用量可视化
- [ ] 缓存命中率监控

---

## 💡 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 总结任务积压 | Redis 内存溢出 | 限制队列长度，添加熔断器 |
| 缓存一致性问题 | 数据不一致 | 更新时立即失效，TTL 作为兜底 |
| Token 追踪丢失 | 计费错误 | 双写 Redis + DB，失败重试 |
| WebSocket 超时 | 用户体验差 | 心跳机制，进度更新 |
| 监控性能开销 | 影响主流程 | 使用直方图，采样率控制 |

---

**开始实施前，请确认：**
1. Redis 集群是否已部署并可用？
2. 是否需要为总结任务准备单独的 LLM 实例？
3. Token 配额的默认值是多少？(建议：免费用户 50k/日，Pro 用户 500k/日)
4. Prometheus + Grafana 是否已部署？
