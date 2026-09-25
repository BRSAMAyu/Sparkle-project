# WT401 Q-03 Autonomous Visual QA — Reachable 屏清单

- base SHA：`61af0f0a`（分支 `wt401-q03-visualqa`）
- rubric 权威：`v3/04_ux/VISUAL_REVIEW_RUBRIC.md`（12 维 0–2 分 + A/B/C 分级）
- 设备档：standard 档（`StimulationLevel.standard` 默认主题，不加 low 档 override）；
  390×844 logical @ 2x（iPhone 14/15 标准 profile）。双刺激档对比属 wt399/U-02 范围，本卡不做。
- 渲染方式：flutter test 真实 GoRouter 泵（`routerProvider` + demo mode + 真 auth
  harness，复用 `test/app/router_smoke_test.dart` 已验证配方），`matchesGoldenFile`
  落 PNG 到 `v3-output/WT401-Q03-VISUAL/evidence/`。无 mock 语义：状态一律由
  真实 Notifier/Repository 状态构造（fixture 数据允许）。
- chat 屏注记：V3-FIX-53（wt400 修复中）涉及真后端工具流；本卡 chat 状态一律用
  fixture/本地草稿驱动，不依赖真后端流，不阻塞在 FIX-53。

## A. 核心 journey 屏（12 维全量打分 + 全状态，A/B=0 才算过）

| # | 路由 | 屏 | 状态覆盖 |
|---|------|----|----------|
| C01 | `/home` | DashboardScreen | default(demo) / loading / empty(首目标空态) / error |
| C02 | `/galaxy` | GalaxyScreen | default(demo) / loading / error |
| C03 | `/chat` | ChatScreen | default(新会话) / fixture 会话 |
| C04 | `/community` | CommunityMainScreen | default(demo) |
| C05 | `/profile` | ProfileScreen | default(demo) |
| C06 | `/login` | LoginScreen | default（公开面） |
| C07 | `/onboarding/persona` | PersonaOnboardingScreen | default |
| C08 | `/errors` | ErrorListScreen | default / empty |
| C09 | `/errors/new` | AddErrorScreen | default |
| C10 | `/goals/new` | GoalCreateScreen | default |
| C11 | `/plans` | PlanHomeScreen | default |
| C12 | `/review?mode=today` | ReviewScreen | default |
| C13 | `/notification-center` | NotificationCenterScreen | default |

## B. Long-tail reachable 屏（default 态逐屏截图 + 程序化溢出/截断检测）

| # | 路由 | 说明 |
|---|------|------|
| L01 | `/register` | 注册 |
| L02 | `/forgot-password` | 忘记密码 |
| L03 | `/reset-password` | 重置密码 |
| L04 | `/legal/terms` | 条款 |
| L05 | `/legal/privacy` | 隐私 |
| L06 | `/focus` | 专注 |
| L07 | `/tasks` | 任务列表 |
| L08 | `/tasks/new` | 建任务 |
| L09 | `/openclaw` | OpenClaw hub |
| L10 | `/calendar` | 日历 |
| L11 | `/calendar-stats` | 日历统计 |
| L12 | `/calendar/day` | 日详情 |
| L13 | `/sprint` | 冲刺 |
| L14 | `/sprint/history` | 冲刺历史 |
| L15 | `/growth` | 成长 |
| L16 | `/plans/history` | 计划历史 |
| L17 | `/exam-sprint/setup` | 考前冲刺 setup |
| L18 | `/exam-sprint/diagnose` | 诊断 |
| L19 | `/exam-sprint/review` | 复盘 |
| L20 | `/exam-sprint/completion` | 完成 |
| L21 | `/exam-sprint/portfolio` | 学习档案 |
| L22 | `/learning/insights` | 学情洞察 |
| L23 | `/learning/forecast` | 预测 |
| L24 | `/learning/insights/growth-chronicle` | 成长编年 |
| L25 | `/learning/insights/dashboard` | 洞察面板 |
| L26 | `/learning/insights/directives` | 指令审计 |
| L27 | `/learning-path` | 学习路径 |
| L28 | `/learning-report` | 学情报 |
| L29 | `/review-plan` | 复习计划 hub |
| L30 | `/reflection/summary` | 反思摘要 |
| L31 | `/memory` | 记忆面板 |
| L32 | `/memory/settings` | 记忆设置 |
| L33 | `/memory/understanding` | 理解面板 |
| L34 | `/profile/edit` | 编辑资料 |
| L35 | `/profile/settings` | 统一设置 |
| L36 | `/profile/music-library` | BGM 库 |
| L37 | `/profile/persona` | 画像 |
| L38 | `/profile/posters` | 海报工坊 |
| L39 | `/profile/system-updates` | 系统更新 |
| L40 | `/profile/memory-settings` | 记忆设置(入口) |
| L41 | `/profile/openclaw-settings` | OpenClaw 设置 |
| L42 | `/profile/sync-center` | 同步中心 |
| L43 | `/profile/sessions` | 会话管理 |
| L44 | `/profile/security-log` | 安全日志 |
| L45 | `/profile/export-data` | 数据导出 |
| L46 | `/achievements` | 成就 |
| L47 | `/achievements/map` | 成就地图 |
| L48 | `/achievements/streak` | 连续打卡 |
| L49 | `/achievements/contract` | 契约 |
| L50 | `/leaderboards/self-anchor` | 自我锚（D-COMM-1 唯一裁决面） |
| L51 | `/community/feed` | 动态 |
| L52 | `/community/friends` | 好友 |
| L53 | `/community/friends/requests` | 好友请求 |
| L54 | `/community/friends/discover` | 发现好友 |
| L55 | `/community/users/search` | 找人 |
| L56 | `/community/groups` | 小组 |
| L57 | `/community/groups/search` | 找组 |
| L58 | `/community/groups/discover` | 发现小组 |
| L59 | `/community/groups/create` | 建组 |
| L60 | `/community/posts/create` | 发帖 |
| L61 | `/community/favorites` | 收藏 |
| L62 | `/community/blocked` | 屏蔽 |
| L63 | `/community/accountability` | 问责 |
| L64 | `/community/squads` | 小队 |
| L65 | `/curiosity-capsule` | 好奇心胶囊 |
| L66 | `/cognitive/patterns` | 认知模式 |
| L67 | `/tools/library` | 工具库 |
| L68 | `/tools/translator` | 工具宿主 |
| L69 | `/photon/history` | 光子流水 |
| L70 | `/seed-libraries` | 种子库 |
| L71 | `/seed-libraries/marketplace` | 种子市场 |
| L72 | `/shop` | 商店 |
| L73 | `/visual-elements` | 视觉元素 |
| L74 | `/theater` | 剧场 |
| L75 | `/simulation` | 模拟 |
| L76 | `/documents` | 文档库 |
| L77 | `/translations/history` | 翻译历史 |
| L78 | `/weather` | 天气引导 |
| L79 | `/memory/detail` | 记忆详情（demo id） |
| L80 | `/galaxy/drafts/review` | 星图草稿审 |
| L81 | `/errors/:id`（demo id） | 错题详情 |
| L82 | `/goals/:goalId`（demo id） | 目标详情 |
| L83 | `/tasks/:id`（demo id） | 任务详情 |
| L84 | `/community/groups/:id`（demo id） | 小组详情 |
| L85 | `/community/users/:id`（demo id） | 用户主页 |

## C. 参数屏/未挂载说明

- `/chat/settings`、`/chat/group/:id`、`/chat/private/:id`：group/private 需真实
  会话 id 与后端；用 `/chat` fixture 态代表 chat 面，参数屏登记为 backend-gated。
- `/profile/password-reset`、`/profile/social-accounts`、`/profile/task-reminders`、
  `/profile/skills`、`/profile/upgrade-guest`、`/profile/admin-operations`、
  `/profile/delete-account`、`/profile/account-security`、`/seed-libraries/new`、
  `/seed-libraries/:id`、`/community/groups/:id/{tasks,members,files,moderation}`、
  `/community/accountability/:id`、`/community/squads/:id`、`/tasks/:id/execute`、
  `/plans/:id`、`/plans/:id/edit`、`/plans/:id/review`、`/galaxy/node/:id`、
  `/focus/mindfulness/:id`、`/achievements/:id`、`/achievements/milestone/:milestoneId`、
  `/errors/:id/edit`：可达但依赖具体实体 id；抽查代表性 id，缺数据时截图即其
  真实缺数据态（不算 mock）。

## D. 覆盖统计

- 路由表叶子路径共 ~102（不含 legacy redirect 4 条）。
- 本卡计划截图：核心 13 屏 × 多状态 ≈ 30 张 + long-tail ≈ 60 张 ≈ 90 张 PNG。
- 12 维 rubric 打分表：`rubric_scores.md`（核心屏全 12 维 + long-tail 按维度汇总）。
