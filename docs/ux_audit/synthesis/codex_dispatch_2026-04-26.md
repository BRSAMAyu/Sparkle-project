# Sparkle UX Audit — Codex 派发综合（Round 1–12 汇总）

**日期**：2026-04-26
**汇总自**：reviewer_a / reviewer_b 27 条 chain 审查 + accumulated_findings.md
**目的**：把多轮审查中发现的真实瑕疵升温为「用户能感知到的超能力」。本文按"文件冲突域 + 用户能力"划分 13 条并行执行 lane。每条 lane 是一份**完整可投递给 Codex 的提示**——已注明用户可见目标、现状证据、边界、禁区、验证方式，但**不规定具体修法**。

---

## 0. 给 Codex 的全局协作守则（每条 lane 都默认遵守）

1. **先审后改**：每条 lane 给定的"现状证据"都是 Round 1–12 审查时的快照，可能已经过时或部分被其他分支修复。**动手前必须 grep 当前代码状态确认问题仍存在**；如果发现问题已被修复或描述与现状不符，把发现写入该 lane 末尾的 `## 实际现状` 段落并停下。
2. **目标导向，方案自由**：本文给出的"建议方向"仅用于校准上下文。如果你在审查中找到更优解，可自行采用，但需在 PR 描述里说明为什么不走建议方向。
3. **边界与禁区**：lane 中的 `Bounds` 列出可触动文件，`Forbidden` 列出**绝对不能动**的文件（通常因为另一条并行 lane 正在改）。如果完成任务必须越界，**先停下创建 issue 描述冲突**，不要硬改。
4. **不要做 cleanup**：不允许顺手重构、改名、删注释、加日志、补 type hints。每条 lane 只交付该 lane 列出的能力。
5. **写测试**：后端用 pytest（asyncio_mode=auto），Go 用 `go test`，Flutter 用 `flutter test`。**每条 lane 必须新增至少一个直接验证用户可见效果的测试**（不是覆盖率）。
6. **遵守 Aurora 治理**：阅读 CLAUDE.md 中 53 条 governance rule。如改 kill switch / memory write / inferred extraction，本 lane 验收前必须跑 `bash scripts/run_all_rule_guards.sh`。
7. **Proto/DB schema 变更**：如改 `proto/*.proto`，必须 `make proto-gen`；如改 schema，必须 `alembic revision -m ...` + `alembic upgrade head` + `make sync-db`。
8. **报告产出**：交付时在 `docs/ux_audit/synthesis/lane_<id>_handoff.md` 写一份 ≤200 字交付简报，含：实际改了什么文件、用户现在能看到什么效果、跑通了哪些验证、有哪些已知遗留。

---

## 1. Lane 索引 & 并行编排建议

| ID | Lane | 核心用户能力 | 主要冲突域 | 推荐顺序 |
|----|------|-------------|-----------|----------|
| **A** | Galaxy 真相统一 + 跨页刷新 | 完成任务/复习错题 → 星图立即变深，且无双扣 | galaxy_service / task_service / error_book_mastery_sync / error_replan_bridge / mobile galaxy 协议 | **波次 1** |
| **B** | Aurora 信号开关启用 + Kill switch 健全 | 用户输入的所有信号真正进入 AI；运维能安全降级 | settings.py flags / idiographic / srl_phase / social_signal_bridge / state_aggregator / drill / .env.example | **波次 1**（独立配置层）|
| **C** | 跨会话记忆 + 胶囊偏好真正影响 AI | Aurora 在第二次对话引用上次内容、引用用户收藏的胶囊偏好 | prompts.py / context_manager.py / behavior_signal_collector.py / capsule_favorite_service / dual_core_router | 波次 1（与 A/B 不重叠）|
| **D** | 任务卡点 → Aurora 实时诊断 | 点"卡住了"后弹出基于当前状态的 Aurora 诊断而非静态文案 | models/task.py / api/v1/tasks.py / decision_loop.py / mobile stuck_help_sheet / task_execution_screen | 波次 2（依赖 B 信号开关已开）|
| **E** | Focus → 任务进度 + 学习时长 | 完成番茄钟后任务进度更新、学习总时长不再硬编码 0 | focus_service.py / event_bus.py 事件定义 / plans.py:1391 / mobile mindfulness_provider | 波次 2 |
| **F** | 冷启动建模 → 第一份计划无报错 | 新用户一次"开始规划"就能进入计划页，不报"计划生成没成功" | orchestrator.py:652 / planning_workflow.py:770 / modeling_chat_screen.dart / plan_routes.dart | 波次 2 |
| **G** | Achievement 死代码激活 + EventBus 重试 | 契约/连续学习/夜间等成就能解锁；瞬时错误不直接进 DLQ | event_bus.py / achievement_engine.py / achievement_event_consumer.py / contract_service.py | 波次 2 |
| **H** | 错题录入预处理质量 | 拍照错题先 OCR；分析失败时按学科 fallback；缺关联节点时给提示 | error_book_service.py（仅 OCR/_build_fallback_analysis）/ mobile error_list_screen | 波次 3（A 完成后再做）|
| **I** | 自适应规划接日历 | 考试前一天计划自动避开有冲突的时段 | adaptive_replanner.py / planning_workflow.py / aurora service.py | 波次 3 |
| **J** | Aurora 启动消息韧性 | daily startup API 失败有可见重试，不再静默降级；comeback 基于真实活跃 | chat_screen.dart（仅 daily startup hydration 段）/ aurora_daily_startup_repository.dart / aurora service.py:306 | 波次 3 |
| **K** | 推送可达性 + 偏好控制 | 间隔重复不会因宕机错过；周报通知打开就展开；per-type 偏好开关；通知列表点击韧性 | celery_tasks.py / notification_service.py / notification_center_service.py / mobile notification_list_screen / weekly_growth_narrative_card / learning_insights_overview_screen | 波次 3 |
| **L** | 跨页数据新鲜度 + RefreshIndicator | Galaxy/学习档案/成就页可下拉刷新；返回页面看到最新状态 | mobile galaxy_screen / learning_portfolio_screen / achievement screen | 波次 3 |
| **M** | Galaxy 节点复习 chat 体验 | 用户能在 chat 里看出在复习哪个节点；Aurora 知道掌握度 | mobile node_detail_sheet / chat_screen / aurora service.py（review_focus 扩展）| 波次 3 |
| **N** | 冲刺归档自动化 + Portfolio 口径统一 | 完成所有任务后即使跳过考后评估也归档；进行中/已完成数字含义一致；10 上限可分页 | exam_sprint_review_service.py / sprint_completion_screen.dart / learning_portfolio_screen | 波次 4 |

> **冲突标注**：每条 lane 的 `Forbidden` 字段会列出"另一条 lane 正在改的文件"。如果你拿到的两条 lane 同时列出对方为 Forbidden，先做完一条再做另一条。

---

## 2. Lane A — Galaxy 真相统一 + 跨页刷新

### 用户应当看到的效果
1. 用户完成一个 Sprint Pack 任务后，Galaxy 星图上该节点的颜色**立即**变深（不需要重启 app，不需要离开页面再回来）。
2. 用户复习一道错题后，Galaxy 星图也立即反映 mastery 变化。
3. 一道错题创建后，对应节点 mastery **只扣减一次**（按 error_type 权重，比如 knowledge_gap 扣 -10），而不是被双重处罚。
4. 用户完成任务后切到学习档案 / 成就页，看到的也是最新数据。

### 现状证据（Round 1–12 快照，请先验证仍存在）
- **Sprint Pack 0–1 vs 0–100 双刻度**：`backend/app/services/task_service.py:477` 用 `min(1.0, current_mastery + 0.25)` 以 0–1 写入；`galaxy_service.py:1396` 夹到 0.25 写入 DB。Mobile `mobile/lib/features/galaxy/data/models/galaxy_llm_protocol.g.dart:88` 用 `(json['mastery_score'] as num?)?.toInt()` 把 0.25 截成 0 → `galaxyMasteryRatio(0)=0` → 节点永远灰。
- **错题 mastery 双扣**：`error_book_service.py:350-361` 同步调 `ErrorBookMasterySyncService.apply_error_diagnosis`（已扣一次）；同时发布 `ErrorCreated` 事件 → `galaxy_event_consumer.py:78-156` → `error_replan_bridge.py:216-224` 仍无条件再调 `_update_mastery_from_error()` 二次扣减。注释说"已迁移到 ErrorBookMasterySyncService"但代码未删。
- **错题复习绕过 GalaxyService**：`error_book_mastery_sync_service.py:243-246` 直接 UPDATE `UserNodeStatus.mastery_score`，没走 `GalaxyService.update_node_mastery`，因此跳过 Outbox / 审计 / WebSocket 推送 → 复习后用户在 Galaxy 看不到变化。
- **任务完成 mastery 无 revision**：`task_service.py:480-486` 调 `update_node_mastery` 不传 revision，走 fallback UPSERT，多设备并发可能 last-write-wins。`galaxy_service.py:1402-1486` 的 atomic 路径需调用方传 revision。
- **Mobile invalidate 漏项**：
  - `task_provider.dart:412-421` `completeTask` invalidate `galaxyRefreshTrigger / planDetail / weeklyGrowthNarrative`，**漏了** `learningPortfolioProvider`、`achievementProvider`。
  - `error_book_provider.dart:454-464` `submitReview` invalidate 9 个 provider 但**完全没有 Galaxy** 相关 provider。

### Bounds（可触动）
- 后端：`backend/app/services/task_service.py`、`backend/app/services/galaxy_service.py`、`backend/app/services/error_book_service.py`、`backend/app/services/error_book_mastery_sync_service.py`、`backend/app/services/error_replan_bridge.py`、`backend/app/services/galaxy_event_consumer.py`（仅删冗余调用，不动其他订阅者）
- 移动端：`mobile/lib/features/galaxy/data/models/galaxy_llm_protocol.g.dart`、`mobile/lib/features/error_book/data/providers/error_book_provider.dart`、`mobile/lib/features/task/presentation/providers/task_provider.dart`（只动 `completeTask` 内 invalidate 列表）

### Forbidden（其他 lane 的领地）
- `mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart`、`task_execution_screen.dart` → Lane D
- `error_book_service.py` 中的 OCR / `_build_fallback_analysis` → Lane H
- `mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart` 的 RefreshIndicator → Lane L

### 关键决策点（请审查后选择）
- 真相是 0–100 还是 0–1？团队代码里两种刻度并存。**建议**：在 DB / API 层只用 0–100 整数（已有 ratio 转换函数），把 task_service `+0.25` 替换为 `+25`；如选择保留 0–1，则需在 mobile 端把 `toInt()` 改为 `toDouble()` 并校正 ratio 函数。**两条路都可行，但选择必须一致并记录在 ADR 里**。
- 错题 mastery 写入是该走 sync service 还是 EventBus 一条路？**建议**：保留 sync service（同步路径，写时立即可见），删掉 `error_replan_bridge._update_mastery_from_error`（异步重复路径）。但你需要确认 ErrorReplanBridge 不再依赖该函数返回值。

### 验证（必须）
1. 单元/集成测试：连续完成 4 个 Sprint Pack 任务（每个 +25），最终 mastery=100，颜色等级是 stage 4。
2. 集成测试：创建一道 knowledge_gap 错题 → mastery 只扣 -10（不是 -18），Galaxy WebSocket 收到一次 mastery_updated 事件。
3. 集成测试：复习一道 error → mastery 写入 → Outbox 写入 → WebSocket 客户端能收到 `node_mastery_updated`。
4. Flutter widget 测试：调用 `completeTask` 后 `learningPortfolioProvider` 和 `achievementProvider` 被 invalidate；调用 `submitReview` 后 `galaxyRefreshTriggerProvider` 计数 +1。

---

## 3. Lane B — Aurora 信号开关启用 + Kill switch 健全

### 用户应当看到的效果
1. 用户在对话中说"明天要考高数"、"TCP 很难"——这些信号被**捕获并写入 memory**，下次会话 Aurora 真的引用。
2. 用户加学习伙伴后，Aurora 的对话/计划建议中真的体现了伙伴维度（不再 shadow 模式空跑）。
3. 运维想把任意 Aurora 子系统降级时，能从 Admin API 一键切到 shadow（保留计算）或 off（彻底关闭）；shadow 模式真的"只算不写"，不会污染 DB。

### 现状证据
- **关键信号被一行 flag 关掉**：
  - `backend/app/config/settings.py:596` `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED: bool = False` → `memory_inferred_write_lane.py:443-445` 直接 return `disabled` → per-turn 推断写入完全不工作。
  - `backend/app/config/settings.py:320` `AURORA_STAGE33_SOCIAL_MODE = "shadow"` → `prompts.py:3276` 因 mode != live 不渲染社交段。
- **Shadow 模式存在三种不同语义（数据污染风险）**：
  - `idiographic_association_service.py:192` `compute_and_update()` 只检查 `mode == "off"`，shadow 时仍 upsert vectors / changepoints / associations + 发事件 + 写 cache → **shadow == live**。
  - `srl_phase_tracker_service.py:118` `handle_transition_event()` 同样 shadow == live，状态转换全部持久化。
  - 对比 `policy_scheduler_service.py:224` 与 `push_service.py:148` 才是正确的 tri-state（shadow 评估但不执行）。
- **核心服务无 kill switch**：`social_signal_bridge.py`、`state_aggregator/service.py`、`aurora/privacy.py` 全文无 `kill_switch / read_mode / KillSwitchBinding`。
- **Drill / Admin / 文档不足**：drill 脚本仅覆盖 stage 33-40（缺 18/19/21/23-31）；Admin API `memory_admin.py` 仅 stage 18/19/21；`.env.example` 没有任何 `AURORA_*_MODE` 条目。

### Bounds（可触动）
- 配置：`backend/app/config/settings.py`（**仅 flag 默认值**），`.env.example`
- 服务：`backend/app/services/idiographic_association_service.py`、`backend/app/services/srl_phase_tracker_service.py`、`backend/app/services/social_signal_bridge.py`、`backend/app/state_aggregator/service.py`
- Drill 脚本：`scripts/stage{18,19,21,23,24,25,26,27,28,29,30,31}/drill_transitions.sh`（按现有 stage33 模板新建）
- Admin API：`backend/app/api/v1/memory_admin.py`（扩展 endpoint）
- Rule guard：`scripts/rule_guard_manifest.tsv`（新增 shadow 语义一致性检查规则，命名规则按 CLAUDE.md AS-AZ 风格延续）

### Forbidden
- `backend/app/orchestration/prompts.py` → Lane C
- `backend/app/services/memory_inferred_write_lane.py` 的核心逻辑 → 不要改逻辑，**只改 flag 默认**
- `backend/app/services/capsule_favorite_service.py` / `behavior_signal_collector.py` → Lane C

### 关键决策点
- 把 `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED` 默认改 True 之前，**必须**先确认：(1) Rule Y（推断写入治理）guard 通过；(2) 用户级 opt-out 路径仍然能关；(3) 隐私 redact 链路活跃。
- `AURORA_STAGE33_SOCIAL_MODE` 默认改 live 之前，**必须**确认 social_signal_bridge 在 shadow 状态下确实会被尊重（先把 kill switch 加上，再切 live）。
- shadow 语义统一：建议规范化为「shadow = 计算+记录但不持久化、不发事件、不影响下游」。但 idiographic / srl 服务的 shadow 改造可能涉及把"持久化"这一段提取成 if-branch，请审查是否会破坏既有数据契约。

### 验证（必须）
1. 单元测试：`idiographic_association_service.compute_and_update` 在 shadow 模式下：(a) 不调用任何 DB upsert；(b) 不发布 `idiographic.updated` 事件；(c) 仍然返回计算结果。
2. 同上对 `srl_phase_tracker_service.handle_transition_event`。
3. 端到端：把 `SPARKLE_MEMORY_INFERRED_WRITE_ENABLED` 设为 True 后，模拟用户说"我下周要考高数"，断言 user_memory 表收到一条 inferred 写入。
4. Drill：每个新建的 drill 脚本能把对应 binding 切 off→shadow→live→shadow→off 并通过断言。
5. `bash scripts/run_all_rule_guards.sh` 全部通过。

---

## 4. Lane C — 跨会话记忆 + 胶囊偏好真正影响 AI

### 用户应当看到的效果
1. 用户第二次打开 chat 时，Aurora 在第一句就能引用上次会话内容（"我们昨天聊到 TCP 流量控制，今天先复盘一下吧"），且能自然带入时间感（"上周"/"昨天"/"刚才"）。
2. 用户收藏过的认知胶囊真的影响 Aurora 的行为：偏好深度内容的用户少看到碎片化推送，偏爱某科目的用户在该科任务上得到更细致的引导。

### 现状证据
- **Prompt 段太单薄**：`prompts.py:3407-3433` `_format_past_session_memory_section()` 只输出 bullet list（"你之前了解的关于用户的信息：…"），无引导指令告诉 LLM 何时该主动引用。
- **丢失上下文维度**：`context_manager.py:281-292` 已 fetch `subject_type / source_type / occurred_at / tags`，但 `prompts.py:3419-3421` 只取 `summary/text/content/title`。`occurred_at` 完全没用，AI 不知道记忆新鲜度。
- **胶囊偏好死代码**：`capsule_favorite_service.py:200-260` 的 `get_preferences()`（产出 `content_depth_preference / subject_affinity / recent_notes`）在 `context_manager.py / prompts.py` 中**零引用**。
- **行为信号收集器不订阅胶囊**：`behavior_signal_collector.py` 全文无 `capsule` 关键字，只处理 `task_feedback / task_abandoned / task_completed / plan_replanned / behavior_pattern`。
- **路由输入无胶囊字段**：`dual_core_router.py:41-66` `DualCoreRoutingInput` 没有任何内容偏好维度。

### Bounds（可触动）
- `backend/app/orchestration/prompts.py`（仅 `_format_past_session_memory_section` 与新增 capsule 偏好 section）
- `backend/app/core/context_manager.py`（capsule preference 注入）
- `backend/app/services/behavior_signal_collector.py`（订阅 `CAPSULE_FAVORITE_UPDATED / CAPSULE_FEEDBACK_SUBMITTED`）
- `backend/app/services/profile_event_consumer.py`（在 cache invalidate 之后调用 `get_preferences()` 写入推断画像）
- `backend/app/services/capsule_favorite_service.py`（仅暴露给 context_manager 的接口）
- 可选：`backend/app/orchestration/dual_core_router.py`（如要把 capsule 偏好引入路由）

### Forbidden
- `backend/app/config/settings.py` → Lane B（你不能改 flag 默认）
- `backend/app/services/idiographic_association_service.py / srl_phase_tracker_service.py` → Lane B
- `backend/app/services/memory_service.py` 的写入逻辑（写入开关在 Lane B；写入流程不动）

### 关键决策点
- 引导指令（"在合适时机主动引用上次内容"）应该作为系统 prompt 段，还是作为对话规则？建议放在 `_format_past_session_memory_section` 段头，给 LLM 明确触发条件（如"当用户问候 / 暧昧请求 / 第一句对话时主动衔接"）。
- 胶囊偏好放在 prompt 哪个层级？建议放在用户画像段附近，与"行为模式"并列，用极短的可读句子（一行内 3-4 个事实）。
- 是否引入 routing 维度：路由可以不动（最小改动），但 prompt 注入是必须。

### 验证（必须）
1. 集成测试：构造一段历史 `episodic_memory` → 调用 `build_system_prompt` → 断言 prompt 中包含时间标签（"上周"/"刚才"等）和引导指令。
2. 集成测试：用户收藏 3 个不同深度的胶囊 → `get_preferences()` 输出 `content_depth_preference="deep"` → prompt 中包含该偏好 → LLM 回复中（用 mock）能基于此调整内容深度。
3. 单元测试：`behavior_signal_collector` 收到 `CAPSULE_FAVORITE_UPDATED` 事件时，创建对应 cognitive fragment。

---

## 5. Lane D — 任务卡点 → Aurora 实时诊断

### 用户应当看到的效果
1. 用户在任务执行页点"卡住了"按钮，**不是**弹出当初任务卡里那段写死的"genericSuggestions"，而是 Aurora 基于当前任务进度、最近 N 步操作、上次类似情境的实时诊断。
2. 点"和 Sparkle 聊聊这个问题"不会销毁任务执行页，用户可以从 chat 退出回到原任务，计时器仍在跑。
3. 后端真正知道用户正在 stuck，可以基于这个信号触发 reflection / 自适应压缩 / 推送干预。

### 现状证据
- **没有 STUCK 状态**：`backend/app/models/task.py:47-51` `TaskStatus` enum 仅 `PENDING / IN_PROGRESS / COMPLETED / ABANDONED`。无 API 标记 stuck。
- **决策环路检查的是从未被设置的字段**：`backend/app/aurora/runtime_v1/decision_loop.py:641` `_is_stuck_task_scene()` 检查 `task_state.stage == "stuck"`，但全代码库无任何路径写入此值。
- **Sheet 内容是创建时静态文案**：`mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart:27-31` 读 `task.guideJson`，由 `task_card_generator.py:256-283` 在计划生成时写入。
- **Chat 跳转销毁任务页**：`task_execution_screen.dart:477` `_openStuckChat` 用 `context.go()` 替换栈；line 480-493 `_sendAuroraTrigger` 不传 stuck context，Aurora 进 `_is_stuck_task_scene` 永远为 False。

### Bounds
- 后端：`backend/app/models/task.py`（添加 STUCK enum + 数据库 migration）、`backend/app/api/v1/tasks.py`（新增 `POST /tasks/{id}/stuck` 端点）、`backend/app/services/task_service.py`（标记 + 发事件）、`backend/app/aurora/runtime_v1/decision_loop.py`（接通 stuck 信号）、`backend/app/aurora/runtime_v1/service.py`（确保从 stuck event 能拼出诊断 prompt）
- 移动端：`mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart`、`mobile/lib/features/task/presentation/screens/task_execution_screen.dart`、`mobile/lib/features/task/presentation/providers/task_provider.dart`（仅 stuck 相关 action）
- Migration：`backend/alembic/versions/`（新增 stuck enum migration）

### Forbidden
- `task_provider.dart::completeTask` 内 invalidate 段 → Lane A
- `focus_service.py` → Lane E

### 关键决策点
- stuck 是 task 状态还是 task event？建议 event（不污染状态机），但需要后端持久化便于追溯。
- chat 跳转：建议改为 `Navigator.of(context, rootNavigator: false).push(...)` 或用 Modal Sheet，保留任务执行页。
- Aurora 诊断：先用 task_state.stage = stuck 触发 micro-teaching 模式（基础设施已有 `STUCK_TASK_STAGE_TOKENS`），再让 stuck event payload 携带最近的步骤进度让 prompt 更具体。

### 验证
1. 集成测试：标记任务 stuck → 后端发布事件 → orchestrator 调用 prompt 时 `_is_stuck_task_scene` 返回 True → prompt 包含 micro-teaching 段。
2. Flutter 测试：点击 sheet 中"和 Sparkle 聊聊"，断言任务执行页未被销毁且计时器仍 active。
3. E2E：用户进入 task → 点 stuck → API 调用成功 → sheet 内容来源于实时调用而非 task.guideJson。

---

## 6. Lane E — Focus → 任务进度 + 学习时长

### 用户应当看到的效果
1. 用户完成一个绑定到任务的番茄钟后，对应任务进度更新（minutes_spent 累加）；如果完成了任务总时长，状态变 COMPLETED。
2. 计划详情页 / 学习档案页里的"累计专注时长"不再显示 0。
3. Aurora 能感知到用户专注了多久（调整后续任务难度）。

### 现状证据
- **focus.session.completed 事件丢 task_id**：`focus_service.py:174-186` payload 含 `session_id / duration_minutes / mastery_updates`，**不含** `task_id`。
- **EventBus 事件类零定义**：`event_bus.py` 全文无 `focus` 相关事件类。
- **硬编码 0**：`backend/app/api/v1/plans.py:1391` `"total_minutes_spent": 0,  # Would be calculated from focus sessions`。
- **Mobile 不 invalidate**：`mindfulness_provider.dart` grep 0 个 task provider invalidate。
- **轻微**：`focus_service.py:187-190` publish 失败用 `logging.warning` 静默吞，未走 DLQ。

### Bounds
- 后端：`backend/app/services/focus_service.py`（payload + 异常处理）、`backend/app/core/event_bus.py`（新事件类）、`backend/app/api/v1/plans.py`（plans.py:1391 实算）、`backend/app/services/task_service.py`（focus → task progress 的更新逻辑，新增方法即可）
- 移动端：`mobile/lib/features/focus/presentation/providers/mindfulness_provider.dart`（完成后 invalidate 任务 provider）

### Forbidden
- `achievement_event_consumer.py / achievement_engine.py` → Lane G（不要扩成就路径）
- `task_provider.dart::completeTask` → Lane A

### 关键决策点
- task 进度更新走同步还是 EventBus consumer？建议新建 consumer（focus.session.completed → 任务进度更新），保持 focus_service 单一职责。
- plans.py:1391 的 `total_minutes_spent` 该实时聚合还是 cache？建议从 FocusSession 表实算（用户量小，性能 OK），需要查询索引。

### 验证
1. 单元：focus_service.complete_session(task_id=X) 后事件 payload 含 task_id。
2. 集成：完成两个 25 分钟番茄钟（同 task）后任务的 minutes_spent=50，进度条更新。
3. API 测试：`GET /plans/{id}` 中 `total_minutes_spent` 反映真实聚合。

---

## 7. Lane F — 冷启动建模 → 第一份计划无报错

### 用户应当看到的效果
新用户完成 Aurora 建模后，**一次**点击"开始规划"就能进入计划页，不再看到"计划生成没成功"的错误卡片，按系统返回键也不会回到 onboarding。

### 现状证据
- **两轮才出 plan_id**：`planning_workflow.py:770` + `orchestrator.py:652-654` + `modeling_chat_screen.dart:729-732`。第一轮：`from_modeling_complete=True` 导致 fast_track_context 保持 None → orchestrator.py:652 跳过 build → 669 不注入 → session 进入 AWAITING_CONFIRM → 返回策略提案无 plan_id → mobile line 731 抛"计划已经开始生成，但入口还没准备好"。第二轮："开始规划"匹配 PLANNING_CONFIRM_PATTERNS 才成功。
- **报错文案误导**：modeling_chat_screen.dart:744-748 把正常中间态显示为"计划生成没成功"。
- **fallbackRoute 错误**：`modeling_chat_screen.dart:80-81` `RouteResilienceScope(fallbackRoute: UserRoutes.personaOnboarding)` → 按返回回到 `/onboarding/persona`，与 `_finish()` 行为不一致。
- **成功路径用 root navigator**：`modeling_chat_screen.dart:741` + `plan_routes.dart:163` `parentNavigatorKey: navigatorKey` → 进入计划页时底部 tab bar 消失。
- **遗漏 invalidate**：modeling_chat_screen.dart:738-740 缺 `learningPortfolioProvider`。

### Bounds
- 后端：`backend/app/orchestration/orchestrator.py`（第 650 行附近 fast_track 处理）、`backend/app/orchestration/planning_workflow.py`（line 770 附近 AWAITING_CONFIRM 流程）
- 移动端：`mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart`、`mobile/lib/features/plan/plan_routes.dart`、`mobile/lib/features/plan/presentation/screens/plan_detail_screen.dart`（仅 PlanDetailScreen.pop 行为）

### Forbidden
- `mobile/lib/features/task/presentation/providers/task_provider.dart` → Lane A
- 其他 modeling 相关已 ✅ 的部分（如 tension 追踪、多轮对话）

### 关键决策点
- 选择 A：在第一轮就把 `fast_track_context` 构造好（即使是从 modeling_complete），让 orchestrator 直接进入 generating。
- 选择 B：让 mobile 端识别 AWAITING_CONFIRM 是中间态而非错误，自动发送第二轮"开始规划"。
- **建议 A**——更纯净，减少 mobile 端胶水代码。

### 验证
1. 集成：从 modeling_complete=True 直接调用 generate_plan，第一次返回就含 plan_id，无 AWAITING_CONFIRM。
2. Flutter widget 测试：成功生成后导航到计划页时底部 tab bar 仍可见；按返回键到 home 而非 onboarding。

---

## 8. Lane G — Achievement 死代码激活 + EventBus 重试

### 用户应当看到的效果
1. 契约/连续学习/夜猫子等成就在符合条件时真能解锁。
2. 接近解锁的成就（25/50/75% 进度）有持久可见的提示，不只是 chat 里 3 秒文字。
3. 网络抖动 / DB 连接瞬断不会让事件直接进 DLQ；用户操作产生的事件会被重试到成功或确实超过 max_retries。

### 现状证据
- **8 个事件类型从未触发**：`achievement_engine.py:91-119` 定义了 `CONTRACT_COMPLETED / CONTRACT_FAILED / MUTUAL_STUDY / HIDDEN_TRIGGER / SPRINT_STARTED / SPRINT_ABANDONED / DAILY_CHECKIN / WEEKEND_WARRIOR`，但生产代码全无 `process_event(...)` 调用。`ContractService.check_contract_status:2514-2544` 检查到契约结束但不调成就。
- **achievement.progress 无消费**：`_publish_achievement_progress:1322-1334` 发布事件，mobile 端无 `achievement_progress` WebSocket handler。
- **Milestone 仅短暂 chat 文字**：`chat_notifier_actions.dart:604` 仅显示 `lastActionStatus: 'milestone_reached'` 3 秒。
- **EventBus retry 路径死代码**：`event_bus.py:1161-1173` `_process_stream_message` 回调失败直接 `_move_to_dlq`，**完全不调用** `_handle_failed_message`（line 911-951）的 retry/DLQ 决策；`_requeue_for_retry`（line 871-909）从未被引用。
- **孤儿事件**：`task.started / plan.created / user.registered / reflection.completed / trait_observed / coldstart_completed / user_settings.updated / calendar.event.* / mastery_updated_from_error / Card Protocol 7 类` 等无 consumer。

### Bounds
- 后端：`backend/app/core/event_bus.py`（_process_stream_message 接通 retry）、`backend/app/services/achievement_engine.py`（仅注释/触发桥接，不动核心逻辑）、`backend/app/services/achievement_event_consumer.py`、`backend/app/services/contract_service.py`（解锁触发）、可选新建 daily_checkin / weekend_warrior 触发点
- 移动端：`mobile/lib/features/chat/presentation/providers/chat_notifier_actions.dart` 或一个新的 milestone toast widget（让进度提示真正持久可见）

### Forbidden
- `mobile/lib/features/achievement/...` 主流程已 ✅，不动主链路
- `focus_service.py` → Lane E

### 关键决策点
- DLQ vs retry 平衡：**建议** max_retries=3 + 指数退避（已有），超过才进 DLQ。`_handle_failed_message` 已实现，只需在 `_process_stream_message` 调用它。
- 8 个孤儿事件类型：先评估其中哪些是"已废弃定义"哪些是"待接线"。建议 (a) `WEEKEND_WARRIOR / DAILY_CHECKIN`：通过新 Celery 任务每日扫描；(b) `CONTRACT_*`：在 ContractService.check_contract_status 完成时直接触发；(c) `MUTUAL_STUDY / HIDDEN_TRIGGER / SPRINT_STARTED / SPRINT_ABANDONED`：先创 issue 标记 wontfix 或定义触发点。
- 孤儿事件审计：在 `event_bus.py` 的事件类型中加注释（"consumer in service X"），让审计可读化。

### 验证
1. 单元：模拟 consumer 异常 1 次 → 第 2 次成功，`_handle_failed_message` 路径被调用，事件不进 DLQ。
2. 模拟 3 次失败 → 第 4 次进 DLQ。
3. 集成：契约完成 → ContractService 调用 → AchievementEvent.CONTRACT_COMPLETED 触发 → 解锁。
4. Flutter widget 测试：milestone 25% 时显示 toast/snackbar 而非仅 lastActionStatus。

---

## 9. Lane H — 错题录入预处理质量

### 用户应当看到的效果
1. 用户拍照错题，无论文字描述长短都先 OCR 提取一遍。
2. 创建错题后无法关联到任何节点时，UI 给出"添加学科 / 关联课程"的引导，不是空着。
3. 英文错题（如英语语法错）的 fallback 分析不会被一律分类为 knowledge_gap。

### 现状证据
- **OCR 阈值偏激**：`error_book_service.py:266` `error.question_image_url and (not error.question_text or len(error.question_text) < 10)` → 12 字符的描述就跳过 OCR。
- **空关联静默**：`error_book_mastery_sync_service.py:170-172` `linked_knowledge_node_ids` 为空直接返回空。前端无提示。
- **Fallback 仅中文**：`error_book_service.py:600-608` `_build_fallback_analysis` 仅检查 "指针/计算/公式" 等中文关键词。

### Bounds
- 后端：`backend/app/services/error_book_service.py`（仅 OCR 触发判定 + `_build_fallback_analysis`）、`backend/app/services/error_book_mastery_sync_service.py`（空节点路径返回结构）
- 移动端：`mobile/lib/features/error_book/presentation/screens/error_list_screen.dart` 或 detail（新增"无关联节点"引导卡）

### Forbidden
- `error_book_service.py:350-361` analyze_and_link 主流程 + `error_replan_bridge.py` → Lane A（已被 Lane A 修双扣）
- `mobile error_book_provider.dart submitReview` → Lane A

### 关键决策点
- OCR 触发：建议改为「有图片就 OCR」+ "如果文本字段非空，OCR 结果作为补充而非替换"（merge 策略避免误覆盖用户手输）。
- Fallback：扩展为按 subject / language detect 的多分支，或直接接最简单的 LLM 调用作为兜底。建议前者（更可控）。

### 验证
1. 单元：12 字符文字 + 图片错题 → OCR 被触发，结果合入 question_text 而非覆盖。
2. 单元：空 linked_knowledge_node_ids → 后端返回 hint 字段；mobile 渲染对应 UI。
3. 单元：英文错题 → fallback 不再固定 knowledge_gap。

---

## 10. Lane I — 自适应规划接日历

### 用户应当看到的效果
明天用户有考试或上课，今天的自适应压缩/计划生成不会安排在那个时段；考前一周开始压缩计划时，会避开当周的明确冲突。

### 现状证据
- **adaptive_replanner / planning_workflow 完全不引用 calendar**：grep 0 个 `calendar` 关键字。`should_compress` 仅 `completion_rate < 0.5 && days_left <= 5`。
- **daily startup 也不参考 calendar**：service.py 个性化消息无日历感知。
- ✅ `_get_calendar_context` 实现完整、kill switch 默认 live、任务可同步到日历事件。基础设施齐全，只缺消费方。

### Bounds
- 后端：`backend/app/orchestration/adaptive_replanner.py`、`backend/app/orchestration/planning_workflow.py`、`backend/app/aurora/runtime_v1/service.py`（daily startup 段）

### Forbidden
- `mobile/lib/features/calendar/` → 不动
- 日历同步链路已 ✅，不要重写

### 关键决策点
- adaptive_replanner 接 calendar：建议只在 `should_compress` 后的 build_compressed_sprint_day_spec 增加"避开冲突时段"约束，而非重构整套逻辑。
- daily startup 接 calendar：第一句问候后追加"今天 14:00 你有 X 课，建议把 Y 任务放在早上完成"。

### 验证
1. 单元：用户日历 14:00-15:30 有事件 + completion_rate 40% + days_left=3 → 压缩任务被调到 9:00-10:00。
2. 集成：daily startup 在用户有当日 / 临近日历事件时引用具体时间。

---

## 11. Lane J — Aurora 启动消息韧性

### 用户应当看到的效果
1. daily startup API 失败时，用户看到一个轻量"今日加载失败 重试"的 banner，不再静默掉。
2. comeback 检测基于真实活跃（最后任务完成 / 最后消息发送），不是 last_login_at。
3. demo 模式不再硬编码"计算机网络/TCP"，而是基于用户真实学科或回退到通用文案。

### 现状证据
- **静默吞**：`chat_screen.dart:424-426` `_hydrateDailyStartupIfNeeded` 失败时 `catch (_) { return false; }`；line 369-371 `examSprintDashboardProvider.future.timeout(5s)` 硬超时也 return false。
- **comeback 基于登录**：`backend/app/aurora/runtime_v1/service.py:306` 用 `user.last_login_at`，变量名虽叫 `last_activity_at` 但实际是登录时间。
- **demo 硬编码**：`aurora_daily_startup_repository.dart:22-29` 返回 "计算机网络"+"TCP 流量控制"。
- **galaxy_screen.dart:2710** `contributionStats` error 返回 `SizedBox.shrink()` 也是同类静默。

### Bounds
- 移动端：`mobile/lib/features/chat/presentation/screens/chat_screen.dart`（仅 daily startup hydration 段，~370-430）、`mobile/lib/features/aurora/data/repositories/aurora_daily_startup_repository.dart`、`mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`（contributionStats error 处理）
- 后端：`backend/app/aurora/runtime_v1/service.py`（仅 `get_comeback_context` 中 last_activity 字段来源）

### Forbidden
- chat_screen 其他段（如 WebSocket 重连 → 已 ✅）
- aurora service.py 中 daily_startup 的主流程

### 关键决策点
- 真实活跃时间：建议从 `user_activity_log` 或最近 `task.completed / message.sent` 事件推导，存到 user.last_activity_at 字段（如无则加 migration）。
- daily startup 失败 UI：建议沿用 chat 的 SnackBar 风格 + 按钮"重试"，不要全屏错误。

### 验证
1. Flutter widget：daily startup API 失败 → SnackBar 显示，点击重试调用一次。
2. 单元：用户连续 5 天有 task.completed 但未重新登录 → comeback 不触发。
3. 单元：demo 模式 + 用户学科 ≠ 计算机网络 → 不返回 TCP 文案。

---

## 12. Lane K — 推送可达性 + 偏好控制

### 用户应当看到的效果
1. 间隔重复提醒在用户的某个间隔（1/3/7/14/30 天）即使因系统宕机错过当日，第二天会被补送。
2. 周报通知点开后周报卡**自动展开**显示 highlights，无需用户再点。
3. 用户能在设置里分别关闭"复习提醒"和"冲刺提醒"。
4. 通知列表点击通知不会因为深链栈无效而失败。

### 现状证据
- **精确匹配错过则丢失**：`celery_tasks.py:1150` `_spaced_repetition_due_interval_days` 用 `elapsed_days in (1,3,7,14,30)` → day 7 被跳过则 day 8 永久丢失。无 grace 窗口。
- **周报展开常量缺失**：`celery_tasks.py:1689` 推送 `?initialPanel=weeklyNarrative`，`learning_insights_overview_screen.dart:25-27` 仅定义 `panelSimulation/panelTheater/panelReport`；`weekly_growth_narrative_card.dart:17` `_expanded=false` 硬编码。
- **per-type 偏好缺失**：`NotificationPreferences` 仅 `enable_system / enable_interventions`，6 种推送中只有 interventions 受 enable_interventions 控制。
- **路由韧性差**：`notification_list_screen.dart:87` 用 `context.push` 而非 `RouteResilience.openExternalRoute()`；line 94 用 `handleDeepLink` 而非 `handleExternalDeepLink`。
- **空通知列表无引导**：line 29-30 仅 "No new notifications"。
- **500 用户上限**：celery_tasks.py:1250/1265、1757-1817。

### Bounds
- 后端：`backend/app/core/celery_tasks.py`（间隔窗口 + 周报路由 + 500 上限）、`backend/app/services/notification_service.py`（per-type 偏好检查）、`backend/app/services/notification_center_service.py`（per-type 偏好接入）、`backend/app/models/notification_*.py`（preferences 字段扩展 + migration）
- 移动端：`mobile/lib/features/insights/.../learning_insights_overview_screen.dart`（panelWeeklyNarrative 常量 + initialPanel handling）、`mobile/lib/features/insights/.../weekly_growth_narrative_card.dart`（initialExpanded 参数）、`mobile/lib/features/home/presentation/screens/notification_list_screen.dart`（路由韧性 + 空状态）、`mobile/lib/features/settings/...`（per-type toggle UI）

### Forbidden
- `mobile/lib/core/services/push_navigation_service.dart` 主流程已 ✅
- `notification_service._should_push_notification` 既有 `enable_system / quiet_hours` 不要拆掉

### 关键决策点
- 间隔窗口：建议改为「elapsed_days >= interval AND elapsed_days < interval + grace_days(2)」，并加 dedup 防重复推送。
- per-type：建议在 `NotificationPreferences` 扩展 `disabled_types: list[str]`（开放白盒，未来不必再加字段）。
- 500 上限：替换为分页+游标扫描，每批 200，无总上限。

### 验证
1. 单元：interval=7, elapsed=8 + 无前一天发送记录 → 触发。
2. Flutter：路由 `/learning/insights?initialPanel=weeklyNarrative` → 周报卡 initialExpanded=true。
3. Flutter：通知列表点击 → `RouteResilience.openExternalRoute` 被调用。
4. 集成：用户 disabled_types=["spaced_repetition"] → 间隔重复推送被抑制；冲刺提醒仍发送。

---

## 13. Lane L — 跨页数据新鲜度 + RefreshIndicator

### 用户应当看到的效果
1. Galaxy 星图、学习档案、成就页均支持下拉刷新。
2. 用户从其他页面回到这三个页面时，看到的是最新数据（不靠 SSE 也能刷）。

### 现状证据
- **3/4 关键页缺 RefreshIndicator**：grep 确认 Galaxy、学习档案、成就页均无 `RefreshIndicator`，只有任务列表有。
- **AutomaticKeepAliveClientMixin 副作用**：`galaxy_provider.dart` 导航回 Galaxy 时不重新加载，依赖 SSE。

### Bounds
- 移动端：`mobile/lib/features/galaxy/presentation/screens/galaxy_screen.dart`、`mobile/lib/features/plan/presentation/screens/learning_portfolio_screen.dart`、`mobile/lib/features/achievement/presentation/screens/achievement_screen.dart`（或对应 main screen）

### Forbidden
- `task_provider.dart` invalidate 列表 → Lane A
- contributionStats error 处理 → Lane J

### 关键决策点
- RefreshIndicator 触发哪些 invalidate：每个页面对应自己的核心 provider + 跨页相关。

### 验证
- Flutter widget：在每个页面执行下拉手势 → 对应 provider 被 invalidate 一次。

---

## 14. Lane M — Galaxy 节点复习 chat 体验

### 用户应当看到的效果
1. 进入复习 chat 后顶部有明显的 banner/indicator（"正在复习：TCP 流量控制 · 当前掌握度 60%"），用户多轮对话后仍能辨识。
2. Aurora 收到的 initial_context 不只是节点 id，还有 mastery、学习次数、最近错题 — 复习内容能基于这些定制。
3. mastery=0 时按钮文案改成"开始学习"而非"开始复习"。
4. 节点详情 sheet 渲染 description / keywords。

### 现状证据
- **chat 无 review banner**：grep `review_node` 在 chat_screen.dart 无匹配；`chat_mode='study_plan'` 仅影响 starters。
- **initial_context 太单薄**：`node_detail_sheet.dart:129-132` + `service.py:765-777` 仅传 `{review_node, node_label}`。
- **按钮文案不变**：node_detail_sheet.dart:342-348 mastery=0 时文案仍"开始复习"。
- **description/keywords 未渲染**：node_detail_sheet.dart:206-254 grep 0 个 description/keywords。

### Bounds
- 移动端：`mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart`、`mobile/lib/features/chat/presentation/screens/chat_screen.dart`（仅顶部 banner，与 Lane J 不冲突）
- 后端：`backend/app/aurora/runtime_v1/service.py`（`_review_focus_from_context` 扩展接受更多字段）

### Forbidden
- chat_screen 其他段 → Lane J
- aurora service 中 daily_startup → Lane J

### 关键决策点
- banner 数据源：建议从 chat session 的 metadata 中取（已有 channel），不要新加 API。
- initial_context 字段：mastery / last_review_at / recent_error_count / weak_subareas（节选）。

### 验证
1. Flutter widget：进入 chat with `?review_node=X` → banner 渲染 X 名称 + mastery。
2. 集成：调用 prompt 时 initial_context 包含 mastery 字段；prompt 中体现该 mastery。

---

## 15. Lane N — 冲刺归档自动化 + Portfolio 口径统一

### 用户应当看到的效果
1. 用户完成冲刺所有任务后即使跳过"考后评估"，学习档案也显示该冲刺为 completed。
2. 学习档案中"已完成 / 进行中"两组的"掌握 X 节点"含义一致（都是节点计数 OR 都是百分比，不混用）。
3. 用户做满 10 个以上冲刺后，最早的归档不会消失（分页 / 加载更多 / 完整列表）。

### 现状证据
- **跳过评估则不归档**：`exam_sprint_review_service.py:393-414` 的 portfolio active 判定基于 `plan.is_active`，仅 `submit_post_exam_review` 才归档。
- **数字口径不一致**：line 374 已完成用 `covered_topics_after`（节点计数），line 397 进行中用 `plan.mastery_level * 100`（百分比换算）。
- **MAX_ARCHIVE_ENTRIES=10 截断**：line 61 + 1043-1044 `entries[-10:]`。

### Bounds
- 后端：`backend/app/services/exam_sprint_review_service.py`（自动归档触发 + portfolio 数字字段统一 + 分页）
- 移动端：`mobile/lib/features/plan/presentation/screens/sprint_completion_screen.dart`、`mobile/lib/features/plan/presentation/screens/learning_portfolio_screen.dart`、`mobile/lib/features/plan/presentation/providers/learning_portfolio_provider.dart`

### Forbidden
- modeling_chat_screen.dart → Lane F
- task_provider.dart → Lane A

### 关键决策点
- 自动归档触发点：建议在 sprint 任务全部 completed 时立即归档（task_service 中钩子），考后评估变成"补充"而非"必须"。
- 口径统一：建议两组都展示节点计数，把进行中的 `plan.mastery_level * 100` 转换为节点计数（用 mastery≥60 阈值，与已完成口径一致）。
- 分页：portfolio API 增加 cursor 分页，移动端"加载更多"按钮。

### 验证
1. 单元：sprint 全任务 completed → portfolio 显示 status=completed。
2. 单元：进行中冲刺的 `mastered_topics_count` 与已完成口径一致。
3. 集成：用户做 12 个冲刺，列表能加载完整，无丢失。

---

## 16. 共用验收清单（每条 lane 完成时检查）

```
□ grep 验证现状证据中的 file:line 仍有问题（或写明已修）
□ 仅触动 Bounds 列出的文件，未触 Forbidden
□ 新增 ≥1 个直接验证用户可见效果的测试
□ 后端：pytest 通过 + 影响域内的 acceptance scripts 通过
□ Go：go test ./... 通过（如改 gateway）
□ Flutter：flutter analyze + flutter test 通过
□ 如改 proto：make proto-gen 通过且 Go/Python/Dart 编译
□ 如改 schema：alembic upgrade head + sync-db
□ 如改 kill switch / inferred / privacy：bash scripts/run_all_rule_guards.sh 通过
□ 在 docs/ux_audit/synthesis/lane_<id>_handoff.md 写交付简报
□ 不在产品代码中加注释解释这次任务（仅写非显然的 why）
□ 提交 PR 标题格式：fix(ux-audit): lane <id> — <能力>
```

---

## 17. 暂不派发 / 仍待审计

以下 chain 在 audit_state 标 done 但 reviewer 文件丢失，或还未进入审查队列。**Codex 不要主动修这些**，等下一波审查产出真实证据：

- C04（错题→修复任务橙色卡）— 间接被 Lane A 覆盖部分
- C20（Sprint Pack 端到端集成）— 间接被 Lane A 覆盖
- D01（离线/弱网）— 缺 reviewer 文件
- D07（设置/隐私控制）— Reviewer A 完成但被覆盖丢失
- E01 Major（Proto 13 RPC 无 Go 集成）— 仅在 Flutter 真需要时才修，先标 wontfix
- E06 Major/Minor、E09、E11、E13–E19 — 大部分仍在 reviewer 队列中
- E18（Plan health score 计算准确性）— 未审，可能与 Lane I 关联

---

## 18. 给"总指挥"的协作提示

1. **波次启动**：建议 1 次启动 4–5 条 lane，让它们在不同分支并行。第一波建议 A、B、C、F（文件冲突最少且影响最深）。
2. **波次间合并**：每波次结束做一次 `main` 合并 + smoke test，再启动下一波。
3. **冲突处理**：如两条 lane 都需要碰某文件（如 `prompts.py`），先做 Lane B 的 flag 改动 → merge → 再让 Lane C 读取已开启状态写 prompt 段。
4. **回归基线**：每波合并后跑 `make local-final-signoff`，把当前能跑通的 acceptance script 数固化到 baseline。
5. **架构师只做监督**：你（Claude / Architect）不写代码，只在每波完成后审 handoff 文档 + 抽查 1-2 条 lane 的真实交付，决定下一波启动哪几条。

---

**结尾自检**：本文出 13 条主 lane + 4 条暂不派发，覆盖 27 条已审 chain 中约 38 条 Critical + 30 条 Major 发现。每条 lane 都给出了「用户能感知到的效果 → 当前断点证据 → 边界与禁区 → 决策建议 → 验证方式」的完整闭环，但**不规定具体修法**——把代码空间留给 Codex。
