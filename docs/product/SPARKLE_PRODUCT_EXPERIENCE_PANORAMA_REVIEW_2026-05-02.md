# Sparkle 产品体验全景审查与修正版

> 日期：2026-05-02  
> 范围：终端用户体验、移动端可感知闭环、产品验收口径  
> 基准：`SPARKLE_FULL_VISION_FINAL_AUDIT_2026-05-02.md`、`SPARKLE_FULL_VISION_FIX_WORKFLOW_2026-05-02.md`、`SPARKLE_FULL_VISION_COMPLETION_2026-05-02.md`、当前代码仓库  
> 结论：原文的产品判断基本正确，但若直接作为执行基准，会把若干已经落地的能力误判为缺失，也会把“工程完成”误读成“用户体验完成”。本文件给出纠偏后的体验现状、差距定义、优先级和验收标准。

---

## 0. 总判断

Sparkle 的核心命题仍然成立：产品护城河不是“更强的聊天”，而是“更准确地理解一个具体学生，并把这种理解转化为持续可执行、可纠正、可验证的成长计划”。

当前真正的问题不是“后端有灵魂、前端完全没有”，而是更细的一层：

1. 后端、API、Flutter 分别已经有不少能力，但它们没有被组织成一条稳定的用户旅程。
2. 多份 2026-05-02 文档之间存在口径冲突：工程收尾报告宣布 Phase 1 达成，体验修复工作流仍列出多个用户可感知缺口。
3. 一些原审计项已被后续提交修复，继续按原表执行会重复造轮子。
4. 最大的未完成项从“缺功能”转为“缺体验聚合”：用户需要在关键场景里看到原因、证据、进度、可撤销控制和下一步。

因此，后续执行不应再以“补 12 个 widget”为中心，而应以 6 条用户闭环为中心：

- Onboarding 后看到 Sparkle 对我的理解，并能纠正。
- 目标有独立详情页，能看到最低达标线、进度、瓶颈和今日下一步。
- Chat 的回答能解释使用了哪些上下文、为什么用、为什么是这个风格。
- Task 执行能解释暂停/恢复，并温和阻止低收益偏航。
- Insights 能展示成长编年史和学习仪表板，形成 Pattern -> Action -> Outcome 叙事。
- Community 首屏从内容流转为目标问责 Hub。

---

## 1. 原文需要修正的事实

| 原文判断 | 当前代码核对 | 修正结论 |
|---|---|---|
| Flutter 约 732 个 Dart 文件 | 当前 `mobile/lib` 下约 1098 个 `.dart` 文件 | 规模描述过期，移动端复杂度高于原文 |
| Goal 无独立 ORM，`minimum_acceptance_criteria` 完全缺失 | `backend/app/models/goal.py` 已有 `Goal` ORM 和 `minimum_acceptance_criteria`，迁移 `b698b0802ef1_c25_add_goals_table.py` 已存在 | 后端模型缺口已修复；体验缺口变成“移动端无独立 Goal Detail 与标准确认流程” |
| CausalTimelinePanel 缺失 | `mobile/lib/features/chat/presentation/widgets/causal_timeline_panel.dart` 已存在，`aurora_receipt_chip.dart` 可打开 | 不再是缺失 widget；仍需确认它是否在黄金路径中自然出现 |
| ContextReceiptBar 已实现但 SourceExplanationCard 缺失 | `ContextReceiptBar`、`AuroraReceiptChip`、`/signals/context-receipt` 已存在 | 缺口不是“完全看不到来源”，而是缺统一的 SourceExplanationCard，把 used/skipped/source confidence/correction 聚合到回答下方 |
| 社区只有社交 Feed | `accountability_screen.dart`、`accountability_detail_screen.dart`、伙伴邀请接受/拒绝流程已存在 | 社区问责能力存在；问题是信息架构和首屏默认仍偏 Feed |
| CRDT 数据层零 UI 可见 | `sync_center_screen.dart`、`sync_center_provider.dart`、outbox status/conflict UI 已存在 | 不能再称“零 UI”；缺口是关键编辑流的内联同步反馈与冲突解释不足 |
| LowYieldGentleBlock widget 缺失 | `StrategyInterventionCard` 已明确标注 divine moment #5 “阻止低收益”，后端 `LowYieldGuard` 已接入 | 不应新造完全重复卡片；应把 LowYieldGuard 事件稳定映射到现有 StrategyInterventionCard 或薄封装 |
| TASK RESTORE 状态缺失 | 修复工作流记录为已完成；任务 API 和 UI 中已有 restore/resume 相关入口 | 需要改写为“RESTORE/PAUSED 的原因和恢复条件在任务详情中不够显性” |
| 连胜无质量加权 | 修复工作流宣称已完成，但当前代码中未发现清晰的 StreakQualityIndicator 或质量字段端到端消费 | 保留为“需复核”：后端可能有提交记录，移动端质量感仍未验收 |
| Learning Dashboard 完全缺失 | 已有 `LearningInsightsOverviewScreen`、`LearningReportScreen`、`WeeklyGrowthNarrativeCard` | 缺口是“成长编年史完整页 + 时间/效率/薄弱点综合仪表板”，不是完全没有学习洞察 |

---

## 2. 修正版体验现状

### 2.1 Onboarding 与用户理解

现状：Persona onboarding、modeling chat、profile transparency 和 self-model 后端能力都存在。用户可以提供大量个人信息，系统也能在后端形成 claims、readout summary、correction feedback。

用户真实感受：流程像“我被问了很多”，但不够像“Sparkle 已经理解了我”。onboarding 结束后的理解回放缺失，导致用户看不到这些信息如何改变计划、提醒和回答风格。

修正后的缺口：不是 SelfModelAccessor 本身缺失，而是缺 UnderstandingSnapshot 的可视化和可纠正入口。

验收标准：完成 modeling chat 后，用户看到 5-8 条具体、可纠正的理解项；每条有证据摘要、置信度、纠正按钮；纠正后显示“这会影响计划粒度/提醒频率/资料选择/语气风格”等具体效果。

### 2.2 Chat 与透明回答

现状：WebSocket chat、PlanReviewCard、ContextReceiptBar、AuroraReceiptChip、CausalTimelinePanel、GoalArbitrationCard、StrategyInterventionCard 等组件已存在；后端也有 `/signals/envelope`、`/signals/context-receipt`、`/signals/receipt-action`。

用户真实感受：聊天能力已经不薄，但“为什么这样回答”仍分散在多个入口里。用户需要一个稳定、低干扰的解释层：用了什么资料、没用什么资料、为什么这次更谨慎/更简短/更推动。

修正后的缺口：ExperienceEnvelope 的移动端消费仍不完整；SourceExplanationCard 应作为回答下方的统一折叠层，而不是另一个孤立 widget。

验收标准：AI 回复有来源或风格调整时，消息下方出现一个折叠解释条；展开后可看到 used/skipped sources、跳过原因、风格原因、纠正入口；默认不打断主对话。

### 2.3 Goal 与计划中心

现状：Goal ORM、minimum acceptance criteria、GoalSwitcher、MultiGoalDashboard、GoalWorldGraph API 都已存在。计划系统和任务系统也有较完整状态机。

用户真实感受：目标仍不像“中心引力点”。用户能切换目标，但很难进入一个目标的完整详情页，看清最低成功标准、当前进度、知识瓶颈、计划健康和今日下一步。

修正后的缺口：后端模型已经补上，移动端 Goal Detail 是第一优先级。

验收标准：从首页目标卡点击目标进入 Goal Detail；首屏包含目标进度、最低达标线、今日最小下一步；下滑看到知识瓶颈、计划健康、问责状态和相关资料。

### 2.4 Task 执行与偏航干预

现状：任务状态机、pause/resume/restore、TaskQuickActions、LowYieldGuard、StrategyInterventionCard 均存在不同程度实现。

用户真实感受：任务管理能力强，但暂停/恢复的解释不够像“伙伴在帮我拆局”。低收益提醒已经有基础卡片，但它需要稳定触发、明确原因、可纠正反馈和低打扰呈现。

修正后的缺口：不用新建完全独立的 LowYieldGentleBlock；应把 LowYieldGuard -> StrategyInterventionCard -> Outcome/feedback 串成闭环。

验收标准：PAUSED 任务显示暂停原因、恢复条件、恢复按钮；低收益行为出现轻量提示，用户可选择“切换 / 继续 / 不对，纠正”，反馈进入后续策略。

### 2.5 Insights、成长编年史与学习仪表板

现状：GrowthChronicleService 和 DB snapshot 存在；移动端已有 WeeklyGrowthNarrativeCard、LearningInsightsOverviewScreen、LearningReportScreen。

用户真实感受：已有“学习洞察”和“报告”，但还没有一个稳定的“我的成长故事”空间。用户看不到一个月后可以回顾的 Pattern -> Action -> Outcome 时间线。

修正后的缺口：GrowthChronicle 不是从零开始，而是需要完整页面、确认/编辑/驳回机制、证据链和 ModelUpdateReceipt。

验收标准：Insights 中有 Growth Chronicle 和 Learning Dashboard 两个明确入口；编年史条目可确认、编辑、驳回；仪表板展示时间分布、效率、薄弱点、知识变化；关键任务完成/失败后能看到“Sparkle 学到了什么/没有写入什么”。

### 2.6 Galaxy 与目标知识图谱

现状：Galaxy 3D 星图、GoalWorldGraphService、`/aurora/spine/goal-graph/{goal_id}`、mobile endpoint 常量已经存在。

用户真实感受：Galaxy 仍偏“酷的知识探索”，不是“为了我的目标服务的地图”。用户不一定知道某个节点阻塞了哪个任务、影响哪个达标线。

修正后的缺口：缺 GoalWorldGraph overlay/mini panel，把节点状态和当前目标绑定。

验收标准：Galaxy 可切换到“当前目标视图”；节点至少区分已掌握、瓶颈、待攻克；点击节点能解释它对目标的影响。

### 2.7 Community

现状：Feed、群组、好友、问责伙伴、check-in、接受/拒绝邀请等能力已存在；但社区默认首屏仍由 FeedPostCard 组织。

用户真实感受：用户会先感受到“社区内容流”，再发现问责功能。愿景中“责任空间”的产品心智没有被首屏建立。

修正后的缺口：不是重建社区，而是重排信息架构：Accountability Hub 为首屏，Feed 降为二级入口。

验收标准：打开社区 Tab，第一屏是我的承诺、伙伴进度、共同目标、需要帮助的人；发布动态仍可用，但不再主导社区心智。

### 2.8 Achievement 与激励

现状：成就系统、streak stats、streak history、streak details UI 都存在。

用户真实感受：连胜仍可能被理解为“打开 App 算一天”，而不是“高质量坚持”。即便后端已有质量加权提交记录，移动端也缺清晰的质量解释。

修正后的缺口：StreakQualityIndicator 仍需端到端验收。它应解释今天为何算高质量/普通/低质量，而不是只显示天数。

验收标准：连胜页或首页火焰旁显示质量等级；用户能看到今日依据（专注分钟、任务完成、计划推进、恢复困难任务等）。

### 2.9 Settings 与可控性

现状：无障碍、i18n、透明度设置、source context receipts 等较完整。

用户真实感受：设置多，但缺“这个设置会怎样改变 Sparkle 行为”的预览。

修正后的缺口：设置页需要行为影响说明，不是再加更多开关。

验收标准：关键设置项显示影响范围，例如“关闭资料收据后，聊天中不再显示本次使用/跳过的资料说明，但仍会用于内部质量审计”。

---

## 3. 修正版差距清单

| 优先级 | 差距 | 当前状态 | 下一步 |
|---|---|---|---|
| P0 | Community 首屏仍偏 Feed | 问责能力已存在，默认心智仍是内容流 | Accountability Hub 替代社区首屏，Feed 降级 |
| P0 | Goal Detail 不完整 | Goal ORM/API 基础已补，移动端缺详情页 | 新增 GoalDetailPage + MinimumCriteriaCard + GoalBottleneckStrip |
| P0 | UnderstandingSnapshot 缺失 | Self-model 后端可读，前端无回放 | onboarding 结束、首页、聊天抽屉复用同一面板 |
| P0 | GrowthChronicle 完整页缺失 | 后端 + weekly narrative 存在 | 新增编年史页面和确认/编辑/驳回流程 |
| P0 | SourceExplanationCard 缺失 | receipt 能力分散存在 | 在 AI 回复下方统一呈现 used/skipped/correction |
| P1 | ExperienceEnvelope Mobile 消费不完整 | `/signals/envelope` 存在，mobile 无稳定消费入口 | 增加 endpoint 常量、provider、轻量解释 UI |
| P1 | GoalWorldGraph 移动端目标视图缺失 | 后端 API 与 endpoint 常量存在 | Galaxy overlay/mini panel |
| P1 | PAUSED/RESTORE 解释不足 | 状态与动作已有 | Task 卡片展示原因、恢复条件、恢复建议 |
| P1 | LowYieldGuard 闭环不足 | 后端与 StrategyInterventionCard 存在 | 统一事件映射、反馈和 outcome |
| P1 | Streak 质量感不足 | streak UI 存在，质量端到端需复核 | StreakQualityIndicator + 依据解释 |
| P2 | CRDT 同步可见性不均匀 | Sync Center 已存在 | 在关键编辑流内联同步状态/冲突解释 |
| P2 | Settings 行为影响不清 | 设置能力多 | 增加影响范围说明和预览 |

---

## 4. 执行顺序建议

### Sprint 1：把“我是谁、我要什么、今天做什么”连起来

目标：用户第一天就能感到 Sparkle 不是普通 AI。

1. UnderstandingSnapshot：onboarding 结束页 + 首页入口。
2. GoalDetailPage：最低达标线、进度、今日最小下一步。
3. SourceExplanationCard：Chat 回复解释来源与风格。

验收方式：按 Golden Path 第 1 天剧本走通，用户能纠正理解、确认目标标准、理解计划来源。

### Sprint 2：把“执行偏航”和“成长回顾”连起来

目标：用户第一周能感到 Sparkle 在陪伴执行，而不是只给计划。

1. PAUSED/RESTORE 原因卡。
2. LowYieldGuard -> StrategyInterventionCard 闭环。
3. GrowthChroniclePage 的最小版。

验收方式：制造任务暂停、低收益行为、任务完成/失败三个场景，都能看到原因和可操作下一步。

### Sprint 3：把“知识、社区、激励”围绕目标重排

目标：用户第一个月能感到所有模块围绕目标旋转。

1. Community Accountability Hub。
2. GoalWorldGraphMiniPanel。
3. LearningDashboardPage。
4. StreakQualityIndicator。

验收方式：社区首屏不再是 Feed；Galaxy 能解释目标瓶颈；连胜显示质量依据；Insights 能讲述一个月成长故事。

---

## 5. Golden Path 验收剧本

### 第 1 天

- 用户完成 onboarding + modeling chat。
- 看到 UnderstandingSnapshot，至少 5 条具体理解项，每条可纠正。
- 设定考研/毕业设计目标。
- Goal Detail 显示 minimum acceptance criteria、进度起点、今日最小下一步。
- Chat 首次计划回复下方显示 SourceExplanationCard，说明用了哪些资料/记忆/目标上下文。

### 第 1 周

- 首页显示今日焦点，不是杂乱提醒。
- 用户暂停任务时，能看到暂停原因和恢复条件。
- 用户做低收益行为时，收到轻量提醒，可接受/忽略/纠正。
- 坚持多天后，连胜显示质量依据，而不只是天数。

### 第 1 个月

- Insights 中能看到成长编年史，包含转折点和证据。
- Learning Dashboard 显示时间分布、效率趋势、薄弱点变化。
- Galaxy 能切到当前目标视图，解释瓶颈节点与目标关系。
- Community 首屏是承诺和伙伴进度，而不是帖子流。

### 第 3 个月

- 用户能回看“我如何从 Pattern A 变成 Pattern B”。
- Sparkle 的微调整都有原因、可撤销、可纠正。
- 用户愿意让 Sparkle 自动调整微计划，因为系统每次解释依据并保留控制权。

---

## 6. 不应再做的事

- 不要按原文机械新建 12 个互不相干的 widget。已有 `StrategyInterventionCard`、`GrowthCard`、`CommunityInsightCard`、`ContextReceiptBar`、`CausalTimelinePanel` 等，应优先复用。
- 不要再把 Goal ORM 当作核心缺口。核心缺口已经转移到移动端详情页和聚合 API。
- 不要把“工程完成报告”直接等同于“用户体验完成”。用户只承认可见闭环。
- 不要让社区继续同时承担“社交网络”和“问责空间”的第一心智。首屏必须做选择。
- 不要让解释层喧宾夺主。Source、Envelope、Timeline 都应默认折叠，用户需要时再展开。

---

## 7. 最终裁定

原文的愿景叙事值得保留，但差距表需要更新。Sparkle 不是“后端很强、前端很空”的状态，而是“能力散落在多条管线里，尚未被编排成可感知的成长旅程”。

下一阶段的产品目标应定义为：

> 让每个关键用户动作都产生一个可见闭环：Sparkle 理解了什么、为什么这么建议、用户能怎样纠正、结果如何改变下一步。

只要这条闭环在 Onboarding、Chat、Goal、Task、Insights、Galaxy、Community、Achievement 中都成立，Sparkle 才能从“还不错的 AI 学习助手”跃迁为“真正懂我的成长伙伴”。
