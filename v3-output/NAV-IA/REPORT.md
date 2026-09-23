# NAV-IA — App 级信息架构与导航审查报告

- 纵队：A（北极星全旅程）· 信息架构线
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt223`（基线 `6043725c`）
- 方法：静态测绘 GoRouter 路由表（`mobile/lib/app/routes.dart` + 32 个 `*_routes.dart`）+ 全库入边统计（对每条路由做 `context.push/go/replace` 字面量、路由常量、`pushNamed/goNamed`、`ToolRegistry.routeBuilder` 别名、深链映射五类入边扫描）
- 性质：纯研究，零代码改动。所有 file:line 均为真实引用，可复核。

---

## 1. 现状测绘

### 1.1 总量

- **注册路由：139 条**（`grep -c "GoRoute("` 全量），其中约 5 条为 legacy redirect（`chat_routes.dart` 4 条 + `documents_routes.dart` 1 条），实际约 **134 个可达面**。
- **底部 Tab：5 个**（`shell_navigation.dart:233-259`）：Home `/home`、Galaxy `/galaxy`、Chat `/chat`、Community `/community`、Profile `/profile`。满足 3-5 tab 铁律，无超标。
- **`/tools/:toolId`** 是元路由：经 `ToolRegistry` redirect 到 7 个功能路由（`tools_routes.dart:36-56`）——工具库是 focus/errors/review-plan/forecast/patterns/capsule/seed-libraries 的**别名入口层**。

### 1.2 导航图（文字版）

图例：`T`=tab 根 ｜ `→`=push（入栈）｜ `⇢`=go/redirect（换栈）｜ 括号内=入边数（指向该面的 UI 入口数，含别名层）｜ ⚠=异常，详见 §3

```
Splash `/` ──⇢ auth 未登录 → /login（6 条 auth 路由：login/register/forgot/reset/legal×2）
   └──⇢ 已登录 → /home（onboarding 未完成 → /onboarding/persona、/onboarding/modeling-chat）

T0 HOME `/home`（DashboardScreen，2861 行，67 个 import，slot 化聚合面）
│  ├ slot 系统 11+ 个可开关 slot（dashboard_edit_sheet.dart:589-650：dailyBriefing/metricsRow/
│  │  commandCenter/understanding/returnCaseFile/goalDetailSnapshot/multiGoalDashboard/
│  │  taskBoard/examSprint/dashboardUpdates/growthQuality…）
│  ├→ /tasks（11）、/tasks/:id（11）、/tasks/:id/execute（12）、/tasks/new（5）—— 任务族，入口最密
│  ├→ /plans/:id（shell 内 detail，10）、/plans/new（9）、/plans/history（3）、/growth（4）
│  ├⇢ /chat（7，换 tab）、⇢ /galaxy（5，换 tab）、⇢ /goals/new（2）、→ /goals/:goalId
│  ├→ /focus（8）、/exam-sprint/setup（2）、/community/accountability（5）、/community（4）
│  ├→ /tools/library（4，其中 3 处带 ?tab=manage）、/calendar-stats（3）、/calendar（2）、
│  │  /calendar/day（2）、/errors?dimension=analysis（1）
│  ├→ /cognitive/patterns（5）、/curiosity-capsule（3）、/seed-libraries（2+create 2）
│  ├→ /theater（15）、/simulation（16）—— 演练族，入边极多
│  ├→ /achievements（7）、/achievements/:id（6）、→ streak/map/contract（list 屏内 3 跳）
│  ├→ /notifications（1）⚠ 与 /notification-center 并存
│  ├→ /learning/insights（2，insight_hub_card）、/learning-report（11）
│  └→ /weather（1）、/openclaw（5）、/review-plan（5）、/review（5）、/shop（1）⚠
│
T1 GALAXY `/galaxy`（含 working view：节点 preview → 演练/复习/建任务）
│  ├→ /galaxy/node/:id（5）、→ /galaxy/drafts/review（2，galaxy 自身 + document_library_screen:1099）
│  ├→ /theater（query 带 target_node_id，galaxy_screen.dart:1106）、⇢ /chat?prompt=…（:1149 复习直启）
│  └→ /tasks/new（:3125）
│
T2 CHAT `/chat`（AI 助手；收件箱为顶栏唯一入口 ChatInboxEntryIcon，sheet 形态，无路由，D8-5 裁决）
│  ├→ /chat/settings（1）、→ /chat/group/:id、/chat/private/:id（4 条 legacy redirect 保留）
│  ├→ /openclaw?section=delegate（chat_screen.dart:1352）
│  ├→ /notification-center（chat_inline_signals.dart:183）⚠
│  └→ /settings/transparency（chat_settings_screen.dart:277）⚠⚠ 未注册路由 → 404
│
T3 COMMUNITY `/community`（3 内嵌 tab：Partners/Feed/Groups，community_main_screen.dart:14-18）
│  ├→ /community/posts/create（4）、→ /community/groups/discover（4）、/community/groups/create（3）
│  ├→ /community/groups/:id（6+）→ tasks（1）/members（1，literal）/files（1）；⚠ moderation（0）
│  ├→ /community/friends（8）→ /chat/private/:id、pushNamed friendRequests（7）、friendsDiscover（4）
│  ├→ /community/accountability（5）→ accountabilityDetail（10）
│  ├→ /community/users/:id（4）、→ /community/blocked（1，friends_screen:201）
│  ├→ /community/squads（2）⚠ 仅 /sprint 屏（sprint_screen.dart:69）与错题分享弹窗（share_error_to_squad_dialog.dart:113）
│  │     └→ /community/squads/:id（仅 list 屏内 1 条，squad_list_screen.dart:109）
│  └ 孤儿路由（0 入边）：/community/feed 的同形屏、/community/groups/search、/community/users/search、
│     /community/favorites ⚠ 详见 §3-A
│
T4 PROFILE `/profile`（15 个一级入口，profile_screen.dart:643-837）
│  ├→ /profile/settings（unified_settings_screen.dart，3898 行）→ bgmLibrary/skills/taskReminders/
│  │     syncCenter/openclawSettings/memorySettings/exportData/memory 面板（:1975）/adminOperations…
│  ├→ /profile/edit、/profile/persona、/profile/posters、/profile/skills、/profile/account-security、
│  │     /profile/memory-settings ⚠、/profile/export-data、/profile/delete-account、/profile/upgrade-guest
│  ├→ /profile/* 其余 10 面：music-library/persona/system-updates/password-reset/openclaw-settings/
│  │     sync-center/social-accounts/sessions/security-log/task-reminders/admin-operations/learning-mode ⚠
│  ├→ /achievements（678）、/library（670）、/photon/redeem-pro（693）、/visual-elements（710）、
│  │     /learning-portfolio（661）
│  └ （设置页还直推 /notification-center：memory_settings_screen.dart:593 ⚠ 跨域耦合）
│
根级独立族（均在根 navigator，RouteResilienceScope 兜底返回）：
· Plan/Sprint 族 14 条：/plans/:id（shell 内）/sprint（6 入边）/sprint/history（5）/plans/:id/review（1）
  /exam-sprint/{setup,diagnose,review,completion,portfolio}（setup 2 + flow 内串联）/learning-portfolio（8）
· Insights 族 6 条：/learning/insights（2）/learning-report（11）/growth-chronicle（1）/dashboard（1）
  /directives（1）/learning/forecast（仅工具别名 1）⚠/learning-path（0）⚠⚠
· Memory 族 4 条：/memory（1，仅设置页 :1975）/memory/understanding（1）/memory/detail（2）
  /memory/settings（1，仅 persona 屏 :333）⚠ 与 /profile/memory-settings 同屏双路由
· 通知 3 条：/notifications（1）/notification-center（4）/notification-analytics（0）⚠⚠
· 光子 3 条：/photon/redeem-pro（2：profile+shop）/photon/history（0 ⚠ 二级孤儿）/photon/transfer（0）⚠⚠
· 其他：/shop（1，仅 streak_details_screen:415）⚠、/leaderboards/self-anchor（2）、/weather（1）、
  /errors 4 条、/review 2 条、/translations/history（1）、/visual-elements（2）
· 深链 sparkle:// 10 类映射（deep_link_service.dart:14-25）：achievement/milestone/insights/task/plan/
  capsule/node/prism/openclaw/openclaw-settings；推送 payload 可带任意 destination_route
```

### 1.3 各屏可达路径数与深度（核心任务视角）

| 核心任务 | 路径 | 跳数 | 评价 |
|---|---|---|---|
| 记录错题 | Home → tools/library → errors（别名）或 Home 卡片直达 `/errors?dimension=analysis` | 1-2 | 良 |
| 开始复习 | Home → `/review`；Galaxy 节点 → `/chat?review=…` | 1-2 | 良 |
| 建学习计划 | Home → `/plans/new?type=growth`（2 处直达） | 1 | 优 |
| 进入冲刺 | Home 卡片 → `/exam-sprint/setup`；plan_card/knowledge_detail/self_anchor/review_hub → `/sprint` | 1-2 | 良，但入口语义分裂（见 B-2） |
| 查看成就 | Home → `/achievements` → streak/map/contract | 2-3 | 可接受（低频子面） |
| **找到小队** | Home → `/sprint`（经 plan_card 等）→ `/community/squads` → `/community/squads/:id` | **3 起** | 差（见 B-1） |
| **光子流水** | Profile → `/photon/redeem-pro`？❌ redeem 屏不含流水卡；PhotonBalanceCard 未被任何屏嵌入 | **不可达** | 断（见 A-2） |
| **AI 高级/透明度设置** | Chat → chat/settings → 「高级」→ `/settings/transparency` | **落地 404** | 断（见 A-1） |
| 记忆面板 | Profile → settings（3898 行大页）→ 内存面板 | 2-3 | 深，尚可（低频管理面） |
| 学习洞察总览 | Home insight_hub_card → `/learning/insights`；但 `/learning-report` 有 11 条入边 | 1 | 但族内结构混乱（见 B-4） |

---

## 2. 对标（顶级 App IA 惯例）

以 iOS HIG／Material 3 navigation guidance 及一线产品（Things/Notion/Discord/Spotify/多邻国）通行做法为基准：

1. **3-5 tab 铁律**：Sparkle 5 tab，合规。
2. **每 tab 单一职责**：Home=今日聚合、Galaxy=知识地图、Chat=AI 助手、Community=同伴、Profile=身份与设置。总体成立；但 **Home 同时是"今日概览"和"全功能启动台"**（134 面中约 60+ 面的入边源自 Home 的 slot/卡片），职责过载。
3. **核心任务 ≤2 跳**：学习主链路（记错题/复习/建计划/冲刺/问 AI）基本达标；**小队（同伴协作主推功能）3 跳起**，是唯一系统性超标的活跃功能。
4. **设置集中**：Profile→settings 两层集中制符合惯例；但设置页存在**跨域直推**（memory_settings → notification-center）与**同屏双路由**（memory settings），违背"单一事实入口"。
5. **消息中心唯一**：Sparkle 有 **3 个通知面**（`/notifications`、`/notification-center`、`/notification-analytics`）+ 1 个 in-app overlay + chat 收件箱，**违反唯一性**；且 Community tab 的红点 badge 挂的是私信/群聊未读（`message_notification_service.dart:33`，枚举只有 privateMessage/groupMessage/mention），点进 Community tab 落地在 Partners，而会话列表藏在 Friends/Groups 二级内——**badge 语义与落点错位**（`shell_navigation.dart:250-253`）。
6. **入口深度对称**：光子（虚拟货币）作为激励核心，入口 2 条且流水不可达，与成就在 Home 的 7 条入边严重不对称。

---

## 3. 失衡点清单（每条带路由证据）

### A 档：断裂（用户可实际撞墙）

**A-1 死链：`/settings/transparency` 未注册路由 → 404**
- 证据：`chat_settings_screen.dart:277` `context.push('/settings/transparency')`；全库 `*routes*.dart` 中 grep `transparency` = 0 条注册。落入 `routes.dart:110` errorBuilder（"页面不存在"）。
- 影响：Chat 设置 → 高级选项，用户必然撞 404。

**A-2 光子流水不可达（二级孤儿）**
- `/photon/history`（`photon_routes.dart:8`）唯一入边是 `PhotonBalanceCard`（`photon_balance_card.dart:30`），而 PhotonBalanceCard **没有被任何 Screen 嵌入**（全库引用仅 photon 自己的 widgets 目录）；`photon_redeem_pro_screen.dart` 不含 BalanceCard/HistoryList。
- 影响：用户从 Profile/Shop 能兑换 Pro，却永远看不到流水。付费/激励系统的信任面断裂。

**A-3 深链/推送目标面不对称**
- `deep_link_service.dart:14-25` 只映射 10 类资源；community/group/squad/error/review/calendar 均不可深链。推送侧 `push_navigation_service.dart:110-117` 把 notification_id 一律导向 `/notification-center`，而 Home 通知卡却去 `/notifications`（`home_notification_card.dart:63`）——同一实体（通知）两个落点。

### B 档：结构性失衡（可用但违背全局 IA 原则）

**B-1 小队系入口倒挂：三屏中最深的功能挂在最低频的入口下**
- `/community/squads` 入边仅 2：`sprint_screen.dart:69` 与 `share_error_to_squad_dialog.dart:113`；squad detail 入边仅 1（`squad_list_screen.dart:109`）。
- 小队被 D-COMM-3/4/5 定为冲刺社交核心（routes 注释原文"Sprint squad list（我的小队 + 创建/加入入口）"），但 Community tab（同伴关系的家）内**无任何入口**；用户心智路径"社交→小队"要 3 跳且第一跳在 Sprint 屏。
- 同时 `AccountabilityHubScreen`（`pages/accountability_hub_screen.dart:17`，约 700 行成品屏）**零挂载**：无路由、无 import，是整屏孤儿。

**B-2 Sprint 入口群语义分裂（一个概念，四个词汇，六个入口）**
- `/sprint`（6 入边：plan_card:60、knowledge_detail:476、review_plan_hub:118、self_anchor:81、sprint_history:95、home 弹窗）、`/sprint/history`（5）、`/plans/:id/review`、`/exam-sprint/*` 5 条、Home 的 examSprint slot（dashboard:682）。
- "冲刺"入口同时从计划卡、知识点、复习枢纽、排行榜、报告屏 5 个异质语境进入，且 `/sprint` 与 `/exam-sprint/setup` 是两套并行的冲刺概念。入边多不是问题，**词汇与落点不成族**才是：报告屏 `learning_report_screen.dart:1206` 甚至在运行时把 `/sprint` 重映射到 sprintHistory（同一链接不同语境不同落点）。

**B-3 通知三面 + badge 错位（消息中心不唯一）**
- `/notifications`（home_routes.dart:14，NotificationListScreen，1 入边）vs `/notification-center`（notification_center_routes.dart:9，4 入边：recent_insights_card:253、chat_inline_signals:183、memory_settings:593、推送）vs `/notification-analytics`（0 入边，孤儿）。
- Community tab badge = 私信/群聊未读（`shell_navigation.dart:250` + `message_notification_service.dart:31-33`），但落点是 Community tab 根（Partners），会话列表实际在 friends_hub_view/groups_hub_view 二级。

**B-4 Insights 族 6 面结构混乱**
- `/learning-report` 11 条入边（最高频洞察面），而名义上的族根 `/learning/insights` 仅 2 条；`/learning/forecast` 唯一入口藏在工具库别名（tool_registry.dart:296）；`/learning-path`（insights_routes.dart:19）0 入边纯孤儿；growth-chronicle/dashboard/directives 各 1 条入边，全是 overview 屏内单向尾流。
- 用户视角：查"学习报告"心智 1 跳直达 report，查"趋势预测"要绕道工具库，查"学习路径"无门。

**B-5 同屏双路由（记忆设置）与设置页跨域直推**
- `MemorySettingsScreen` 双路由：`/memory/settings`（memory_routes.dart:14，入边=user_persona_screen:333）与 `/profile/memory-settings`（user_routes.dart:45，入边=profile_screen:799 + unified_settings:1974）。
- `memory_settings_screen.dart:593` 直推 `/notification-center`——设置页之间互相跳到别的 feature 的设置，形成网状而非树状。

**B-6 Calendar 双路径同屏**
- `/calendar`（calendar_routes.dart:17）与 `/calendar-stats`（:18）pageBuilder 完全相同，都渲染 `CalendarStatsScreen`。入边分流：Home 卡片 2+3 条分别用两个 path。对深链/埋点/回退语义是隐性成本。

### C 档：风格噪音（记录不改）

- `/documents` → `/library` redirect（documents_routes.dart:22）与 chat 4 条 legacy redirect 是**有意保留**的兼容层，属规范做法。
- Home 聚合面巨大（2861 行）但已有 slot 开关系统（dashboard_edit_sheet）自治理，属产品密度选择而非 IA 缺陷。
- `/tools/:toolId` 别名层本身设计良好（未知 toolId 回落 `/home`，tools_routes.dart:39-41）。

---

## 4. 红蓝辩论记录

**辩题 1：小队入口倒挂是真失衡还是"刻意把小队限定在冲刺语境"？**
- 红（主张改）：D-COMM-3/4/5 注释自证小队=冲刺社交产品面，但产品把它放在用户最不可能发现的地方；北极星是"AI 学习成长系统"，同伴协作是留存飞轮，3 跳起 + Community 内零入口与战略权重不匹配。
- 蓝（主张不改）：小队依附 sprint 语境（组队冲刺），放开到 Community 会稀释"冲刺组队"的叙事；且当前小队功能仍在迭代（只有 list/detail 两屏挂载），过早加入口会放大半成品暴露面。
- **裁决**：真失衡，但承认语境论的部分正确性。修法不是"加到 Community 首屏大卡"，而是低成本的"Partner tab 战况区补 1 行入口 + sprint 屏入口保留"——单向增强，不动 sprint 语境主入口。收益（发现性）>成本（1 个卡槽），过第一关。北极星加权：学习闭环（冲刺→复盘→同伴）是主旅程，加权后明确该改。

**辩题 2：通知三面合并是重构还是点修？**
- 红：消息中心唯一是铁律，三面并 state 双源（unreadMessageCountProvider vs notification repository）迟早出一致性 bug。
- 蓝：`/notifications`（home 卡片落地）与 `/notification-center`（推送落地）内容域不同（前者学习提醒、后者全站信箱），合并要动两个 feature 的数据层，今晚不可能，也不该在导航审查里做数据层手术。
- **裁决**：**不改结构，先统一落点**——把全部"通知"类入口收敛到 `/notification-center` 单一落点（Home 卡片改指向），`/notifications` 降级为 redirect（照抄 chat legacy redirect 的成熟模式，零风险）；`/notification-analytics` 是运营面，从路由表摘除挂载（保留文件）或挂到 admin-operations 下。数据层合并另立卡片。过第二关：改法 = 2 处 push 改 1 处 redirect，成本小时级。

**辩题 3：A-1 死链（/settings/transparency）该补路由还是删按钮？**
- 红：chat_settings 写了"高级/透明度"文案（l10n key `chatSettingsOpenAdvanced`），说明功能有真实意图，该补路由。
- 蓝：找不到任何 TransparencyScreen 产物——这是半成品入口混入了主干；补一个空壳路由是给半成品背书。
- **裁决**：删按钮（或换为展示型说明行）。理由：北极星加权下 AI 透明度不是当前主旅程结点；死链伤害（每次点击 404）> 半成品隐藏的伤害。成本：删 5 行。若产品确认要做透明度页，届时一并注册路由恢复入口。

**辩题 4：Sprint 词汇分裂要不要现在统一？**
- 红：`/sprint` vs `/exam-sprint/*` vs `plans/:id/review` 三套概念对用户是同一个"我的冲刺"，应合并。
- 蓝：exam-sprint 是结构化流程（setup→diagnose→review→completion 有向流），`/sprint` 是自由冲刺面板，二者数据模型不同（exam_sprint_repository vs plan_repository），合并是重构不是导航修正。
- **裁决**：不合并路由（第三关否决"推翻重来"），只做**词汇与入口归拢**：入站导航统一叫"冲刺"并优先落 `/sprint`（面板内已有去 setup 的引导位），报告屏 `learning_report_screen.dart:1206` 的运行时重映射改为显式双入口。成本 1 天内，收益是心智一致性。

**辩题 5：孤儿路由清理会不会误删未发布功能？**
- 红：8 条 0 入边路由可能是"下周就要接上"的。
- 蓝：死代码挂在路由表里每条都是可深链面（`deep_link_service.dart:66-68` 接受任意 `/` 开头直通路由），未发布的面通过深链可被提前触达，反而是事故源。
- **裁决**：分三类处理（见提案 P-5）：有成品屏无入口的（users/search、groups/search、favorites、AccountabilityHubScreen）挂入口或下架二选一由产品定；明确废弃的（learning-path、reflection/summary、photon/transfer、photon/history、notification-analytics、settings/learning-mode）加 `redirect` 到近亲面而不是删文件——保持编译面不破坏他人分支。

---

## 5. 提案（渐进改良，全部点状，无推翻重来）

> 量级标尺：S=半天内 ｜ M=1-2 天 ｜ L=3 天以上（本清单刻意不含 L 项）

### P-1 【S】修复 A-1 死链
- 现状：`chat_settings_screen.dart:277` push 未注册的 `/settings/transparency` → 404。
- 改法：移除该 ListTile（含 l10n 引用不变），或临时降级为 disabled 行。
- 验收：Chat→设置→全项可点，无一触达 errorBuilder；`grep -rn "settings/transparency" mobile/lib` = 0。
- 量级：S。

### P-2 【S→M】光子面闭合（A-2）
- 现状：`/photon/history` 二级孤儿；redeem 屏无流水。
- 改法：在 `photon_redeem_pro_screen.dart` 顶部嵌入现成的 `PhotonBalanceCard`（其 :30 已带 push history），入口即闭合；`/photon/transfer` 加 redirect → `/photon/redeem-pro`。
- 验收：Profile→兑 Pro→可看到余额卡→点卡进流水；`sparkle://` 直通 `/photon/transfer` 落在 redeem 屏。
- 量级：S（嵌入 1 widget + 1 条 redirect）。

### P-3 【S】通知落点统一（B-3 第一刀，不动数据层）
- 现状：通知类入口分流 `/notifications` 与 `/notification-center`。
- 改法：`home_notification_card.dart:63` 改指 `/notification-center`；`/notifications` 路由改为 redirect → `/notification-center`（复制 chat_routes legacy redirect 模式，chat_routes.dart:88-107）；`/notification-analytics` 从 `NotificationCenterRoutes.routes` 摘除（文件与屏保留，登记 KNOWN_CODE_DEBT_LEDGER）。
- 验收：全库通知类 push 字面量与常量全部指向 `/notification-center`；老路径 `/notifications` 可达且落在同一屏。
- 量级：S。

### P-4 【S】Community tab 内补小队入口（B-1）
- 现状：`/community/squads` 仅 sprint 屏与错题分享弹窗两个入边。
- 改法：`partners_tab.dart`（或 Groups tab 顶部的发现区，groups_hub_view.dart:190 一带）加一行"冲刺小队"入口 push `CommunityRoutes.squads`；sprint 屏既有入口保留不动。
- 验收：Community 任一内嵌 tab ≤2 跳到 squad list；sprint 屏入口不回归。
- 量级：S。
- 附带（同卡顺手）：`AccountabilityHubScreen` 挂载与否请产品裁决——挂载则注册 `/community/accountability/hub` 并在 accountability 屏加入口；不挂载则移入 `scripts/devtools` 归档目录或删除，勿留零引用成品屏在主干。

### P-5 【S】孤儿路由一次清点（辩题 5 裁决落地）
- 改法（全部用 redirect，不删文件）：
  - `/learning-path` → `/learning/insights`（insights_routes.dart:19）
  - `/reflection/summary` → `/learning-report`（同属回顾语义）
  - `/settings/learning-mode` → `/profile/settings`（user_routes.dart:304）
  - `/community/favorites`、`/community/users/search`、`/community/groups/search`、`/community/groups/:id/moderation`：产品二选一（挂入口 / redirect 到近亲面）。倾向：favorites → `/community/friends`；search 两面 → 对应 hub view（groups_hub_view 内嵌搜索位）；moderation → `/community/groups/:id/members`（组长动线本来就在成员页）。
- 验收：`deep_link_service` 直通以上任意路径均落在真实面；路由表无 0 入边且无 redirect 的"哑路由"。
- 量级：S（每条 3-5 行）。

### P-6 【M】Sprint 入口词汇归拢（辩题 4）
- 改法：新增统一 l10n 词条"冲刺"用于所有入站锚点文案；`learning_report_screen.dart:1206` 的 `/sprint → sprintHistory` 运行时重映射改为双显式入口（"冲刺面板"→`/sprint`、"冲刺历史"→`/sprint/history`）；`/sprint` 面板头部保留去 `/exam-sprint/setup` 的引导。
- 验收：全库对冲刺族入口的文案来源单一 l10n key；报告屏两个入口落点可预期。
- 量级：M（跨 5 个 feature 的文案+2 处导航）。

### P-7 【M】Calendar 单路径化（B-6）
- 改法：保留 `/calendar` 为唯一 path，`/calendar-stats` 改 redirect → `/calendar`（3 处入边改常量引用）。
- 验收：CalendarStatsScreen 只有一个注册 path；Home 卡片入边全走 `/calendar`。
- 量级：S-M。

### P-8 【暂缓→另立卡】通知数据层合并、Insights 族信息重构、Home 启动台减负
- 说明：三者都要动数据层或产品信息架构决策，不属于"导航点修"。本卡只登记事实（B-3/B-4/Home 过载），建议进下一轮排期。Insights 族若做，方向是"report 为主面、overview 降为 report 的一个 tab"，预期 L 量级。

### 优先级排序（北极星加权：主旅程发现性 > 信任面完整 > 一致性 > 整洁）
1. P-1（死链，用户必撞）
2. P-2（付费信任面断裂）
3. P-3（消息中心唯一性第一刀）
4. P-4（北极星主旅程：冲刺→小队）
5. P-5、P-7（卫生批处理，可同一 PR）
6. P-6（词汇归拢，需文案配合）

---

## 6. 收工清单

- 本报告为唯一交付物（`v3-output/NAV-IA/REPORT.md`），零代码、零测试、无 patch。
- 未在主仓与 worktree 外留下任何临时文件；无进程残留。
- 复核提示：所有入边计数基于 `grep`（`/usr/bin/grep`）静态扫描五类入边（字面量 push/go/replace、路由常量、pushNamed/goNamed、ToolRegistry.routeBuilder、DeepLinkService 映射），若后续合入新增入口，以最新 main 为准。
