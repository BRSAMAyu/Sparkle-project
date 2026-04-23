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
