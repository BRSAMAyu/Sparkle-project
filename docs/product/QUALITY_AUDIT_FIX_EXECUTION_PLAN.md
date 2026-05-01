# Sparkle 质量审计修复执行计划

**日期**: 2026-05-02
**关联文档**: `docs/product/QUALITY_AUDIT_DEEP_REPORT.md`
**并行安全**: 每个工作包（Work Package, WP）拥有独占的文件所有权，任意两个WP不会编辑同一文件

---

## 文件所有权矩阵

每个WP只能编辑其声明的文件。如需修改非声明文件，需在本文档中重新分配。

```
WP-01 → websocket_proxy.go
WP-02 → chat_orchestrator.go, chat_orchestrator_chatflow.go
WP-03 → auth.go, ws_auth.go, error_sanitizer.go, 新建 api_errors.go
WP-04 → cors.go, security.go, timeout.go, setup.go, db.go
WP-05 → chat_history.go, semantic_cache.go, rate_limit.go, client.go, health_checker.go
WP-06 → agent_grpc_service.py, profile_front_door_service.py, growth_dashboard_service.py, ltm_release_gate.py
WP-07 → memory_service.py, cognitive_service.py, behavior_signal_collector.py, predictive_service.py
WP-08 → core/security.py, core/llm_secure_io.py, core/safe_error_messages.py
WP-09 → galaxy_service.py, openclaw/url_guard.py, celery_app.py
WP-10 → backend/app/services/ 中含 print() 的23个文件（不含WP-06/07/08/09的文件）
WP-11 → community_provider.dart, achievement_provider.dart, galaxy_repository.dart, local_vocabulary_provider.dart
WP-12 → photon/transaction_history_list.dart, error_book/presentation/ 全部文件
WP-13 → simulation_provider.dart, simulation_screen.dart, translation_popover.dart
WP-14 → chat/presentation/widgets/ 全部交互元素 + visual_elements/ 3个文件
WP-15 → memory_panel_screen.dart, memory_settings_screen.dart, calendar_stats_screen.dart
WP-16 → docker-compose.prod.yml, docker-compose.yml
WP-17 → monitoring/ 全部告警YAML
WP-18 → schema.sql（只读参考，修改通过 Alembic 迁移）
WP-19 → 删除废弃文件 + quality/coverage_thresholds.json + .pre-commit-config.yaml + ci.yml
WP-20 → proto/ 全部 .proto 文件
```

---

## WP-01: WebSocket Proxy 完整加固

### 目标
确保WebSocket代理的所有goroutine有panic recovery，community WS路径有XSS消毒，用户ID不被明文记录到日志。

### 为什么重要
这是Go Gateway中最关键的外部连接点。一个goroutine panic会导致半开连接（用户看到连接正常但无响应），community WS未消毒消息可能导致XSS攻击。

### 需要修改的文件
`backend/gateway/internal/handler/websocket_proxy.go`

### 问题描述

**问题1 — 无panic recovery**: 文件中约3-5个`go func()`启动的goroutine（client→backend转发、backend→client转发、ping/pong）均没有`defer recover()`。如果任何goroutine发生panic（nil指针、slice越界等），该goroutine静默死亡，导致WebSocket连接变为半开状态。

**问题2 — Community WS无XSS消毒**: `HandleCommunityWS`或`proxyWebSocket`方法将客户端消息直接转发到Python后端，没有经过bluemonody消毒。而chat路径（chat_orchestrator.go）有消毒。这意味着community群聊消息可以包含任意HTML/脚本。

**问题3 — 用户ID明文日志**: `log.Printf("WebSocket connected for user: %s", userID)` 在每次连接时记录用户ID。

### 期望结果
1. 每个goroutine都有panic recovery，panic时记录结构化日志并关闭连接
2. Community WS路径的文本消息经过bluemonody UGC策略消毒
3. 用户ID在日志中使用hash或仅记录前8字符

### 验证方法
- 确认每个`go func()`开头有`defer func() { if r := recover(); ... }()`
- 确认community WS路径调用`sanitizer.Sanitize()`
- 确认日志不再包含完整用户ID
- 运行 `cd backend/gateway && go build ./...` 确保编译通过

---

## WP-02: Chat Handler 错误处理 + 消毒加固

### 目标
确保envelope协议路径的聊天消息经过XSS消毒，WebSocket写入错误不被静默丢弃，WS错误格式与REST保持一致。

### 为什么重要
envelope协议是Flutter客户端的主要聊天路径。如果这条路径没有HTML消毒，恶意用户可以通过聊天发送script标签。`_ = writeLegacyJSON`丢弃错误意味着客户端可能永远收不到某些消息。

### 需要修改的文件
- `backend/gateway/internal/handler/chat_orchestrator.go`
- `backend/gateway/internal/handler/chat_orchestrator_chatflow.go`

### 问题描述

**问题1 — Envelope协议缺消毒**: 在`wsModeEnvelope`处理路径中，`input.Message`被解码后直接发送给gRPC，没有经过bluemonody消毒。查找`chat_orchestrator.go`中解码envelope payload的位置，在发送到gRPC之前添加`input.Message = sanitizer.Sanitize(input.Message)`。

**问题2 — 写入错误被丢弃**: 搜索`_ = writeLegacyJSON`和`_ = writeJSON`，约10+处。每一处都应该记录错误而不是静默丢弃。将`_ = writeLegacyJSON(...)`改为`if err := writeLegacyJSON(...); err != nil { log.Printf(...) }`或等价的结构化日志。

**问题3 — WS错误格式**: WebSocket错误响应使用`gin.H{"type": "error", "message": ...}`格式，而REST使用`gin.H{"error": ..., "error_code": ..., "category": ...}`。考虑对齐到统一格式，但要确保Flutter客户端能兼容（如果改格式需要同步修改Flutter，可以先只加日志不改格式）。

### 期望结果
1. envelope协议消息经过bluemonody消毒
2. 所有WebSocket写入错误被记录（不是静默丢弃）
3. 如果改了错误格式，确保Flutter端兼容

### 验证方法
- 搜索确认无`_ = writeLegacyJSON`或`_ = writeJSON`残留
- 确认envelope路径有Sanitize调用
- `cd backend/gateway && go build ./...`

---

## WP-03: 错误响应标准化 + Auth中间件优化

### 目标
建立统一的REST错误响应格式，修复auth中间件的错误消息不经过消毒器的问题，为本地黑名单缓存添加大小上限。

### 为什么重要
目前每个REST handler自己构造`gin.H{"error": "..."}`格式，没有error_code、request_id等字段。Flutter客户端无法做统一的错误处理。Auth中间件的错误消息直接硬编码英文，不经过i18n系统。

### 需要修改的文件
- `backend/gateway/internal/handler/error_sanitizer.go`
- `backend/gateway/internal/middleware/auth.go`
- `backend/gateway/internal/middleware/ws_auth.go`
- **新建**: `backend/gateway/internal/handler/api_errors.go`

### 问题描述

**问题1 — 无统一错误格式**: 所有handler返回`gin.H{"error": msg}`。需要定义标准结构：
```
type APIErrorResponse struct {
    Error     string `json:"error"`
    ErrorCode string `json:"error_code,omitempty"`
    RequestID string `json:"request_id,omitempty"`
}
```
创建helper函数`RespondError(c *gin.Context, status int, code string, message string)`，自动注入request_id。

**问题2 — Auth错误消息绕过消毒**: `auth.go:147,154`直接返回`gin.H{"error": "Authorization token required"}`。应使用新的统一错误响应函数。

**问题3 — 本地黑名单缓存无上限**: `auth.go:36-39`中`globalLocalBlacklist`的`jtiSet`和`userRevoked` map在持续撤销活动下可能无限增长。清理只在超过100条时触发。添加硬上限（如10000条），超出时淘汰最旧的条目。

### 期望结果
1. 新的`api_errors.go`提供统一错误响应函数
2. auth.go和ws_auth.go使用统一函数
3. 本地黑名单有硬上限保护
4. 现有handler可以渐进式迁移（不需要一次改完所有handler）

### 验证方法
- 新文件编译通过
- auth.go的ErrorJSON调用被替换
- 黑名单缓存有max size常量和淘汰逻辑
- `cd backend/gateway && go build ./...`

---

## WP-04: 中间件 + 连接池配置优化

### 目标
添加CORS Max-Age减少preflight请求，为CSP style-src unsafe-inline添加文档注释，配置Go pgxpool合理的连接数，确保WebSocket路由超时文档清晰。

### 为什么重要
CORS缺少Max-Age意味着每次跨域请求都有OPTIONS preflight，增加延迟。Go pgxpool使用默认4个连接在生产负载下会成为瓶颈。

### 需要修改的文件
- `backend/gateway/internal/middleware/cors.go`
- `backend/gateway/internal/middleware/security.go`
- `backend/gateway/internal/middleware/timeout.go`
- `backend/gateway/cmd/server/setup.go`
- `backend/gateway/internal/db/db.go`（如果pool配置在这里）

### 问题描述

**问题1 — CORS无Max-Age**: `cors.go`中设置了AllowOrigins、AllowMethods、AllowHeaders，但缺少`Access-Control-Max-Age` header。浏览器每次跨域请求都发preflight OPTIONS。添加`c.Header("Access-Control-Max-Age", "86400")`。

**问题2 — CSP注释**: `security.go:18`中`style-src 'self' 'unsafe-inline'`已有注释说明权衡，确保注释清晰说明为什么保留unsafe-inline。

**问题3 — pgxpool默认配置**: 在`setup.go`中找到pgxpool创建的位置，将默认MaxConns从4提升到合理值（如20-30），添加MinConns(如5)和MaxConnIdleTime。

**问题4 — Timeout文档**: `timeout.go`中`isLongRunningRoute`函数豁免了部分路由，但WebSocket upgrade路径没有显式列出。添加注释说明WS连接通过HTTP hijack绕过timeout中间件。

### 期望结果
1. CORS响应包含Max-Age header
2. pgxpool有显式MaxConns/MinConns配置
3. timeout.go有WS路径的文档注释

### 验证方法
- `cd backend/gateway && go build ./...`

---

## WP-05: Go Gateway 结构化日志迁移

### 目标
将Go Gateway中最密集的printf式日志迁移到zap结构化日志，使日志可搜索、可过滤、可关联。

### 为什么重要
目前454处`log.Printf` vs 211处zap日志。printf日志缺少结构化字段，无法在Grafana/Loki中高效搜索和过滤。chat_history.go有15+处printf日志，rate_limit.go有多处，client.go有连接错误日志。

### 需要修改的文件
- `backend/gateway/internal/service/chat_history.go`
- `backend/gateway/internal/service/semantic_cache.go`
- `backend/gateway/internal/middleware/rate_limit.go`
- `backend/gateway/internal/agent/client.go`
- `backend/gateway/internal/agent/health_checker.go`

### 问题描述
搜索上述文件中所有`log.Printf`、`log.Println`、`log.Print`调用，替换为结构化日志：
- `log.Printf("Failed to connect: %v", err)` → `logger.Error("Failed to connect", zap.Error(err))`
- `log.Printf("Rate limit: %s", key)` → `logger.Warn("Rate limited", zap.String("key", key))`

项目已有zap基础设施在`backend/gateway/internal/infra/logger/logger.go`。使用方法参照同目录下已使用zap的文件。

**注意**: semantic_cache.go中的FT.SEARCH解析逻辑比较脆弱（类型断言链），在迁移日志时可以同时添加防御性检查，对nil/非预期类型返回error而不是静默返回空结果。

### 期望结果
1. 上述5个文件中所有`log.Printf/Println/Print`替换为zap结构化日志
2. semantic_cache.go的类型断言有防御性检查
3. 编译通过

### 验证方法
- `cd backend/gateway && go build ./...`
- `grep -r "log.Printf\|log.Println\|log.Print" internal/service/chat_history.go internal/middleware/rate_limit.go internal/agent/client.go` 确认返回0结果

---

## WP-06: Python 关键服务错误处理修复

### 目标
修复后端最关键的服务（gRPC服务层、用户画像、成长仪表板、LTM门控）中的裸`except Exception:`，让错误可见而不是被静默吞没。

### 为什么重要
这些是用户请求链路上的核心服务。`agent_grpc_service.py`是所有gRPC请求的入口，一处错误吞没可能导致整条请求链的调试信息丢失。

### 需要修改的文件
- `backend/app/services/agent_grpc_service.py`
- `backend/app/services/profile_front_door_service.py`
- `backend/app/services/growth_dashboard_service.py`
- `backend/app/services/ltm_release_gate.py`

### 问题描述
搜索每个文件中的`except Exception:`块。对于每个：

1. **分析上下文**: 这个try块在做什么？哪些异常是预期的？
2. **替换为具体类型**: 
   - 数据解析失败 → `except (ValueError, KeyError, json.JSONDecodeError)`
   - Redis/网络失败 → `except (redis.RedisError, ConnectionError, asyncio.TimeoutError)`
   - 数据库失败 → `except (sqlalchemy.exc.SQLAlchemyError, asyncpg.PostgresError)`
3. **添加日志**: 每个catch块至少要有`logger.warning/error`
4. **决定返回值**: 
   - 如果调用方检查None → 可以返回None但必须记录日志
   - 如果调用方不检查None → 应该raise或返回安全的默认值
5. **保留必要的兜底**: 顶层入口（如gRPC方法）可以保留`except Exception`作为最后防线，但必须记录完整堆栈

### 期望结果
1. 4个文件中的裸`except Exception:`数量大幅减少
2. 每个catch块有具体的异常类型和日志
3. `cd backend && python -c "import app.services.agent_grpc_service"` 验证导入正常

### 验证方法
- `grep -c "except Exception:" backend/app/services/agent_grpc_service.py` — 数量应显著下降
- 确认无语法错误

---

## WP-07: Python 数据服务错误处理修复

### 目标
修复数据层服务（记忆、认知、行为信号、预测）中的裸`except Exception:`和未类型化的None返回。

### 为什么重要
这些服务处理用户数据。错误被吞没后变为None，调用方不做null检查导致下游AttributeError，用户看到的是毫无意义的错误信息。

### 需要修改的文件
- `backend/app/services/memory_service.py`
- `backend/app/services/cognitive_service.py`
- `backend/app/services/behavior_signal_collector.py`
- `backend/app/services/predictive_service.py`
- `backend/app/services/intervention_feedback_binding_service.py`

### 问题描述
与WP-06相同的修复策略。额外注意：

1. `predictive_service.py`有10+处`return None`，调用方直接访问`.health`、`.score`等属性。需要：
   - 要么将返回类型改为`Optional[...]`并确保调用方有null check
   - 要么返回一个安全的默认对象（如`PredictionResult(score=0.0, confidence=0.0)`）

2. `behavior_signal_collector.py:790`的Redis fallback已记录日志但未传播错误。考虑是否需要在Redis不可用时通知上层。

### 期望结果
1. 裸except数量减少
2. None返回有明确的类型提示（`Optional[...]`）
3. 关键路径有安全默认值

### 验证方法
- `grep -c "except Exception:" backend/app/services/memory_service.py` 等
- `cd backend && python -m py_compile app/services/memory_service.py`

---

## WP-08: Python 安全加固

### 目标
将Python端token黑名单在Redis不可用时改为fail-closed模式；将LLM安全kill switch改为分层设计，密钥脱敏永远不被绕过。

### 为什么重要
目前如果Redis宕机，Python端会把已撤销的token视为有效（fail-open）。kill switch关闭时，连API密钥脱敏都被绕过，用户消息中的密钥会原样发给LLM。

### 需要修改的文件
- `backend/app/core/security.py`
- `backend/app/core/llm_secure_io.py`
- `backend/app/core/safe_error_messages.py`

### 问题描述

**问题1 — Token黑名单fail-open**: `security.py:163-166`中`is_token_revoked()`在异常时返回False（视为未撤销）。在生产环境中应返回True（视为已撤销）。添加环境检查：
```python
except Exception as e:
    logger.error(f"Token revocation check failed: {e}")
    if settings.ENVIRONMENT == "production":
        return True  # fail-closed in production
    return False  # fail-open in development for debugging
```

**问题2 — Kill switch全有或全无**: `llm_secure_io.py:65-67`中`redact_secrets()`在`llm_safety_enabled()`为False时直接返回原始值。建议分层：
- `redact_secrets()` → **永远执行**（不检查kill switch）
- `sanitize_text_for_llm()` → 受kill switch控制
- `wrap_user_message()` → 受kill switch控制
- `sanitize_llm_output()` → 受kill switch控制

修改方式：在`secure_messages()`、`sanitize_text_for_llm()`等函数中检查kill switch，但在`redact_secrets()`中不检查。

**问题3 — safe_error_messages覆盖不全**: `safe_error_messages.py`仅覆盖3种异常类型。扩展覆盖`ValueError`（用户输入错误）和LLM提供商异常。

### 期望结果
1. Python端token黑名单在生产环境fail-closed
2. 密钥脱敏永远生效（不受kill switch影响）
3. 错误消息映射更完整

### 验证方法
- `cd backend && python -m py_compile app/core/security.py app/core/llm_secure_io.py`
- 搜索确认`redact_secrets`不检查`llm_safety_enabled()`

---

## WP-09: 后端服务专项修复

### 目标
修复Galaxy废弃方法的运行时保护、SSRF防护的DNS重绑定漏洞、Celery任务的全局超时缺失。

### 为什么重要
Galaxy废弃方法可导致用户mastery被双重扣分。SSRF DNS重绑定允许攻击者通过OpenClaw访问内部服务。Celery任务无超时意味着一个挂起的LLM调用会永久占用worker。

### 需要修改的文件
- `backend/app/services/galaxy_service.py`
- `backend/app/services/openclaw/url_guard.py`
- `backend/app/core/celery_app.py`

### 问题描述

**问题1 — Galaxy双重mastery**: `galaxy_service.py:159-281`中`handle_error_created`和`update_mastery_from_error`标记为DEPRECATED，警告"调用将导致双重精通扣除"。当前保护仅靠注释。需要添加运行时保护：
- 选项A：在方法开头`raise DeprecationWarning("Use ErrorBookMasterySyncService instead")`
- 选项B：改为no-op（`return None`），同时记录warning日志
- 选择哪种取决于是否还有调用方

**问题2 — SSRF DNS重绑定**: `url_guard.py:31-76`中`validate_external_url`在验证时解析DNS，但实际HTTP请求时不再验证。攻击者可使用DNS重绑定（首次解析为公网IP，第二次解析为127.0.0.1）。修复方向：
- 使用自定义DNS解析器
- 或在httpx连接时通过transport钩子重新验证IP
- 或禁止follow_redirects并逐跳验证

**问题3 — Celery无全局超时**: `celery_app.py`缺少`task_time_limit`和`task_soft_time_limit`。添加：
```python
CELERY_TASK_TIME_LIMIT = 600     # 10分钟硬超时
CELERY_TASK_SOFT_TIME_LIMIT = 540  # 9分钟软超时（触发异常）
```

### 期望结果
1. Galaxy废弃方法有运行时保护（不会静默执行）
2. SSRF防护在连接时重新验证IP
3. Celery任务有全局超时

### 验证方法
- `cd backend && python -m py_compile app/services/galaxy_service.py app/services/openclaw/url_guard.py app/core/celery_app.py`

---

## WP-10: Python logging清理

### 目标
将Python后端中散落的`print()`调用替换为标准logging，同时清理其他文件中的裸`except Exception:`。

### 为什么重要
print()绕过日志框架，没有时间戳、级别和上下文。在容器化环境中print输出可能被丢弃或无法被Loki收集。

### 需要修改的文件
搜索`backend/app/`中所有包含`print(`的.py文件（排除`_deprecated/`和`__pycache__`），大约23个文件。
- `backend/app/data/populate_achievements.py`
- `backend/app/config_production.py`
- `backend/app/core/llm_safety.py`
- 以及其他20个文件

### 问题描述
将每个`print(...)`替换为适当的日志级别：
- `print(f"Processing {item}")` → `logger.debug(f"Processing {item}")`
- `print(f"Error: {e}")` → `logger.error(f"Error: {e}")`
- 确保文件顶部有`import logging; logger = logging.getLogger(__name__)`

**注意**: 不要修改WP-06/07/08/09已声明的文件中的print（如果有，留给对应WP处理）。

### 期望结果
1. `grep -r "^\s*print(" backend/app/ --include="*.py" | grep -v _deprecated | grep -v __pycache__` 结果大幅减少
2. 编译通过

### 验证方法
- `cd backend && python -m py_compile app/data/populate_achievements.py` 等

---

## WP-11: Flutter Stream泄漏 + 错误处理修复

### 目标
修复community和achievement模块的StreamSubscription泄漏，清理galaxy和vocabulary模块中的静默异常吞没。

### 为什么重要
StreamSubscription不取消会导致ghost listener——在StateNotifier被dispose后仍然处理事件，可能导致对已释放资源的操作和内存泄漏。静默catch使生产调试几乎不可能。

### 需要修改的文件
- `mobile/lib/features/community/presentation/providers/community_provider.dart`
- `mobile/lib/features/achievement/presentation/providers/achievement_provider.dart`
- `mobile/lib/features/galaxy/data/repositories/galaxy_repository.dart`
- `mobile/lib/features/vocabulary/data/providers/local_vocabulary_provider.dart`

### 问题描述

**问题1 — StreamSubscription泄漏**: 
- `community_provider.dart:101` — `FriendsNotifier`构造函数中`events.listen(_handleEvent)`未存储subscription引用
- `community_provider.dart:1591` — `PrivateMessagesNotifier._initialize()`同样问题
- 修复：存储`StreamSubscription`引用，在`dispose()`中取消
- 参照`GroupChatMessagesNotifier`（line 1126-1131）的正确模式

**问题2 — 硬编码中文（community_provider.dart）**: 
- line 1632: `'群成员'`
- line 1634: `'提及了你'`
- 替换为l10n key或I18nService调用

**问题3 — 空catch块**: 
- `galaxy_repository.dart` 有5处`catch (_) {}`（API调用失败静默返回空数据）
- `local_vocabulary_provider.dart` 有5处`catch (_) {}`
- 修复：至少改为`catch (e) { debugPrint('className.methodName: $e'); }`
- 对于数据加载路径：传播错误到UI state

### 期望结果
1. 所有StreamSubscription在dispose中取消
2. community_provider的硬编码中文已迁移
3. galaxy_repository和vocabulary_provider的catch有日志输出

### 验证方法
- `cd mobile && flutter analyze`
- 确认dispose()方法中有subscription.cancel()

---

## WP-12: Flutter i18n迁移 — Photon + Error Book

### 目标
将photon和error_book模块中的硬编码中文字符串迁移到i18n系统。

### 为什么重要
photon模块的transaction_history_list.dart有10+处硬编码中文，包括日期格式化`'yyyy年MM月dd日'`，对英文用户完全不可用。error_book模块也有多处原始中文。

### 需要修改的文件
- `mobile/lib/features/photon/presentation/widgets/transaction_history_list.dart`
- `mobile/lib/features/error_book/presentation/screens/error_list_screen.dart`
- `mobile/lib/features/error_book/presentation/widgets/review_performance_buttons.dart`
- `mobile/lib/features/error_book/presentation/widgets/error_question_image.dart`
- 可能需要修改的l10n ARB文件

### 问题描述
查找所有硬编码中文字符串（包含中文字符`[\u4e00-\u9fff]`的字符串字面量）。对每个：

1. 在ARB文件中添加对应的key-value（中文和英文）
2. 将硬编码字符串替换为`context.l10n.keyName`

特别注意：
- `transaction_history_list.dart:188-195`的日期格式化 — 使用`DateFormat`的locale参数
- `'今天'`、`'昨天'`、`'X天前'` — 需要相对时间本地化

**不要修改**: 使用`I18nService.instance.isChinese ? '中文' : 'English'`模式的代码（这种模式已经处理了双语，只是不够优雅，暂不迁移）

### 期望结果
1. photon和error_book的presentation层无硬编码中文
2. 日期格式化跟随locale
3. `cd mobile && flutter analyze` 通过

### 验证方法
- `grep -r "[\u4e00-\u9fff]" mobile/lib/features/photon/presentation/ --include="*.dart"` 应返回0结果
- 同理检查error_book

---

## WP-13: Flutter i18n迁移 — Simulation + Translation

### 目标
将simulation和translation模块中的硬编码中文迁移到i18n系统。

### 为什么重要
simulation_provider.dart有5+处中文错误/状态消息（如`'模拟生成失败'`、`'实时连接中断，已恢复到最近一次保存的模拟进度。'`），这些消息直接影响用户体验。

### 需要修改的文件
- `mobile/lib/features/simulation/presentation/providers/simulation_provider.dart`
- `mobile/lib/features/simulation/presentation/screens/simulation_screen.dart`（如果有硬编码）
- `mobile/lib/features/translation/presentation/widgets/translation_popover.dart`

### 问题描述
与WP-12相同策略。注意simulation_provider中的中文大多在error/fallback消息中，需要确保l10n key的命名清晰反映使用场景。

translation_popover.dart:
- line 127: `'已加入生词卡，24小时后复习'`
- line 271: `'翻译失败'`

### 期望结果
1. simulation和translation模块无硬编码中文
2. `cd mobile && flutter analyze` 通过

### 验证方法
- grep检查无中文硬编码残留

---

## WP-14: Flutter Semantics标签 + 视觉元素调色板

### 目标
为chat模块的118个缺Semantics标签的交互元素添加无障碍标注；合并visual_elements模块中三重复制的颜色调色板。

### 为什么重要
25.3%的Semantics覆盖率意味着屏幕阅读器用户（视障群体）无法有效使用大部分chat功能。三重复制的调色板类增加维护成本和颜色不一致风险。

### 需要修改的文件
- `mobile/lib/features/chat/presentation/widgets/` 中所有含GestureDetector/InkWell/IconButton的文件
- `mobile/lib/features/visual_elements/presentation/widgets/visual_element_card.dart`
- `mobile/lib/features/visual_elements/presentation/widgets/visual_element_preview_dialog.dart`
- `mobile/lib/features/visual_elements/presentation/screens/visual_elements_screen.dart`
- **可能新建**: `mobile/lib/features/visual_elements/presentation/shared/visual_element_palette.dart`

### 问题描述

**问题1 — Semantics缺失**: 
搜索chat/widgets/目录中所有`GestureDetector(`、`InkWell(`、`IconButton(`、`TextButton(`实例。对每个检查是否有`Semantics(`包装或`semanticLabel`属性。缺失的需添加：
```dart
Semantics(
  button: true,
  label: '描述这个按钮的作用',
  child: GestureDetector(...)
)
```

优先级：先处理chat_input.dart、chat_bubble.dart、voice_input_button.dart等高频交互文件。

**问题2 — 调色板三重复制**: 
三个文件中定义了相同的私有颜色类：
- `_InkVisualPalette` (7个Color常量)
- `_VisualInk` (10个Color常量，是上面超集)  
- `_InkStagePalette` (7个Color常量)
- `_RarityColors` 定义3次
- 稀有度颜色map重复3次

创建单一共享的`VisualElementPalette`类，三个文件统一引用。

### 期望结果
1. chat模块Semantics覆盖率提升至80%+
2. visual_elements有单一调色板定义
3. `cd mobile && flutter analyze` 通过

### 验证方法
- 统计Semantics标签数量
- 确认无重复的私有颜色类定义

---

## WP-15: Flutter Memory/Calendar状态管理优化

### 目标
改善memory和calendar模块中过度使用setState管理复杂状态的问题，添加缺失的骨架屏加载。

### 为什么重要
memory_panel_screen.dart有35+个setState调用管理17个本地状态字段（lists、sets、enums、error、loading），是"双重状态"反模式的典型案例。

### 需要修改的文件
- `mobile/lib/features/memory/presentation/screens/memory_panel_screen.dart`
- `mobile/lib/features/memory/presentation/screens/memory_settings_screen.dart`
- `mobile/lib/features/calendar/presentation/screens/calendar_stats_screen.dart`

### 问题描述
这三个文件都是`ConsumerStatefulWidget`（同时有Riverpod和本地setState）。目标是将数据相关的状态（loading、error、lists）迁移到StateNotifier，只保留纯UI状态（toggle开关、表单字段焦点）在本地setState。

**不要过度重构**: 只需要在现有结构上做增量改善：
1. 将loading/error状态提取到provider
2. 数据列表（preferences、goals、episodic memories）提取到provider
3. 表单临时状态保留在setState

**额外**: memory_settings_screen.dart中有多处`I18nService.instance.isChinese ? '中文' : 'English'`内联三元表达式。如果时间允许，迁移到l10n key（但不强制）。

### 期望结果
1. memory模块数据状态由provider管理
2. setState调用减少到<10个（仅用于UI toggle）
3. `cd mobile && flutter analyze` 通过

### 验证方法
- 统计setState调用数量
- 确认编译通过

---

## WP-16: Docker/部署生产加固

### 目标
将生产docker-compose中的latest标签替换为固定版本，添加缺失的健康检查和资源限制，验证Redis持久化配置。

### 为什么重要
生产环境使用latest标签意味着每次部署可能拉到不同版本的镜像，行为不可预测。缺失健康检查意味着Docker不知道服务是否真正可用。缺失资源限制意味着一个失控的容器可以耗尽整台机器的资源。

### 需要修改的文件
- `docker-compose.prod.yml`
- `docker-compose.yml`（对比用，修改限于dev环境的小修正）

### 问题描述

**问题1 — latest标签**: `docker-compose.prod.yml:347,425`中Prometheus和Grafana使用`latest`。dev compose正确使用了`prometheus:v2.53.4`和`grafana-oss:11.1.4`。将prod对齐到相同固定版本。

**问题2 — 缺健康检查**: 生产环境nginx、db、redis、minio、tempo、prometheus、alertmanager、loki、promtail、grafana缺健康检查。参照dev compose中已有的健康检查模式添加。

**问题3 — 缺资源限制**: 生产环境除celery_worker外，所有服务无deploy.resources配置。参照dev compose为每个服务添加合理的memory limit和reservation。

**问题4 — Redis持久化**: 确认生产Redis挂载的`redis.conf`包含RDB或AOF持久化配置。如果没有，添加。

**问题5 — PostgreSQL调优**: 生产PostgreSQL应考虑添加`shared_buffers`、`work_mem`、`max_connections`等参数。可以通过command参数或自定义postgresql.conf。

### 期望结果
1. 所有镜像使用固定版本标签
2. 所有服务有健康检查
3. 所有服务有资源限制
4. Redis持久化已确认
5. `docker compose -f docker-compose.prod.yml config` 验证YAML有效

### 验证方法
- `docker compose -f docker-compose.prod.yml config` 不报错
- 搜索确认无`latest`标签

---

## WP-17: 监控告警补充

### 目标
添加缺失的3个关键告警：WebSocket连接增长速率、会话锁争用、gRPC流信号量利用率。

### 为什么重要
这三个盲区意味着运维人员在用户可感知的故障发生后才能发现（通过其他告警间接推断），无法主动预防。

### 需要修改的文件
- `monitoring/sparkle_slo_alerts.yml`（添加新告警）
- `backend/gateway/internal/handler/ws_registry.go`（导出连接计数到Prometheus）
- `backend/gateway/internal/handler/chat_orchestrator.go`（导出信号量利用率）
- `backend/app/orchestration/state_manager.py`（导出锁争用计数）

### 问题描述

**告警1 — WebSocket连接增长**: 
- ws_registry.go有`Count()`方法但未导出到Prometheus
- 添加`sparkle_ws_active_connections` gauge，在Register/Unregister时更新
- 添加告警：`deriv(sparkle_ws_active_connections[30m]) > 0.5`（30分钟内稳定增长）

**告警2 — 会话锁争用**: 
- state_manager.py的锁获取失败时没有指标
- 添加`sparkle_session_lock_acquire_failures_total` counter
- 添加告警：`increase(sparkle_session_lock_acquire_failures_total[5m]) > 5`

**告警3 — gRPC流信号量**: 
- chat_orchestrator.go有streamSem但利用率未导出
- 添加`sparkle_grpc_stream_semaphore_usage` gauge
- 添加预警：使用率 > 80% 持续5分钟

### 期望结果
1. 3个新的Prometheus指标
2. 3条新的告警规则
3. Go和Python编译通过

### 验证方法
- `cd backend/gateway && go build ./...`
- `cd backend && python -m py_compile app/orchestration/state_manager.py`

---

## WP-18: 数据库Schema改进

### 目标
为关键外键添加ON DELETE子句，添加业务关键CHECK约束（如photon_balance >= 0），为缺少的向量列添加HNSW索引。

### 为什么重要
无ON DELETE意味着删除父记录会被FK约束阻止或留下孤立记录。无CHECK约束意味着应用bug可以直接导致负数余额。

### 需要修改的文件
- 创建新的Alembic迁移文件（`alembic revision -m "add_on_delete_and_check_constraints"`）
- 可能需要创建新的HNSW索引迁移

### 问题描述

**问题1 — ON DELETE**: 搜索schema.sql中所有没有`ON DELETE`子句的外键约束。至少为以下高频表添加：
- achievements → users (ON DELETE CASCADE)
- shop_purchases → users (ON DELETE CASCADE)  
- 其他用户数据表

**问题2 — CHECK约束**: 添加业务关键验证：
```sql
ALTER TABLE user_photon_balances ADD CONSTRAINT chk_photon_balance_non_negative CHECK (balance >= 0);
ALTER TABLE tasks ADD CONSTRAINT chk_flame_level_range CHECK (flame_level BETWEEN 0 AND 100);
```

**问题3 — HNSW索引**: 检查哪些表有embedding列但没有HNSW索引，添加：
```sql
CREATE INDEX idx_xxx_embedding_hnsw ON xxx USING hnsw (embedding vector_cosine_ops) WHERE (embedding IS NOT NULL);
```

### 期望结果
1. 新的Alembic迁移文件
2. 迁移有正确的upgrade()和downgrade()
3. `cd backend && alembic check` 无冲突

### 验证方法
- `cd backend && alembic check`
- 检查迁移文件的SQL语法

---

## WP-19: 废弃代码清理 + 测试/CI配置

### 目标
删除确认无活跃引用的废弃代码，提升测试覆盖率阈值，修复CI跳过Go lint的问题。

### 为什么重要
762行废弃工具代码增加维护负担。Go Gateway 10%的覆盖率阈值形同虚设。CI跳过go-vet意味着安全检查被绕过。

### 需要修改的文件
- **删除**: `backend/app/tools/focus_tools.py`
- **删除**: `backend/app/tools/knowledge_tools.py`
- **删除**: `backend/app/tools/milestone_tools.py`
- **删除**: `backend/app/tools/ops_tools.py`
- **删除**: `backend/app/tools/preferences_tools.py`
- **删除**: `backend/app/core/access_control.py`
- **修改**: `backend/app/core/complexity_analyzer.py` — 先修复`llm_router.py:33`的import
- **修改**: `backend/app/services/analytics/weekly_stats_service.py` — 先修复`weekly_digest_service.py:16`的import
- **修改**: `quality/coverage_thresholds.json`
- **修改**: `.pre-commit-config.yaml`

### 问题描述

**问题1 — 废弃工具文件**: 5个tool文件标记为DEPRECATED，grep确认零活跃import。直接删除。

**问题2 — 废弃模块仍被import**: 
- `complexity_analyzer.py`被`llm_router.py:33`导入 — 需要先理解llm_router如何使用它，要么迁移功能要么将import标记为temporary
- `weekly_stats_service.py`被`weekly_digest_service.py:16`导入 — 同理

**问题3 — 覆盖率阈值**: `coverage_thresholds.json`中：
- Python: 35% → 50%（渐进式）
- Go handler: 35% → 50%
- Go middleware: 无 → 40%
- Go DB: 0% → 10%
- Flutter: 15% → 25%

**问题4 — CI跳过Go lint**: `.pre-commit-config.yaml:120`中`ci: skip: [go-vet, golangci-lint]`。移除这个skip，改为在CI中安装Go。

### 期望结果
1. 5个废弃tool文件已删除
2. 废弃模块的活跃import已处理
3. 覆盖率阈值已提升
4. CI不再跳过Go lint

### 验证方法
- `cd backend && python -c "import app.services.llm_service"` — 确认删除不影响导入
- `cd backend && python -m py_compile app/services/llm_router.py`（如果修改了import）

---

## WP-20: Proto文件修复

### 目标
修复proto3中误用的`optional`关键字，添加WebSocket版本协商策略文档注释，清理PUT/PATCH歧义。

### 为什么重要
proto3的`optional`关键字语义不同于proto2，可能导致生成的代码行为不一致。WebSocket无版本协商意味着未来协议变更会导致兼容性问题。

### 需要修改的文件
- `proto/agent_service.proto`
- `proto/websocket.proto`
- `backend/gateway/internal/handler/proxy_routes.go`（PUT/PATCH路由）

### 问题描述

**问题1 — optional关键字**: `agent_service.proto:124,127`使用`optional`。proto3中所有字段默认optional（零值即为默认），显式`optional`会生成`xxxValue`包装类型。确认是否需要`hasXxx()`语义。如果不需要，移除`optional`关键字。

**问题2 — WebSocket版本**: `websocket.proto:11`有`version`字段但无协商逻辑。添加注释说明版本策略：
```protobuf
// Version negotiation: client sends preferred version, server responds with
// the highest mutually supported version. Currently only "1.0" is supported.
// Breaking changes require new version number and dual-version support period.
string version = 1;
```

**问题3 — PUT/PATCH歧义**: `proxy_routes.go:132-133`同时暴露PUT和PATCH给plans。添加注释说明为什么两者都接受，或移除PUT只保留PATCH。

### 期望结果
1. proto文件中optional关键字已评估和修复
2. websocket.proto有版本策略注释
3. proxy_routes.go有路由语义注释

### 验证方法
- proto文件语法检查
- Go和Python代码确认proto变更不影响现有功能（如果不改proto语义）

---

## 并行执行注意事项

### 绝对禁止事项
1. **不要修改不在你WP声明中的文件** — 如需修改，先提出申请
2. **不要运行`make proto-gen`** — proto生成是全局操作，由专人统一执行
3. **不要运行`alembic upgrade head`** — 数据库迁移由专人统一执行
4. **不要修改任何`.lock`文件** — pubspec.lock、go.sum等
5. **不要修改`CLAUDE.md`** — 这是项目级配置文件

### 编译验证
每个WP完成后必须运行对应层级的编译检查：
- Go: `cd backend/gateway && go build ./...`
- Python: `cd backend && python -m py_compile <modified_file>`
- Flutter: `cd mobile && flutter analyze`

### 完成标志
每个WP完成后，在项目根目录创建 `.claude/fix-progress/WP-XX.done` 文件，内容为：
```
WP-XX: [标题]
Status: DONE
Modified files: [列表]
Verification: [编译命令输出摘要]
```
