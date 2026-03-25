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

**根据用户等级动态设置** (参考 [GLM Rate Limits](https://www.bigmodel.cn/dev/howuse/rate-limits)):

| 用户等级 | 月消费 | GLM-4 并发 | GLM-4-Flash 并发 |
|---------|--------|-----------|-----------------|
| Free | 0-50元 | 5 | 5 |
| Level 1 | 50-500元 | 10 | 10 |
| Level 2 | 500-5000元 | 20 | 50 |
| Level 3 | 5000-10000元 | 30 | 100 |
| Level 4 | 1万-3万 | 100 | 200 |
| Level 5 | 3万+ | 200 | 300 |

```python
# 使用方式
async with llm_concurrency.acquire("zhipu"):
    await llm_service.chat(...)
```

**环境变量配置**:

```bash
# 设置用户等级（自动调整并发限制）
ZHIPU_USER_LEVEL=3  # free/1/2/3/4/5/pro

# 或直接设置并发数
ZHIPU_CONCURRENT_LIMIT=30
```

### 5. 模型回退系统 (`app/services/llm/fallback.py`) ⭐ NEW

新增智能模型回退管理器，自动处理 429 错误并切换到同层级替代模型：

**功能特性**:
- ✅ 检测 429/Rate Limit 错误，立即触发回退
- ✅ 优先切换同 tier 的其他模型
- ✅ 如果同 tier 无可用模型，降级到下一 tier
- ✅ 指数退避重试 (100ms → 200ms → 400ms → ...)
- ✅ Redis 分布式健康追踪
- ✅ 熔断器集成 (5 次失败后熔断 60 秒)

**回退路径示例**:

```
zhipu_chat (STANDARD) 失败
    ↓
deepseek_chat (STANDARD) 尝试
    ↓
qwen_plus (STANDARD) 尝试
    ↓
zhipu_flash (FAST) 降级
    ↓
glm_4_7_flash (FREE_FAST) 最后手段
```

**使用方式** (自动集成):

```python
# 自动回退已集成到 LLMService.chat() 和 stream_chat()
# 开发者无需修改现有代码

# 查看回退日志
[LLMFallback] Attempt 1/3: model=glm-4.7
[LLMFallback] Attempt 1 failed: reason=rate_limit_429
[LLMFallback] Waiting 100ms before retry...
[LLMFallback] Attempt 2/3: model=deepseek-chat
[LLMFallback] SUCCESS after 1 attempts: final_model=deepseek-chat
```

### 6. 性能日志 (`app/services/llm_service.py`)

添加详细的性能追踪日志：
- `[LLM] stream_chat START` - 调用开始
- `[LLM] stream_chat FIRST_CHUNK` - 首个 chunk 到达时间 (TTFC)
- `[LLM] stream_chat END` - 调用结束时间和总耗时
- `[LLMFallback]` - 回退尝试日志

### 7. 延迟预期更新 (`app/core/llm_router.py`)

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

### 回退系统测试 (`test_llm_fallback.py`) ⭐ NEW

| 测试项 | 结果 |
|--------|------|
| 429 错误检测 | ✅ PASS |
| 超时错误检测 | ✅ PASS |
| 健康追踪器 | ✅ PASS (需 Redis) |
| 回退候选选择 | ✅ 6 个候选 |
| 指数退避计算 | ✅ 100-1600ms |
| 并发限制配置 | ✅ 5-30 并发 |
| 真实 LLM 调用 | ✅ 7.8s 响应 |

### 修复前后对比

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 超时设置 | 5秒 (Go) | 60秒 (Go + Python) |
| 并发控制 | 无 | Semaphore (5-30) |
| 429 错误 | 频繁触发 | 自动回退 |
| 模型回退 | 无 | 智能回退系统 |
| 响应时间 | ~118秒 | 0.5-8秒 |
| TTFC | 未知 | 500ms-3s |

---

## 配置说明

### 环境变量

```bash
# gRPC 超时（秒），默认 60
GRPC_TIMEOUT_SECONDS=60

# GLM 用户等级（自动调整并发）
ZHIPU_USER_LEVEL=3  # free/1/2/3/4/5/pro

# 或直接设置并发数
ZHIPU_CONCURRENT_LIMIT=30

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

### 模型层级体系

```
REASONING (推理)
  ├── zhipu_reason (GLM-4.7 + 保留思考)
  ├── deepseek_reason (DeepSeek-R1)
  └── qwen-max-qwq (通义千问推理)

STANDARD (标准)
  ├── zhipu_chat (GLM-4.7 快速)
  ├── deepseek_chat (DeepSeek-V3)
  └── qwen-plus (通义千问)

FAST (快速)
  ├── xiaomi_chat (小米 MIMO)
  └── zhipu_flash (GLM-4.7-FlashX)

FREE_REASONING (免费推理)
  └── glm_4_7_flash_thinking (GLM-4.7-Flash + 思考)

FREE_FAST (免费快速)
  └── glm_4_7_flash_no_thinking (GLM-4.7-Flash 快速)

SPECIALIST (专家)
  ├── siliconflow_ocr (DeepSeek OCR)
  └── siliconflow_translate (混元 MT)
```

---

## 文件变更清单

1. `backend/app/services/llm/providers.py` - 超时 + 并发控制
2. `backend/app/services/llm/concurrency.py` - 并发管理器（支持用户等级）
3. `backend/app/services/llm/fallback.py` - ⭐ 新增模型回退管理器
4. `backend/gateway/internal/config/config.go` - 超时配置
5. `backend/gateway/internal/handler/chat_orchestrator.go` - 消息处理超时
6. `backend/app/services/llm_service.py` - 性能日志 + 回退集成
7. `backend/app/core/llm_router.py` - 延迟预期更新
8. `backend/scripts/test_llm_direct.py` - 直接 API 测试脚本
9. `backend/scripts/test_llm_fallback.py` - ⭐ 新增回退系统测试脚本

---

## 后续建议

1. **监控** - 使用新增的日志监控实际 TTFC、总耗时和回退事件
2. **告警** - 设置告警阈值（如 TTFC > 5秒，回退率 > 10%）
3. **优化** - 考虑为标准聊天任务禁用思考模式（`clear_thinking=True`）
4. **扩展** - 如需更高并发，可联系 GLM 客服增加限额
5. **分析** - 记录回退事件用于分析模型稳定性

---

## 测试命令

```bash
# 直接 API 测试
cd backend && python scripts/test_llm_direct.py

# 回退系统测试
cd backend && python scripts/test_llm_fallback.py

# WebSocket 性能测试
cd backend && python test_websocket_performance.py

# 查看 LLM 调用日志
docker compose logs grpc-server 2>&1 | grep "\[LLM\]"

# 查看回退日志
docker compose logs grpc-server 2>&1 | grep "\[LLMFallback\]"
```

---

## 参考资料

- [智谱 AI 速率限制文档](https://www.bigmodel.cn/dev/howuse/rate-limits)
- [智谱 Coding Plan 套餐概览](https://docs.bigmodel.cn/cn/coding-plan/overview)

