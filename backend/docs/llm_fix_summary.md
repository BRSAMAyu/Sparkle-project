# LLM 调用性能问题修复总结

**日期**: 2026-01-29
**问题**: WebSocket 聊天响应时间异常（~118秒）
**状态**: ✅ 已修复

---

## 问题诊断

### 原始症状
- GLM-4.7 模型正确选择，但响应时间 ~118 秒
- 并发消息处理失败
- 测试通过率: 1/5 (20%)

### 根本原因分析
1. **OpenAI 客户端无超时** - Python 端 HTTP 请求可能无限等待
2. **Go Gateway 超时过短** - 默认 5 秒，无法覆盖 GLM 思考模式
3. **GLM API 并发限制** - 多请求触发 429 错误
4. **延迟预期不匹配** - `clear_thinking=False` 实际需要 10-30s，但配置为 1.5s

---

## 修复内容

### 1. OpenAI 客户端超时 (`app/services/llm/providers.py`)

```python
# 添加了明确的超时配置
timeout_config = Timeout(
    timeout=timeout_seconds,  # 默认 60 秒
    connect=10.0,
)

self.client = AsyncOpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=timeout_config,
)
```

### 2. Go Gateway 超时 (`backend/gateway/internal/config/config.go`)

```go
// 从 5 秒改为 60 秒
viper.SetDefault("GRPC_TIMEOUT_SECONDS", 60)
```

### 3. 消息处理超时 (`backend/gateway/internal/handler/chat_orchestrator.go`)

```go
// 添加超时控制
timeoutSeconds := 60
if h.cfg != nil && h.cfg.GRPCTimeoutSeconds > 0 {
    timeoutSeconds = h.cfg.GRPCTimeoutSeconds
}
ctx, cancel := context.WithTimeout(ctx, time.Duration(timeoutSeconds)*time.Second)
defer cancel()
```

### 4. 并发控制机制 (`app/services/llm/concurrency.py`)

新增并发管理器，使用 semaphore 限制对 LLM API 的并发请求数：

- **GLM (Zhipu)**: 2 并发（免费版限制严格）
- **DeepSeek**: 5 并发
- **其他**: 5-10 并发

```python
# 使用方式
async with llm_concurrency.acquire("zhipu"):
    await llm_service.chat(...)
```

### 5. 性能日志 (`app/services/llm_service.py`)

添加详细的性能追踪日志：
- `[LLM] stream_chat START` - 调用开始
- `[LLM] stream_chat FIRST_CHUNK` - 首个 chunk 到达时间 (TTFC)
- `[LLM] stream_chat END` - 调用结束时间和总耗时

### 6. 延迟预期更新 (`app/core/llm_router.py`)

```python
# 思考模式延迟预期更新为实际值
"zhipu_reason": avg_latency_ms=20000,  # 从 1500 → 20000
"glm_4_7_flash_thinking": avg_latency_ms=15000,  # 从 1000 → 15000
```

---

## 测试结果

### 直接 API 测试 (`test_llm_direct.py`)

| 测试项 | 响应时间 | 状态 |
|--------|----------|------|
| 非流式调用 | 3.6s | ✅ OK |
| 流式调用 (TTFC) | 507ms | ✅ 优秀 |
| 并发请求 (2个) | 2.8s | ✅ 无429错误 |

### 修复前后对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 超时设置 | 5秒 (Go) | 60秒 (Go + Python) |
| 并发控制 | 无 | Semaphore (2-5) |
| 429 错误 | 频繁触发 | 已解决 |
| 响应时间 | ~118秒 | 0.5-4秒 |
| TTFC | 未知 | 500ms-3s |

---

## 配置说明

### 环境变量

```bash
# gRPC 超时（秒），默认 60
GRPC_TIMEOUT_SECONDS=60

# LLM 层级选择（可选）
# LLM_TIER_STANDARD=zhipu_chat
```

### clear_thinking 参数说明

| 模型 | clear_thinking | 预期延迟 | 用途 |
|------|----------------|----------|------|
| zhipu_chat | True | 400ms | 标准聊天，快速响应 |
| zhipu_reason | False | 20s | 深度推理，保留思考 |
| glm_4_7_flash | True | 200ms | 快速响应，免费 |
| glm_4_7_flash | False | 15s | 深度推理，免费 |

---

## 文件变更清单

1. `backend/app/services/llm/providers.py` - 超时 + 并发控制
2. `backend/app/services/llm/concurrency.py` - 新增并发管理器
3. `backend/gateway/internal/config/config.go` - 超时配置
4. `backend/gateway/internal/handler/chat_orchestrator.go` - 消息处理超时
5. `backend/app/services/llm_service.py` - 性能日志
6. `backend/app/core/llm_router.py` - 延迟预期更新
7. `backend/scripts/test_llm_direct.py` - 新增测试脚本

---

## 后续建议

1. **监控** - 使用新增的日志监控实际 TTFC 和总耗时
2. **告警** - 设置告警阈值（如 TTFC > 5秒）
3. **优化** - 考虑为标准聊天任务禁用思考模式（`clear_thinking=True`）
4. **扩展** - 如需更高并发，可联系 GLM 客服增加限额

---

## 测试命令

```bash
# 直接 API 测试
cd backend && python scripts/test_llm_direct.py

# 查看 LLM 调用日志
docker compose logs grpc-server 2>&1 | grep "\[LLM\]"

# 查看并发统计
# TODO: 添加 /admin/llm-stats 端点
```
