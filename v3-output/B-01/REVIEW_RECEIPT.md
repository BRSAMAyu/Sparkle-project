# B-01 Review Receipt — 独立复核（Reviewer）

- 被审对象：`wt6/v3-output/B-01/`（MODULE_MATRIX.csv / portfolio.json / REPORT.md / changes.patch）
- 被审基线：wt6 HEAD `a2d8a10c192f451a2c11042df8e4f6227cad37f9`（已用 `git rev-parse` 独立确认，与 CSV source_sha 逐行一致）
- 复核人 worktree：wt7 @ 566517a2；主仓与 wt6 全程只读
- 复核方法：不复用 Worker 口径，关键断言全部重跑——目录清单 diff、GoRouter/引用 grep、未鉴权 curl（:8080，仅 GET）、`docker exec sparkle_db psql` 只读 SELECT、v3 决策文档逐条对照
- 日期：2026-09-19

---

## 1. 完备性复核 — PASS

- `ls mobile/lib/features/` = 42 个目录；与 CSV `name` 列做 `diff`（/tmp 临时件，已自清）→ **EXACT MATCH 42/42**，无遗漏、无多报、无重复。
- CSV 数据行 42 + header = 43 行；状态分布独立重算：CORE 15 / CONTEXTUAL 18 / LABS 5 / HIDDEN 4 / RETIRE 0 / UNKNOWN 0，与自报一致。

## 2. portfolio.json 与 CSV 同口径 — PASS

- 脚本逐字段比对 42 行：`feature_id/name/module_path/status/jtbd/data_truth/reachability_evidence/v3_surface` **全部一致**；`journey_map` 仅格式差异（CSV 带描述文字，json 只有 GJ 代码，GJ 集合一致）。
- json `counts` 与 CSV 重算一致；`unknown_items` 为空且与"无 UNKNOWN 残留"一致。

## 3. HIDDEN 四项逐项独立重验 — 全部站得住

### 3.1 leaderboard（F20）
- 无 `leaderboard_routes.dart`（`ls mobile/lib/features/*/[a-z]*_routes.dart` 清单中不存在）；`grep -rn "LeaderboardScreen|leaderboard_screen"` 排除 feature 自身 → **0 命中**；`LeaderboardProvider/Repository` 全仓 **0 外部接线**。
- community 内的 `leaderboardSummary` 为小队仪表盘数据字段（accountability_model.dart:229 等），与 leaderboard feature 无导航关系，不构成入口。
- deep_link_service `_routeMapping`（:22-33）无 leaderboard。DB `leaderboard_snapshots` **0 行**；curl `/api/v1/leaderboards` → **401**（端点活、UI 死）。
- **结论：死屏判定成立。**

### 3.2 photon（F26）
- `photon_routes.dart` 注册 `/photon/history` 与 `/photon/transfer`，经 routes.dart:396 挂载；除此之外全仓 `PhotonRoutes.|/photon/` **0 外部引用**。
- `PhotonBalanceCard` **0 外部消费者**（仅 photon_balance_card.dart:30 自身 push transactionHistory）；`/photon/transfer` **0 导航引用**；deep link 无映射。
- DB `photon_transaction_history` **25 行**（复测一致）；curl `/api/v1/photons` → **401**。
- **结论：孤儿组件 + 孤儿路由判定成立。**

### 3.3 reflection（F28）
- `/reflection/summary` 经 `ReflectionRoutes.routes` 注册（routes.dart:397）；`ReflectionRoutes.summary` 与 `'/reflection'` 字符串在全仓（排除 reflection_routes.dart 自身）**0 引用**；deep link 无映射；唯一 `/reflection` 字符串命中是 api_endpoints.dart:79-80 的**后端 API 路径**（非页面导航）与 focus 内无关的 reflection_dialog 组件。
- curl `/api/v1/reflections/summary` → **401**（后端活）。
- **结论：孤儿路由判定成立。**（注：deep_link_service `resolveRoute` 对以 `/` 开头的裸路径直通，理论上存在旁路，但无任何生产者；Worker 已把"推送/深链旁路巡检"列入补测第 3 项，处理诚实。）

### 3.4 shop（F33）
- `/shop` 注册（routes.dart:402）；全仓唯一入口 = `streak_details_screen.dart:415` `context.push('/shop')`（与自报"1 处入口"精确一致）；`ShopScreen` **0 外部 import**。
- DB `shop_items` **0**、`shop_purchases` **0**；curl `/api/v1/shop/items` → **401**。
- **结论：「可达但孤立 + 空目录」判定成立。**
- ⚠ **验收条款张力（见 §8-E11）**：B-01 卡 Acceptance 要求"HIDDEN/RETIRE 用户不可达"，shop 现状有一条真实入口。Worker 如实记录而非掩盖（CSV 写明"可达但孤立"并建议入口随降权移除），这是正确处理，但 V3-0 gate 放行前需跟踪该入口移除。

## 4. CORE/CONTEXTUAL 抽查（另 4 项）

### 4.1 goal（F15, CORE）
- `/goals/new`、`/goals/:goalId` 注册（goal_routes.dart:15-16，routes.dart:388 挂载）；home 侧字符串导航实测 **3 处**（dashboard_screen.dart:474、:519，multi_goal_dashboard_card.dart:161；CSV 写 2 处，少数了一处 multi_goal_card，方向保守）。
- DB：`goals` **0 行**、`plans` **399 行**（复测一致）。
- 写入路径：`goal_decomposition_service.py:132` = `async def create_goal(`，实际 `db.add(goal)` 在 **:177**；调用方真实存在（api/v1/goals.py:130、user_persona_batch.py:317/351/435、plan_review_service.py:2052）。**断言实质成立，行号引用不精确（见 §8-E5）。**

### 4.2 achievement（F01, CONTEXTUAL）
- achievement_routes.dart **6 个 GoRoute**（与"6 路径"一致）；`sparkle://achievement` 深链确认（deep_link_service.dart:23-24, 92-96）。
- 字符串导航实测 **8 个调用点 / 7 个外部文件**（shell_navigation:216、dashboard_card_section:150、metrics_row:98、sprint_screen:377、unified_notification_card:432/434、accountability_detail:151、friend_profile:231）+ 1 处常量引用。CSV 写"5 处"= **低估**（保守方向，见 §8-E7）。
- DB：`user_achievements` **1011**、`achievements` **47**（复测一致）。

### 4.3 community（F07, CONTEXTUAL）
- Tab-4 确认：routes.dart:335-338 Branch 3 = `/community`（StatefulShellRoute.indexedStack）。
- 子路由实测 **20 个 GoRoute**（CSV 写 21，差 1）；"13 个外部文件引用路由常量"**无法复现**：外部使用 `CommunityRoutes.` 的仅 **2 个文件**（app/routes.dart、chat/group_chat_screen.dart）；13 = import community_routes.dart 的文件总数，其中 12 个在 feature 内部——**证据表述夸大/口径错标（见 §8-E4）**。状态判定不受影响（Tab 注册 + 28 个外部文件含 `/community/` 字符串 + DB group_members 664 等均实）。

### 4.4 vocabulary（F42, CONTEXTUAL）
- feature 内**无 screen**（presentation/ 仅 providers）✓；`vocabulary_lookup` 确认注册于 tool_registry.dart:216（embeddedBuilder=VocabularyLookupTool），经 `/tools/:toolId` 出现 ✓；curl `/api/v1/vocabulary/wordbook` → **401**。

## 5. 关键断言重验

| 断言 | 复核结果 |
|---|---|
| /reflection/summary、/photon/transfer 孤儿路由 | ✓ 成立（§3.3/3.2） |
| leaderboard 全仓 0 引用死屏 | ✓ 成立（§3.1；community 的 leaderboardSummary 是数据字段非导航） |
| shop 空目录（两表 0 行）+ 1 入口 | ✓ 成立（§3.4） |
| goals 0 行但写入路径真实 | ✓ 实质成立（:132 函数定义，:177 db.add，多调用方；行号引用不精确） |
| 六类零写入表 | ✓ 全部复测 0：leaderboard_snapshots、shop_items/purchases、theater_predictions/candidate_bundles、simulation_runs、seed_libraries/seed_items/ratings、marketplace_packs/skills |
| 其余 data_truth 行数 | ✓ 复测 25+ 张表全部一致：users 248、user_sessions 242、user_preferences_center 248、tasks 1219、focus_sessions 2431、calendar_events 1793、chat_messages 954、group_members 664、user_node_status 8478、knowledge_nodes 157、notifications 2968→**3041**、push_histories 2225→**2361**（两处为 n_live_tup 随时间自然漂移，REPORT §6 已声明该口径）、episodic_memories 235、memory_preferences 89、routing_decision_log 450、understanding_depth_daily 149、notification_interactions 978、stored_files 7、document_chunks 7、behavior_patterns 40、cognitive_fragments 103、user_tool_history 15、user_visual_elements 80、visual_elements 50、plan_execution_records 0 |
| ⚠ galaxy_skins | **28 有误**：galaxy_skins=8、user_galaxy_skins=20，28 系两表相加（§8-E6） |
| curl 探测 | ✓ 抽测 8 条全部复现：shop/items、leaderboards、photons、reflections/summary、achievements、community/groups、vocabulary/wordbook → 401；goals → 301（注册，gin 尾斜杠重定向，非 404） |
| 网关 ~69 组 / FastAPI 104 include_router | 实测 Group( 72、include_router 105 —— 数量级与口径正确，±3/±1 为近似值，不影响任何结论 |

## 6. GJ 映射完备性 — 条件满足，出处标注有缺陷

- **完备性本身成立**：33 项 CORE/CONTEXTUAL 每项 journey_map ≥1 条 GJ；无 GJ 的项全部为 LABS/HIDDEN（F20/F22/F26/F33/F34/F37/F41 共 **7 项**）。
- ⚠ **REPORT 统计错误**：「唯一无 GJ 的 9 项全部是 LABS/HIDDEN」——实际是 **7 项**（LABS+HIDDEN 共 9 项，但 seed_library 映射了 GJ1、reflection 映射了 GJ5）（§8-E2）。
- ⚠ **出处/命名缺陷（本复核最重要发现，§8-E1）**：REPORT 称 GJ 锚点「源自 NORTH_STAR §3–§4」。但 NORTH_STAR.md 无任何 GJ 字面定义（§3=P1–P5、§4=Sparkle Moment）；而权威 GJ 清单在 `v3/05_metrics_eval/GOLDEN_JOURNEYS.md`，定义为 **GJ01–GJ20 且语义完全不同**（如 GJ04="我卡住了"→one clarification→rescope，Worker 的 GJ4=goal-track）。Worker 的 GJ1–GJ8 是自建的组合级 journey 框架——内部自洽、可从 NORTH_STAR P1–P5/Sparkle Moment/§7 五 Tab 推导，验收条款（每项映射 ≥1 GJ）在其框架下满足——但 **ID 与权威清单冲突，下游卡引用 GJ04 等编号会产生歧义**。合并时必须加注（改名如 PJ1–PJ8，或给出与 GJ01–GJ20 的对照）。
- 逐条映射合理性抽查（achievement→GJ2、community→GJ7、goal/plan→GJ4、vocabulary/document/file→GJ8、memory/settings→GJ6、openclaw→GJ3、intent→GJ3）：均能在 NORTH_STAR 语义下自圆，无牵强到影响状态判定的映射。

## 7. V3 决策一致性 — PASS

对照 `v3/00_context/DECISIONS_V3.md` 逐条：
- **D17**：「Achievement 可保留安静反馈；Shop/Photon 从核心旅程降级；Leaderboard 默认隐藏」→ CSV F01/F33/F26/F20 标注逐字吻合（leaderboard 追加 cohort 污染禁上线 + RETIRE 倾向建议，属合理从严）。
- **D19**：Focus/Calendar/ErrorBook/Vocabulary/Translation/Knowledge/Documents→Goal Context；Mirofish/Theater/Simulation→Labs/HIDDEN → CSV 长尾分组**逐项吻合**（visual_elements 归 LABS 援引 D19/D21、seed_library 归 LABS 援引 D05，均成立）。
- **D20**：shop/theater/simulation/seed「空表面不上」标注吻合。
- D04 五 Tab、D18 community 去 feed、D16 openclaw 唯一 Runtime、D09 knowledge/memory 分离：标注均一致。
- **与权威模板关系**：`v3/00_context/MODULE_MATRIX.csv` 是 desired-role 模板（B-01_current_state=TO_VERIFY，"B-01 fills current HEAD evidence"），Worker 填充行为正是卡片指令，不构成"重建真源"。状态过渡均有记录：achievement SECONDARY→CONTEXTUAL、photon/shop SECONDARY→HIDDEN（D17 支撑）、**reflection desired CONTEXTUAL→Worker 判 HIDDEN**（依据当前孤儿证据与卡片"不凭旧文档"指令，属授权内偏离，但建议合入时在 gate 记录该偏离）；intent INTERNAL→CONTEXTUAL 为状态枚举所限（无 INTERNAL 档），已在 v3_surface 注明。

## 8. 发现的错误（逐条；均不推翻状态判定）

| # | 严重度 | 错误 | 证据 |
|---|---|---|---|
| E1 | **中** | GJ1–GJ8 为 Worker 自建框架，却标注「源自 NORTH_STAR §3–§4」；与权威 `v3/05_metrics_eval/GOLDEN_JOURNEYS.md` 的 GJ01–GJ20 编号冲突、语义不同，下游引用有歧义 | NORTH_STAR.md 全文无 GJ 字面；GOLDEN_JOURNEYS.md:3-22 |
| E2 | 低 | REPORT「无 GJ 的 9 项」实为 **7 项**（seed_library 有 GJ1、reflection 有 GJ5） | CSV journey_map 列逐行清点 |
| E3 | 低 | Tab 编号错标：chat 写 Tab-2、galaxy 写 Tab-3；实际 UI 顺序 home/galaxy/chat/community/profile（chat=Tab-3、galaxy=Tab-2）。community Tab-4、profile Tab-5、home Tab-1 正确 | shell_navigation.dart:235-257 destinations 顺序；routes.dart Branch 0-4 |
| E4 | 低 | community 证据夸大：「21 条子路由」实为 20 GoRoute；「13 个外部文件引用路由常量」实为外部 2 文件（13 是 import 该 routes 文件的文件总数，12 个在 feature 内） | community_routes.dart 20×GoRoute；grep CommunityRoutes 外部=routes.dart+group_chat_screen.dart |
| E5 | 低 | `goal_decomposition_service.py:132` 被引为 db.add(goal) 落表处；:132 是 `async def create_goal(`，db.add 在 **:177**。实质（写入路径真实）成立 | sed -n '132p;177p' |
| E6 | 低 | galaxy_skins「28 行」：实为 galaxy_skins 8 + user_galaxy_skins 20 相加，表名与行数混淆 | psql 复测 |
| E7 | 低 | achievement「字符串导航 5 处」低估（实为 8 调用点/7 文件+1 常量引用）；plan「15 路径」vs 实测 14 GoRoute。保守方向，不影响可达性结论 | grep 复算 |
| E8 | 低 | REPORT §5 补测 6 项 vs portfolio.json retest_needed 5 项（少 leaderboard cohort 一项，该项为条件性故可辩护，但两产物口径不一） | 两文件比对 |
| E9 | 备注 | 网关组数 ~69（实测 72）、include_router 104（实测 105）为近似值 | grep 计数 |
| E10 | 备注 | notifications/push_histories 行数随时间漂移（2968→3041、2225→2361），REPORT §6 已声明口径，不算错误 | 两次探测差值 |
| E11 | **中（验收条款层面）** | B-01 卡 Acceptance「HIDDEN/RETIRE 用户不可达」：shop 现状有 1 条真实入口（streak_details_screen.dart:415），严格读不满足。Worker 如实记录（「可达但孤立」）并建议移除入口——处理诚实，但 **gate 放行前必须跟踪该入口移除或改判** | B-01.md:32 + §3.4 |

## 9. 补测清单诚实性 — PASS

REPORT §5 六项（goal 落表、plan_execution_records、reflection 孤儿模拟器巡检、photon 入口巡检、LABS 群数据隔离、leaderboard cohort 复算）全部是静态证据无法定论的运行时项，无一将未验证内容伪装成已验证；引用的 B-02 INV-01/02/03/04/09/13 在 `wt6/v3-output/B-02/data_truth_inventory.csv` 中确认存在。LIGHT 约束遵守（无模拟器/Gradle/写路径探测；复用运行中实例且只读，REPORT §6 已声明）。

## 10. 总 Verdict

**ACCEPT**（附修正要求，均可文字层修复，无需重做证据）：
1. 必改：E1 —— 在 REPORT/portfolio.json 为自建 GJ 框架改名（如 PJ1–PJ8）或附与 GOLDEN_JOURNEYS.md GJ01–GJ20 的对照表，并修正出处表述；E11 —— shop 入口移除动作登记为 gate 跟踪项。
2. 应改：E2/E3/E4/E5/E6（计数与行号勘误）、E8（两产物 retest 口径对齐）。
3. 核心结论全部独立复核成立：42/42 完备、HIDDEN 四项判定站得住、goals 写入路径真实、V3 决策标注一致、portfolio 与 CSV 同口径、33 项 CORE/CONTEXTUAL 全部有 journey 映射。
