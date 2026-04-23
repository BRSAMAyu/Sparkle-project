# Sparkle 1-107 轮严格复核成果重建版

更新时间：2026-04-24  
重建时间：2026-04-23 22:10 Asia/Shanghai  
用途：在 `65-107` 原始审查文档缺失的情况下，最大化恢复此前上下文中保留下来的源码复核成果。

## 0. 重要声明

这不是 107 份原始审查报告的完整归档，也不是原始报告逐字恢复。

当前本地 Git 可恢复的原始审查文件到 `Round 64`。`65-107` 的原始报告没有在当前 Git、stash、reflog、dangling object 或 worktree 中找到。因此本文采用以下分层口径：

- `T1`：当前 `docs/audit` 中有原始报告或汇总记录，可追溯到文件。
- `T2`：原始报告缺失，但我此前已经在本对话上下文中保留了源码核验结论、文件路径和问题描述。
- `T3`：只记得方向但缺少足够文件/细节，不纳入执行清单，只作为后续重新审查提示。

本文的目标是恢复“有效成果”，不是证明“107 轮原始材料完整存在”。后续如果找回原始报告，应以本文为基线增量校正。

## 1. 当前恢复到工作区的归档

已恢复的主索引：

- `docs/audit/DEEP_AUDIT_SUMMARY.md`

已恢复的审查文件范围：

- 早期主链路审查：`Round 1-20`
- 之后保留下来的局部审查：`Round 46-64` 的一部分，以及若干复核/补审文件
- 当前 `DEEP_AUDIT_SUMMARY.md` 汇总到 `Round 64`

当前缺失但上下文仍有结构化复核结论的范围：

- `Round 65-107`
- 其中 `Round 81-107` 的问题点、文件路径和修复方向保存较完整

## 2. 已确认修复、降级或应剔除的旧结论

这些结论不应继续作为原始 P0/P1 直接派工：

- `Theater 预测 IDOR`：已修复。`backend/app/services/theater/prediction_theater_service.py` 关键路径使用 `_get_prediction_for_user_or_raise(prediction_id, user_id=...)`。
- `Execution Schedule check_url SSRF`：已修复。`backend/app/services/execution_schedule_service.py` 对 `check_url` 使用 `validate_external_url(...)`。
- `Internal file processing token fail-open`：已修复。`backend/app/api/v1/files.py` 的 `verify_internal_token()` 在缺少内部 key 时 fail-closed。
- `Gateway distributed rate limiter ms/sec`：已修复。`backend/gateway/internal/middleware/distributed_rate_limiter.go` 已按 `elapsedMs / 1000.0` 计算。
- `LLM 安全层零接入`：不再成立。`backend/app/services/llm_service.py` 已接入 `refresh_llm_safety_mode`、`wrap_user_message`、`wrap_tool_result`；剩余工作是覆盖率和统一验收。
- `Photon 管理员调整分离提交`：按当前 `get_db()` 请求事务模型和 `PhotonService.external_transaction_managed` 行为，原 P0 表述不成立。
- `Adaptive Replanner 零 EventBus`：说法过重，当前链路至少有部分事件；应改为“事件覆盖不完整/ outcome 事件缺口”。
- `_recently_triggered` 时区比较 bug：此前核验为不成立。
- `refresh token 缺少轮换`、`community_context 从未注入 prompt`、`Social -> Router 管道不存在`：此前复核为不成立或已过时。
- `WebSocket Proxy token query string`：部分路径曾真实存在，但恢复到的后续审计显示部分代理已修；后续必须按具体代理路径重新验收。
- `STT provider finally close 全局 provider`：后续恢复汇总显示已修复，保留回归测试即可。
- `FastAPI route handlers P0`：后续恢复汇总显示若干 P0 已修复，剩余按 P1/P2 复验。

## 3. 全项目剩余主修复面

### A. 权限与所有权边界

#### A1. 胶囊系统越权读写

可信度：`T2`

相关文件：

- `backend/app/services/curiosity_capsule_service.py`
- `backend/app/services/capsule_share_service.py`

确认问题：

- `mark_as_read()` 仍存在过直接 `db.get(CuriosityCapsule, capsule_id)` 的路径，没有按 `user_id` 收口。
- `share_to_group()` / `share_to_friend()` 只校验胶囊存在，不校验胶囊归属。

修复方案：

- 所有胶囊读写统一使用 `capsule_id + current_user_id` 查询。
- 建立 `get_capsule_for_owner_or_404()` 之类 helper，禁止 service 内裸 `db.get()`。
- 增加非 owner 标记已读、分享群组、分享好友的回归测试。

验收标准：

- A 用户不能读取、标记、分享 B 用户胶囊。
- 越权返回 403 或 404，且不改变计数和状态。

#### A2. 社区高级功能越权

可信度：`T2`

相关文件：

- `backend/app/services/community_advanced_service.py`

确认问题：

- `ForwardService.forward_message()` 未校验调用者是否有权读取源消息。
- `ReportService.review_report()` 未校验 reviewer 角色。
- `ReportService.create_report()` 与 `FavoriteService.add_favorite()` 未校验目标消息可见性。
- `BroadcastService.create_broadcast()` 存在 N+1 管理员检查。

修复方案：

- 建统一 `assert_message_access(user_id, message_id)`，覆盖群组消息和私聊消息。
- 举报审核必须验证管理员/版主角色。
- 收藏、举报、转发必须先校验可见性，再产生副作用。

验收标准：

- 用户不能收藏、举报、转发不可见消息。
- 非审核角色不能更新举报状态。

#### A3. 实验系统 ownership 缺失

可信度：`T2`

相关文件：

- `backend/app/api/v1/experiments.py`

确认问题：

- `get/start/pause/resume/complete/analyze` 等端点只按 `experiment_id` 读取对象。
- 普通用户可能操作他人实验，除非路由层另有未见的统一管理员限制。

修复方案：

- 普通用户只能操作 `created_by == current_user.id` 的实验。
- 管理员权限显式通过 admin dependency。
- 生命周期操作全部复用同一个 `get_experiment_for_actor()`。

验收标准：

- A 用户无法读取、启动、暂停、恢复、完成、分析 B 用户实验。

#### A4. 全局调度 tick 暴露给普通登录用户

可信度：`T2`

相关文件：

- `backend/app/api/v1/executions.py`

确认问题：

- `tick_execution_schedules()` 声明了 `current_user`，但随后 `del current_user`，等价于任意登录用户可触发全局调度。

修复方案：

- 改为 admin dependency 或内部 task token。
- 如果保留 HTTP 入口，应仅允许内部调用。

验收标准：

- 普通登录用户调用返回 403。

#### A5. Presence 枚举

可信度：`T2`

相关文件：

- `backend/app/api/v1/monitoring.py`

确认问题：

- `/online/{user_id}` 允许任意登录用户查询任意用户在线状态。

修复方案：

- 仅允许查询自己、好友、同群成员，或管理员。

验收标准：

- 非关系用户无法枚举他人在线状态。

#### A6. Agent Graph V2 条件性匿名风险

可信度：`T2`

相关文件：

- `backend/app/api/v2/agent_graph.py`

确认问题：

- `api/v2/agent/chat` 曾存在硬编码 `user_id = "test_user"`，认证依赖被注释。
- 默认 `ENABLE_AGENT_GRAPH_V2=False`，因此是条件性风险。

修复方案：

- 启用 flag 前必须恢复 auth dependency。
- 禁止硬编码测试用户进入生产路径。

验收标准：

- flag 开启时未认证请求不能进入 chat。

### B. 内部接口、WebSocket 与跨服务信任边界

#### B1. Signal Push 内部接口 fail-open

可信度：`T2`

相关文件：

- `backend/gateway/internal/handler/signal_push.go`

确认问题：

- `InternalAPIKey == ""` 时放行。
- key 比较使用普通 `==`，不是常量时间比较。

修复方案：

- 非 dev 环境强制配置 `INTERNAL_API_KEY`。
- 使用常量时间比较。
- 启动阶段 fail-fast。

验收标准：

- 生产环境缺 key 无法启动或请求一律 503/401。

#### B2. Gateway 配置危险默认

可信度：`T2`

相关文件：

- `backend/gateway/internal/config/config.go`

确认问题：

- 非开发环境没有强制 `INTERNAL_API_KEY`。
- `REDIS_FAIL_CLOSED` 只在未设置时强制 true，显式 false 仍可进入非 dev 环境。

修复方案：

- prod/staging 下禁止内部 key 为空。
- prod/staging 下禁止 Redis fail-open，除非显式 break-glass 且有日志告警。

验收标准：

- CI/启动测试覆盖危险配置。

#### B3. WebSocket 根路由边界不一致

可信度：`T2`

相关文件：

- `backend/gateway/cmd/server/setup.go`

确认问题：

- `/ws/chat`、`/ws/files`、`/ws/stt`、community WS routes 注册在 root router。
- 这些路径未统一经过 HTTP API rate limiter/timeout 链。
- 部分 WS 自身有连接/消息级保护，因此不是“零保护”，而是边界不一致。

修复方案：

- 统一 WS middleware：origin、连接数、read limit、idle timeout、ping/pong、指标。
- 明确哪些 HTTP middleware 对 WS 不适用，哪些必须补到 WS 专用链。

验收标准：

- 所有 WS 入口都有同等安全边界和监控指标。

#### B4. Community WS token 和连接治理

可信度：`T2/T1`

相关文件：

- `backend/gateway/internal/handler/websocket_proxy.go`

确认问题：

- 早期复核中发现 token 被拼到 backend query string。
- 后续恢复到的 `Round 50` 显示这部分可能已修或部分过时。
- 社区 WS proxy 仍需验收 read deadline、pong handler、ping ticker、idle timeout、per-user 连接数、空 Origin、close 指标。

修复方案：

- 后端社区 WS 支持 `Authorization` 头透传，禁止 query token fallback。
- 复用 `/ws/chat` 的 deadline/ping-pong/idle timeout 模式。
- 增加 per-user connection limit。

验收标准：

- token 不出现在 URL、日志、proxy target。
- 僵尸连接会被清理。

#### B5. STT WebSocket origin

可信度：`T2`

相关文件：

- `backend/gateway/internal/handler/stt_handler.go`

确认问题：

- `CheckOrigin` 曾直接 `return true`。
- 后续恢复到 `Round 63` 显示 STT provider close 问题已修，但 origin 仍需独立确认。

修复方案：

- 使用与主 WS 一致的 origin allowlist。

验收标准：

- 非允许 origin 无法建立 STT WS。

#### B6. Flutter WebSocket Client 高优先级问题

可信度：`T1`

相关文件：

- `mobile/lib/...` Flutter WS 相关文件

恢复索引确认：

- `Round 56` 显示 4 个 P0 均确认，需 mobile team 排期。

确认问题：

- Legacy 连接状态过早标记。
- Community WS 存在短窗口竞态。
- Community token URL 明文暴露。
- ChatRepository 每次 build 新建 WS 实例。
- 401 检测过宽、心跳失败广播、枚举重复、dispose 顺序错误也应纳入。

修复方案：

- WS 生命周期从 widget build 中剥离。
- token 通过 header/安全握手传递。
- 建统一连接状态机和 dispose 顺序。

验收标准：

- rebuild 不新建连接。
- 断线、401、心跳失败、前后台切换可预测。

### C. 事务、并发、幂等与状态一致性

#### C1. SignalHub map 并发竞态

可信度：`T2`

相关文件：

- `backend/gateway/internal/service/signal_hub.go`

确认问题：

- `Send()` 在释放读锁后遍历 `map[JSONWriteCloser]struct{}`。
- `Unregister()` 可并发修改同一 map。

修复方案：

- 锁内复制连接 slice，解锁后发送。
- 或保证整个 map 遍历在锁保护下，但发送不能长时间阻塞锁。

验收标准：

- `go test -race` 不再报 map 并发读写。

#### C2. Companion / Outcome 状态晋升缺事务和乐观锁

可信度：`T2`

相关文件：

- `backend/app/services/companion_state_service.py`
- `backend/app/services/outcome_promotion_governor.py`

确认问题：

- `write_session_state()` 多层状态 read-modify-write，无 optimistic locking。
- `apply_learning_report()` 先写 session，再分开 episode/profile promotion，没有统一事务边界。
- profile ledger 计数存在全量加载。
- `_upsert_learning()` 静默截断到最后 50 条。

修复方案：

- 引入版本字段或 compare-and-swap。
- session/episode/profile promotion 使用统一事务或幂等 outbox。
- 截断策略显式化并可审计。

验收标准：

- 并发学习报告不会丢写或覆盖。

#### C3. Recommendation Feedback / Preference 调优丢写

可信度：`T2`

相关文件：

- `backend/app/services/recommendation_feedback_service.py`

确认问题：

- `_apply_user_tuning()` 读偏好、merge、update，没有版本保护。
- `get_global_adjustments()` 全表扫描近期 `UserItemInteraction`。
- `_load_recent_interactions()` 无 LIMIT。
- `get_feedback_insights()` 循环重复加载 recent interactions。

修复方案：

- Preference Center 增加版本号或 JSONB CAS patch。
- recent interactions 加 LIMIT。
- 全局统计下推 SQL 聚合。

验收标准：

- 并发反馈不会互相覆盖。

#### C4. Execution Service 幂等键随机化

可信度：`T2`

相关文件：

- `backend/app/services/execution_service.py`

确认问题：

- `_build_idempotency_key()` 拼接随机 uuid 后缀，无法真正幂等。
- 类级 `_failure_counts`、`_degraded_users` 状态跨请求/用户/进程生命周期共享。

修复方案：

- 幂等键改为 `plan_id/task_id/operation_kind/request_scope` 等稳定组合。
- 故障状态按用户/计划维度持久化或放入受控缓存。

验收标准：

- 同一请求重放不会重复执行副作用。

#### C5. BehaviorSignalCollector 可靠性

可信度：`T1/T2`

相关文件：

- `backend/app/services/behavior_signal_collector.py`
- `backend/app/services/task_event_consumer.py`

确认问题：

- 事件 dict 的 `UUID(str(event["user_id"]))` 等入口缺少校验，异常会直接打断消费路径。
- Redis 冷却失败策略曾存在 fail-open 或降级不足。
- `_maybe_emit_pattern_adjustment()` 需要与其它信号一样有 cooldown。
- `handle_behavior_pattern_event()` 在循环里 replanner 成功后 bridge 失败会 `db.rollback()`，可能撤销前面计划的 replanner 变更。
- `intervention_created=False` 时 replanner 变更可能不提交。
- 每个事件都新建 collector 和多个子服务，热路径对象创建偏重。

修复方案：

- 入口事件 schema 校验，非法事件 ack 到 dead-letter 或记录后跳过。
- Redis 不可用时 fail-soft：本地 TTLCache 或跳过重计算，不能每事件全量运行。
- 每个 plan iteration 使用 savepoint。
- replanner 变更和 intervention bridge 解耦提交。

验收标准：

- Redis 故障不会造成认知片段洪泛。
- 单个 bridge 失败不回滚其它计划成功调整。

#### C6. A/B Experiment 并发和状态一致性

可信度：`T2`

相关文件：

- `backend/gateway/internal/middleware/ab_test_middleware.go`
- `backend/app/services/ab_test_framework_enhanced.py`
- A/B experiment models/API

确认问题：

- Go AB middleware 把 `experimentID` 直接拼入 URL。
- `recordFromContext()` 使用不安全 `variant.(*VariantInfo)` 断言。
- `assign_variant()` 使用 Python `not ABExperimentAssignment.is_excluded`，不是 SQLAlchemy `~`。
- `start_experiment()` 无状态预检查，可重复启动覆盖 `start_date`。
- `assign_variant()` 不校验实验状态。
- `create_experiment()` 先 flush experiment 再 variants，commit 后置，中间状态不一致。
- `record_metric()` 每条 metric commit。
- 缺少 `(experiment_id, user_id)` 唯一约束。

修复方案：

- URL 参数 encode / path safe join。
- 类型断言使用 checked assertion。
- 修正 SQLAlchemy 条件。
- 实验状态机集中管理，分配只允许 running。
- 增加唯一约束和 upsert。

验收标准：

- 并发分配同一用户不会生成重复 assignment。

### D. 配额、计费、积分与经济系统

#### D1. Quota/Billing 双轨账本

可信度：`T2`

相关文件：

- `backend/gateway/internal/service/quota.go`
- `backend/gateway/internal/db/scripts/reserve_quota.lua`
- `backend/app/core/llm_quota.py`

确认问题：

- `ReserveRequest()` 扣 `user:quota:{uid}`。
- `RecordUsage()` 累加 `llm_tokens:{uid}:{date}`。
- 两者没有自动对账。
- `reserve_quota.lua` 把 missing quota 当 0，未初始化用户会被拒。
- `queue:sync:quota` 只有 producer，未见 consumer。
- Python `check_quota()` 是非原子 check-then-increment。

修复方案：

- 明确单一账本：reservation + settlement 或 usage counter 二选一。
- quota 初始化前移到用户创建/套餐变更。
- 删除死队列或补 reconciliation worker。
- Python quota 改为 Redis Lua/事务。

验收标准：

- 异常中断后 quota 能退还或结算。

#### D2. Photon 经济系统

可信度：`T2`

相关文件：

- `backend/app/services/photon_service.py`
- `backend/app/api/v1/photons.py`
- `backend/app/services/shop_service.py`

确认问题：

- `get_transaction_summary()` 把交易加载到 Python 聚合。
- `transfer_photons()` 对双方余额行加锁顺序不固定，反向转账有死锁风险。
- `/transfer` 返回硬编码 placeholder UUID。
- `_update_balance()` 在 commit 前失效缓存，回滚时可能产生脏空缓存。
- `deduct_photons()` 先查缓存余额，再行锁扣款，前置检查认知分裂。
- `ShopService.get_available_items()` ownership 检查 N+1。
- `ShopService.purchase_item()` 绕过统一扣款层，直接更新余额并手写购买交易。

修复方案：

- summary 改 SQL `SUM/COUNT/GROUP BY`。
- 转账按 `sorted(user_id)` 固定锁顺序。
- 返回真实 transfer transaction id。
- 缓存失效放到 after-commit。
- Shop 购买复用统一扣款接口。

验收标准：

- 并发转账不死锁、不重复扣款。
- 余额、交易、物品状态一致。

#### D3. Chat/LLM 配额估算和预留

可信度：`T1`

相关恢复轮次：

- `Round 47`
- `Round 53`

确认问题：

- ChatOrchestrator 配额预留失败/异常后不退还。
- token 估算对 CJK 偏差大。
- Go Chat Orchestrator 存在 CJK 配额估算偏低、速率限制默认值过激、goroutine 脱离 context、SHA-1 hash 碰撞等问题。

修复方案：

- 对配额 reservation 建 refund/finalize 机制。
- 使用 tokenizer 或语言感知估算。
- goroutine 继承 request context。
- 哈希改 SHA-256 或带命名空间的稳定键。

验收标准：

- 失败请求不消耗用户额度。

### E. LLM 安全、Prompt 注入、输出约束与错误泄露

#### E1. Predictive 输出动作无白名单

可信度：`T2`

相关文件：

- `backend/app/services/predictive_service.py`

确认问题：

- `_merge_prediction_payload()` 接受任意 `predicted_action_type`。
- realtime forecast path 缺用户级并发 guard。
- API 层 `detail=str(e)` 广泛存在。
- `/dashboard` 串行调用重方法。

修复方案：

- 建 action enum whitelist，不合法回退 rule-based default。
- 每用户预测刷新加 lock。
- API 层统一 safe error。

验收标准：

- LLM 不能返回任意 action 驱动后续流程。

#### E2. Expansion prompt injection

可信度：`T2`

相关文件：

- `backend/app/services/expansion_service.py`

确认问题：

- `_build_expansion_prompt()` 将 context JSON 内容直接拼入 prompt。
- `_find_semantic_duplicate()` 全表向量搜索无过滤。
- `_create_expanded_nodes()` 可能部分写入。
- `record_feedback()` `asyncio.create_task` fire-and-forget。
- relation 路径有 N+1。

修复方案：

- 结构化上下文，不裸拼自然语言。
- context 字段长度限制、字符净化。
- 向量去重加 user/domain/subject 过滤。
- feedback refresh 改 outbox/job。

验收标准：

- 用户内容不能突破 prompt 边界。

#### E3. Prompt Assembly / Response / Plan Review

可信度：`T1/T2`

相关文件：

- prompt assembly 相关模块
- plan review service
- response builder / UX envelope

确认问题：

- `format_map` 值未消毒。
- Graph 节点零上下文。
- error summary / recent errors 死数据。
- token 预算 `len/4` 粗糙。
- 模板重复、i18n 缺失。
- Plan Review 审核提示词裸拼接、背景偏见式可行性规则、审核结果事件缺口。

修复方案：

- prompt var 统一 sanitizer。
- Graph/error context 必须有注入验收测试。
- 审核结果发布统一 outcome event。
- token 预算改 tokenizer 或语言感知估算。

验收标准：

- Prompt 中所有用户可控字段均带边界和净化。

#### E4. 统一错误泄露

可信度：`T1/T2`

典型文件：

- `backend/app/api/v1/predictive_analytics.py`
- `backend/app/api/v1/leaderboards.py`
- `backend/app/api/v1/recommendations.py`
- `backend/app/api/v1/experiments.py`
- `backend/app/api/v1/ingestion.py`
- `backend/app/services/agent_grpc_service.py`

确认问题：

- API 层多处 `detail=str(e)`。
- Agent gRPC service 曾有 29 处 `str(e)` 泄露。

修复方案：

- 建统一 `safe_http_error()` / `internal_server_error()`。
- 对外稳定错误码，对内 log exception。

验收标准：

- 500 响应不包含内部异常、SQL、路径、provider 错误细节。

#### E5. Notification evidence token 暴露

可信度：`T2`

相关文件：

- `backend/app/services/notification_center_service.py`

确认问题：

- `_system_to_unified()` 把 `push_record.evidence_token` 返回给客户端 metadata。

修复方案：

- evidence token 仅保留内部审计链路，用户 payload 删除。

验收标准：

- 客户端通知 payload 不含内部 token。

### F. 全量扫描、N+1 与热路径性能

#### F1. Review History / Feedback Learning

可信度：`T2`

相关文件：

- `backend/app/services/review_history_service.py`
- `backend/app/services/feedback_learning_service.py`

确认问题：

- `export_learning_data()` 全表加载。
- `get_aggregation()` / `get_review_trends()` 拉 range rows 到 Python 聚合。
- `_review_history_services` 全局 dict cache 泄漏 session。
- `record_review()` 存储无界 `content_snapshot` 和 `user_query`。
- `get_misclassified_reviews()` 逻辑矛盾，普通 satisfied feedback 下条件不可达。
- `analyze_and_learn()` 使用全局最近 1000 条审查/反馈，无用户/租户隔离。
- `_apply_high_confidence_adjustments()` 只改内存，重启丢失。
- `analyze_execution_quality()` 用全零 UUID。

修复方案：

- 统计下推 SQL。
- 增加用户/租户边界。
- 学习调整持久化。
- 全局 service cache 改 request-scoped。

验收标准：

- 大数据量下导出/聚合不 OOM。

#### F2. Notification Center

可信度：`T1/T2`

相关文件：

- `backend/app/services/notification_center_service.py`

确认问题：

- `get_unified_notifications()` 先对 system/intervention/push 分源分页，再合并，分页语义错误。
- `mark_all_notifications_read()` 热路径逐条写交互/动作更新。
- `_find_notification_for_record()` 全量扫 intervention notifications。
- 部分问题后续已修，如 bulk update、LIKE escape、time_to_action。

修复方案：

- 统一 SQL/CTE 或游标聚合后分页。
- mark-all-read 批量 update。
- record id 建索引或直接查询。

验收标准：

- 分页稳定，无重复/遗漏。

#### F3. Friend Match / Recommendation

可信度：`T2`

相关文件：

- `backend/app/services/friend_match_service.py`
- `backend/app/services/recommendation_feedback_service.py`

确认问题：

- `_load_accountability_state()` 加载所有 CORE pending/active partnerships 后 Python 过滤。
- `_load_public_candidates()` 排除逻辑主要在 Python。
- `_get_cached_recommendations()` `hit_count` 非原子。
- recommendation feedback recent interactions 无 LIMIT。

修复方案：

- 候选过滤下推 SQL。
- hit count 原子 update。
- recent interactions 限制窗口和数量。

验收标准：

- 候选池大时接口延迟稳定。

#### F4. Leaderboard

可信度：`T2`

相关文件：

- `backend/app/services/leaderboard_service.py`
- `backend/app/api/v1/leaderboards.py`

确认问题：

- `_get_global_leaderboard()` 加载所有 active users 后 Python 排序。
- `get_my_rank()` 只看 top 100。
- `get_summary()` 串行拉 4 个榜。
- `refresh_leaderboard_cache` 使用普通 `get_current_user`，无 admin guard。
- API 暴露 `str(e)`。

修复方案：

- 排名下推 SQL/window function。
- my_rank 用 rank query。
- summary 并发或缓存。
- refresh-cache 加 admin/internal guard。

验收标准：

- top N 和 my rank 在大用户量下准确。

#### F5. Insight / Perceptible / Idiographic / PersDyn

可信度：`T2`

相关文件：

- `backend/app/services/perceptible_intelligence_service.py`
- `backend/app/services/user_insight_compiler.py`
- `backend/app/services/idiographic_association_service.py`
- `backend/app/services/persdyn_attractor_service.py`

确认问题：

- task duration comparison 加载完整 Task 对象。
- weekly report active users 串行处理。
- Redis 异常时 `_session_has_sent_insight()` 返回 true，导致洞察停发。
- `_score_scenarios()` 使用 server-local `datetime.now().hour`。
- `compile()` 在 post-calibration refresh 可能重复分析/预测。
- `_apply_calendar_signals()` 28 天窗口无 LIMIT，跨夜事件小时展开有误。
- accountability signals 缺 deleted filter。
- idiographic 全用户重算串行。
- `_effective_window_days()` 可能被最近 changepoint 过度截短。
- persdyn task query 无下界，plan adherence 分母用全历史 plan tasks。

修复方案：

- 只 select 必需字段。
- user-level job queue。
- Redis failure fail-open/降级而非停发。
- 使用用户时区。
- 时间窗口和软删除过滤统一。

验收标准：

- 周报和洞察生成可并发、可恢复、时区正确。

#### F6. Metacognition

可信度：`T2`

相关文件：

- `backend/app/services/metacognition_service.py`

确认问题：

- `_collect_completion_bias_rows()` / `_collect_mastery_bias_rows()` 使用 `generated_at.asc().limit(60)`，取 oldest 60。
- `_build_dashboard_card()` 对模板使用 `next(...)` 无 fallback，可能 `StopIteration`。

修复方案：

- 改为 `desc().limit(60)` 再按需要排序。
- 模板缺失时 fallback。

验收标准：

- 新数据优先进入分析。

### G. 上传、文档、静态资源与文件链路

#### G1. File Handler / Upload

可信度：`T1/T2`

相关文件：

- `backend/gateway/internal/handler/file_handler.go`
- file upload/storage 相关路径

确认问题：

- `validateFileByMagicBytes()` 有实现但曾未进入生产调用。
- File Handler 审查恢复显示 SVG stored XSS、bucket 泄露、幽灵文件、fire-and-forget 处理、非原子删除。

修复方案：

- CompleteUpload 后进入后台处理前做 magic bytes。
- SVG 禁用或 sanitize。
- 删除、DB、对象存储通过事务/outbox 保证最终一致。

验收标准：

- 伪装文件类型无法通过。

#### G2. Document / Ingestion

可信度：`T2`

相关文件：

- `backend/app/api/v1/ingestion.py`
- `backend/app/api/v1/router.py`
- `backend/app/services/document_service.py`
- `backend/app/services/file_processing_orchestrator.py`

确认问题：

- `/clean` 和 `/clean/{task_id}` 无 auth dependency。
- `ingestion.router` 同时挂到 `/documents` 和 `/ingestion`。
- `_resolve_allowed_path()` `return None` 后挂着 `_generate_quick_summary` / `_extract_section_summary` / `extract_vector_chunks` 等死代码。
- 路径校验使用 `".." in file_path`，误杀合法文件名。
- `_store_chunks()` 每 16 个 chunk commit，中途失败产生部分嵌入写入。

修复方案：

- 清洗端点加 auth。
- 路由挂载收敛。
- 死代码移出或恢复为类方法。
- 使用 `Path.resolve()` 做路径边界校验。
- chunk 写入用单事务或 job-level compensation。

验收标准：

- 未认证不能清洗文档。
- 处理失败不会留下半索引文档。

#### G3. Public uploads

可信度：`T2`

相关文件：

- `backend/app/main.py`

确认问题：

- `/uploads` 静态挂载公开。

修复方案：

- 区分 public assets 和 private user documents。
- 私有文件走鉴权下载或签名 URL。

验收标准：

- 直接访问私有上传路径失败。

### H. 异步可靠性、事件总线和后台任务

#### H1. Redis EventBus / Task Queue

可信度：`T1`

相关恢复轮次：

- `Round 3`
- `Round 33`

确认问题：

- 主 stream 仍需 maxlen。
- pending reclaim / XAUTOCLAIM 不完整。
- lock fail-open 风险。
- Celery Beat 缺失、日期比较 bug、嵌套 `asyncio.run`、event loop 竞态等需要重新源码核验。

修复方案：

- Redis stream 使用 maxlen approximate trimming。
- consumer group 增加 pending reclaim。
- 分布式锁 fail-closed 或明确降级策略。
- Celery 调度和 async 桥接重构。

验收标准：

- consumer crash 后 pending 事件可恢复。

#### H2. Expansion feedback fire-and-forget

可信度：`T2`

相关文件：

- `backend/app/services/expansion_service.py`

确认问题：

- `record_feedback()` 使用 `asyncio.create_task` 刷新 galaxy feedback signals。

修复方案：

- 改 outbox / queue / retryable job。

验收标准：

- 后台失败可重试、可观测。

#### H3. Profile Event Consumer

可信度：`T1`

相关文件：

- profile event consumer 相关路径

恢复索引确认：

- `Round 64` 新审：consumer_name 不固定、focus/error 不清缓存。

修复方案：

- consumer name 稳定化或明确多实例语义。
- focus/error 事件触发 profile context cache invalidation。

验收标准：

- 重启不会导致不可预期重复消费。

### I. Group Chat / Community / Search

#### I1. Group Chat Handler

可信度：`T2`

相关文件：

- `backend/gateway/internal/db/query.sql.go`
- `backend/gateway/internal/handler/group_chat.go`

确认问题：

- `GetGroupMessages` reply join 没有 `rm.deleted_at IS NULL`，被删除的 replied message 可能泄露。
- `IsGroupMember` 只检查存在，不检查 status。
- handler 分页参数无 sanity cap。
- reply join 未确保 `rm.group_id = gm.group_id`。
- `content_data` 被 select 但 JSON 响应丢弃。

修复方案：

- reply join 加 `rm.deleted_at IS NULL` 和同 group 条件。
- membership 查询加入 status/deleted filter。
- limit/offset clamp。
- 明确 content_data 是否返回。

验收标准：

- 删除消息不会经 reply 泄露。

#### I2. Community Search

可信度：`T2`

相关文件：

- `backend/app/services/community_advanced_service.py`

确认问题：

- `MessageSearchService` 使用 `to_tsvector('simple')`，中文搜索质量差。

修复方案：

- 中文分词或 fallback trigram/ILIKE 策略。

验收标准：

- 中文关键词可检索。

### J. API 边界、代理和中间件

#### J1. Client Telemetry 匿名写入

可信度：`T2`

相关文件：

- `backend/gateway/internal/handler/proxy_routes.go`
- `backend/app/api/v1/client_telemetry.py`

确认问题：

- `POST /api/v1/client-telemetry/events` 和 `/batch` 不走 auth middleware。
- 后端使用 `get_optional_current_user`。

修复方案：

- 生产写入要求 auth 或受控匿名设备 token。
- rate limit 和 body size limit。

验收标准：

- 匿名请求不能刷写 telemetry。

#### J2. REST Proxy routes

可信度：`T1`

相关恢复轮次：

- `Round 59`

确认问题和状态：

- DataConsistencyHandler 无认证、NoRoute auth 通配符代理、X-Forwarded 缺失等 P0 后续显示已修。
- 仍需验收未代理 Python 路由、Any 通配符、全局 body size、A/B 中间件同步 HTTP 等降级项。

修复方案：

- 保持白名单代理。
- 明确 body limit。
- A/B 中间件异步或缓存化。

验收标准：

- 未列入白名单的路由不会被 proxy 绕过认证。

#### J3. FastAPI Middleware / DI

可信度：`T1`

相关恢复轮次：

- `Round 62`

确认问题和状态：

- `blacklist_token NameError` 已修。
- `get_db_context asyncio.run` 仍确认。
- BaseHTTPMiddleware、JWT 双重解码、get_db commit/WAL 写放大等需要逐项复验。

修复方案：

- async context manager 不使用 `asyncio.run`。
- 请求事务边界统一。

验收标准：

- 异步环境中不会因为 nested loop 崩溃。

### K. STT、gRPC、Agent Bridge

#### K1. STT

可信度：`T1/T2`

相关文件：

- `backend/app/services/stt_service.py`
- `backend/gateway/internal/handler/stt_handler.go`

确认问题和状态：

- 恢复索引显示 STT provider finally close 和错误文本泄露已修。
- Gateway STT origin 仍需验收。

修复方案：

- provider lifecycle 回归测试。
- origin allowlist。

#### K2. gRPC client circuit breaker

可信度：`T1`

相关恢复轮次：

- `Round 49`

确认问题：

- health check 使用 `StreamChat` 完整 FSM。
- `RESOURCE_EXHAUSTED` 重试。
- `WithBlock` 启动阻塞。
- 流中途失败对断路器不可见。

修复方案：

- 使用轻量健康 RPC。
- 不重试资源耗尽类错误。
- breaker 统计 stream mid-flight failures。

验收标准：

- 上游异常能正确打开/半开/关闭断路器。

#### K3. Agent gRPC service

可信度：`T1`

相关恢复轮次：

- `Round 55`

确认问题：

- `UnboundLocalError` 崩溃。
- `finish_reason STOP` 被当 ERROR 的跨轮问题。
- `SubmitPlanReview` 多 DB session。
- context 取消不检查。
- 多处 `str(e)` 泄露。
- limit 无上限。
- `grpc_auth` 交叉验证可绕过。

修复方案：

- 修正变量初始化和 finish_reason mapping。
- 单请求 DB session 策略。
- 尊重 context cancellation。
- safe error。
- limit clamp。
- auth 双端一致。

验收标准：

- STOP 不触发错误态。
- 未授权 gRPC 调用失败。

## 4. 轮次重建摘要

### 已恢复到 Git 的重要轮次

- `Round 47`：ChatOrchestrator chatflow，配额不退还、CJK token 估算偏差。
- `Round 48`：File Handler，SVG XSS、bucket 泄露、幽灵文件、fire-and-forget、非原子删除。
- `Round 49`：gRPC client/circuit breaker，health probe 和 breaker 可观测性。
- `Round 50`：WebSocket Proxy，部分旧 token/query 说法过时，但 per-user 连接数、空 Origin、指标仍需处理。
- `Round 51`：Gateway middleware，TrustedProxies、CSP、WS 路由绕过仍需验收。
- `Round 52`：UX Envelope，P0 内存泄漏已修，schema/metadata/i18n/类型安全仍需处理。
- `Round 53`：Go Chat Orchestrator，legacy 反馈并发写、health probe、限流、CJK、SHA-1、goroutine context。
- `Round 54`：Prompt Assembly，prompt injection、Graph 零上下文、error data 死代码。
- `Round 55`：Agent gRPC，STOP 非 ERROR、auth、str(e)、limit。
- `Round 56`：Flutter WS Client，4 个 P0 全部确认。
- `Round 57`：Notification Center，部分已修，仍需分页/N+1/token payload 验收。
- `Round 58`：BehaviorSignalCollector，UUID 校验、冷却策略、pattern adjustment。
- `Round 59`：Go REST Proxy，3 个 P0 已修，剩余降级项需验收。
- `Round 60`：FastAPI route handlers，P0 已修，剩余 P1/P2 需验收。
- `Round 61`：ProfileContextService，部分 false/已修，P1-1 确认。
- `Round 62`：FastAPI Middleware/DI，logger 已修，`asyncio.run` 确认。
- `Round 63`：STT，两个 P0 已修。
- `Round 64`：Profile Event Consumer，consumer name 和 cache invalidation。

### 上下文重建的 `65-107` 有效成果

- `Round 67`：`tick_execution_schedules` 任意登录用户可触发，确认成立。
- `Round 78`：`validateFileByMagicBytes()` 死代码，确认成立。
- `Round 79`：STT 服务单例/provider lifecycle 曾为问题，后续部分已修；Gateway STT origin 仍需验收。
- `Round 80`：社区 WS proxy idle/ping-pong 需按当前代码重新验收。
- `Round 81`：Internal API auth fail-open，确认成立于 Signal Push。
- `Round 82`：Config validation 部分成立，保留 internal key 和 redis fail-closed 两点。
- `Round 83`：Quota/Billing 双轨账本、orphan queue、Python quota 非原子。
- `Round 84`：SignalHub map 并发竞态。
- `Round 86`：Group Chat deleted reply 泄露、成员状态校验不足、分页无上限。
- `Round 87`：Predictive 并发、action whitelist、`str(e)`。
- `Round 88`：Companion 状态写入无乐观锁、firewall 英文关键词、evidence 归一化过窄。
- `Round 89`：Friend Match 全量 partnership 扫描、候选过滤后置、cache hit 非原子。
- `Round 90`：Metacognition oldest-60 与 template `StopIteration`。
- `Round 91`：Execution Service 类级故障状态与随机幂等键。
- `Round 92`：Notification Center 分源分页、N+1、evidence token 暴露。
- `Round 93`：Perceptible task full-load、周报串行、Redis fail-closed 停发。
- `Round 94`：Feedback Learning / Review History 自身数据面问题。
- `Round 95`：Insight Compiler 重复分析、calendar 全量加载、软删除过滤缺失。
- `Round 96`：Leaderboard 全量排序、`my_rank` top100、summary 串行、refresh-cache 无 admin。
- `Round 97`：Expansion 全表向量去重、部分提交、prompt 注入、fire-and-forget。
- `Round 98`：Idiographic / PersDyn 历史任务无界、窗口裁剪、plan adherence 分母错误。
- `Round 99`：Outcome Promotion 无乐观锁、无统一事务。
- `Round 100`：Recommendation Feedback 全表扫描、并发丢写、无 LIMIT、API 输入/错误边界薄弱。
- `Round 101`：Document Service 死代码、无认证、双挂载、批次提交。
- `Round 102`：Community Advanced 转发/举报/收藏权限边界问题。
- `Round 103`：Review History 全表导出/聚合、global service cache 泄漏。
- `Round 104`：Experiment API ownership 缺失、Gateway experimentID URL 直拼。
- `Round 105`：AB framework `assign_variant` Python `not`、不校验实验状态、无唯一约束。
- `Round 106`：Photon summary 全量聚合、转账死锁、placeholder transfer id；管理员调整分离提交剔除。
- `Round 107`：BehaviorSignalCollector Redis 冷却降级、事务回滚边界、14 天窗口无 LIMIT、pattern adjustment 冷却。

## 5. 执行优先级

### 第一批：安全边界和可滥用入口

1. 胶囊 ownership。
2. 社区高级功能 message access。
3. 实验 ownership。
4. 执行调度 tick admin/internal guard。
5. Signal Push internal auth fail-closed。
6. Gateway config dangerous defaults。
7. WS origin/token/连接治理。
8. `/uploads` 私有化和文档清洗鉴权。

### 第二批：账本、事务、幂等

1. Quota/Billing 单账本。
2. Photon 转账锁顺序、cache after-commit、真实 transaction id。
3. Execution idempotency key。
4. SignalHub map 竞态。
5. Companion / Outcome / Preference 乐观锁。
6. BehaviorSignalCollector savepoint 和 Redis 降级。
7. A/B assignment 唯一约束和状态机。

### 第三批：LLM 和错误边界

1. Predictive action whitelist。
2. Expansion prompt injection。
3. Prompt Assembly sanitizer。
4. Plan Review outcome event。
5. API/gRPC safe error。

### 第四批：性能和后台可靠性

1. Review History / Feedback Learning SQL 聚合。
2. Notification Center unified pagination。
3. Leaderboard window function。
4. Friend Match / Recommendation LIMIT 和 SQL filter。
5. Perceptible / Insight / Idiographic job 化。
6. EventBus / Celery / Profile Event Consumer。

### 第五批：移动端和体验层

1. Flutter WS lifecycle。
2. UX Envelope schema / metadata cap。
3. i18n 与 CJK token 估算。

## 6. 后续验收规则

- 权限问题必须有越权测试。
- 幂等问题必须有重复事件测试。
- 并发问题必须有 race/concurrent test 或事务级验证。
- 性能问题必须给出 SQL 下推、LIMIT、索引或 benchmark 证据。
- LLM 问题必须有恶意输入/prompt injection 回归样例。
- 已修复/降级项必须写入“关闭依据”，不能只从列表里删除。

## 7. 仍需重新找回或重审的缺口

这些内容不能靠上下文完整恢复，建议后续重新审查：

- `65-77` 轮的完整原始报告和所有 P0/P1 细节。
- `1-34` 早期报告中未进入当前上下文的低层细节。
- 所有当前已被其它 agent 修过的模块，需要按最新源码重新验收。
- 任何只存在于缺失原始报告中的 P2/低优先级问题，本文未完整恢复。

## 8. 使用方式

本文可以作为后续执行型 Codex 的恢复版总基线，但派工时应遵守：

- 优先派 `T1/T2` 且有明确文件路径的问题。
- 每个 worker 只拿一个工作流或一个模块。
- 修复前先在当前源码重新确认问题仍存在。
- 修复后由审查角色对照本文验收，并更新状态为 `open / fixed / false-positive / downgraded`。
