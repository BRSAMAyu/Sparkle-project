# PROD-LOG2 — 35+ 卡修复后的活栈日志二轮巡检（对照验证 + 新问题挖掘）

- 卡号：PROD-LOG2（北极星全旅程战役 · C 纵队生产级打磨线·二轮）
- 基线：`5ec142d6`（worktree wt208）；主仓运行实例同源（网关 08:33 起 / 引擎 09:10 起，均已含全部修复）
- 日期：2026-09-23 10:36–11:00；巡检方式：**纯只读**（grep / docker logs / psql SELECT / redis-cli SCAN / 代码行核对），未改任何代码、未重启进程、未写 DB
- 日志源与覆盖窗口：
  - 网关（修复后二进制）：`/tmp/gateway_server.log`（stdout，08:33:26 起，1778 行）+ 主仓 `backend/gateway/logs/local/gateway.log`（29.4MB，新旧实例共用，**08:33 后窗口零 ERROR**）
  - 引擎第一修复后实例：`/tmp/uvicorn_engine.log` + `/tmp/grpc_server.log`（09:10:32–10:38，轮 14977/1725 行）——**10:40 引擎再次重启，两文件被顶掉**（现仅存 10:40 新 boot 111/117 行）。本报告的"修复后"计数以巡检时录得的 09:10 实例为准（证据已抄录于本报告）
  - 一轮"修复前"计数：引自 `v3-output/PROD-LOG/REPORT.md`（其分析对象的旧实例日志已被清理，无法重放）
- 脱敏说明：日志中未发现明文 key/token/密码；报告只报字段名不报凭据值。`.env` 仅以 grep -c 判断"是否配置"，未读取值。
- 证据标注约定：`log:` 为真实日志行摘录；`code:` 的 文件:行号 均在 wt208 基线逐行核对。

---

## ① 一轮九缺陷修复对照表（全部 9 项：修复确认，0 复发）

| # | 一轮缺陷 | 修复 commit | 修复前（一轮实测） | 修复后窗口实测（09:10 引擎 / 08:33 网关） | 判定 |
|---|---|---|---|---|---|
| 1 | SecurityMonitor 启动即死（安全监控裸奔） | `9ba67176` PROD-FIX-1 | 每次启动 1 条 warning，后台任务 0 | `log: "Security Monitor startup verified: initialized=True background_tasks=2 redis_ready=True"`（09:10:36 与 10:40:20 两次启动均实证）；已开始产出告警（见 ③-1） | **✅ 修复+实战运行** |
| 2 | `KnowledgeNode.importance` 坏引用 → user_state_v1 整体缺失 | `9ba67176` PROD-FIX-1 | 50 条 warning/2h，上下文必炸 | `user_state_v1`/`importance` 关键字 **0 命中**；窗口内 grpc 有真实聊天流量（orchestrator 相关 597 行、reviewer 09:22 起审查 create_plan 等） | **✅ 0 复发** |
| 3 | 事件总线幂等锁不按组隔离（扇出延迟+刷屏） | `de9fcd42` PROD-FIX-2 | ~129 条 warn；修复中发现更深病灶：done-marker 流级→跨组被误判重复**跳过执行** | `Could not acquire lock` **0 命中**（且抢锁失败已降 DEBUG）；GRP-组键 `evt:{stream}:{group}:{id}` 在码 | **✅ 0 复发** |
| 4 | ReviewerAgent 超时空消息 + 不可诊断 | `5588ed0a` PROD-FIX-3 | 6 条空消息 error | `Review failed` **0 命中**；reviewer 正常工作（deepseek-flash / qwen3.7-flash 多次审查）；超时诊断分支在码：`code: agents/reviewer_agent.py:410-415`（注释直引 PROD-LOG #4，带 review id/elapsed/threshold）——窗口内未实战触发 | **✅ 修复在码 + 0 复发** |
| 5 | WS close 1000 正常断连被告警 | `de9fcd42` PROD-FIX-2 | 129+94 条 warn | 修复后窗口 **4 次 WS connected + 4 次 disconnected → 0 条 read error/warn**；`code: gateway/internal/handler/chat_orchestrator.go:217-225 logWebSocketReadError`（close 1000→Debug） | **✅ 实战验证** |
| 6 | Outbox publisher 无退避 | `de9fcd42` PROD-FIX-2 | 8,494 条（事故期 10 条/s） | 窗口内 DB 全程在线，0 次失败可演练；代码验证：`code: gateway/internal/cqrs/outbox/publisher.go:98-150`（指数退避 2x→60s 封顶、首条+每 10 条限速日志、成功复位+recovery Info、183 行单测） | **✅ 码验**（待下次 DB 故障实战） |
| 7 | checkpoint 允许清单过期（585 条假告警） | `5588ed0a` PROD-FIX-3 | 585 条 WARNING | 已知 key 全部降 DEBUG：274 条（240@:59 + 34@:66）**WARNING 带 0 条**；但按设计中的"未知 key 仍 WARNING+register hint"路径，**新暴露 4 个未登记 key**：snapshot×10 / user_context×7 / focused_memory×7 / executable_plan×7 = 31 条（见 ②-5） | **✅ 修复生效 + 残留清单待补** |
| 8 | 关停 `context canceled` 记 ERROR | `5588ed0a` PROD-FIX-3 | 每次重启 ~13 条 ERROR | 08:33:23 关停整段 **全 `level=info`**（`"Outbox cleaner stopped (graceful shutdown)"`、`"Worker stopping","error":"xreadgroup: context canceled"` 等）；08:33 后窗口 error=0。窗口内残留的 06:11:40 / 08:08:29 关停 ERROR 均为**旧二进制**产物 | **✅ 实战验证** |
| 9 | 调度 tick `%s` 参数被 loguru 丢弃 | `5588ed0a` + `d659717b` LOGURU-BATCH | 每分钟一条字面 `%s` | `log: "Execution schedule tick completed: due=0 dispatched=0"` ×88——真实数字；全窗口引擎日志 `%s` 字面量 **0 命中**（163 处 printf 风格批量迁移生效） | **✅ 实战验证** |

**EXC-TRACEBACK（`17f4b5df`，234 处 traceback 附加）**：窗口内引擎 85 条 ERROR 中 **0 条带 traceback**。判定：**无法在窗口内确认生效**——234 个迁移点没有一条在本次错误面上触发。且相邻的**最高频错误站不在 234 之列**（见 ②-2 空消息簇）。建议：下次错误窗口复查；或主动把 ②-2 涉及的 llm_service/fallback 两站纳入 exception 附加。

---

## ② 新问题清单（按 生产影响×修复成本 排序；全部今晚新代码面/修复后新暴露）

### 1. i18n 假 key 刷屏 = 修复后最大噪音簇（5739 条 / 88 分钟，占引擎 WARNING 93%）
- **证据**：`log: uvicorn_engine.log "WARNING | app.core.i18n:t:91 - Translation key not found: 样本不足，继续观察中。 for locale: zh"` ×5691（grpc 另 48）。uvicorn WARNING 总量 6145，本簇占 **92.6%**。
- **根因**：`code: services/metacognition_registry.py:290` `template="样本不足，继续观察中。"`——把**字面句子**当模板 key；`:349` `I18n.t(item.template, locale=locale, **values)` 直接查 key；`code: core/i18n.py:91` 每次未命中打 WARNING。批量评测/生成流每条消息触发多次。
- **影响**：WARNING 带被单簇淹没（狼群效应反噬——真告警更难被看见）；i18n 未命中的兜底行为是返回 key 本身（输出碰巧正确），掩盖了配置错误。
- **修复思路**：:290 模板改为合法 key（或该条走"直出文案"分支不经过 t()）；i18n.t 对不含 `.` 的 key 直接静默返回（防御）。规模 S。

### 2. minimax_m3_batch 车道故障级联 + glm_batch 队列饱和丢任务（双 batch worker 新载荷面，价值最高）
- **证据链**（09:10–10:38 窗口）：
  - `log: "WARNING | llm.concurrency:__aenter__ - [LLMConcurrency] Timeout waiting for minimax (timeout=45.0s)"` ×34；ERROR 级 `Timeout acquiring semaphore for minimax` ×11；
  - 熔断：`log: "Circuit breaker OPENED for minimax_m3_batch until … (failures: 9)"` ×5、`"Model marked unhealthy after 8 consecutive failures"`；
  - **空消息错误**：`log: "ERROR | llm_service:chat:800 - LLM Chat Error: "` ×23 + `"ERROR | llm.fallback:execute_with_fallback:491 - [LLMFallback] Non-retryable error: "` ×23（`code: services/llm_service.py:800`、`services/llm/fallback.py:491` 均为裸 f-string，无 TimeoutError 分支、无 exception 附加——**一轮 ②-4 的同病在新站复发**）；
  - **队列饱和**：`log: "WARNING | queue_backpressure:_enforce_from_decision:237 - [QueueBackpressure] drop dispatch queue=glm_batch depth=200 cap=200 …; task NOT enqueued"` ×103；`log: "WARNING | predictive_service:_schedule_long_horizon_refresh:1988 - Failed to schedule long horizon prediction … dispatch dropped (queue backpressure) or failed"`——**长程预测任务被静默丢弃**。
- **根因**：batch 车道今晚切 MiniMax M3（日志内 route 文案自证："batch 车道默认已切 MiniMax M3（GLM 保留待用）"）+ 双 batch worker 上量后：①minimax 供给（并发信号量）跟不上派发速率，45s 信号量超时→熔断；②glm_batch 派发队列恒定顶满 cap=200，**有界丢弃策略在持续满载时=稳定丢任务**，且只有逐条 WARNING 无聚合指标。
- **影响**：长程预测/批处理任务静默丢失（用户面=预测不更新）；每任务多耗 45s 等待才 fallback；错误消息不可诊断。
- **修复思路**：a) minimax 并发上限与派发速率匹配（或派发前查信号量水位）；b) glm_batch 队列 depth 指标化 + 满载持续时间告警（丢弃应可观测为速率而非单条）；c) llm_service.py:800 / fallback.py:491 补 `except TimeoutError` 诊断分支 + `logger.opt(exception=True)`（与 ②-4 reviewer 同法）。规模 M。

### 3. 小米车道死配置：`mimo-v2-flash` 被端点本身拒绝
- **证据**：`log: "LLM Chat Error: Error code: 404 - {'error': {'code': '…', 'message': 'Unsupported model mimo-v2-flash'}}"`（3 站×2 条）；`code: config/settings.py:476-477` `XIAOMI_CHAT_MODEL/XIAOMI_STANDARD_MODEL = "mimo-v2-flash"`、主仓 `.env:82` 同值、`XIAOMI_MIMO_BASE_URL=https://api.xiaomimimo.com/v1`。
- **影响**：`xiaomi_chat` 挂在 fast 车道降级链第 3 位（`code: core/llm_router.py:924` `fast_models = ["dashscope_fast","deepseek_fast","xiaomi_chat","glm_4_7_flash_no_thinking"]`）——每次 fast 链降级到它必白打一跳（网络延迟+ERROR+熔断计数），再跳下一站。车道从配置上就是死的。
- **修复思路**：向小米端点核实正确模型名并更正 settings/.env；或在模型配置加载时做一次 dry-run 校验。规模 S。

### 4. SecurityMonitor DEBUG 告警每分钟重发——绕过了自家冷却机制
- **证据**：`log: "WARNING | security_monitor:_check_system_security:665 - SecurityMonitor: DEBUG mode is ON"` + `":715 - Security alert: system_security_issue [high] DEBUG mode is enabled"` **每分钟一对 ×88 分钟**（90+90 条）。
- **根因**：`code: core/security_monitor.py:672-677` `_check_system_security` **直调** `_send_alert_notification`，绕过 `trigger_security_alert`（:366）里现成的 300s 冷却（`:402 setex security:alert_cooldown:{type}`）。机制在、路径没用上。
- **影响**：开发环境 1440 条/天；生产若配 Slack/SMTP（当前均未配置，已核实 .env 两项为空）= 每分钟一条高危外呼。DEBUG=True 是真阳性（.env `DEBUG=True`/`ENVIRONMENT=development`），错的是重复频次。
- **修复思路**：system_security 检查走 `trigger_security_alert` 吃冷却；或按"状态翻转"告警（变化才发，持续保持静默）。规模 S。

### 5. checkpoint 允许清单残留 4 个未登记 key（一轮修复的尾巴）
- **证据**：`log: "WARNING | checkpoint.redis_checkpointer:save:66 - Skipping non-serializable context key: snapshot (not in KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS; register it if it is a runtime dependency)"`——snapshot×10 / user_context×7 / focused_memory×7 / executable_plan×7 = 31 条。
- **根因**：`code: checkpoint/redis_checkpointer.py:19-28` KNOWN 清单含旧 7 key，不含上述 4 个；:66 的新告警路径按设计工作（这正是修复的预期行为——提示登记）。
- **修复思路**：把 4 个 key 补进 frozenset（一行）。规模 XS。

### 6. Aurora relationship `label` 坏引用——一轮 ②-2 的同病新站
- **证据**：`log: "WARNING | orchestration.context_builder:_build_llm_profile_bundle - Failed to integrate Aurora profile context: 'SparkleRelationshipState' object has no attribute 'label'"` ×6；`code: orchestration/context_builder.py:1161` `bundle_profile_data["relationship_label"] = rel_state.label`；`SparkleRelationshipState` 实际字段（`code: aurora/schemas/primitives.py:286+`）为 `relationship_maturity / communication_style_emergent / title / …`，**无 `label`**。
- **影响**：属性漂移→Aurora profile bundle 集成整体失败被 catch 吞成一行 warning（与一轮 ②-2 同模式），AI 拿不到关系状态维度。
- **修复思路**：改用真实字段名（`title` 或派生 label）；该 catch 至少 error 级+计数。规模 S。

### 7. planning-experiment 实验指标静默丢失
- **证据**：`log: "WARNING | api.v1.experiments:assign_variant - Experiment planning-experiment is not UUID-backed; falling back to control cohort"` ×8 + `"record_metric - Skipping metric for non-UUID experiment assignment"` ×8；`code: api/v1/experiments.py:415/:458`。
- **影响**：字符串 ID 实验走进 UUID 接口→变体指派回退 control、**指标全部跳过**——该实验的 A/B 数据完全不可用（评估面失真，GAIN 类评估若依赖它会得出假阴性）。
- **修复思路**：为 planning-experiment 建 UUID 后端记录，或在实验注册层强制 UUID 化。规模 S-M。

### 8. 低频/观察项（登记不修）
| 项 | 计数 | 位置 | 备注 |
|---|---|---|---|
| `user_visual_configs_pkey` 唯一键冲突 IntegrityError | ×2 | uvicorn ERROR 簇 | upsert 未走 ON CONFLICT，冲突场景 500；evidence 见巡检时 ERROR 聚类（文件已被 10:40 重启顶掉，原文已抄录） |
| `Asyncio loop exception: Task exception was never retrieved` | ×11 | `app.main:_global_task_exception_handler` | 全局兜底在打，任务源未定位；或与 minimax 超时的 fire-and-forget 任务相关 |
| Validation error `PUT /api/v1/profile/preferences` | ×1 | FastAPI 422 | 客户端发 `{pref_key, pref_value:{value}}`，API 要顶层 `value`——契约不一致，移动端或 driver 一方需对齐 |
| `GenerateTasksForPlanTool not registered` | ×1 | `orchestration.plan_review_service` | 计划审批后任务生成工具未注册一次 |
| `_bind_response_session_id` 缺 session_id 兜底 | ×21 | orchestrator | 一轮观察项仍在（兜底工作正常） |
| `detect_merge_overrides` 仍 WARNING | ×27 | context_sources | 一轮 ③ 降噪建议未实施 |
| 启动期 `No valid tools found` ×6 + LangChain RunnableConfig UserWarning ×7 + GIN-debug 路由表 ~1006 行 | 每次启动 | 三处 | 一轮 ③ 建议均未实施（不影响运行，登记） |

---

## ③ SecurityMonitor 实战首查（专答）

**它真正运行后抓到了什么**：
1. `system_security_issue [high] DEBUG mode is enabled` ×90（每分钟一条，见 ②-4）——**真阳性**：`.env` 确为 `DEBUG=True`/`ENVIRONMENT=development`。这是它上线后唯一的捕获。
2. 登录爆破/可疑 IP：**零告警，且 DB 实证"无米下锅"**——`login_attempts` 自 09-22 起 34 行全部 `success=t`、失败 0、IP 全部 127.0.0.1(21)/::1(13)（本地评估/探针流量）。爆破检测（`code: security_monitor.py:113-114`：5 次失败/300s/IP，redis 计数 `security:failed_logins:{ip}`，`SUSPICIOUS_IP_THRESHOLD=10`）从未达到阈值。redis `SCAN security:*` 无残留告警键。

**probe 账号注册会不会淹没它——不会**：
- `record_login_attempt` 只在**失败**登录时递增爆破计数（`code: security_monitor.py:247-249` `if not success: _check_failed_login_rate`）；注册后自动登录走 success 路径，只落一行 LoginAttempt，无阈值语义。今晚几十个 probe 注册→34 行成功记录，监控无感。
- 真正的误报面不在爆破，而在 ②-4 的 DEBUG 每分钟重发；且当前 Slack(`SLACK_ALERT_WEBHOOK_URL`)/SMTP 均未配置（.env 核实为空），告警只进结构化日志——一旦生产配置了外呼，300s 冷却被 ②-4 路径绕过的问题会放大为每分钟外呼。
- 启动验证线两次实证（09:10:36、10:40:20）：`initialized=True background_tasks=2 redis_ready=True`；后台任务为 2 个（`_monitor_security_events` 每分钟 + `_cleanup_old_data` 每小时，`code: :140-142`），一轮所述"3 个协程"系旧代码。

---

## ④ 降噪/修复建议（按性价比排序）

| 优先 | 项 | 动作 |
|---|---|---|
| P0 | ②-1 i18n 假 key（5739 条/88min） | metacognition_registry.py:290 改合法 key 或跳过 t()；规模 S，一次性消掉 93% WARNING |
| P0 | ②-2 batch 车道丢任务 | glm_batch 队列 depth 指标化+满载告警；minimax 供给匹配派发速率；llm_service.py:800/fallback.py:491 补超时诊断分支（同 PROD-FIX-3 reviewer 手法） |
| P1 | ②-3 小米死车道 | 更正 mimo 模型名或从 fast_models 链摘除该 hop |
| P1 | ②-4 SecurityMonitor 重复告警 | system_security 走 trigger_security_alert 吃 300s 冷却 |
| P2 | ②-5 checkpoint 4 key 登记 | redis_checkpointer.py:19 frozenset 补 4 行 |
| P2 | ②-6 Aurora label | context_builder.py:1161 改真实字段 |
| P2 | ②-7 planning-experiment UUID 化 | 实验注册层强制 |
| P3 | 引擎日志无轮转 | /tmp 单文件被重启顶掉（本轮 09:10 实例证据即因此丢失）——loguru 加 rotation+retain，或日志落 logs/ 目录 |
| P3 | 网关历史日志归档 | 主仓 `logs/local/gateway.log` 29.4MB（一轮建议未执行）；好消息：修复后增速已正常（~0.2MB/2h，洪峰簇消失） |
| P3 | 一轮 ③ 未实施降噪 | detect_merge_overrides→INFO、"No valid tools"→汇总、RunnableConfig 注解、GIN_MODE=release |

---

## ⑤ 健康面快照（2026-09-23 ~10:45）

| 层 | 状态 |
|---|---|
| Go 网关 :8080（PID 31955，08:33 起） | **修复后 2h 窗口 error=0、warn=6**（全为 auth 面：2 invalid token / 1 missing token / 3 middleware error）；关停路径 INFO 化实证 |
| Python 引擎 :50051+:8000（09:10–10:38 实例） | ERROR 85 条：57 条为 minimax/batch 车道（②-2）、22 条空消息（不可诊断）、6 条 mimo 死配置——**零一条与一轮九缺陷相关**；WARNING 6145 条中 92.6% 为 i18n 假 key（②-1） |
| 引擎 10:40 第三实例 | 干净 boot：38 tools 注册、SecurityMonitor 再次 verified、无异常 |
| PostgreSQL / Redis / MinIO | 容器 healthy，近 3h 容器日志 error/fatal/panic = 0 |
| 引擎稳定性观察 | 24h 内三次重启（06:52 → 09:10 → 10:40），间隔 2h18m/1h30m——与舰队发版节奏吻合（非崩溃面），但每次重启丢日志的代价见 ④-P3 |

**总评**：一轮九缺陷**全部修复确认、零复发**（6 项实战验证、3 项码验待实战）。修复质量高——PROD-FIX-2 甚至挖出一轮未发现的更深病灶（跨组误跳过）。二轮新挖 7 个真问题，最大噪音源已从"代码缺陷刷屏"（一轮 101,071 条洪峰时代）转移到"配置/契约错误刷屏"（i18n 假 key），错误面的工程化程度在收敛；当前最值得投入的是 batch 车道的容量匹配与可观测性（②-2，唯一静默丢任务面）。

---

## 附：巡检纪律执行说明
- 全程只读：docker 仅 logs/ps/exec psql(SELECT)/redis-cli(SCAN)；psql 查询仅 SELECT count/group by；未改代码、未重启进程、未写 DB、未动主仓。
- /tmp 无本卡产物（全部单行命令、证据抄录进本报告），无需清理。
- 脱敏复核：全部摘录不含 key/token/密码/IP 之外的主机信息。
- 本报告为唯一交付物：`v3-output/PROD-LOG2/REPORT.md`（worktree wt208）。
