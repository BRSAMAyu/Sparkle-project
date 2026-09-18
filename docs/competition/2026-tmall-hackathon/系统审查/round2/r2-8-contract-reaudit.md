# R2-8 契约复审（第三次收口，本次完成）

> 基线：主仓库 HEAD `85a106f5`（fix(web): round-2 N-series）。审查只读；修复经独立
> worktree `Sparkle-sysrev/wt-r28`（detach @85a106f5）完成并导出 patch。
> 日期：2026-09-18 ｜ 执行：R2-8 契约复审员（前两次被系统事故击杀，本次为唯一遗留整块）

## 0. 结论一句话

**proto ↔ 引擎 ↔ 网关三方 17 RPC 全对齐，路由面 BA-ROUTES 守卫绿（344↔924）；
但 REST payload 层挖出 1 个 P1 类漂移（Idempotency 头名不匹配，4 个移动端经济流
端点必 400，已修入 patch），1 个 P1 陷阱（网关死代码 persister 引用已删列，挂账），
外加 5 条 P2/P3 挂账。G8 统一过的枚举无回归性漂移。**

## 1. 覆盖面

| 维度 | 数量 | 说明 |
| --- | --- | --- |
| proto 服务/RPC | 7 文件 / 17 RPC（agent_service） | 引擎 `agent_grpc_service.py` 实现 17/17；网关 `internal/agent/client.go` 包装 17/17；`websocket.proto`（envelope/ACK/NACK/干预）与网关三模入站（binary proto / envelope JSON / legacy flat JSON）一致 |
| proto 子树 | proto/sparkle/{inference,rag,signals} | 存在于 gen/ 对应目录，无孤儿 |
| 网关代理路由面 | 344 ↔ 924 引擎路由，54 catch-all 组，112 ledgered diffs | `scripts/guards/check_rule_ba_routes_parity.py` 实跑 **OK**（路由面守卫覆盖，本次不重复人工审） |
| REST payload 抽查 | 11 端点/链路 | auth guest、chat WS send、chat history GET、tasks CRUD、goals create、leaderboards、shop purchase、exam-sprint（8 条全量）、tts、stt、profile chat-opening、users/me |
| 枚举 | 9 组 | TaskType(7)/TaskStatus(7)/PlanType(2)/PlanStage(4)/PlanPriority(4)/LeaderboardType(7)/LeaderboardPeriod(4)/MessageRole(3)/GoalType 规范映射 |

## 2. 重点新变更点核验（今晚变更）

### 2.1 chat history is_interrupted/is_reasoning_complete 链 ✅（读路径）

- 引擎 REST `GET /chat/history/{session_id}`（profile/chat.py 不涉及；网关是入口）：
  网关 `handler/chat_history.go` 的 `ChatHistoryMessageDTO` 已含
  `is_interrupted`/`is_reasoning_complete`（75b3ffe1 BA guard 补的），
  且出站时把服务层 Unix 秒 `timestamp` 换算成 RFC3339 `created_at`、同时给
  `conversation_id`+`session_id` 双字段——mobile `ChatMessageModel.fromJson`
  （读 `created_at`、`conversation_id ?? session_id`）完全咬合。**PASS**。
- mobile `chat_message_model.g.dart`：`is_interrupted`/`is_reasoning_complete`
  均可空容错解析，缺省不炸。**PASS**。

### 2.2 网关死 persister：引用已删列 + 秒当毫秒 ⚠️ P1（挂账，见 §4）

`internal/service/chat_history_persister.go`：
- INSERT 引用 `chat_messages.metadata` —— **gfix03 已 DROP 该列**
  （`alembic/versions/gfix03_dead_columns_drop_20260918.py`；schema.sql 快照确认无此列）。
  HEAD 提交 85a106f5 自己的注释写明"全仓审计漏掉了本文件这段手写 SQL"——修了读路径
  （chat_history.go fallback），**漏了同一提交族引入的写路径死代码**。
- `to_timestamp($7::bigint / 1000.0)` 把秒级时间戳当毫秒除，真接线会把全部消息
  写成 1970-01-21。
- 缓解因素：全仓 grep 无任何 `ChatHistoryPersister` 接线（cmd/setup 均无）——**当前是
  死代码**，不在运行时引爆；但 `queue:persist:history` 队列仍在每条消息 RPush
  （断路器 10k 封顶 + 本地重试缓冲 500 封顶，内存有界）。
- 落库真由引擎侧负责（`orchestration/persistence_layer.py` 助手消息 +
  `context_builder.py` 用户消息），引擎 ORM 与 DB 列一致（无 metadata 映射）。

### 2.3 TTS/STT 新端点契约登记 ✅

- 引擎 `POST /tts/synthesize`（`api/v1/tts.py`：`{text≤2000, voice?, instructions?}` →
  binary audio/wav|mpeg；失败 503）→ router `/tts` 前缀；网关 `proxy_routes.go:894`
  已注册 `tts.POST("/synthesize")`（6b0c02db）。**对齐**。
- 引擎 `POST /stt/transcribe` + WS `/stt/stream` → router `/stt` 前缀；网关注册了
  `/stt/transcribe`；`/stt/stream` WebSocket 网关**未代理**（批量转写走 REST 已覆盖，
  实时流当前无网关路径）。mobile 侧两端点均无消费方（voice 沿用端内能力）→ P3 登记。
- STT proto（`stt_service.proto`：StreamSpeechToText/TranscribeAudio/EnhanceTranscript）
  与引擎 `stt_grpc_service.py` 同名实现，REST 端点是 gRPC 之上的薄封装。**PASS**。

### 2.4 exam-sprint 补齐 4 条 ✅（8/8 全对齐）

引擎 8 条（intake/dashboard/diagnose·generate/diagnose·grade/post-exam-review/
sprint-summary/completion/portfolio）↔ 网关 8 条（35b29ba5 补 4 + 既有 4）。
mobile 已消费 intake/dashboard/post-exam-review/completion/portfolio；
`diagnose/generate`、`diagnose/grade`、`sprint-summary` 移动端未接（引擎契约以
`ExamSprintDiagnosticService` Pydantic 为准，schema 自洽）→ P3 登记。

## 3. REST payload 抽查明细（11 项）

| # | 端点 | 请求 | 响应 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | POST /auth/guest | mobile query `guest_id` ↔ 引擎同名 query 参数 | mobile 兼容 `{token:{...}}` 与顶层 token 双形态，引擎两形态都发 | ✅ PASS |
| 2 | WS chat send（legacy flat JSON） | mobile `{message,session_id,request_id,nickname,file_ids,include_references,chat_mode,use_document_context,extra_context}` ↔ 网关 `chatInput` json tag 全一一对齐；无 `type` 字段落 `message` 默认分支 | ack/delta/status 事件 mobile `_safeInt(data['timestamp'])` ↔ 网关 `time.Now().Unix()` | ✅ PASS |
| 3 | GET /chat/history/:id | limit/offset | `created_at`(RFC3339)+`conversation_id`+`is_interrupted` 等全链 | ✅ PASS（富字段 TTL 后降级见 P2-1） |
| 4 | tasks CRUD | mobile TaskModel 字段 ↔ 引擎 TaskCreate/TaskUpdate（含 guide_json/ai_prompt/phase_index/success_criteria） | 同构 | ✅ PASS（枚举见 §5） |
| 5 | POST /goals + milestones | mobile `goal_type/title/motivation/time_horizon/description/milestones[{id,title,description,estimated_days,acceptance_criteria}]` ↔ GoalCreateRequest/GoalMilestonePayload snake_case 全对齐 | CreatedGoal 读 `first_task_id` ↔ GoalResponse | ✅ PASS（trailing-slash：引擎 "" 与 "/" 双注册，mobile 打平路径） |
| 6 | GET /leaderboards* | type/limit/offset/period | `{success,data}` 包裹 ↔ mobile unwrapMap+`['data']` | ✅ PASS |
| 7 | POST /shop/purchase | `{item_id}` + 幂等头 | —— | ❌ **P1 头名漂移（已修，见 §4）** |
| 8 | exam-sprint 全量 | 见 §2.4 | —— | ✅ PASS（3 条 mobile 未接，P3） |
| 9 | POST /tts/synthesize / POST /stt/transcribe | §2.3 | —— | ✅ PASS（mobile 未接，P3） |
| 10 | POST /profile/chat-opening | mobile `{conversation_id}` ↔ ChatOpeningRequest；读 `created==true` ↔ ChatOpeningResponse | —— | ✅ PASS |
| 11 | GET /users/me 系列 | —— | mobile UserModel json keys ↔ engine `_build_user_profile`（UserProfile + linked_providers/password_login_enabled/tos/privacy 注入） | ✅ PASS |

## 4. 发现与处置

### P1-1（已修入 patch）Idempotency 头名类漂移：4 个移动端经济流端点必 400

- **事实**：mobile `IdempotencyInterceptor` 对 POST/PUT/PATCH 统一注入
  `X-Idempotency-Key`（与引擎全局幂等中间件 `app/api/middleware.py:119` 同名约定）；
  但 6 个端点用 `Header(None, alias="Idempotency-Key")` 强制要求另一头名，
  头名不匹配 → FastAPI 解析为 None → 400。
- **影响**：移动端可达的 4 个全断——`POST /shop/purchase`（购买）、
  `POST /photons/transfer`（转账）、`POST|DELETE /achievements/contracts`
  （创建/取消契约=押金经济流）。其中 DELETE 连 X- 头都没有（拦截器不覆盖 DELETE）。
  今晚 gamification fieldtest "idempotency/double-spend verified" 是脚本直连引擎
  带正确头测的，移动端 UI 路径未覆盖。
- **修复**（`r2-8-idempotency-header-compat.patch`，基线 85a106f5）：
  - 引擎 4 端点同时接受 `X-Idempotency-Key` 别名（`idempotency_key = idempotency_key or x_idempotency_key`），向后兼容既有 `Idempotency-Key` 调用方与全部现有测试；
  - mobile 拦截器把 DELETE 纳入注入范围（常量集合写法，dart format 过）；
  - 新增回归 `test_purchase_accepts_x_idempotency_key_alias`（红绿：修复前该测试 400）。
  - 定向测试：shop 3 + photons 6 + achievements 7 + idempotency 中间件 1 = **17 passed**。
- **不修（有意）**：`POST /photons/adjust`（superuser-only，脚本方可带规范头）、
  `POST /achievements/events/process`（verify_internal_token 内部 API）保持原样，
  避免扩大 diff；如需全量统一可后续一个 follow-up。

### P1-2（挂账，建议尽快）网关死 persister = 修好就能炸的陷阱

见 §2.2。三个选项（任一都行，需 owner 决策）：
a) 直接删除 `chat_history_persister.go`（~330 行，无引用无测试）+ 停止向
   `queue:persist:history` RPush（省每消息一次管道写）；
b) 修两处 bug（去掉 metadata 列 + `to_timestamp($7)` 秒级直用）并接线恢复网关侧双写；
c) 最小止血：只把 INSERT 改成不带 metadata 列并修 to_timestamp，防未来误接线。
倾向 a)：引擎侧持久化管道已覆盖，网关双写属冗余路径。

### P2 挂账（3 条）

- **P2-1 chat history 富字段 30 分钟后降级**：引擎侧只持久化 content/model_name
  （persistence_layer/context_builder），widgets/tool_results/reasoning_*/is_interrupted
  仅存 Redis（TTL 30min）。TTL 过期后 DB fallback 只有裸文本，mobile 重进会话
  丢卡片与推理链。engine `chat_messages` 无 metadata 列（gfix03 刚删），需要引擎侧
  新持久化设计（actions 列可承载一部分）。
- **P2-2 网关 history role 大小写双源不一致**：Redis 路径返回 `"user"/"assistant"`
  （小写，写侧 `saveMessage` 决定），DB fallback 直接扫出枚举 label
  `"USER"/"ASSISTANT"`（大写）。mobile `_normalizeRoleJsonValue` 容错（toLowerCase），
  但任何新消费方都会踩。建议网关 DB 路径 `strings.ToLower(role)`。
- **P2-3 无消费队列**：`queue:persist:history` 只写不读（唯一读者是死 persister），
  每条 WS 消息白写一次 Redis 管道（有界 10k+500）。随 P1-2 一并处置。

### P3 挂账（3 条）

- **P3-1 goal type 语义漂移**：mobile `_typeMap` 把 UI 的 academic→exam、
  skill→job_search、habit→fitness；引擎 `GOAL_TYPE_CANONICAL_MAP` 里 academic/
  skill/habit 是独立规范型。功能不断（引擎归一化兜底+unknown 透传告警），但
  两端类型学不一致，成长档案分类会偏。建议对齐 mobile 映射表。
- **P3-2 leaderboard `group_flame` 未露出**：引擎 LeaderboardType 已加 group_flame
  （今晚 global board 修复），mobile 枚举无此值（fromString 回退 global，安全降级）。
- **P3-3 语音/exam 诊断移动端未接**：/tts/synthesize、/stt/*、exam-sprint
  diagnose/generate、diagnose/grade、sprint-summary 网关已通、mobile 无消费方与
  模型定义（api_endpoints.dart 无对应常量）。接前需补 fromJson 模型。

## 5. 枚举一致性（G8 后无回归）

| 枚举 | 引擎 | DB enum | mobile | 结论 |
| --- | --- | --- | --- | --- |
| TaskType 7 值 | `LEARNING..OCR` | tasktype 同 | JsonValue 同 7 | ✅ |
| TaskStatus 7 值 | `PENDING..ABANDONED`（含 RESTORE/STUCK/PAUSED） | taskstatus 同 | 同 7 | ✅ |
| PlanType/Stage/Priority | sprint·growth / sprint·daily·review·paused / critical·high·normal·low | varchar | JsonValue 全同 | ✅ |
| LeaderboardType | 7 值（含今晚新 group_flame） | varchar | 6 值（回退安全） | ✅（P3-2） |
| LeaderboardPeriod | all_time/weekly/monthly/daily | varchar | 同 4 | ✅ |
| MessageRole | user/assistant/system | messagerole（label 大写，SQLAlchemy name 存储惯例一致） | _normalizeRoleJsonValue 容错 | ✅（P2-2 双源大小写） |
| GoalType | GOAL_TYPE_CANONICAL_MAP（exam/academic/project/job_search/skill/fitness/habit/startup/other/general + 中英文别名） | varchar(64) | UI 映射表 | ✅ 功能（P3-1 语义） |

## 6. 台账同步

漏洞台账 R2-8 行已更新（本文件 + patch 为凭）：契约复审整块收口，
R2-08 剩余项全部转化为上述 P1-2/P2/P3 挂账编号。

## 7. 复现与环境备注

- patch 应用：`git apply docs/competition/2026-tmall-hackathon/系统审查/round2/r2-8-idempotency-header-compat.patch`（基线 85a106f5；亦已实际应用于 `Sparkle-sysrev/wt-r28` 可直接复核）。
- 定向测试命令（引擎侧需 SECRET_KEY）：
  `SECRET_KEY=... pytest backend/tests/api/test_shop_api.py backend/tests/api/test_photons_api.py backend/tests/api/test_achievement_api.py backend/tests/unit/test_idempotency_middleware.py`
- 过程备注：任务交接称 wt1 @85a106f5，实查 wt1 检出为 6e9abd97 且载有其他在跑员的
  未提交改动（signals/tests），故另建 detach worktree wt-r28 修复，未触碰 wt1 既有改动。
