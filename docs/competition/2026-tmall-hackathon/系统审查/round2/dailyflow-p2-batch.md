# 每日流 R2 P2 批次修复（dailyflow-p2-batch）

- 基线：`faaae378`（含 dailyflow-p1 修复批与 p1a/p1b 热修）
- worktree：`Sparkle-sysrev/wt5`（本报告 + 同名 .patch，不 commit）
- 关联：`docs/competition/2026-tmall-hackathon/多端实测/daily-flow-eval-r2.md`「新发现」P2-D…P2-J
- 验证：pytest 定向 25 新增用例先红后绿 + 邻域回归 32 passed；Go 定向（CGO_ENABLED=0）
  先红后绿 + service/handler 两包全量 ok；主仓 sparkle 库/redis 只读取证。
- `backend/.env`：worktree 内真实副本（gitignored，不入 patch）。

---

## P2-D 聊天双写去重失配（行数×2）——判定：引擎 authoritative，收敛网关单写为默认关闭

**实库取证（只读查询 sparkle 库）**：eval 用户 3 轮对话 12 行，每轮 4 行，两个派生
会话各 2 行。三个标签逐一代入公式命中：

| 会话 | 网关行（MD5） | 引擎行（uuid5） |
|---|---|---|
| df2-d1-s1 | `3c3cb8ef…` = uuid3(URL,"sparkle:chat-session:"+label) | `fefd227a…` = uuid5(URL,"sparkle-session:"+label) |
| df2-d2-s1 | `774a2570…` ✓ | `7cc91561…` ✓ |
| df2-d3-s1 | `cfbe9bf9…` ✓ | `6679e8c8…` ✓ |

**谁是 authoritative——引擎**。依据：① 读路径按引擎会话（eval 原话"读路径不受影响，
读引擎会话"）；② 记忆写入 lane（MemoryInferredWriteLaneService）挂在引擎 assistant 行的
FK 上；③ chat_sessions 会话列表由引擎 checkpoint nudge 写入；④ 网关 persister 本是
DF-2 复活的后备写手，非业务所有权方（AGENTS 硬规则 3：网关禁业务逻辑）。

**关键时序证据**：网关行先落（00:18:15），引擎行后落（00:18:16.5，差 ~1.5s）。即
使把派生对齐，网关 persister 的 NOT EXISTS(±15s) 在 INSERT 时也看不到尚未提交的
引擎行——**仅对齐派生 + 去重不足以收敛，必须单写**。

**修法（两层）**：
1. `config.go`：`CHAT_PERSISTER_ENABLED` 默认 `true → false`；`setup.go` 在 persister
   关闭时同步调用新方法 `ChatHistoryService.SetPersistQueueProducerEnabled(false)`，
   `SaveMessage` 跳过入队、`flushRetryBuf` 清空缓冲——否则无消费者的
   `queue:persist:history` 会无界增长。Redis 读缓存（chat:history/chat:sessions/
   session_meta）写入不受影响。此后聊天行**唯一写方是引擎**。
2. `chat_history_persister.go resolveSessionUUID`：MD5("sparkle:chat-session:") →
   `uuid.NewSHA1(uuid.NameSpaceURL, "sparkle-session:"+raw)`，与引擎
   `orchestrator._coerce_session_uuid` 完全一致（跨语言钉死，见测试）。作为**opt-in
   后备写手**（env 一键开回）时，其 NOT EXISTS 去重才真正对得上引擎行；对**历史滞留
   队列**补排也是幂等的（旧行时间戳 ±15s 窗口内必有引擎行）。

**红绿**：新增 `TestResolveSessionUUIDMatchesEngineDerivation`（Python uuid5 独立
算出的期望值钉死）——修复前断言红（红值恰是 eval 观察到的 `3c3cb8ef`），修复后绿；
`TestPersistQueueProducerDisabledSkipsQueue`（miniredis）修复前编译红（方法不存在），
修复后绿。DF-2 既有 7 用例全绿未动语义。

## P2-E 标签会话历史读 500

**定位**：`chat_history.go getMessagesFromDB` 对 `df2-d1-s1` 直接
`sessionUUID.Scan()` 失败 → `invalid session_id` → handler 500。Redis 30min 缓存
过期后必现（eval 实测）。

**修法**：`getMessagesFromDB` 与 `ensureSessionAccess` 对非 UUID 标签改用
`resolveSessionUUID` 同派生映射（uuid5 伪会话）。效果三态：① 标签会话有引擎行 →
200 返回真实历史（userOwnsSessionInDB 按伪 UUID+user 命中）；② 从未用过的标签 →
200 空数组；③ 他人标签（DB 有行、owner 不符）→ 403（原来此路径直接跳过 DB 鉴权，
顺带补上了越权口子）。

**红绿**：与 P2-D 共用派生 parity 测试（映射正确性），读路径三态由
`getMessagesFromDB` 单元级覆盖不足的部分以 handler 全量套件回归（ok）。

## P2-F 问候线缓存键含过期上下文

**定位**：`growth_dashboard_service.get_daily_context_line` 缓存 TTL =
`_seconds_until_next_day`（到午夜），当日首生成后 ctx（streak=1）整天冻结，
与驾驶舱（3）矛盾，force_refresh 才能纠正。

**修法**：新增常量 `DAILY_CONTEXT_LINE_TTL_SECONDS = 1800`，
`ttl = min(到午夜, 1800)`——问候线最多 30 分钟后跟上真实进度，AI 生成成本仍被摊薄。
（eval 注明"模拟法与产品缺陷叠加"：同日 DB 回拨不清缓存属模拟法产物，产品侧缺陷
即 TTL 无界，本修覆盖之。）

**红绿**：`test_daily_context_line_ttl_is_bounded` 修复前红（ttl=到午夜 > 1800），
修复后绿；`test_daily_context_line_regenerates_with_fresh_context_after_ttl` 锁
"重新生成必须重读上下文"。`test_growth_dashboard_service.py` 回归绿。

## P2-G tasks/today 全量返回（50 条无分页）

**定位**：`daily_task_selection_service._is_today_relevant` 对无 due_date 的
PENDING 一律判"今日相关"——intake 32 天模板（`day:N` 标签 +
`order_index=day*1000`）+ 历史自建任务全数通过，limit=50 顶满。

**修法**（`_is_today_relevant` 语义收紧 + 端点分页）：
- 无日期开放任务需"今日锚点"：**带序的冲刺计划任务**（`day:` 标签或
  day-encoded order_index，与 exam_sprint_dashboard 同一套 `_task_day_index`
  约定）只在 `day_index ≤ 计划当前日`（target_date 推算，`_plan_current_day`）
  时相关；**无计划的自建任务**仅创建当日相关。到期/逾期/进行中/卡住/今日完成的
  语义不变（future-dated 排除是 R1 DF-8 修复已有行为）。
- `GET /tasks/today` 新增 `limit` Query（默认 50，1..200）支持分页；移动端
  不传参行为不变。
- 语义变化备案：旧的无日期自建任务从 today 列表退场，仍可经 `GET /tasks` 与
  `/tasks/recommended` 触达。

**红绿**：`test_dailyflow_p2_today_filter.py` 4 用例（纯函数 3 + db_session 端到
端 1：32 天模板 + 5 天前自建任务 → 仅 Day1-3 浮出，`limit=50` 不再顶满）修复前
红（32+1 全返回/新 helper 缺失），修复后绿。

## P2-H 胶囊"消失"——判定：证据与结论反转，实为"复读"，缺陷在"无每日再生"

**取证（eval 自留证据 `/tmp/df2/evidence/` + 只读 DB 查询）**：
- `d1/d2/d3_capsules.json` 响应体都是**同一条** D1 胶囊（id `9cc2672a`），非 0 条；
- DB 中该行 `is_read=false` 且 `created_at=2026-09-17 00:17` 至今在库。
- 结论：`get_today_capsules` 无日期过滤（"今日未读"实为"全部未读"），D1 永读
  ⇒ 列表永不空 ⇒ 端点的 `if not capsules: 自动生成` 永不触发 ⇒ **无每日再生**。
  eval 文档"返回 0 条"与其自身证据不符（其探针按 dict 取 `capsules` 键误读了
  list 响应）。
- 另：`generate_daily_capsule` 里 `curiosity_pref < 0.3` 静默跳过是唯一静默
  None 路径，本例未触发（D1 已成功生成 24.7s 那次）。

**修法**：① `get_today_capsules` 加 `created_at ≥ 当日零点`（名副其实"今日"）；
② 新增 `has_generated_today`（含已读），端点仅在"今日尚无任何胶囊"时触发生成
——次日立即再生（eval 要的每日节奏），同日已读不重复进 24.7s 同步生成。
首生成同步 24.7s 本身属 P1-C 同族"同步副作用"债，本次以每日一次上限兜住，异步化
留待后续。

**红绿**：`test_dailyflow_p2_capsule_today_window.py` 4 用例（旧未读不回流、
`has_generated_today` 计已读、当日已读不再生成、新日仍会生成）修复前 3 红方法
缺失/行为红，修复后全绿；`test_capsules_api.py` 既有 3 用例回归绿。

## P2-I insights 三日 0 条——判定：数据未生成（信号门控按设计未触发），非缺陷

**取证**：读路径正常（`d0–d3_insights.json` 全 200，0ms 级）；redis 只读扫描
`spine:user_traces:8b923994…` 仅 1 条 trace `ct_8a941c205bcc`，其
`signal_ids/directive_ids/audit_ids` 全空、`outcome="task_completed_normally"`
——spine 管线在跑，但 `TaskTimeoutDetector` 要求"实际耗时 > 预估×阈值 且连续
`_CONSECUTIVE_TIMEOUTS_TRIGGER` 次"才产信号；eval 任务均正常完成 → 无信号 →
无 directive。R1 D3 的 4 条来自当时确有超时信号，非稳定行为。
**不改码**。若产品要提升 directive 覆盖率（聊天量/streak 里程碑等新信号源），
建议另立专项登记 signal detector 扩展，不属本修复批。

## P2-J 任务 type 枚举对外暴露内部值

**核实**：线上大写枚举（`LEARNING`…）即移动端 dart `@JsonValue('LEARNING')`
契约，**不能改序列化**。输入侧 `TaskCreate` 已有 `coerce_task_type` 小写别名归一
（"learning/error_fix/study/review/practice/homework"…），但 **`TaskUpdate` 缺
同款 before-validator**——同形态 payload 局部更新 422（eval"未复测小写别名映射"
的真实残留）。

**修法**：`TaskUpdate` 补 `_normalize_task_type`（None 直通保持"未更新"语义）。

**红绿**：`test_dailyflow_p2_task_type_aliases.py` 15 用例（Create 别名矩阵 +
Update 别名 + None/非法/线上格式不变锁）修复前 Update 别名 3 例红，修复后全绿。

---

## 汇总

| 项 | 文件 | 测试 |
|---|---|---|
| P2-D 单写收敛 | `gateway/internal/config/config.go`、`gateway/cmd/server/setup.go`、`gateway/internal/service/chat_history.go`、`chat_history_persister.go` | chat_history_persister_sql_test.go 追加 2（parity 钉死 + 生产者门控） |
| P2-E 标签读 500 | `gateway/internal/service/chat_history.go`（getMessagesFromDB / ensureSessionAccess） | 与 P2-D 共用 + handler 套件回归 |
| P2-F 问候 TTL | `app/services/growth_dashboard_service.py` | tests/unit/test_dailyflow_p2_context_line_ttl.py（2） |
| P2-G today 过滤 | `app/services/daily_task_selection_service.py`、`app/api/v1/tasks.py` | tests/unit/test_dailyflow_p2_today_filter.py（4） |
| P2-H 胶囊再生 | `app/services/curiosity_capsule_service.py`、`app/api/v1/capsules.py` | tests/unit/test_dailyflow_p2_capsule_today_window.py（4） |
| P2-J Update 别名 | `app/schemas/task.py` | tests/unit/test_dailyflow_p2_task_type_aliases.py（15） |
| P2-I | 不改码（判定：数据未生成） | 取证记录于上文 |

**测试账**：新增 25 用例先红后绿；回归 Go `internal/service`+`internal/handler`
两包 ok（CGO_ENABLED=0），pytest 邻域 `test_capsules_api`+`test_growth_dashboard_service`
+`test_task_complete_and_update_api`+`test_task_quick_actions_api` 18 passed、
`test_growth_api`+`test_task_complete_galaxy_outbox`+`test_daily_sprint_reminder`
14 passed。

## 剩余风险 / 备注

1. **存量重复行**：eval 用户 12 行（3c3cb8ef 与 fefd227a 各半）等历史双写数据留库
   供复核，未清理（共享库，属 C 档）；读路径按引擎伪会话查询，不受孤儿行影响
   （会话列表 SQL 已排除全零会话，`3c3cb8ef` 孤儿会话可能出现在按消息聚合的
   会话列表里，量小，留待数据治理批）。
2. **滞留队列**：`queue:persist:history` 旧积压（eval 期 24–44 条）在生产者门控后
   不再增长；如需清空，置 `CHAT_PERSISTER_ENABLED=true` 跑一次即可——派生对齐后
   对引擎已落库行全部幂等跳过。
3. **问候线成本**：最坏每活跃用户每 30 分钟一次 rule/AI 生成；rule 兜底无 LLM 成本，
   AI 路径沿用既有生成管线。
4. **today 语义变化**：旧无日期任务退出 today 列表属预期产品语义（见 P2-G 备案），
   若产品要"无限期可见"需引入收件箱概念，另行立项。
5. **胶囊异步化**：首生成 24.7s 同步未动（P1-C 同族债），本批仅保证每日至多一次。
6. **预存失败**：`test_task_quick_actions_api::test_skip_task_marks_task_abandoned`
   在干净 faaae378 上即失败（test 的 fake 缺 `route_history_decision_id` 形参），
   与本批无关，未动。
7. `backend/.env` 为 worktree 内 gitignored 真实副本；uv 临时重解析产生的
   `uv.lock` 改动已还原，`.venv` 收工已清。
