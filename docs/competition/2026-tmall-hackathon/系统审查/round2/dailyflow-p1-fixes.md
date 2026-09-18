# 每日流实测 P1×4 + P2×1 修复批（dailyflow-p1-fixes）

- 基线：`efb1567a`（origin/main，含 781c0280 exam 修复批）
- worktree：`Sparkle-sysrev/wt4`
- 关联报告：`docs/competition/2026-tmall-hackathon/多端实测/daily-flow-eval.md`（023cded3）
- 验证：pytest 定向套件（15 passed）+ Go 定向套件（service/handler ok，CGO_ENABLED=0）
- 红绿纪律：每项先写失败测试再修复，全部转绿；无既有测试被改语义（仅 DF-3 套件追加用例）。

---

## DF-1 反思提交三日 3 败（P1）

**根因**（与 eval 推断一致，已用失败测试复现 400 原文）：
`backend/app/schemas/task_feedback.py` 的 `TaskFeedbackResponse` 声明
`created_at: str` / `updated_at: str`，而 ORM 给出 `datetime`。pydantic v2 的
ValidationError（ValueError 子类）被端点 `except ValueError` 吞掉转成
400——数据已入库但客户端视为失败（重复提交风险）。全仓其余 schema 均用
`created_at: datetime`，此处是孤例。

**修法**：两字段 `str → datetime`（JSON 线上格式仍是 ISO 字符串，移动端无感）。
eval 中 D3「fast-fail 未入库」是另一路径：`_get_and_validate_task` 对非
COMPLETED 任务抛 ValueError → 400，属合理校验，不动。

**红绿证据**：`backend/tests/api/test_task_feedback_submit_api.py` 3 用例
（提交 200 + created_at 序列化、行已落库、重复提交为更新）。修复前 3 失败
（400 "Input should be a valid string"，与 eval 报文逐字一致），修复后 3 通过。

## DF-2 聊天历史不落库 / 会话列表空（P1，先核实）

**核实结论（psql 主仓 sparkle 库）**：
- eval 用户 `4fe87b78…`：`chat_messages` 4 条 USER / **0 条 ASSISTANT**、`chat_sessions` 0 行——**当时"真不落库"，eval 报告属实**。
- 但当前 main 栈实证 assistant 已落库（近 2 小时 52 条 ASSISTANT；引擎侧 RB-06 持久化在 eval 栈之后的 chat/memory 修复批中接通），`chat_sessions` 也有 107+ 行（引擎 checkpoint nudge `_ensure_session`）。
- 残留的真缺陷在**网关侧持久队列**：`ChatHistoryPersister` 从 initial commit 起就是死代码——`NewChatHistoryPersister` 无人调用，`queue:persist:history` 只进不出（eval 时积压 131，核实期仍有 24-44 条滞留，含 eval 的 assistant 回复原文）。
- 且该 persister 若被启动会 100% 失败，共 6 处潜在缺陷：
  1. INSERT 引用已被 gfix03 迁移删除的 `metadata` 列；
  2. `to_timestamp($7::bigint / 1000.0)` 把生产方的**秒**级时间戳当毫秒 → 1970 年；
  3. `session_id` 直插非 UUID 标签（"df-d2-s1"）→ uuid 类型报错；
  4. `ON CONFLICT (id)` 与复合主键 `(id, created_at)` 不匹配 → 42P10；
  5. role 直插小写 "assistant"，而 `messagerole` 枚举存的是 SQLAlchemy 成员名 `USER/ASSISTANT/SYSTEM` → 22P02；
  6. `updated_at` NOT NULL 无默认值，INSERT 不提供 → 23502；且单行失败会污染整个事务批。
  另有设计缺陷：引擎已持久化同一消息，无去重会造成 DB 回读双份。

**修法**（`backend/gateway/internal/service/chat_history_persister.go`）：
- 抽出 `chatMessageInsertSQL` / `chatSessionUpsertSQL` 常量：去掉 metadata 列；秒级
  `to_timestamp($6::double precision)`；冲突目标改 `(id, created_at)`；
  `NOT EXISTS`（session+role+content, created_at ±15s）对引擎已落库行去重；
  提供 `updated_at`。
- 新增 `resolveSessionUUID`（合法 UUID 直通；标签类 id 用 uuid5 派生稳定伪会话，重试幂等）与
  `normalizeChatRole`（枚举名归一，未知 role 跳过）、`parseMessageTimestampSeconds`（秒/毫秒/RFC3339 容错）。
- 复用生产者稳定 `msg.ID` + 每消息 savepoint，单行坏数据不再污染整批。
- `cmd/server/main.go`：`cfg.ChatPersisterEnabled`（新配置 `CHAT_PERSISTER_ENABLED`，
  **默认 true**）下以 bgCtx 启动 persister，优雅停机时 `Stop()`。

**红绿证据**：
- Go：`chat_history_persister_sql_test.go` 7 用例（SQL 无 metadata/秒级语义/冲突目标/去重守卫、
  伪会话确定性、时间戳解析、session upsert 秒级）。修复前编译红/断言红，修复后全绿。
- 端到端（一次性 harness，已删）：对共享 Redis/PG 实跑 DrainOnce——滞留队列清空；
  probe 消息以 `created_at=2026-09-18 19:02:29`（= to_timestamp(1789758149)，非 1970）落库、
  伪会话行进 `chat_sessions`；对引擎已落库的 10 条实时消息全部去重跳过（chat_messages 行数零增长）。
  probe 数据已清理。

## DF-3 诊断 422 冷启动死路（P1，非 781c0280 已修的数据结构项）

**根因**：eval 存档 `d1_diag.json` 实证 422 报文 = 「知识节点覆盖不足，至少需要 5 个不同知识领域」，
eval 账号的冲刺科目是**大学物理**。`_resolve_nodes` 对无题包科目（当前内置仅
计算机网络、数据结构）在模板选择之前就抛该错——即使用户补足 5 个节点，
`_select_templates` 依然无题可出，是纯误导性死路。

**修法**：`_resolve_nodes` 仅在科目命中题包时做 ≥5 领域校验；未命中题包时直接抛
可行动错误：「诊断暂支持的科目：计算机网络、数据结构；「大学物理」暂未内置诊断题包」。
不再为每个科目补题包打地鼠（那是 781c0280 的路线，已覆盖两大主科目）。

**红绿证据**：`test_exam_sprint_diagnostic_service.py` 追加
`test_diagnose_unsupported_subject_gives_actionable_error`：修复前断言失败
（报错即「知识节点覆盖不足」），修复后通过；原有 4 用例全绿未动语义。

## DF-4（eval 编号 DF-5）星图与学习行为零耦合（P1）

**根因**：`TaskService.complete` 的星图钩子只有两条：`task.knowledge_node_id`
非空走 `spark_node`；或 guide_json 带 sprint-pack 节点走冲刺激励。每日流的自建任务
两者皆无 → 3 天 4 任务后 unlocked/mastered/study_minutes 恒 0。

**修法**（复用现有 galaxy 服务，不造新轮子）：
- `GalaxyService.ensure_task_node(title, task_id)`：先按标题（大小写不敏感）精确匹配
  既有节点（点亮既有星辰而非复制）；未命中则按规范化标题 uuid5 物化**确定性任务星**
  （source_type=user_created、source_task_id 留痕），同主题重复学习在同一颗星上累积
  掌握度，不刷屏。
- `TaskService.complete`：无锚点任务完成后 fallback `ensure_task_node` +
  `spark_node(trigger_expansion=False)`——unlocked/mastered/study_minutes 立即响应真实学习。
- `GalaxyService.task_node_uuid`：uuid5(“sparkle:task-node”, 去空白小写标题)，跨重启稳定。

**红绿证据**：`backend/tests/unit/test_task_galaxy_coupling.py` 4 用例
（未关联任务完成→新星点亮+StudyRecord、同主题两任务共享一星且 study_count≥2、
精确标题点亮既有种子星不复制、task_node_uuid 确定性）。修复前 4 失败，修复后 4 通过；
`test_exam_sprint_diagnostic_service.py`（galaxy 回写相关）9 用例回归通过。

## DF-5（eval 编号 DF-9，P2）推送通道结构性静默

**核实结论**：celery 侧已被 main 修复（`task_default_queue=default`、`run_push_policy_scheduler`
显式路由 default、worker 消费 glm_batch——`scan_*` 等 shared_task 未显式路由的任务现落
default 可被消费，无需重复修）。**真正残留的是引擎内 APScheduler 智能推送循环的两个静默源**：

1. `PushService.process_all_users` INNER JOIN `PushPreference`：从未碰过推送设置的用户
   整个不可见（开发库 138/149 活跃用户无该行）。
2. `UserPushOptIn` DEFAULTS `enabled=False`（P3' 引入的产品级总开关）：从未显式 opt-in
   的用户在 `_send_push` 第一道闸就被跳过。两层叠加 ⇒ 渠道结构性静默，eval「3 天零产出」
   实为必然而非偶发（叠加测试时段 02:36–03:08 的静默时段属合理 DND，未改）。

**修法**：
- `settings.PUSH_OPT_IN_DEFAULT_ENABLED = True`（新配置，可 env 置 false 回到纯 opt-in）；
  `user_push_opt_in_service.DEFAULTS["enabled"]` 改读该配置——默认 **opt-out** 语义，
  用户仍可在 push-settings 一键关闭（显式落库 False 后不再打扰，P3' 的初衷不受影响）。
- `process_all_users` 改为评估全部活跃用户（`process_user_push` 已对缺失偏好行合成默认，
  P2' 已修 `user.push_preference is None` 解引用）。

**红绿证据**：`backend/tests/unit/test_push_default_coverage.py` 2 用例
（无偏好行用户被评估并触发、无 opt-in 行用户默认 enabled=True）。修复前 2 失败
（evaluated_users=0 / enabled=False），修复后通过；push 三套既有回归
（delivery/policy_compiler/recall_policy_guards）15 用例全绿。

---

## 汇总

| 项 | 文件 | 测试 |
|---|---|---|
| DF-1 反思 400 | `backend/app/schemas/task_feedback.py` | tests/api/test_task_feedback_submit_api.py（3） |
| DF-2 聊天持久化 | `gateway/internal/service/chat_history_persister.go`、`gateway/cmd/server/main.go`、`gateway/internal/config/config.go` | chat_history_persister_sql_test.go（7）+ e2e 实跑 |
| DF-3 诊断 422 | `backend/app/services/exam_sprint_diagnostic_service.py` | test_exam_sprint_diagnostic_service.py 追加 1 |
| DF-4 星图耦合 | `backend/app/services/galaxy_service.py`、`backend/app/services/task_service.py` | tests/unit/test_task_galaxy_coupling.py（4） |
| DF-5 推送静默 | `backend/app/services/push_service.py`、`backend/app/services/user_push_opt_in_service.py`、`backend/app/config/settings.py` | tests/unit/test_push_default_coverage.py（2）+ 回归 15 |

## 剩余风险 / 备注

1. **DF-2 去重窗口**：引擎落库与网关队列表created_at 相差 >15s 的极端时钟漂移会出现双行；
   同主机部署实测漂移 <1s。伪会话（非 UUID 标签）不会出现在按 session 的历史回读中，
   仅作为持久留痕——会话列表跨设备一致性依赖引擎侧 chat_sessions（已验证有写入方）。
2. **DF-2 灰度**：`CHAT_PERSISTER_ENABLED=false` 可一键回到引擎单写（现状）。
3. **DF-4 产品边界**：非内置科目从「误导 422」变「明确告知暂不支持」，并未扩题库；
   题包扩展仍走 781c0280 的 SprintPackRegistry 路线。
4. **DF-5 语义变化**：推送从 opt-in 变 opt-out（默认 True）。若产品仍要纯 opt-in，
   设 `PUSH_OPT_IN_DEFAULT_ENABLED=false` 即回退，测试不受影响（测试读 settings 默认值）。
5. **DF-4 星图增长形态**：自建任务标题会生成任务星（含 eval 式「Day 2·建立框架」这类标题），
   星图会出现任务名星辰；若产品想要更干净的语义归并，需后续接 embedding 归类
   （`auto_classify_task` 已存在，本次未启用以避免测试环境嵌入依赖）。
6. `test_exam_sprint_review_service.py::test_completed_sprint_auto_archives_without_post_exam_review`
   在干净 efb1567a 上即失败（与本批无关，预存失败，未动）。
7. 定向测试未跑全量套件（纪律要求）；两处新增配置均有默认值，未触碰 backend/.env。
