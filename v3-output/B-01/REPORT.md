# B-01 报告：42 模块产品生死簿与可达性真相

- 任务卡：B-01（stream BASELINE，gate V3-0，risk medium）
- 基线 HEAD：`a2d8a10c192f451a2c11042df8e4f6227cad37f9`（worktree wt6）
- 方法：LIGHT 静态证据（GoRouter 注册表 + 入口引用分析 + gateway 路由代码 + 未鉴权 curl 探测 + DB 只读 SELECT）
- 日期：2026-09-19
- 交付：`MODULE_MATRIX.csv`（42 行）、`portfolio.json`（同口径 machine-readable）、本报告

## 1. 方法

1. **可达性**：以 `mobile/lib/app/routes.dart` 的 GoRouter 注册表为准，逐 feature 提取 `*_routes.dart` 的路径常量与注册状态；再用跨 feature 引用分析（Route 常量外部引用 + `context.go/push('/…')` 字符串导航 + `core/services/deep_link_service.dart` 深链映射）判定「注册 ≠ 可达」。
2. **后端真相**：枚举 `backend/gateway/internal/handler/proxy_routes.go`（gin，~69 个 `/api/v1` 代理组，273 条 method+path）与 `backend/app/api/v1|v2`（FastAPI，104 个 include_router）；对运行中的网关做未鉴权 curl 探测（401=存在需登录 / 404=路径未注册）。
3. **数据真实性**：`docker exec sparkle_db psql`（只读）查 248 张表的 `pg_stat_user_tables.n_live_tup`；mobile 侧核对 mock 接线（`USE_MOCK` 编译期门控 / `DemoDataService.isDemoMode` 运行时门控，默认均走真实 API）；交叉引用 `v3-output/B-02/data_truth_inventory.csv`（15 项既有结论，含 INV-09 排行榜 cohort 污染、INV-01 3518 行 DemoDataService）。
4. **状态判定**：CORE/CONTEXTUAL/LABS/HIDDEN/RETIRE/UNKNOWN，依据 `v3/NORTH_STAR.md` §7、`v3/00_context/DECISIONS_V3.md`（D04/D17/D18/D19/D20）、`v3/03_modules/LONG_TAIL.md`。未知不猜。

**Golden Journeys（判定锚点，源自 NORTH_STAR §3–§4）**：
GJ1 first-run（splash→auth→onboarding→home）｜GJ2 today-loop（home→task→focus→完成→achievement）｜GJ3 stuck-loop（chat/aurora→friction→hybrid→outcome，即 Sparkle Moment）｜GJ4 goal-track（goal→plan→calendar/sprint→galaxy）｜GJ5 understand-reflect（insights→report→memory→cognitive）｜GJ6 trust-control（settings→memory 设置→导出/隐私）｜GJ7 social-sprint（community→小队问责→check-in）｜GJ8 knowledge-material（documents→galaxy 节点→错题→复习）。

## 2. 统计（42/42 全定级，无 UNKNOWN 残留）

| 状态 | 数量 | 明细 |
|---|---|---|
| CORE | 15 | aurora, auth, chat, cognitive, galaxy, goal, home, insights, memory, onboarding, plan, settings, splash, task, user |
| CONTEXTUAL | 18 | achievement, calendar, community, document, documents, error_book, experience, file, focus, intent, knowledge, notification_center, openclaw, report, reviews, tools, translation, vocabulary |
| LABS | 5 | mirofish, seed_library, simulation, theater, visual_elements |
| HIDDEN | 4 | leaderboard, photon, reflection, shop |
| RETIRE | 0 | （leaderboard 死屏为最接近项，见 §4） |
| UNKNOWN | 0 | （空表疑点列入 §5 补测，不影响状态判定） |

**CORE/CONTEXTUAL → Golden Journey 映射完整性**：33 项全部映射到至少一条 GJ（见 CSV `journey_map` 列）。唯一无 GJ 的 9 项全部是 LABS/HIDDEN（用户不可达或默认隐藏），符合验收标准。

## 3. 关键发现（可达性真相）

1. **42 个 feature 目录 ≠ 42 个可达页面**。其中 8 个目录无独立屏：aurora/experience/knowledge/intent/file/document 为数据层/组件层（被 chat、galaxy、goal、documents 消费，这是合理架构而非债务）；vocabulary 以 `vocabulary_lookup` 注册进 `tool_registry` 经 `/tools/:toolId` 出现；settings 无独立路由组，4 屏经 UserRoutes/profile 挂载。
2. **三个从未注册进 GoRouter 的目录**：`leaderboard`（有屏但全仓 0 引用=死代码）、`mirofish`（仅共享视觉组件）、`vocabulary`（仅 providers+工具注册）。
3. **两个「注册但零入口」的孤儿路由**：`/reflection/summary`（常量 0 外部引用 + 字符串导航 0 处）与 `/photon/transfer`；外加孤儿组件 `PhotonBalanceCard`（0 外部消费者，连带 `/photon/history` 不可达）。
4. **shop 形式可达但内容空**：`/shop` 注册 + streak_details 1 处入口，但 `shop_items`/`shop_purchases` 均 0 行——用户点进去是空目录（D20 违风险）。
5. **数据真实性分层清楚**：mock 只出现在两处门控之后（`USE_MOCK` 编译期、`DemoDataService.isDemoMode` 运行时，持真实 token 时被 auth_provider 强制关闭）。真实写入最强的表：user_node_status 8478、notifications 2968、focus_sessions 2431、decision_records 2418、calendar_events 1793、tasks 1219、chat_messages 954。
6. **六类表完全零写入**：leaderboard_snapshots、shop_items/purchases、theater_predictions、simulation_runs、seed_libraries/items、marketplace_*——对应后端端点活着但从未被真实使用，是「端点丰富、产品为空」的典型长尾。
7. **goals 表 0 行但写入路径真实**（`goal_decomposition_service.py:132` 用 `db.add(goal)` 落 Goal ORM）：plans 399 行是实际主载体，goal 创建落表需运行时复核（不阻塞其 CORE 判定，JTBD/入口证据独立成立）。

## 4. leaderboard / shop / photon 的 V3 决策标注

| 模块 | 决策 | 静态证据 | 依据 |
|---|---|---|---|
| leaderboard | **HIDDEN**（死屏建议随 HIDDEN 一并删除→RETIRE 倾向） | GoRouter 未注册；`leaderboard_screen.dart` 全仓 0 引用；`leaderboard_snapshots` 0 行；后端 `/leaderboards` 活但无 cohort 过滤（B-02 INV-09：guest/seed 100% 占据 top-50） | D17「Leaderboard 默认隐藏」+ D20「不造假数据」；修复 cohort 过滤前禁止任何入口 |
| shop | **HIDDEN**（真实目录接入前不上） | `/shop` 注册 + streak_details 1 处入口（形式可达）；`shop_items` 0、`shop_purchases` 0 | D17「Shop 从核心旅程降级」+ D20「空表面不上」；建议该 1 处入口随 gamification 降权移除，避免空目录暴露 |
| photon | **HIDDEN**（已是事实孤儿，确认即可） | `PhotonBalanceCard` 0 外部消费者；`/photon/transfer` 0 入口；`/photon/history` 仅被孤儿卡引用；后端 `/photons` 活且 `photon_transaction_history` 25 行真实交易 | D17「Photon 从核心旅程降级」；25 条历史数据保留在后端，UI 不可达与 V3 目标态一致 |

**长尾判定（D19）**：contextual 能力 = focus / calendar / error_book / documents+document / vocabulary / translation / tools / reviews / report / reflection(并入 insights) ；LABS = simulation / theater / mirofish / visual_elements / seed_library。与 LONG_TAIL.md 的 Portfolio test 逐项对照：LABS 群全部答不出「删除是否损伤 WVPL」（全部 0 写入或纯展示），维持降级。

## 5. 需模拟器补测清单（静态证据不足以定论的运行时项）

> 本卡为 LIGHT 任务，以下项不影响本次状态判定（判定依据为独立的 JTBD/入口证据），但 V3-0 gate 通过前建议由 HEAVY 实测卡补验：

1. **goal 创建落表**：`goals` 表 0 行 vs `plans` 399 行——运行时创建一个 goal 验证落表位置（`mobile/lib/features/goal` + `/api/v1/goals`）。
2. **plan_execution_records 0 行**：task/agent 执行链（`/tasks/:id/execute`）是否真实落库，还是只写 tasks 表。
3. **reflection 孤儿确认**：模拟器全路径巡检（含推送/深链旁路）确认 `/reflection/summary` 无可达路径；另确认 insights 内是否已内嵌等价反思面板。
4. **photon 孤儿确认**：巡检 profile/settings 无 photon 余额入口。
5. **LABS 群数据隔离**：theater/simulation/seed_library 打开后确认 demo 数据不混入真实缓存（D20；红测 `mock_statistics_guard_test.dart` 当前 RED，B-02 INV-02/03/04）。
6. **游客/seed 入榜**：leaderboard 若未来复活，先用 DB 复算验证 cohort 过滤（INV-09）。

## 6. 边界与诚实声明

- 服务探测用的是主仓运行中的实例（只读 curl/psql），未启动任何新服务、未动模拟器。
- 网关探测 404 的语义 = 「该子路径未注册」，已与 proxy_routes.go 源码双重核对（如 `/theater` 组只有 `/predictions/*` 子路径，故 `/theater/sessions` 404 不代表 theater 后端缺失）。
- `pg_stat_user_tables.n_live_tup` 受 autovacuum 时机影响，空表结论均与「是否找到写入代码路径」交叉核对后才写进 data_truth（如 goals 0 行但写入路径存在→列入补测而非判假）。
- 本卡零代码改动；worktree 内仅新增 `v3-output/B-01/` 四个交付文件。


---

## 复核修订（2026-09-19，独立 Reviewer verdict ACCEPT，非阻塞项此处落档）

1. **GJ 框架说明**：本报告 GJ1–GJ8 为**本卡判定用工作锚点**（自建框架），并非权威编号；权威 Golden Journeys 以 `v3/05_metrics_eval/GOLDEN_JOURNEYS.md` 的 GJ01–GJ20 为准。CSV `journey_map` 列中的 GJ1–GJ8 均按语义对照理解。
2. **勘误**：「无 GJ 的 9 项」实为 7 项；chat/galaxy 两行 Tab 编号对调；community 外部引用实为 2 处（非 13）；goal 写入 `db.add` 实际在 goal_decomposition_service.py:177（非 :132）；galaxy_skins 28 款为两表相加。
3. **Gate 张力（已开 V3-FIX-05）**：shop 判 HIDDEN 但存在 1 条真实入口（streak_details_screen.dart:415），需移除后 HIDDEN 才完全成立。
