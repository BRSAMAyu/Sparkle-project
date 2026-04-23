# Sparkle 持续工程收敛进展账本

日期：2026-04-24  
当前基线：`e6d1e11d`  
工作分支：`main`（候选安全分支同步到 `codex/stage40-main-recovered-final-2026-04-24`）  

## 1. 工作口径

本账本用于承接 `1-107` 轮审查重建成果、后续新增审查、以及当前源码上的再次复核。后续每一轮只按以下口径落账：

- `CONFIRMED`：当前源码仍能复现或证明问题存在。
- `FIXED`：已完成代码修复，并记录验证命令。
- `STALE/FALSE`：审查结论已过期或当前源码不成立，并记录关闭依据。
- `DEFERRED`：问题真实存在，但需要更大架构决策或跨端排期，先保留边界和验收标准。

## 2. 主要输入

- `docs/audit/STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_RECONSTRUCTED_FROM_CONTEXT_2026-04-24_rounds_1_107.md`
- `docs/audit/STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_2026-04-24_rounds_1_107.md`
- `docs/audit/DEEP_AUDIT_SUMMARY.md`
- `docs/audit/STAGE3_40_FULL_CLOSEOUT_VERIFICATION_2026-04-24.md`
- 当前仓库源码与测试结果

## 3. 当前优先级队列

第一批先处理安全边界和可滥用入口：

1. Curiosity capsule ownership。
2. Community advanced message/report/favorite/broadcast access。
3. Experiment API ownership。
4. Execution schedule tick admin/internal guard。
5. Signal Push internal auth fail-closed。
6. Gateway config dangerous defaults。
7. WS origin/token/连接治理。
8. Upload/document/private static 边界。

后续批次按账本继续推进：账本/事务/幂等、LLM 安全、性能与后台可靠性、移动端 WS 生命周期。

## 4. Cycle 1 - 权限边界 A1

状态：`FIXED`

目标：

- 复核 `curiosity_capsule_service.py` 与 `capsule_share_service.py` 是否仍存在胶囊读取/分享 ownership 缺口。
- 若成立，补 `capsule_id + user_id` 作用域检查和越权测试。
- 运行目标测试并记录结果。

源码复核结论：

- `CONFIRMED`：`CuriosityCapsuleService.mark_as_read()` 直接按 `capsule_id` 读取，API 未传入 `current_user.id`。
- `CONFIRMED`：`CapsuleShareService.share_to_group()` / `share_to_friend()` 只验证胶囊存在，不验证分享者 ownership。

修复：

- `mark_as_read()` 改为 `user_id + capsule_id` scoped lookup，并在 API 层对非 owner 返回 404。
- 分享服务改为只查询当前用户拥有的胶囊，非 owner 与不存在统一失败。
- 新增越权回归测试：非 owner 不能标记已读、不能分享给好友、不能分享到群组。

验证：

- `pytest backend/tests/api/test_capsules_api.py backend/tests/unit/services/test_capsule_share_service.py` -> `6 passed`

## 5. Cycle 2 - 权限边界 A2

状态：`FIXED`

目标：

- 复核 `community_advanced_service.py` 的举报、收藏、转发、广播权限边界。
- 对确认存在的问题补服务层访问控制，避免未来新 API 入口绕开。

源码复核结论：

- `CONFIRMED`：`ReportService.create_report()` 不校验举报者能否看到目标消息。
- `CONFIRMED`：`ReportService.review_report()` 不校验审核者是否为目标群管理员。
- `CONFIRMED`：`FavoriteService.add_favorite()` 不校验收藏者能否看到目标消息。
- `CONFIRMED`：`ForwardService.forward_message()` 不校验转发者是否能读取源消息。
- `CONFIRMED`：`BroadcastService.create_broadcast()` 逐群查询管理员权限，存在 N+1，可一次查询收敛。

修复：

- 增加 group/private message 访问 helper：群消息要求当前用户仍是群成员；私聊消息要求当前用户是 sender 或 receiver；撤回/删除消息不可访问。
- 举报、收藏、转发统一复用访问 helper。
- 举报审核要求审核者是被举报群消息所在群的 owner/admin；当前无平台管理员模型，私聊举报暂不允许通过该群管理员服务审核。
- 广播管理员校验合并为一次查询，并对目标群去重后投递。

验证：

- `pytest backend/tests/unit/services/test_community_advanced_access.py backend/tests/api/test_capsules_api.py backend/tests/unit/services/test_capsule_share_service.py` -> `10 passed`

## 6. Cycle 3 - 权限边界 A3

状态：`FIXED`

目标：

- 复核 `backend/app/api/v1/experiments.py` 是否仍存在按实验 ID 直接访问/操作、缺 owner/admin scope 的问题。
- 若成立，补 ownership helper 和越权测试。

源码复核结论：

- `CONFIRMED`：`list_experiments()` 已按 `created_by` 过滤，但 `get/start/pause/resume/complete/stats/analyze` 仍按实验 ID 直接读取或调用 framework。
- `CONFIRMED`：实验详情 response model 声明 `id/created_by/winning_variant_id` 为 `str`，但 ORM 返回 `UUID`，会触发 FastAPI response validation error。

修复：

- 增加 `_get_owned_experiment()` helper：普通用户只能访问 `created_by == current_user.id` 的实验，superuser 可访问全部。
- 在详情、生命周期操作、stats、analyze 前统一调用 ownership helper。
- 保留 `assign`/`metrics` 作为实验参与者入口，后续随 A/B 状态机和唯一约束批次处理。
- 将实验 response model 的 UUID 字段改为 `UUID` 类型，JSON 输出仍为字符串。

验证：

- `pytest backend/tests/api/test_experiments_api_access.py backend/tests/unit/services/test_community_advanced_access.py backend/tests/api/test_capsules_api.py backend/tests/unit/services/test_capsule_share_service.py` -> `13 passed, 1 warning`

## 7. Cycle 4 - 权限边界 A4

状态：`FIXED`

目标：

- 复核 `backend/app/api/v1/executions.py` 的 schedule tick 入口是否仍允许任意登录用户触发全局调度。
- 若成立，改为 superuser 或内部可信入口，并补回归测试。

源码复核结论：

- `CONFIRMED`：`POST /executions/schedules/tick` 依赖 `get_current_user` 后直接 `del current_user`，任意登录用户可触发所有用户 due schedules。
- `CONFIRMED`：相邻的 `POST /executions/schedules/events/trigger` 同样依赖登录用户后丢弃身份，可全局触发 event schedules。

修复：

- 两个全局触发入口改为 `get_current_active_superuser`。
- route-tier 注释从 `authed` 改为 `admin`。
- 保持用户自己的 schedule CRUD 使用 `get_current_user` 和 per-user service scope，不扩大权限。

验证：

- `pytest backend/tests/unit/test_openclaw_admin_api.py::test_execution_schedule_global_triggers_require_superuser backend/tests/unit/test_openclaw_admin_api.py::test_user_execution_schedule_crud_endpoint backend/tests/api/test_experiments_api_access.py backend/tests/unit/services/test_community_advanced_access.py backend/tests/api/test_capsules_api.py backend/tests/unit/services/test_capsule_share_service.py` -> `15 passed, 1 warning`

## 8. Cycle 5 - 权限边界 A5

状态：`FIXED`

目标：

- 复核 `backend/app/api/v1/monitoring.py` 的在线状态查询是否允许任意登录用户枚举任意 user_id。
- 若成立，按 self / friend / same group / superuser 建访问边界并补测试。

源码复核结论：

- `CONFIRMED`：`GET /online/{user_id}` 只要求登录，任意用户可枚举任意 `user_id` 在线状态。
- `CONFIRMED`：`GET /stats` 对任意登录用户返回 active user IDs 和 group IDs，属于更直接的 presence/monitoring 枚举面。
- `CONFIRMED`：`GET /metrics` 属于监控内部面，原来同样只要求登录。

修复：

- 新增 `_can_view_presence()`：允许 self、superuser、accepted friend、same group member 查看 presence。
- `/online/{user_id}` 加入 DB dependency 和访问控制，未授权返回 403。
- `/stats` 与 `/metrics` 改为 `get_current_active_superuser`。
- `/health` 保持公开，用于负载均衡和基础探活。

验证：

- `pytest backend/tests/api/test_monitoring_presence_api.py backend/tests/unit/test_openclaw_admin_api.py::test_execution_schedule_global_triggers_require_superuser backend/tests/unit/test_openclaw_admin_api.py::test_user_execution_schedule_crud_endpoint backend/tests/api/test_experiments_api_access.py backend/tests/unit/services/test_community_advanced_access.py backend/tests/api/test_capsules_api.py backend/tests/unit/services/test_capsule_share_service.py` -> `20 passed, 1 warning`

## 9. Cycle 6 - 权限边界 A6

状态：`FIXED`

目标：

- 复核 `backend/app/api/v2/agent_graph.py` 是否仍存在 hardcoded `test_user`、注释掉认证或默认可用的未授权聊天入口。
- 若成立，恢复认证依赖并补 API 级回归测试。

源码复核结论：

- `CONFIRMED`：`chat_with_agent()` 中认证依赖被注释，`user_id` 硬编码为 `"test_user"`。
- `CONFIRMED`：未认证请求可触达 Agent Graph 聊天入口，且下游 graph 无法区分真实用户。

修复：

- 恢复 `current_user: User = Depends(get_current_user)`。
- graph 输入中的 `user_id` 改为 `str(current_user.id)`。
- 新增 API 测试：未认证请求被拒绝；非流式调用传入 graph 的 `user_id` 等于当前用户 ID。

验证：

- `pytest backend/tests/api/test_agent_graph_api.py backend/tests/api/test_monitoring_presence_api.py backend/tests/unit/test_openclaw_admin_api.py::test_execution_schedule_global_triggers_require_superuser backend/tests/unit/test_openclaw_admin_api.py::test_user_execution_schedule_crud_endpoint backend/tests/api/test_experiments_api_access.py backend/tests/unit/services/test_community_advanced_access.py backend/tests/api/test_capsules_api.py backend/tests/unit/services/test_capsule_share_service.py` -> `22 passed, 8 warnings`

## 10. Milestone A - 权限边界

状态：`READY_FOR_COMMIT`

完成范围：

- A1 Curiosity capsule ownership。
- A2 Community advanced message/report/favorite/forward/broadcast access。
- A3 Experiment ownership。
- A4 Execution schedule global trigger admin guard。
- A5 Presence / monitoring enumeration guard。
- A6 Agent Graph V2 auth restoration。

下一批：

- B1 Signal Push internal auth fail-closed。
- B2 Gateway config dangerous defaults。
- B3/B4/B5 WebSocket origin/token/连接治理。

## 11. Cycle 7 - 跨服务边界 B1/B2

状态：`FIXED`

目标：

- 复核 Gateway Signal Push internal auth 是否仍存在 handler 级 fail-open。
- 复核 Gateway config 是否仍在非开发环境允许危险默认。

源码复核结论：

- `CONFIRMED`：`SignalPushHandler.isAuthorized()` 在 `InternalAPIKey == ""` 时返回 `true`，且使用普通字符串比较。虽然 `/internal` 路由组已有 `InternalAPIKeyMiddleware` 保护，但 handler 自身仍是可复发的 fail-open 防线缺口。
- `FIXED/PREVIOUSLY`：`backend/gateway/internal/config/config.go` 已在非开发环境强制 `INTERNAL_API_KEY` 非空、强制 `RedisFailClosed = true`，并拒绝 `ALLOW_WS_QUERY_TOKEN`、默认 MinIO 密钥等危险配置。本轮不重复修改。

修复：

- `SignalPushHandler.isAuthorized()` 改为 key 未配置时 fail-closed。
- header 与配置 key 均 trim 后用 `subtle.ConstantTimeCompare()` 比较。
- 新增 Go 单测覆盖空配置、缺失 header、错误 header、正确 header。

验证：

- `go test ./internal/handler ./internal/middleware ./internal/config` -> PASS

## 12. Cycle 8 - WebSocket 边界 B3/B4/B5

状态：`FIXED`

目标：

- 复核 root WS routes 是否统一经过 origin、连接数、read limit、idle timeout、ping/pong、metrics 链。
- 复核 community WS proxy 是否仍有 token URL 暴露、idle/ping-pong/per-user limit 缺口。
- 复核 STT WebSocket origin 是否已使用统一 allowlist。

源码复核结论：

- `FIXED/PREVIOUSLY`：`/ws/chat`、`/ws/files`、`/ws/stt`、community WS proxy 路由均先经过 `WsAuthMiddleware`；chat/files handler 已有 origin upgrader、read limit、连接限制和 metrics。
- `CONFIRMED`：community WS proxy 仍将 token 拼进后端 URL，例如 `/api/v1/community/ws/connect?token=...`，且 group WS 也会追加 query token。
- `CONFIRMED`：community WS proxy 缺少 per-user proxy 连接限制、read limit、pong deadline、ping ticker。
- `CONFIRMED`：STT upgrader 仍 `CheckOrigin: return true`。

修复：

- community WS proxy 改为只通过 `Authorization: Bearer ...` 向 Python 后端透传 token，后端 URL 不再携带 token。
- community WS proxy 增加 per-user 连接计数，复用 `WS_MAX_CONNECTIONS_PER_USER`。
- community WS proxy 增加 read limit、pong deadline、ping ticker、write deadline，并用写锁避免 ping 与转发并发写同一连接。
- STT handler 构造函数接收 `config.Config`，origin 校验改用 `IsOriginAllowed()`；无 Origin 的同源/非浏览器连接仍允许。

验证：

- `go test ./internal/handler ./internal/middleware ./internal/config ./cmd/server` -> PASS

## 13. Next Queue

状态：`PENDING`

下一批建议进入账本/幂等与并发：

- C1 SignalHub map 并发竞态。
- C4 Execution Service 幂等键随机化与类级故障状态。
- D1/D3 Quota/LLM 预留与失败退款。

## 14. Cycle 9 - 并发边界 C1

状态：`FIXED`

目标：

- 复核 `backend/gateway/internal/service/signal_hub.go` 是否仍存在 Send 遍历 map 与 Unregister 修改 map 的并发竞态。

源码复核结论：

- `CONFIRMED`：`Send()` 在释放 `RLock` 后遍历 `userConns` 原 map；同时 `Unregister()` 可持写锁删除同一 map 项。锁保护了 map 获取动作，但没有保护后续遍历。

修复：

- `Send()` 在读锁内复制连接快照到 slice，释放锁后执行 `WriteJSON()`。
- 写失败仍调用 `Unregister()` 和 `Close()`，避免坏连接泄漏。
- 新增失败连接清理测试和 concurrent unregister/send 测试。

验证：

- `go test ./internal/service` -> PASS
- `go test -race ./internal/service -run TestSignalHub` -> PASS

## 15. Cycle 10 - 执行幂等与降级状态 C4

状态：`FIXED`

目标：

- 复核 `ExecutionService` 是否仍生成随机 idempotency key，导致同一执行尝试无法稳定去重。
- 复核连续失败降级是否仍依赖类级全局 dict，导致进程内共享状态污染、跨实例语义不清。

源码复核结论：

- `CONFIRMED`：`_build_idempotency_key()` 使用 `uuid.uuid4().hex[:8]` 拼接 key，同一 task/plan 下重复构造会生成不同 key。
- `CONFIRMED`：`_failure_counts` 与 `_degraded_users` 是 `ExecutionService` 类级 dict。由于 API 每次请求都会创建新 service，类级状态被用来维持跨实例降级，但它不是受控持久状态，也会把运行期降级语义绑死在单进程内存。

修复：

- `_build_idempotency_key()` 改为基于 `plan_id + task_id + 已有 execution_intents 数量` 生成稳定 attempt key，例如 `execution-intent:noplan:<task_id>:attempt:1`。
- 同一 task 在未写入新 intent 前重复构造 key 保持一致；已有历史 intent 后进入下一 attempt，避免终态重试撞唯一约束。
- 并发重复创建若撞到 idempotency unique constraint，会回滚后查询已存在 intent，并返回明确的 active execution 错误，避免数据库异常冒成 500。
- 移除类级 failure/degraded dict 的运行依赖，降级状态改为从数据库中近期 terminal intents 的连续失败序列推导。
- `FAILED` / `TIMED_OUT` 计入连续失败；任一非失败终态会自然打断连续失败链，保留“成功/取消/交回后不继续降级”的产品语义。
- `get_health()` / admin dashboard 的 degraded snapshot 改为 async DB-derived snapshot。

验证：

- `python3 -m compileall backend/app/services/execution_service.py backend/tests/unit/test_openclaw_phase4.py` -> PASS
- `pytest backend/tests/unit/test_openclaw_phase4.py::test_execution_intent_idempotency_key_is_stable_per_task_attempt backend/tests/unit/test_openclaw_phase4.py::test_consecutive_failures_trigger_degraded_manual_mode` -> `2 passed`
- `pytest backend/tests/unit/test_openclaw_phase4.py` -> `26 passed`
- `pytest backend/tests/unit/test_openclaw_phase2.py::test_create_intent_blocks_second_active_execution` -> `1 passed`
- `pytest backend/tests/unit/test_openclaw_admin_api.py::test_execution_admin_routes_require_superuser backend/tests/unit/test_openclaw_admin_api.py::test_execution_admin_dashboard_available_for_superuser` -> `2 passed`
- `pytest backend/tests/unit/test_openclaw_admin_api.py::test_user_execution_connection_status_is_available` -> `1 passed`

## 16. Cycle 11 - Python LLM 配额预留 D3

状态：`FIXED`

目标：

- 复核 Python `LLMDispatcher` 是否仍存在配额预留后 provider/circuit/grpc 异常不退还。
- 复核 token 估算是否仍对中文/CJK 输入按 `len // 4` 折扣，导致配额低估。

源码复核结论：

- `CONFIRMED`：`LLMDispatcher.run()` 调用 `limiter.check_and_decr()` 后，`CircuitBreakerOpenException`、`grpc.RpcError`、普通 provider exception 都直接返回错误响应，没有退还已扣估算 token。
- `CONFIRMED`：`_estimate_tokens()` 只按 `prompt_chars // 4 + max_output_tokens` 估算，中文文本与英文同折扣，仍会显著偏低。

修复：

- 为 `RedisRateLimiter` 增加 `refund()`，通过 `rate_limit_refund.lua` 原子扣回 usage counter，避免退还后变成负数。
- `LLMDispatcher.run()` 在异常路径退还完整预留；成功路径按实际输入/输出估算退还未使用部分。
- `_estimate_tokens()` 改为语言感知估算：CJK 字符按 1 token 计，非 CJK 字符按约 4 字符/token 计，再叠加 `max_output_tokens`。
- 新增回归测试覆盖 provider 失败完整 refund、成功响应退还 unused reservation、CJK 不再享受四字符折扣。

验证：

- `python3 -m compileall backend/app/services/llm_dispatcher.py backend/app/services/quota.py backend/tests/unit/test_llm_dispatcher_quota.py` -> PASS
- `pytest backend/tests/unit/test_llm_dispatcher_quota.py` -> `3 passed`
- `pytest backend/tests/unit/test_llm_prediction_routing.py backend/tests/unit/test_llm_quota.py` -> `35 passed`

## 17. Cycle 12 - Go Chat Orchestrator 配额与缓存边界 D3

状态：`FIXED`

目标：

- 复核 Go Chat Orchestrator 是否仍使用 SHA-1 短 hash 生成 semantic cache scope。
- 复核 semantic cache 异步写入是否仍使用 `context.Background()` 脱离请求链。
- 复核 request quota 预留后，在 agent client 不可用、StreamChat 建连失败、stream recv 失败时是否会漏退还。

源码复核结论：

- `CONFIRMED`：`shortHash()` 仍使用 SHA-1，并截断到 12 字符用于 cache scope。
- `CONFIRMED`：semantic cache 写入 goroutine 使用 `context.Background()`，与请求 trace/value/cancellation 语义完全脱离。
- `CONFIRMED`：`ReserveRequest()` 成功后，如果 `agentClient == nil` 或 `StreamChatWithFallback()`/`Recv()` 失败，handler 直接返回错误，没有恢复 `user:quota:{uid}` request quota。

修复：

- `shortHash()` 改用 SHA-256，保持短 scope 输出形态但移除 SHA-1 碰撞弱点。
- semantic cache 异步写入改用 `context.WithoutCancel(ctx)` 派生的 5 秒 timeout context，保留请求 value/trace 语义，同时避免响应完成后立即取消后台缓存写。
- 新增 `refund_quota.lua` 与 `QuotaService.RefundReservation()`：只有 reservation request key 存在时才 `INCR` quota 并推送 sync queue，重复 refund 不会重复加回。
- Chat Orchestrator 在 agent client 不可用、StreamChat 建连失败、stream recv 失败三类“未完成请求”路径调用 reservation refund。
- 更新 quota integration 测试：服务不可用前置失败时，quota 应退回而不是永久扣减。

验证：

- `go test ./internal/service ./internal/handler ./internal/db` -> PASS

## 18. Cycle 13 - Photon 转账与汇总 D2

状态：`FIXED`

目标：

- 复核 Photon 转账是否仍先读缓存余额、再做数据库更新，导致前置判断与真实行锁状态分裂。
- 复核转账是否仍按调用顺序锁定双方余额，存在反向转账死锁风险。
- 复核 `/photons/transfer` 是否仍返回 placeholder transfer UUID。
- 复核 transaction summary 是否仍把整段历史拉回 Python 聚合。

源码复核结论：

- `CONFIRMED`：`transfer_photons()` 先 `get_balance()` 读缓存余额，再通过 `_update_balance()` 逐个更新，前置校验与真实事务锁定路径不一致。
- `CONFIRMED`：`transfer_photons()` 对 `from_user_id`、`to_user_id` 的行锁顺序依赖调用顺序，反向并发转账存在死锁窗口。
- `CONFIRMED`：`/photons/transfer` 仍返回固定 `00000000-0000-0000-0000-000000000000` placeholder。
- `CONFIRMED`：`get_transaction_summary()` 仍把近 N 天交易全量加载到 Python 后再 `sum()` / 分组。

修复：

- `transfer_photons()` 改为在单事务中按 `sorted(user_id)` 固定顺序 `SELECT ... FOR UPDATE` 锁定双方用户行。
- 转账前余额判断改为使用已锁定发送方行的真实余额，不再依赖缓存值。
- 转账返回 payload 带真实 `transfer_id`，API 层直接透传，不再造 placeholder UUID。
- `get_transaction_summary()` 改为 SQL 聚合：`SUM/COUNT/GROUP BY` 在数据库侧完成。

验证：

- `python3 -m compileall backend/app/services/photon_service.py backend/app/api/v1/photons.py backend/tests/unit/test_photon_service.py backend/tests/api/test_photons_api.py` -> PASS
- `pytest backend/tests/unit/test_photon_service.py backend/tests/api/test_photons_api.py` -> `16 passed`

## 19. Cycle 14 - Quota 死队列清理 D1

状态：`FIXED`

目标：

- 复核 `queue:sync:quota` 是否仍只有 producer、没有任何 consumer/reconciliation worker。
- 若确认是死队列，清理 quota 脚本与服务层中的无效 enqueue，避免持续积累无消费状态。

源码复核结论：

- `CONFIRMED`：`DecrQuota()`、`ReserveRequest()`、`RefundReservation()` 都仍向 `queue:sync:quota` 推送事件。
- `CONFIRMED`：当前仓库内未发现对应 consumer、worker 或 reconciliation 入口；`queue:sync:quota` 是死队列。

修复：

- `decr_quota.lua` / `reserve_quota.lua` / `refund_quota.lua` 移除 `RPUSH queue:sync:quota`。
- `QuotaService` 移除仅为 queue payload 存在的 JSON 构造与多余 queue key 传参。
- 单测改为显式断言不会再创建 `queue:sync:quota`。

验证：

- `go test ./internal/service ./internal/db ./internal/handler` -> PASS

## 20. Cycle 15 - LLM Security Wrapper 双记账 D1

状态：`FIXED`

目标：

- 复核 `LLMSecurityWrapper` 是否仍把同一次 LLM 请求同时记入“预检查估算”和“实际使用”，导致日配额双重累计。

源码复核结论：

- `CONFIRMED`：`chat()`、`chat_with_tools()`、`stream_chat()`、`generate_embeddings()` 都先调用 `cost_guard.check_quota(user_id, estimated_tokens)`，随后又调用 `record_usage(user_id, actual_tokens, ...)`。
- `CONFIRMED`：`LLMCostGuard.check_quota()` 在 `check_only=False` 时会直接 `incrby(daily_key, estimated_tokens)`，所以包装层当前会把同一次请求的日配额至少累计两次。

修复：

- 四个包装入口统一改为 `check_quota(..., check_only=True)`，仅做配额准入判断。
- 保留 `record_usage(actual_tokens)` 作为唯一的真实记账入口。
- 新增包装层回归测试，断言 quota 检查是 `check_only=True`，并且实际只记录一次 usage。

验证：

- `python3 -m compileall backend/app/core/llm_security_wrapper.py backend/tests/unit/test_llm_security_wrapper.py` -> PASS
- `pytest backend/tests/unit/test_llm_security_wrapper.py backend/tests/unit/test_llm_quota.py` -> `35 passed`
