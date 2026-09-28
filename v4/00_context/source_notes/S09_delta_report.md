# B-01Δ Scoped Delta 审计报告 — wt790（FIX-513/533/534 收口审计）

- worker：wt790（分支 `agent/node-b/wt790/b01delta` @ `27bd05e5ac4f9acd2d23c9988f42f50c5bcf2cc6`，worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt790-b01delta`）
- 卡：B-01Δ scoped 审计——**只做 5 项定域重审，不做 42 项全量重跑**（WT786-P513MEMO §5.3 处置建议；Q-08 判 V3-0 的前置）
- 审计点：`27bd05e5ac4f9acd2d23c9988f42f50c5bcf2cc6`（main tip @ 派卡时，含 `b53ad522` docs(postgate) 与 `2ec2302c` FIX-533/534 台账登记）
- 对照原册：`v3-output/B-01/`（基线 `a2d8a10c192f451a2c11042df8e4f6227cad37f9`，REVIEW_RECEIPT verdict ACCEPT）
- 口径：与 B-01 原册/RECEIPT 同口径——路由注册（GoRoute + routes.dart 挂载行）× 外部实入口（`context.push/go` 文件:行）× 深链映射 × 后端端点（静态）；五态按「可达性×产品面」实际状态判定，产品意图折叠进 v3_surface 注记（FIX-513 §3 映射规则）
- 边界：**不碰运行栈**——DB 行数/curl 探测一律未复测，data_truth 记「继承基线/未复测」；无模拟器巡检（原册 retest_needed 5 项仍开放）。B-01 原产物、台账、MODULE_PORTFOLIO 零改动。

---

## 一句话结论

5 项全部完成亲证：**leaderboard HIDDEN→CONTEXTUAL、photon HIDDEN→CONTEXTUAL**（两处 A 类状态翻转坐实并定档）；**onboarding 判并入 user 承载、CORE→CONTEXTUAL**（J-02 软化删「必达」前提，全集定位=new）；**journey/recovery 以 F43/F44 新增入册，均 CONTEXTUAL**（B 类全集漂移收口）；43 目录与册载可恢复 1:1。**1 个新缺陷**：J-06 HybridJourneySheet 零生产入口（登记 V3-FIX-535，仅 notes.md）。

---

## 项 1 — leaderboard（F20）：HIDDEN → **CONTEXTUAL**

### 现状证据（HEAD 27bd05e5 亲证）
- **路由注册**：`/leaderboards/self-anchor` 常量+GoRoute 注册于 `mobile/lib/features/leaderboard/leaderboard_routes.dart`（class LeaderboardRoutes，`selfAnchor = '/leaderboards/self-anchor'`）；挂载 `mobile/lib/app/routes.dart:411`（`...LeaderboardRoutes.routes`，上行注释「rule-comm-lb: ignore D-COMM-1 self-anchor only, no global board」）。
- **实入口 2 处**（B-01 口径=外部文件 context.push）：
  - `mobile/lib/features/plan/presentation/screens/sprint_screen.dart:64`（`context.push(LeaderboardRoutes.selfAnchor)`，冲刺历史钮旁次级位置）
  - `mobile/lib/features/community/presentation/screens/squad_detail_screen.dart:295`（小队榜降级态「查看自我锚」按钮，`squad-degrade-self-anchor-button`）
- **死链三件套已删**：`leaderboard_screen.dart` 全仓不存在；D-COMM-4 销账（KNOWN_CODE_DEBT_LEDGER #3：screen/provider/repo 1,143 行整链删除+6 死常量+11 死 l10n 键）。B-01「screen 0 引用死代码」前提已物理消失。
- **全站综合榜仍不路由**：LeaderboardRoutes 仅 selfAnchor 一条；守卫 `scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py` 在树且固化（routes.dart 不挂 LeaderboardScreen + 网关 leaderboards 组 wildcard-only，`backend/gateway/internal/handler/proxy_routes.go:1078-1083`）。
- **后端**：`backend/app/api/v1/router.py:276` include `/leaderboards`；自我锚端点 `GET /leaderboards/self-anchor`（D-COMM-1 裁决落地）。
- **深链**：deep_link_service 0 映射（grep 亲证）。
- **DB/curl**：未复测（不碰运行栈）；基线 leaderboard_snapshots 0 行继承；cohort 污染修复状态未复测（B-02 INV-09 继承为开放项）。

### 判定（B-01 判据同口径）
路由注册+挂载 ✓、≥1 真实外部入口 ✓（2 处，宿主 plan=CORE/community=CONTEXTUAL 均可达面）、后端活 ✓ → 按可达性×产品面判 **CONTEXTUAL**。非 LABS：非实验分组（D19 长尾不含 leaderboard），是 D-COMM-1 正式裁决的产品面（自我 7 日锚，sprint 账本+study_records 真源）。非 CORE：无 Tab，双入口均次级位置。
与原册 diff：status HIDDEN→CONTEXTUAL；reachability_evidence 整行重写；v3_surface 改写为「D17 全站榜禁令不变（D-COMM-1：大池/异质/静态综合分反模式）+唯一路由面=自我锚+cohort 未复测注记」；RETIRE 倾向建议撤销（死屏前提已灭）；journey_map 增「无独立 GJ（sprint/goal 伴随面）」。D17 愿景（默认隐藏）与 HEAD 现实的表面冲突由后续裁决 D-COMM-1（2026-09）消解，不构成违规。

## 项 2 — photon（F26）：HIDDEN → **CONTEXTUAL**

### 现状证据
- **路由注册**：`/photon/redeem-pro`（D-COMM-2 兑换出口）与 `/photon/history` 注册于 `mobile/lib/features/photon/photon_routes.dart`；挂载 `mobile/lib/app/routes.dart:429`。`/photon/transfer` **路由已撤**（PHOTON 卡 #10/A-SPEC2 PH-G3 反刷裁决；屏文件 photon_transfer_screen.dart 保留未删、已登记债务、深链落 errorBuilder 兜底）。
- **实入口（可达面）**：`mobile/lib/features/user/presentation/screens/profile_screen.dart:697`（`context.push(PhotonRoutes.redeemPro)`；user=CORE Tab-5 profile 面）——**唯一计入的用户可达入口**。
- **不计入入口**：`mobile/lib/features/shop/presentation/screens/shop_screen.dart:64` 同样 push redeemPro，但 shop 自身维持 HIDDEN（全仓 `push('/shop')` 外部 0 命中、深链 0 映射、后端 `RELEASE_ENABLE_SHOP=False`（backend/app/config/settings.py:144）→403 先于鉴权，router.py:283-290）——不可达面内的按钮不构成用户可达入口（B-01 RECEIPT §3.4/E11 同口径）。
- **二级入口**：redeem 屏内进交易历史 `photon_redeem_pro_screen.dart:272`（`context.push(PhotonRoutes.transactionHistory)`）——B-01「/photon/history 仅被孤儿余额卡引用」链路重接：余额卡已删（PhotonBalanceCard 全仓 0 命中，删除提交 `c69c6879`），history 改由 redeem 屏二级入口可达。
- **深链**：0 映射。**后端**：/photons include 活（router.py:292）。**DB/curl**：未复测；基线 photon_transaction_history 25 行继承。

### 判定
注册+挂载 ✓ + CORE 面真实入口 1 处 ✓ + 链内二级入口 ✓ + 后端活 ✓ → **CONTEXTUAL**（FIX-513 §3 折叠规则：SECONDARY→可达且产品面活→CONTEXTUAL）。与原册 diff：status HIDDEN→CONTEXTUAL；三项 HIDDEN 证据（孤儿卡/transfer 0 入口/history 仅孤儿引用）全部失效并逐项注明去向；v3_surface 保留 D17 降权语义注记+D-COMM-2 出口语义。

## 项 3 — onboarding（F24）：全集定位=**并入 user 承载**；CORE → **CONTEXTUAL**

### 现状证据
- **目录已删**：`mobile/lib/features/onboarding/` 不存在（ls 亲证）。基线该目录仅含 barrel+interactive_onboarding_screen+architecture_animation（`git ls-tree a2d8a10c` 亲证 3 文件），interactive 层由 FIX-342（`e61085e`）删除。
- **功能实质自始居于 user feature**：persona/modeling 屏文件在基线即位于 `mobile/lib/features/user/presentation/screens/`（persona_onboarding_screen.dart、modeling_chat_screen.dart——user_routes.dart:20 import 亲证）；路由常量 `user_routes.dart:35-36`（`/onboarding/persona`、`/onboarding/modeling-chat`）+GoRoute 注册（:74-77 区段）+挂载 `app/routes.dart:425`（`...UserRoutes.routes`）。B-01 原册 reachability 本就写「注册于 UserRoutes」——只有 module_path 指向了已删目录。
- **现存实入口 2 处外部**：`mobile/lib/features/home/presentation/widgets/onboarding_resume_card.dart:86`（`context.go(UserRoutes.personaOnboarding)`，home 首页续引导卡）；`mobile/lib/features/user/presentation/screens/user_persona_screen.dart:893`（push persona）。链内流转 persona→modeling-chat（persona_onboarding_screen.dart:402/448/624）。
- **关键证据翻转（J-02/A-SPEC8B G1，routes.dart:211-219 注释原文）**：注册墙从「引导未完成=全域硬重定向」改为「**放行+提醒**」——非 guest 用户 onboardingCompleted==false 不再被弹回 persona，可先体验价值（首聊/首目标），首页经 OnboardingResumeCard 提供续引导；反向重定向保留（已完成/guest 踏入 persona 面→/home）。B-01 CORE 判定的唯一 reachability 证据「routes.dart 强制重定向(非游客未完成必达)」**已删除**。
- **深链**：0 映射。DB：未复测（users/user_preferences_center 基线 248 行继承）。

### 判定（全集定位+状态）
- **全集定位：并入 user 承载**（本 delta 判定）。persona/modeling 屏与路由自基线起就物理居于 user feature；原 module_path 只覆盖已删的 interactive 层；HEAD 上不存在（也不需要恢复）独立 onboarding 目录。
- **状态：CONTEXTUAL**（同口径推论）：路由注册+2 外部实入口+产品链活 → 可达；但「必达首程」这一 CORE 区分性证据被 J-02 裁决删除（「价值先于画像」），无 Tab、非强制 → 不再满足 B-01 给 F24 的 CORE 论证。**若主会话产品侧要保 CORE，须以新证据（如注册流程 push 直达）推翻本判定，而非沿用旧重定向证据。**
- **计数口径**：并入后若 F24 保留册内行（module_path=mobile/lib/features/user，本 delta CSV 即此形），册载 44 行 vs 目录 43（onboarding 无目录，1:1 破缺系有意）；若按 RECEIPT §1「目录↔册名 EXACT MATCH」口径则 F24 除名、链注记并入 user 行 → 册载 43 = 目录 43。两形证据相同，计数裁决归主会话（V3-0「42 个 feature」字面须改为 N=43 口径，两形皆然）。
- 与原册 diff：module_path 改指 user；status CORE→CONTEXTUAL；reachability/v3_surface 整行重写（J-02 软化+并入注记+D05 不伪造历史保留）。

## 项 4 — journey（**新增 F43**）：**CONTEXTUAL**（附 J-06 孤儿注记）

### 现状证据
- **目录**：`mobile/lib/features/journey/`（widgets/repositories/models，**无 routes 文件、无 GoRoute、无深链**——嵌入面形态）。
- **实入口 1 处**：FirstActionCard 挂 home dashboard `mobile/lib/features/home/presentation/screens/dashboard_screen.dart:1168`（新用户 hasNoGoals 分支亦可见；卡内自守门：无 goal/无链路状态→SizedBox.shrink，零布局影响）。J-04 链（生成/确认/拒绝/编辑/重开回放）在卡内闭环。
- **后端活**：`/journey` 组 router.py:71/212（first-action 生成/状态/编辑）；J-06 hybrid 四面（start/judgment/outcome-confirm/GET state）。创建提交 `02b82cd2`（J-04）、`7bd6ade3`（J-06）。
- **新缺陷（V3-FIX-535，仅 notes.md 登记）**：**HybridJourneySheet（J-06 移动面）全仓外部 0 调用**——`showHybridJourneySheet`/`HybridJourneySheet` grep 全 lib 仅 journey feature 自身 3 文件命中，hybrid_journey_repository 同样 0 外部消费者；后端 hybrid 四端点活但移动 UI 无生产入口=孤儿面。memo 未及此项（memo 仅证 FirstActionCard 可达）。
- **DB/curl**：未复测；迁移 j05_20260925/j06_20260925（hybrid_journey_artifacts 表）见提交文。

### 判定
嵌入面+CORE 宿主真实入口+后端链活 → **CONTEXTUAL**。非 CORE：无 Tab、卡自守门、按钮 outline/ghost 档（J-03 不与 cockpit primary 竞争）。非 HIDDEN：J-04 面真实可达。journey_map：J-04=first-action 链（Goal→Context→Aurora→Proposal→confirm→Task）、J-06=hybrid 旗舰（prep→judgment→execute→outcome，**移动面暂无入口**）。注：J-04/J-06 为卡级 journey 编号，与 B-01 自建 GJ1–GJ8 框架及权威 GJ01–GJ20 均不同源（RECEIPT E1 歧义在合并时一并加注）。

## 项 5 — recovery（**新增 F44**）：**CONTEXTUAL**

### 现状证据
- **目录**：`mobile/lib/features/recovery/`（sheet/widgets 形态，无 routes、无深链）。
- **实入口 3 处**（全部 `showStuckJourneySheet`，宿主均 CORE 面，携带真实 context）：
  - `mobile/lib/features/home/presentation/widgets/today_cockpit_card.dart:305`（surface=home+cockpit 当前任务 id）
  - `mobile/lib/features/goal/presentation/screens/goal_detail_screen.dart:509`（surface=goal+goalId）
  - `mobile/lib/features/task/presentation/screens/task_execution_screen.dart:544`（surface=task）
- **后端活**：/experience/stuck-journey start|answer|correct（`c4c36ead` J-05；后端读真源派生单问/intervention，不客户端拼模板）。
- **DB/curl**：未复测。

### 判定
3 个 CORE 宿主真实入口+后端三端点活 → **CONTEXTUAL**。journey_map：GJ3=stuck-loop（与 B-01 框架同码：aurora 供判断/数据层，recovery 为用户干预面，分工注记入 v3_surface）。

---

## B-01Δ 矩阵增量（5 行，列名与原 CSV 头同构）

见同目录 `MODULE_MATRIX_DELTA.csv`（header+5 数据行；**原 CSV 未改动**，合入由主会话执行）。source_sha 统一=`27bd05e5ac4f9acd2d23c9988f42f50c5bcf2cc6`。

| feature | 原册(a2d8a10c) | Δ 判定(27bd05e5) | 性质 |
|---|---|---|---|
| F20 leaderboard | HIDDEN | **CONTEXTUAL** | A 类翻转坐实（死链删+self-anchor 可达） |
| F24 onboarding | CORE | **CONTEXTUAL**（并入 user 承载，module_path 改指） | B 类全集漂移+A 类证据翻转（J-02 软化） |
| F26 photon | HIDDEN | **CONTEXTUAL** | A 类翻转坐实（redeem-pro 可达） |
| F43 journey | （未入册） | **CONTEXTUAL**（新增） | B 类全集漂移收口（J-06 孤儿注记→FIX-535） |
| F44 recovery | （未入册） | **CONTEXTUAL**（新增） | B 类全集漂移收口 |

## 对 Q-08 / V3-0 的影响

1. memo §6 阻塞 1（全集破坏）与 2（状态翻转未裁决）**证据层已闭**：本 delta 给出 5 行可合入增量，43 目录可与册载恢复 1:1（F24 除名形）或 44/43 注记形（合入形），计数口径「42→43」须随合入改字。
2. 阻塞 3（双真源）与注记钉时点仍待主会话文字层裁决（memo §5.1/5.2，非本卡范围）。
3. 残余开放（诚实声明）：DB 行数/curl/模拟器运行时巡检全部未做（硬约束不碰运行栈）；原册 retest_needed 5 项维持开放；V3-FIX-535（J-06 移动面孤儿）为新发现缺陷，待派卡。
4. 其余 37+2 项（memo §4 C/D 类证据过时项）未在本次 5 项范围内，按 memo §5.3「不建议全量重跑」维持原册状态，其证据行勘误（settings 2 屏、user WS6 删除等）建议随真源合入时按 memo §4 表格文字层更新。
