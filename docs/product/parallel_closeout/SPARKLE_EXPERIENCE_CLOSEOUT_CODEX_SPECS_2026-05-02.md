# Sparkle 完全体体验收口 — Codex 执行规格

> 日期：2026-05-02 | 分支：`codex/final-closeout-integration-2026-05-02`
> 目标：将已存在的后端能力完整呈现在用户面前。不重写后端，只补最小 BFF 聚合 + Flutter 落地。
> 约束：每个 agent 的产出是独立的功能模块，在各自目录下创建文件，互不侵入。

---

## 0. 全局约束（所有 agent 必须遵守）

### 0.1 后端：BFF 聚合模式

每个 agent 如需新建 BFF 端点，在 `backend/app/api/v1/experience/` 下创建独立路由文件。FastAPI APIRouter 各自独立，最后 merge agent 统一注册。

```python
# 每个 agent 创建自己的 router 文件，格式：
# backend/app/api/v1/experience/xxx_router.py
from fastapi import APIRouter
router = APIRouter(prefix="/experience", tags=["experience"])

@router.get("/xxx")
async def get_xxx(...):
    ...
```

### 0.2 Flutter：独立 feature 模式

每个 agent 的页面和 widget 在各自 feature 目录下创建，不修改其他 agent 的文件：

```
mobile/lib/features/<feature>/presentation/
├── pages/<new_page>.dart          # 页面
├── widgets/<new_widget>.dart      # 组件
└── providers/<new_provider>.dart  # 状态管理

mobile/lib/features/<feature>/
├── <feature>_routes.dart          # 独立路由定义
```

### 0.3 必须满足的 UX 约束

- **暗色模式**：所有颜色通过 `Theme.of(context).colorScheme` 获取，不硬编码
- **双语**：所有用户可见文字通过 `AppLocalizations` 获取，EN+ZH 均需提供
- **WCAG AA 无障碍**：所有交互元素有 `Semantics` 标签，对比度 ≥ 4.5:1
- **可撤销**：所有用户操作提供 undo（snackbar 或确认弹窗）
- **空状态**：数据为空时有引导性占位，不是白屏

### 0.4 冲突避免规则

- **不要编辑**：`app_router.dart`、`providers.dart`、FastAPI `__init__.py`、`docker-compose.yml`
- **不要编辑**：其他 agent 的 feature 目录下的任何文件
- **你自己的路由**：写在 `<feature>_routes.dart` 中，导出 `List<GoRoute>`
- **你自己的 provider**：写在 `<feature>/presentation/providers/` 中，独立文件
- **你自己的 i18n**：每个 agent 创建独立的 ARB 追加文件，命名 `_<agent_id>_en.arb`

---

## Agent A: 社区从社交 Feed → 目标问责空间

### A.1 用户最终感受

> 打开社区，第一眼看到的不再是帖子流，而是"我的承诺"、伙伴们的进度、共同目标的推进状态。我在这里感受到的是"有人在跟我一起往前走"，而不是"又一个社交网络"。

### A.2 当前状态

**后端已有**（完整，不需修改）：
- `backend/app/models/accountability.py` — `AccountabilityPartnership`（initiator_id, partner_id, initiator_goal, partner_goal, check_in_days, status, started_at）+ `AccountabilityCheckin`（partnership_id, user_id, content, mood, minutes, likes, encouragements）
- `backend/app/api/v1/accountability.py` — 完整 CRUD API：request/respond/mine/overview/dashboard/nudge/checkin/like/encourage/achievements/stats/timeline/heatmap
- `backend/app/services/accountability_mvp_service.py` — `PendingCommitment`（id, summary, due_at, subject_type, evidence_token, resolved_at）
- `backend/app/aurora/schemas/primitives.py` — `Commitment` schema（id, user_id, description, success_criteria, status PENDING/ACTIVE/FULFILLED/VIOLATED/RENEGOTIATED, deadline, witness_ids, evidence_refs）
- `backend/app/models/accountability_policy.py` — `AccountabilityPolicy` model

**前端已有**：
- `mobile/lib/features/community/` — 现有社区功能（Feed 风格），包含 community_main_screen, friends_screen, group_members_screen, group_search_screen, favorites_screen, accountability provider

**缺失**：
- 社区首页是 FeedPostCard 流，不是问责 Hub
- 无 CommitmentCard widget
- 伙伴观察/提醒缺四种用户控制（接受/拒绝/稍后/太频繁）
- 无 BFF 聚合端点统一返回问责 Hub 所需数据

### A.3 目标产出

**新建 BFF 端点**（`backend/app/api/v1/experience/community_router.py`）：

```
GET /experience/community-accountability
  返回:
    - my_commitments: List[CommitmentCardPayload] — 我的活跃承诺
    - partner_progress: List[PartnerProgressItem] — 伙伴今日/本周进度
    - shared_goals: List[SharedGoalItem] — 共同目标状态
    - squad_risks: List[SquadRiskItem] — 小队中需要关注的成员
    - helpable: List[HelpableItem] — 我可以帮助的人
```

**新建 Flutter**（均在 `mobile/lib/features/community/presentation/` 下）：

1. **AccountabilityHubScreen**（新页面，替代 community_main_screen 的首屏）：
   - 顶部：我的承诺卡片组（横向滑动），每张显示承诺内容、截止时间、见证人、当前进度
   - 中部：伙伴进度环（共同目标的可视化进度对比，非排名）
   - 下部：需要帮助的人 / 可以求助的人
   - 底部：进入 Feed 的次级入口（保留现有 Feed 为二级页面）

2. **CommitmentCard** widget：
   - 承诺内容摘要、截止日期、当前进度条、见证人（头像或名字缩写）
   - 允许伙伴提醒的边界开关（"允许提醒" / "暂时勿扰"）
   - 点击展开详情：成功标准、里程碑、证据链
   - 状态标签：进行中 / 即将到期 / 已完成 / 已违反

3. **Partner observation control**（四种操作按钮组）：
   - 接受提醒 → 开启通知
   - 拒绝 → 本次拒绝 + 可选原因
   - 稍后 → 1h/3h/明天
   - 太频繁 → 降低提醒频率

4. **AccountabilityHubProvider**（Riverpod）：
   - 调用 `/experience/community-accountability`
   - 管理承诺列表、伙伴状态、提醒边界

**保留不变**：
- 现有 Feed（FeedPostCard 流）降为二级页面，通过 Hub 底部入口进入
- 现有 accountability API 端点全部保留，BFF 聚合层在它们之上

### A.4 验收

- 打开社区 Tab，首屏是问责 Hub 而非帖子流
- 可以看到自己的活跃承诺卡片
- 可以看到伙伴的进度（非排名，而是"一起前进"的视觉）
- 伙伴发送提醒时，可选择接受/拒绝/稍后/太频繁
- Feed 仍然可访问（通过 Hub 底部入口）

---

## Agent B: Goal Detail 完整页面

### B.1 用户最终感受

> 点击一个目标，我看到的不再只是标题和状态。我能看到：这个目标的最低达标线是什么、我完成了多少、当前卡在哪里、哪些知识点是瓶颈、今天最应该做的一步是什么。

### B.2 当前状态

**后端已有**：
- `backend/app/models/goal.py` — `Goal` ORM 模型，字段完整：title, goal_type, description, status, target_date, mastery, progress, priority, is_primary, **minimum_acceptance_criteria** (JSON), domain_pack_id, plan_id, source, completed_at, metadata_payload
- `GET /aurora/spine/goals` — 返回活跃目标 + 仲裁结果（primary_goal_id, time_split, conflicts, rationale）
- `GET /aurora/spine/goal-graph/{goal_id}` — 返回 GoalWorldGraph（nodes + edges + bottleneck + focus suggestions）。Node 含 node_id, label, node_type（10 种）, mastery（0-1）, is_bottleneck, exam_weight, difficulty, trainability, mistakes
- `backend/app/signals/goal_world_graph.py` — `GoalWorldGraphService`，DB 持久化表 `goal_world_graph_snapshots`

**前端已有**：
- `mobile/lib/features/goal/` — 多目标切换（GoalSwitcher），MultiGoalDashboardCard
- 但无独立 Goal Detail 页面，点击目标只切换状态

**缺失**：
- 无独立 Goal Detail 页
- minimum_acceptance_criteria 前端无呈现
- GoalWorldGraph 瓶颈节点无移动端可视化
- 今日最小下一步无呈现

### B.3 目标产出

**新建 BFF 端点**（`backend/app/api/v1/experience/goal_router.py`）：

```
GET /experience/goal-detail/{goal_id}
  返回:
    - goal: {title, goal_type, status, target_date, mastery, progress, priority}
    - minimum_acceptance_criteria: {description, thresholds: [...]}
    - plan_health: {overall, phase_health, task_completion_rate}
    - current_phase: {name, progress}
    - todays_minimal_next_step: {task_id, title, type, estimated_minutes}
    - knowledge_bottlenecks: [{node_id, label, mastery, goal_impact}]
    - accountability_status: {partner_count, active_commitments, last_checkin}
    - related_sources: [{id, title, type, relevance}]
```

**新建 Flutter**（`mobile/lib/features/goal/presentation/`）：

1. **GoalDetailPage**（新页面）：
   - 顶部：目标标题 + 状态标签 + 进度环
   - 最低达标线卡片：显示达标条件和当前差距，"待确认"状态时可编辑
   - 知识瓶颈区：横向滚动的瓶颈节点，每个显示 mastery 和 goal impact
   - 今日最小下一步：突出显示的任务卡片，可直接操作（开始/完成）
   - 计划健康状态带
   - 社群问责摘要（链接到社区问责 Hub）
   - 相关资料来源

2. **GoalDetailProvider**（Riverpod）：
   - 调用 `/experience/goal-detail/{goal_id}`
   - 管理最低达标线编辑、确认状态

3. **MinimumCriteriaCard** widget：
   - 展示达标条件列表（每个条件前有 checkbox 风格的进度指示）
   - 如果未确认，显示"这是 Sparkle 为你建议的最低标准" + "确认" / "修改" 按钮

4. **GoalBottleneckStrip** widget：
   - 水平滚动的知识节点卡片
   - 每张显示节点名、掌握度、与目标的关系（"阻塞任务 X" / "影响阶段 Y"）

### B.4 验收

- 从首页 MultiGoalDashboardCard 点击目标 → 进入 GoalDetailPage
- 看到最低达标线（已确认或待确认）
- 看到知识瓶颈节点，点击可跳转 Galaxy 对应节点
- 看到今日最小下一步，可直接操作
- 看到社群问责摘要
- 所有数据来自后端已有能力，BFF 仅聚合

---

## Agent C: UnderstandingSnapshot — "Sparkle 懂我"面板

### C.1 用户最终感受

> 在 onboarding 结束时，Sparkle 展示"我对你的初步理解"——不是泛泛的好话，而是具体的、可纠正的认知。之后在首页和聊天中，我可以随时展开查看 Sparkle 当前的自我模型——它认为我是谁、证据是什么、置信度多少、哪里可能错了。

### C.2 当前状态

**后端已有**：
- `backend/app/services/aurora_control_surface_service.py` — `AuroraControlSurfaceService.build_snapshot()`：聚合 profile context, calendar context, last correction effect, task health, runtime state, self-model readout summary
- `backend/app/signals/self_model.py` — `SelfModelClaim` 完整字段（claim_id, claim, confidence, scope, evidence, counter_evidence, policy_effects, outcome, retract_conditions）
- `backend/app/aurora/runtime_v1/self_model.py` — `SparkleSelfModelService` runtime readout

**缺失**：
- 无独立 BFF 端点暴露 self-model 快照
- 前端完全没有 self-model 的任何呈现
- onboarding 建模对话后用户看不到"Sparkle 学到了什么"

### C.3 目标产出

**新建 BFF 端点**（`backend/app/api/v1/experience/understanding_router.py`）：

```
GET /experience/understanding-snapshot
  返回:
    - claims: [{claim, confidence, evidence_summary, scope, user_can_correct}]
    - recently_corrected: [{claim, correction, effect_on_policy}]
    - memory_declarations: [{type, content, persistence}]
    - envelope_style: {current_tone, current_verbosity, reason_for_style}
    - last_update_time, total_claims, high_confidence_ratio
```

**新建 Flutter**（放在 `mobile/lib/features/home/presentation/widgets/` 和 `mobile/lib/features/chat/presentation/widgets/`）：

1. **UnderstandingPanel** widget（可复用组件）：
   - 卡片式布局，按认知领域分组（学习习惯 / 能力水平 / 情绪模式 / 偏好）
   - 每个 claim 显示：自然语言描述 + 置信度指示（高/中/低）+ 证据摘要（"基于你最近 7 天的..."）
   - 用户可点击"纠正"→ 弹窗输入纠正 → 必须触发变化（memory claim / routing policy / task granularity / plan risk / knowledge bottleneck / wake policy 六选一）

2. 放置在三个位置：
   - **Onboarding 结束页**：modeling chat 结束后，展示 initial snapshot，强调"你可以纠正我"
   - **首页 Aurora 状态带展开**：在 home screen 顶部状态带，点击展开 UnderstandingPanel
   - **聊天详情抽屉**：在 chat 界面从状态栏下拉/点击，看到当前 self-model 摘要

3. **UnderstandingSnapshotProvider**（Riverpod）：
   - 调用 `/experience/understanding-snapshot`
   - POST 纠正后刷新快照

### C.4 验收

- Onboarding 结束后看到 initial self-model 快照
- 纠正一个 claim 后，系统确认"已更新"并显示影响范围
- 首页可随时展开查看当前 self-model
- 不展示任何内部 token 或 debug 值，只显示自然语言

---

## Agent D: Growth Chronicle + Learning Dashboard

### D.1 用户最终感受

> 在 Insights 里，我看到的不是冰冷的数字，而是一个关于我成长的故事。周叙事告诉我"这周的关键转折是什么"，学习仪表板告诉我"时间花在了哪、效率怎么样、薄弱点在哪"。而且每次重要的完成或失败后，我能看到"Sparkle 从中学到了什么"。

### D.2 当前状态

**后端已有**：
- `backend/app/signals/growth_chronicle.py` — `GrowthChronicleService`，`ChronicleEntry` 含 entry_type（milestone/turning_point/pattern_discovered/user_reflection）, title, narrative, evidence_refs, user_status（pending/confirmed/edited/rejected/hidden）, confidence
- DB 表 `growth_chronicle_snapshots`（user_id, entry_count, confirmed_count, payload JSONB）
- `GET /growth/dashboard` — 成长快照（在 `backend/app/api/v1/growth.py`）
- `GET /growth/weekly-narrative` — 周叙事
- `GET /growth/daily-context-line` — 首页问候语
- `backend/app/services/growth_dashboard_service.py` — 聚合 Task, FocusSession, KnowledgeNode, Plan, UserStreakStats, plan health

**前端已有**：
- `mobile/lib/features/insights/` — `LearningInsightsOverviewScreen`, `WeeklyGrowthNarrativeCard`
- `mobile/lib/features/report/` — report 路由和页面

**缺失**：
- 无 Growth Chronicle 完整页面（目前只有 WeeklyGrowthNarrativeCard 卡片）
- 无 Learning Dashboard（时间分布、效率、薄弱点雷达图）
- 无 ModelUpdateReceipt（"Sparkle 学到了什么"）
- 叙事只是数据呈现，缺少 Pattern → Action → Outcome 的故事格式

### D.3 目标产出

**新建 BFF 端点**（`backend/app/api/v1/experience/dashboard_router.py`）：

```
GET /experience/growth-dashboard
  返回:
    - chronicle_entries: [{entry_type, title, narrative, evidence_refs, timestamp, user_status}]
    - weekly_narrative: {title, story, key_insights, rejected_insights, next_week_suggestion}
    - time_distribution: [{category, hours, trend}]  — 学习时间分布
    - efficiency_metrics: {tasks_completed, avg_completion_time, on_time_rate}
    - weakness_radar: [{area, current_score, target_score, gap}]  — 薄弱点
    - knowledge_changes: [{node_label, mastery_before, mastery_after, reason}]
    - plan_stability: {interruptions, adjustments, abandonment_rate}
    - model_updates: [{trigger_event, what_sparkle_learned, what_changed, what_was_not_written}]
```

**新建 Flutter**（`mobile/lib/features/insights/presentation/`）：

1. **GrowthChroniclePage**（新页面）：
   - 时间线 UI：纵向滚动的时间线，每个节点是一个 ChronicleEntry
   - 里程碑/转折点用不同视觉标记（颜色、图标）
   - 已确认 vs 待确认 vs 被驳回用不同样式区分
   - 点击展开完整叙事、证据链
   - 用户可对每个 entry 选择"确认"/"编辑"/"驳回"
   - 顶部显示周叙事摘要

2. **LearningDashboardPage**（新页面）：
   - 学习时间分布：柱状图/热力图（按天+类别）
   - 效率指标：环形图（完成率、准时率、平均时间）
   - 薄弱点雷达图：多轴雷达图，标注 gap
   - 知识掌握变化：上升/下降箭头 + 原因
   - 计划稳定性：中断次数、调整次数、放弃率

3. **ModelUpdateReceipt** widget：
   - 轻量卡片："因为刚才 XX，Sparkle 学到了：..."
   - 显示：触发事件 → 学到什么 → 改变了什么 → 没有写入什么
   - 用户可选择"记住了" / "不对，纠正"

4. **GrowthDashboardProvider**（Riverpod）：
   - 调用 `/experience/growth-dashboard`

### D.4 验收

- Insights Tab 有 Growth Chronicle 和 Learning Dashboard 两个入口
- 成长叙事以故事格式呈现，不只是数据
- 学习仪表板展示时间、效率、薄弱点、知识变化
- 完成任务/失败后能看到 ModelUpdateReceipt

---

## Agent E: Source & Knowledge 透明化

### E.1 用户最终感受

> 当 Sparkle 给我一个回答时，我能看到它用了哪些资料、为什么用这些而不用那些、置信度多少。在知识星图中，我不仅能看到知识点，还能看到"这个知识点为什么对我当前的目标重要"、"它阻塞了哪个任务"。

### E.2 当前状态

**后端已有**：
- `GET /api/v1/signals/context-receipt` — 返回最新 context receipt（用了哪些 sources、为什么用/不用）
- `POST /api/v1/signals/receipt-action` — 用户对 receipt 的反馈（confirm/correct/dismiss）
- `GET /aurora/spine/receipt` + `POST /aurora/spine/receipt/action` — Aurora 侧 receipt endpoints
- `GET /aurora/spine/goal-graph/{goal_id}` — GoalWorldGraph 节点（含 is_bottleneck, mastery, exam_weight 等）
- `backend/app/signals/source_tray_integration.py` — SourceEffectivenessTracker，compute_retrieval_plan()

**前端已有**：
- Galaxy 3D 星图（physics-based）
- 无 SourceExplanationCard
- 无 Galaxy 内 GoalWorldGraph overlay

### E.3 目标产出

**Flutter 产出**：

1. **SourceExplanationCard**（放在 `mobile/lib/features/chat/presentation/widgets/`）：
   - 在聊天消息下方（AI 回复附件区域），以折叠卡片显示：
     - "本次回答使用了 X 个资料来源"（展开后列出每个 source 的标题、类型、相关性）
     - "未使用的资料"（展开后列出，附原因："已过期" / "置信度不足" / "与你当前目标不直接相关"）
     - 每个 source 旁边有"纠错"按钮 → 触发 `/signals/receipt-action`
     - 置信度指示（颜色条或图标）
   - 暗色模式下所有颜色可读
   - 默认折叠，有数据时才显示

2. **GoalWorldGraphMiniPanel**（放在 `mobile/lib/features/galaxy/presentation/widgets/`）：
   - 在 Galaxy 星图上方或侧边的半屏面板
   - 显示当前目标的 GoalWorldGraph 节点：
     - 瓶颈节点（红色/橙色高亮）
     - 已掌握节点（绿色）
     - 待学习节点（灰色）
     - 每个节点点击显示：名称、掌握度、与目标的关系（"阻塞任务 X" / "是里程碑 Y 的前置"）、考试属性（如有）
   - 切换目标时刷新

3. **SourceExplanationProvider**（Riverpod）：
   - 调用 `/signals/context-receipt` 获取 receipt
   - POST 纠正操作

4. **GoalGraphOverlayProvider**（Riverpod）：
   - 调用 `/aurora/spine/goal-graph/{goal_id}`

### E.4 验收

- 聊天中 AI 回复使用了资料时，下方显示 SourceExplanationCard
- 可以展开看到用了哪些/没用哪些资料
- Galaxy 星图中可以打开 GoalWorldGraph mini panel
- 瓶颈节点视觉突出，可理解为什么重要

---

## Agent F: Task PAUSED/RESTORE + LowYieldGentleBlock

### F.1 用户最终感受

> 当我的任务被暂停时，我能清楚看到暂停原因、恢复条件、一个"恢复任务"按钮。当我在截止日期压力下做无关的事时，Sparkle 会温柔地提示"现在更值得做的可能是..."——但不会强制，我可以接受、忽略或纠正。

### F.2 当前状态

**后端已有**：
- `backend/app/models/task.py` — TaskStatus 枚举含 PAUSED, RESTORE。Task API 完整：start/pause/resume/abandon/complete/snooze/stuck/too-hard/skip + next-action-selection
- `backend/app/api/v1/tasks.py` — 完整 CRUD
- `backend/app/signals/spine_orchestrator.py` — LowYieldGuard 已接入（check_activity, passed/blocked），CitationValidator 已接入

**前端已有**：
- Task 列表、TaskCard、TaskQuickActions
- 但 PAUSED 任务无暂停原因解释
- RESTORE 状态无专门 UI
- 无 LowYieldGentleBlock 卡片

### F.3 目标产出

**Flutter 产出**（`mobile/lib/features/task/presentation/`）：

1. **PausedTaskCard** 升级（改造现有 TaskCard 的 PAUSED 状态渲染）：
   - 暂停原因显示（来自 task.metadata.pause_reason 或后端返回）
   - 恢复条件（如"完成前置任务 X" / "截止日期到达"）
   - "恢复任务"按钮 → 调用 task resume API
   - 暂停时长显示

2. **RestoreTaskDialog**（RESTORE 状态专用）：
   - 弹窗解释"这个任务已从放弃/存档中恢复"
   - 恢复后的下一步建议
   - 用户确认或取消

3. **LowYieldGentleBlockCard**（放在 `mobile/lib/features/chat/presentation/widgets/`）：
   - 轻量提示卡片，非模态，不打断用户
   - 显示："我注意到你正在 X。考虑到 Y（截止日期/目标优先级），现在更值得做的是 Z。"
   - 三个操作按钮：
     - "好的，切换" → 导航到建议任务
     - "我知道，继续" → 关闭卡片
     - "不对，纠正" → 记录反馈
   - 从 WebSocket 推送或主动拉取触发

4. **LowYieldBlockProvider**（Riverpod）：
   - 监听来自 SpineOrchestrator 的低收益行为事件
   - 管理卡片显示/隐藏/已处理状态

### F.4 验收

- PAUSED 任务显示暂停原因、恢复条件、恢复按钮
- RESTORE 任务有恢复弹窗
- 低收益行为触发时，聊天中显示轻量提示卡片
- 用户可选择接受/忽略/纠正

---

## Agent G: StreakQuality + 庆祝升级

### G.1 用户最终感受

> 连胜不再是"你连续打开了 N 天 App"，而是"你连续高质量坚持了 N 天"——有效学习时长、核心任务完成、难点突破都算。庆祝时看到的不只是"连胜+1"，而是"你今天在最容易分心的时段完成了核心任务"。

### G.2 当前状态

**后端已有**：
- `backend/app/services/streak_signal_processor.py` — `StreakSignalProcessor`，处理签到计算 streak_consistency, checkin_regularity, motivation_type
- `backend/app/models/` — `UserStreakStats`（current_streak, max_streak, longest_streak, total_checkin_days, last_activity_date）
- `backend/app/services/achievement_engine.py` — 19 种事件类型，SparkleConfetti 庆祝

**缺失**：
- 连胜仅天数计算，无质量加权
- 前端 StreakQualityIndicator 缺失
- 庆祝触发无证据（只是计数，不显示"为什么"）

### G.3 目标产出

**后端升级**（`backend/app/services/streak_quality.py`，新文件）：

```
StreakQualityService:
  - compute_quality(user_id, date) → StreakQuality:
      effective_minutes: int         # 有效学习时长
      core_tasks_completed: int     # 核心任务完成数
      difficult_breakthroughs: int  # 难点突破数
      plan_consistency: float       # 计划一致性 0-1
      recovery_score: float         # 恢复能力分（中断后重新开始的频率）
      quality_score: float          # 综合质量分 0-1
      is_quality_day: bool          # 是否算高质量日
```

**新建 BFF 端点**（`backend/app/api/v1/experience/streak_router.py`）：

```
GET /experience/streak-quality
  返回:
    - current_streak: int
    - quality_streak: int  — 高质量天数
    - today_quality: StreakQuality
    - weekly_quality_trend: [{date, quality_score, breakdown}]
    - celebration_trigger: Optional[{reason, evidence, suggested_message}]
```

**Flutter 产出**：

1. **StreakQualityIndicator**（放在 `mobile/lib/features/achievement/presentation/widgets/`）：
   - 替换首页和成就页的纯火焰数字
   - 外圈：质量天数 / 内圈：当前连续天数
   - 点击展开 → 显示本周质量趋势（小折线图或条状图）
   - 今日质量 breakdown：有效时长 / 核心任务 / 难点突破 / 计划一致性

2. **CelebrationOverlay 升级**（改造现有 SparkleConfetti）：
   - 庆祝时附带 evidence 文本："今天的核心任务在下午 2 点完成——那通常是你最容易分心的时段"
   - 不只是一个动效，而是有意义的反馈

### G.4 验收

- 首页显示 StreakQualityIndicator（非纯天数）
- 点击可看质量 breakdown
- 庆祝有具体 evidence，不是无意义的数字跳动

---

## Agent H: Settings 行为解释

### H.1 用户最终感受

> 在设置页面，我不只是看到开关和选项。每个设置区域都解释了"Sparkle 会如何使用这个设置"，让我理解我的选择如何影响 Sparkle 的行为。数据导出、删除、记忆隐藏也都可以在设置中找到。

### H.2 当前状态

**后端已有**：
- 无障碍设置（WCAG AA，609 行 Flutter 设置屏幕）
- 情绪自适应 UI（font/animation/color temp）
- 提醒频率、记忆控制、资料使用、研究参与设置
- FV-07 consent tracker、FV-10 data minimization

**缺失**：
- 无"Sparkle 会如何使用这些设置"解释区块
- 数据导出/删除入口不直观
- 设置项之间的关系不透明（"因为设了 A，所以 B 场景下会 C"）

### H.3 目标产出

**Flutter 产出**（`mobile/lib/features/settings/presentation/`）：

1. **SettingsBehaviorExplanation** 区块（添加到现有设置页面）：
   对每个设置区域添加可折叠的解释卡片：
   - **无障碍**："当你开启高对比度，所有 Sparkle 界面将使用高对比度配色..."
   - **情绪自适应**："当你感到疲劳时，Sparkle 会使用更柔和的颜色、更大的字体、减少动画..."
   - **提醒频率**："当前设置下，Sparkle 每天最多提醒 X 次，在 XX 场景下触发..."
   - **记忆控制**："Sparkle 会记住你的 XX 偏好，但不会记录 XX..."
   - **资料使用**："你的学习资料将用于 XX，不会被用于 XX..."
   - **研究参与**："加入研究意味着 XX 数据将被匿名分析..."

2. **数据控制入口**（在设置页底部）：
   - "导出我的数据" → 触发数据导出请求
   - "删除我的数据" → 确认弹窗 + 删除
   - "隐藏我的成长编年史" / "隐藏我的记忆" → toggle
   - 每个操作有明确的后果说明

3. 不新建 BFF 端点——使用已有设置 API。

### H.4 验收

- 每个设置区块有"Sparkle 如何使用"的解释
- 数据导出/删除/隐藏可从设置页触达
- 所有解释支持双语

---

## Agent I: 首页重新布局

### I.1 你的角色

你是**唯一**可以编辑首页布局文件（`mobile/lib/features/home/presentation/screens/home_screen.dart`）的 agent。其他 agent 创建独立 widget，你负责把它们放进首页。

### I.2 目标

首页从"功能入口集合"升级为"今日成长指挥中心"。用户打开 App，第一眼看到的是：今日焦点、当前目标进度、学习质量、是否有需要关注的提醒。

### I.3 首页布局草案

```
┌──────────────────────────────────────┐
│  顶部状态带                            │
│  [问候语] [StreakQuality 小图标]  [▼]  │  ← 点击展开 UnderstandingPanel(C)
│──────────────────────────────────────│
│                                      │
│  🎯 当前目标 (MultiGoalDashboardCard 升级) │
│  ┌────────────────────────────────┐  │
│  │ 考研 — 完成度 65%              │  │
│  │ 今日最小下一步: 完成英语真题卷   │  │  ← 可点击进入 Goal Detail(B)
│  │ [进度环] [知识瓶颈: 3 个]       │  │
│  └────────────────────────────────┘  │
│                                      │
│  📋 今日任务                           │
│  ┌────────────────────────────────┐  │
│  │ □ 完成数学第 5 章练习题           │  │
│  │ □ 整理英语阅读错题本              │  │
│  │ ⏸ 撰写论文大纲 (已暂停: 等待导师) │  │  ← 点击进入 Task Detail(F)
│  │ [+ 添加任务]                     │  │
│  └────────────────────────────────┘  │
│                                      │
│  📊 本周学习质量                       │  ← StreakQuality 小趋势图(G)
│  ┌────────────────────────────────┐  │
│  │ ████░░░░ 高效 12h  | 任务 8/12  │  │
│  └────────────────────────────────┘  │
│                                      │
│  🤝 社群问责                          │  ← 可横向滑动(A)
│  ┌──────┐ ┌──────┐ ┌──────┐        │
│  │ 伙伴A │ │ 伙伴B │ │ 需要  │        │
│  │ 85%  │ │ 60%  │ │ 帮助? │        │
│  └──────┘ └──────┘ └──────┘        │
│                                      │
│  🔔 需要关注的                         │  ← LowYieldGentleBlock / PAUSED 等
│  ┌────────────────────────────────┐  │
│  │ ⚠️ 你可能在低收益行为...         │  │
│  └────────────────────────────────┘  │
│                                      │
│  [底部 Tab Bar: 首页 | Galaxy | ...]  │
└──────────────────────────────────────┘
```

### I.4 首页卡片槽位系统

首页布局定义以下**命名槽位**。每个 agent 的 widget 注册到对应槽位，你负责排版：

| 槽位 | 来自 Agent | Widget | 优先级 |
|------|-----------|--------|--------|
| 顶部状态带展开 | C | UnderstandingPanel | 低（隐藏，点击展开） |
| 当前目标卡片 | B | GoalDetailPreview（GoalDetail 的摘要版） | 最高 |
| 今日任务列表 | (已有) + F | TaskCard（含 PAUSED 状态升级） | 最高 |
| 学习质量小图 | G | StreakQualityIndicator | 高 |
| 社群问责 strip | A | AccountabilityPreviewStrip（Hub 的摘要版） | 中 |
| 提醒区域 | F | LowYieldGentleBlockCard | 动态（有触发时才显示） |
| 周叙事入口 | D | WeeklyGrowthNarrativeCard（已有，升级为 Chronicle 入口） | 中 |

### I.5 产出

1. **HomeScreen 升级**：按上述布局重排
2. **MultiGoalDashboardCard 升级**：点击目标 → 进入 GoalDetailPage(B)，而非仅切换状态
3. **卡片槽位系统**：每个槽位有 loading、empty、error、populated 四种状态
4. 不新建 BFF

### I.6 验收

- 首页以今日焦点和当前目标进度为首屏内容
- 点击目标进入 GoalDetailPage
- 所有卡片有 loading/empty/error/populated 状态
- 布局在暗色模式下正常

---

## Agent J: 收口整合

### J.1 你的角色

你是最后一个运行的 agent。你的任务是机械性整合，不需要理解业务逻辑。

### J.2 产出

1. **GoRouter 路由收口**：
   - 收集所有 `<feature>_routes.dart` 中导出的 `List<GoRoute>`
   - 在 `mobile/lib/app_router.dart` 中合并
   - 确保无路由冲突

2. **Provider barrel 收口**：
   - 收集所有 agent 创建的独立 provider 文件
   - 在相应的 providers.dart 中 export

3. **i18n ARB 合并**：
   - 收集所有 agent 创建的 `_agent_*_en.arb` 和 `_agent_*_zh.arb`
   - 合并到主 ARB 文件中
   - 确保无 key 冲突

4. **FastAPI experience router 注册**：
   - 收集 `backend/app/api/v1/experience/` 下的所有 `*_router.py`
   - 在 FastAPI app 中 `include_router`

5. **flutter analyze + build 验证**：
   - 确保无 error/warning
   - 如有个别 agent 产出有问题，记录但不动代码

### J.3 验收

- `flutter analyze` zero error
- `make gateway-dev` 编译通过
- BFF 端点全部可访问
- 路由无冲突

---

## 附录: 每个 Agent 的 BFF 端点速查

| Agent | BFF 文件 | 端点 |
|-------|---------|------|
| A | `backend/app/api/v1/experience/community_router.py` | `GET /experience/community-accountability` |
| B | `backend/app/api/v1/experience/goal_router.py` | `GET /experience/goal-detail/{goal_id}` |
| C | `backend/app/api/v1/experience/understanding_router.py` | `GET /experience/understanding-snapshot` |
| D | `backend/app/api/v1/experience/dashboard_router.py` | `GET /experience/growth-dashboard` |
| E | (无 BFF，使用已有 endpoints) | 已有 `/signals/context-receipt`, `/aurora/spine/goal-graph/{goal_id}` |
| F | (无 BFF，使用已有 task API) | 已有 `backend/app/api/v1/tasks.py` |
| G | `backend/app/api/v1/experience/streak_router.py` | `GET /experience/streak-quality` |
| H | (无 BFF，使用已有 settings API) | 已有 settings models |
| I | (无 BFF，消费其他 agent 的 widget) | — |
| J | (收口，无新建) | — |

每个 BFF router 文件是独立的 FastAPI APIRouter（prefix="/experience"），Agent J 统一注册。

---

*本规格描述"实现什么用户体验"，不描述"怎么实现代码"。每个 Codex agent 应在此目标范围内自主选择最优实现方案。*
