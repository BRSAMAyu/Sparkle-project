# Sparkle 严格复核版全项目修复方案（恢复版）

更新时间：2026-04-24  
恢复时间：2026-04-23 21:50 Asia/Shanghai  
工作定位：设计 / 审查 / 验收基线，不代替执行型 Codex 直接改业务代码

## 0. 恢复说明

本文件是对我此前“严格复核总方案”的恢复版。恢复过程中发现：

- 当前 `main` 工作区的 `docs/audit` 曾只剩少量文件，且本文件一度为 `0 bytes`。
- 已从本地分支 `integration/phase-i-exit` 恢复 `docs/audit` 审查集。
- 恢复后的 `docs/audit/DEEP_AUDIT_SUMMARY.md` 当前汇总到 `Round 64`。
- 我此前在对话中核验过的 `1-107` 方案内容，部分原始报告文件未在当前 Git 树中找到，因此本文件保留为“经我源码复核形成的总方案基线”，但原始报告归档以当前已恢复文件为准。
- 恢复前的 `docs/audit` 已备份到 `.codex-backups/audit-restore-20260423-2149/`。

当前可打开的关键文件：

- `docs/audit/DEEP_AUDIT_SUMMARY.md`
- `docs/audit/LOOP_SESSION_TRACKER.md`
- `docs/audit/deep_audit_2026-04-22_1200_behavior_signal_collector.md`
- `docs/audit/deep_audit_2026-04-25_0730_profile_event_consumer.md`
- `docs/audit/STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_2026-04-24_rounds_1_107.md`

## 1. 口径

本文只纳入两类内容：

- 我已经回源码确认，且当前仍值得作为全项目主修复面的真实问题。
- 旧审查曾经指出、但当前源码已修复或需要降级的结论。

本文不把所有原始审查报告逐字合并。原始审查内容以 `docs/audit/deep_audit_*.md` 与 `docs/audit/DEEP_AUDIT_SUMMARY.md` 为准；本文负责把这些问题收敛成可执行、可验收的系统修复方案。

## 2. 已恢复的审查归档状态

当前从 `integration/phase-i-exit` 恢复到 `docs/audit` 的审查集包含：

- `DEEP_AUDIT_SUMMARY.md`：汇总到 `Round 64`。
- `deep_audit_2026-04-21_2315_jwt_auth.md` 到 `deep_audit_2026-04-22_0400_cognitive_prism.md` 的早期链路审查。
- `deep_audit_2026-04-22_1030_context_pruner.md`。
- `deep_audit_2026-04-22_1200_behavior_signal_collector.md`。
- `deep_audit_2026-04-23_1200_profile_context_service.md`。
- `deep_audit_2026-04-23_1600_notification_center.md`。
- `deep_audit_2026-04-24_1100_chat_orchestrator_chatflow.md` 与 `deep_audit_2026-04-24_1115_file_handler_upload.md`。
- `deep_audit_2026-04-25_0100_grpc_client_circuit_breaker.md` 到 `deep_audit_2026-04-25_0730_profile_event_consumer.md`。

当前未在 Git 树中找到的内容：

- 我此前曾看到的 `deep_audit_2026-04-24_0500_behavior_signal_collector.md` 文件名。
- 我此前曾看到的 `1-106 / 1-107` 完整原始报告集。
- 旧版 `STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_*` 的非空原文件。

处理原则：

- 已恢复的审查报告作为可追溯原始材料。
- 本文件作为恢复后的执行型总方案。
- 后续如果重新找到完整 1-107 原始报告集，应以本文件为基线做增量核验，而不是直接覆盖。

## 3. 已确认修复或需要降级的旧结论

这些问题不应继续作为最高优先级主修复项派发：

- `Theater` 预测所有权 IDOR：当前关键路径已使用 `_get_prediction_for_user_or_raise(prediction_id, user_id=...)`。
- `Execution Schedule check_url SSRF`：当前 `check_url` 已走 `validate_external_url(...)`。
- `Internal file processing token fail-open`：当前 `backend/app/api/v1/files.py` 的内部 token 校验已 fail-closed。
- `Gateway distributed rate limiter 毫秒/秒换算错误`：当前 `tokensAddedForElapsed()` 已按秒换算。
- `LLM 安全层完全未接入主热路径`：当前 `backend/app/services/llm_service.py` 已接入安全包装；剩余问题应改为“覆盖率和验收不足”。
- `Photon 管理员调整余额和审计记录分离提交`：按当前 `get_db()` 请求事务模型与 `PhotonService` 的 `external_transaction_managed` 处理，不应再按原 P0 表述。
- `WebSocket Proxy token query string`：在后续恢复到的 `Round 50` 中已被复核为部分过时；当前应按具体代理实现重新验收，不能继续沿用早期“一定仍在 URL”结论。
- `STT provider finally close 全局 provider`：恢复到的 `Round 63` 记录显示已修复；后续验收时只需确认没有回归。
- `FastAPI route handlers` 若干 P0：恢复到的 `Round 60` 记录显示已全部 P0 修复，剩余按 P1/P2 或回归测试处理。

## 4. 当前仍应进入主修复面的工作流

### A. 权限与所有权边界

仍需优先修复或重新验收的范围：

- 胶囊系统：`mark_as_read()`、分享给群组/好友等入口必须全部按 `capsule_id + current_user_id` 查询，禁止裸 `db.get()`。
- 社区高级功能：转发、举报、收藏、审核必须校验消息可见性、群成员关系、好友关系、审核角色。
- 实验系统：实验读取、启动、暂停、恢复、完成、分析必须按 `created_by == current_user.id` 或管理员权限收口。
- 全局调度 tick：不能由任意登录用户触发，必须改为 admin 或内部任务 token。
- Presence：`/online/{user_id}` 不应允许任意登录用户枚举他人在线状态。
- Gateway REST proxy：恢复到的 `Round 59` 已显示 P0 修复，但仍建议验收白名单、认证中间件和 `X-Forwarded-*` 头是否在所有代理路径一致。

验收标准：

- 非 owner 不能读取、修改、分享、标记属于他人的对象。
- 非管理员不能触发全局调度、刷新缓存、审核举报或操作他人实验。
- 所有越权用例必须有回归测试。

### B. 内部接口、WebSocket 与跨服务信任边界

仍需修复或验收的范围：

- `Signal Push` 内部接口：必须强制 `INTERNAL_API_KEY`，禁止空 key 放行，密钥比较使用常量时间。
- Gateway 配置：非开发环境必须拒绝危险默认配置，例如 `INTERNAL_API_KEY` 缺失、Redis fail-open。
- WebSocket 根路由：聊天、文件、STT、社区 WS 的 timeout、origin、连接数、read limit、idle timeout、ping/pong 要统一。
- Flutter WebSocket Client：恢复到的 `Round 56` 显示 4 个 P0 全部确认，包括连接状态过早标记、community WS 竞态、token 暴露、repository 每次 build 新建实例。
- gRPC auth 与 agent bridge：恢复到的 `Round 55` 显示 `grpc_auth` 交叉验证可绕过，需要独立验收。
- gRPC client health check：恢复到的 `Round 49` 显示 health check 使用 `StreamChat` 且流关闭/断路器可观测性不足。

验收标准：

- 内部接口在生产环境未配置 key 时启动失败或请求失败。
- 所有 WS 路径具备 origin、连接数、read deadline、idle timeout 和 close 指标。
- 移动端不会把 token 放进 URL，也不会因 rebuild 反复创建长连接。

### C. 事务、并发与幂等一致性

仍需修复或验收的范围：

- Redis EventBus：主 stream maxlen、consumer pending reclaim、lock fail-open、XAUTOCLAIM 等仍需按当前实现复核。
- Achievement / Focus / Task 事件：成就奖励、任务完成、专注完成等路径仍要做幂等键和原子计数。
- SignalHub：map 迭代和 unregister 并发写需要复制快照或锁内复制。
- Companion / Outcome / Preference 写入：所有 JSONB / profile / inferred preference 更新要有乐观锁或 CAS。
- Execution Service：幂等键不能包含随机 UUID，应由业务范围稳定生成。
- BehaviorSignalCollector：事件 dict 校验、Redis 冷却失败策略、pattern adjustment 冷却、事务 savepoint 要统一处理。
- FastAPI dependency：恢复到的 `Round 62` 显示 `get_db_context` 使用 `asyncio.run` 仍需处理。

验收标准：

- 重复事件不会重复发奖、重复扣款、重复写学习记录。
- 并发写同一用户偏好或状态不会丢写。
- Redis 故障不会把冷却、推断、重规划放大成热路径洪泛。

### D. 配额、计费、积分与经济系统

仍需修复或验收的范围：

- ChatOrchestrator 配额：恢复到的 `Round 47` 显示配额预留失败/异常后不退还，token 估算对 CJK 偏差大。
- Go Chat Orchestrator：恢复到的 `Round 53` 显示速率限制默认值过激、CJK 配额估算偏低、SHA-1 哈希碰撞、goroutine 脱离 context。
- Quota/Billing：Go Redis reservation、Python token tracker、billing worker 必须收敛为单一账本或有 reconciliation。
- Photon：转账锁顺序、缓存失效时序、真实 transfer id、summary SQL 聚合仍应按当前源码验收。
- Shop：购买路径必须复用统一扣款层，避免余额、交易、物品三者不一致。

验收标准：

- 配额预留和实际使用有结算/回滚。
- 经济账本单调、可审计、可重放。
- 转账和购买在并发下不会死锁、重复扣款或产生幽灵资产。

### E. LLM 安全、Prompt 注入与输出约束

仍需修复或验收的范围：

- LLM 安全包装已接入，但 prompt assembly、response builder、plan review、expansion、predictive 等模块仍要统一输出 schema、动作白名单和 prompt context 隔离。
- 恢复到的 `Round 54` 显示 `format_map` 值未消毒、Graph 节点零上下文、error data 死代码、token 预算粗糙、模板重复和 i18n 缺失。
- Predictive：`predicted_action_type` 必须白名单化。
- Expansion：上下文不要作为自然语言裸拼，必须结构化、长度限制、净化。
- Agent gRPC / API：`str(e)` 泄露需要统一 safe error。

验收标准：

- LLM 输出不能直接驱动未校验动作。
- 用户可控文本进入 prompt 时必须带边界、角色隔离和长度限制。
- 对外错误稳定，对内日志完整。

### F. 全量扫描、N+1 与热路径性能

仍需修复或验收的范围：

- Review History / Feedback Learning：导出、聚合、趋势、误判分析必须下推 SQL 或加分页。
- Notification Center：统一分页不能先分源分页后合并；mark-all-read 不应逐条写。
- Friend Match / Recommendation Feedback：候选过滤、hit count、recent interactions 要下推和加 LIMIT。
- Leaderboard：全局榜不能加载所有活跃用户到 Python 排序，`my_rank` 不能只看 top 100。
- Insight / Idiographic / PersDyn / Expansion：长窗口查询、向量去重、重算任务需要限制范围和异步化。
- BehaviorSignalCollector：14 天任务/反馈窗口要加 LIMIT，pattern adjustment 要冷却。
- FastAPI route handlers：恢复到的 `Round 60` P0 已修，但 N+1 与 print/不一致 auth 仍需回归。

验收标准：

- 高流量接口有分页、LIMIT、索引和 SQL 聚合。
- 用户级榜单、通知、推荐、洞察路径有可观测 latency 指标。

### G. 异步可靠性、后台任务与事件可交付性

仍需修复或验收的范围：

- Celery / task queue：恢复汇总显示早期报告文件缺失但重新审计发现 Beat 缺失、嵌套 `asyncio.run`、event loop 竞态等高风险项，需要重新跑源码核验。
- Expansion feedback：不能 `asyncio.create_task` fire-and-forget，必须 outbox / queue / retryable job。
- Push / email：恢复到的 `Round 60` 显示部分 create_task 已修为 Celery，需验收所有通知路径。
- EventBus：事件 publish、ack、retry、dead letter、maxlen 需要一套统一策略。
- Profile Event Consumer：恢复到的 `Round 64` 显示 consumer name 不固定、focus/error 不清缓存。

验收标准：

- 后台任务失败可重试、可观测、可追踪。
- consumer 重启不会重复消费或丢失 pending 事件。
- 用户可见副作用不能只存在内存任务里。

### H. 上传、文档、静态资源与文件链路

仍需修复或验收的范围：

- File Handler：恢复到的 `Round 48` 显示 SVG stored XSS、bucket 泄露、幽灵文件、fire-and-forget 处理、非原子删除。
- `/uploads`：私有文件、文档处理中间产物不应直接公开静态挂载。
- Magic bytes：上传完成后的内容嗅探必须进入生产路径。
- Document / ingestion：清洗端点要鉴权，双挂载要收敛，chunk 存储不能中途批量 commit 造成部分写入。

验收标准：

- 用户上传文件默认私有。
- SVG 要么禁用，要么 sanitize。
- 删除、处理、索引三者一致，失败后有补偿。

### I. 移动端与体验层稳定性

仍需修复或验收的范围：

- Flutter WS Client：恢复到的 `Round 56` 是当前移动端高优先级风险，应单独派发 mobile worker。
- UX Envelope：恢复到的 `Round 52` 显示原 P0 内存泄漏已修，但 schema 契约、metadata 膨胀、硬编码中文和类型安全仍需整理。
- Prompt / UX / response builder 的 i18n 盲区会影响中文用户下的配额估算、错误提示、上下文理解。

验收标准：

- 长连接生命周期不依赖 widget rebuild。
- 断线、401、心跳失败、应用前后台切换都有稳定状态机。
- 展示层 payload 有 schema 契约和大小上限。

## 5. 建议执行顺序

### 第一批：先修可被滥用的边界问题

1. 权限与 ownership：胶囊、社区高级功能、实验、调度 tick、presence。
2. 内部接口：Signal Push、Gateway config、gRPC auth、WS origin/token/连接治理。
3. 上传暴露：SVG、bucket、公开 `/uploads`、文档清洗鉴权。

### 第二批：修账本与一致性

1. 配额预留退还与 token 估算。
2. Photon / Shop 账本一致性。
3. 成就、任务、Focus、BehaviorSignal 的幂等与事务。
4. Preference/Profile/Outcome 的乐观锁。

### 第三批：修热路径性能和后台可靠性

1. Review History、Notification Center、Leaderboard、Recommendation Feedback。
2. Celery/EventBus/Profile Event Consumer。
3. LLM prompt/output schema、error leakage、i18n。
4. 移动端 WebSocket 生命周期。

## 6. 执行型 Codex 派工规则

- 一个 Codex 只负责一个工作流或一个模块切片。
- 每个修复必须写清楚“修前风险、修后约束、回归测试”。
- 权限类问题必须补越权测试。
- 幂等/事务类问题必须补并发或重复事件测试。
- 性能类问题必须给出查询变化，最好补 SQL 层聚合测试或 benchmark。
- 修复完成后由审查角色按本文验收，不要只按原始审查标题验收。

## 7. 当前可直接关闭或降级的验收项

- `Theater` 预测 IDOR：按当前源码可关闭，但建议保留 regression。
- `Execution Schedule check_url SSRF`：按当前源码可关闭。
- `Internal file token fail-open`：按当前源码可关闭。
- `Distributed rate limiter ms/sec`：按当前源码可关闭。
- `LLM 安全层零接入`：关闭原说法，改为覆盖率验收。
- `Photon admin adjustment separate commit`：关闭原说法，改为经济账本一致性整体验收。
- `STT provider finally close`：恢复汇总显示已修，后续只验回归。
- `FastAPI route handlers P0`：恢复汇总显示已修，后续只验剩余 P1/P2。

## 8. 后续如果找回 1-107 原始报告

如果之后重新找到那批未合并的 100+ 轮原始报告，请按下面流程处理：

1. 不要直接覆盖本文件。
2. 先把原始报告补进 `docs/audit/recovered_rounds/` 或当前 `docs/audit/`。
3. 更新 `DEEP_AUDIT_SUMMARY.md` 的真实轮次。
4. 逐条对照本文的 9 个工作流，把新增内容标为“新增确认 / 已被覆盖 / 误报 / 已修复”。
5. 再生成下一版 `STRICT_REVALIDATED_GLOBAL_REPAIR_PLAN_YYYY-MM-DD_rounds_*.md`。
