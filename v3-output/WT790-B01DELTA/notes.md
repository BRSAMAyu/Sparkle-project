# wt790 B-01Δ notes — 工作实录

- 日期：2026-09-27；分支 `agent/node-b/wt790/b01delta` @ `27bd05e5ac4f9acd2d23c9988f42f50c5bcf2cc6`（worktree `/Users/brsama/code/GitHub/Sparkle-sysrev/wt790-b01delta`）
- 派卡时主仓 HEAD 复核：`b53ad522` docs(postgate) 在 `git log --oneline -3` 内 ✓；worktree 建立时 main 已前进至 `27bd05e5`（state(fleet) 轮#277，含 FIX-533/534 台账登记 `2ec2302c`）——审计点钉在 27bd05e5，全部证据行号以该树为准。
- 素材在位复核：`v3-output/WT786-P513MEMO/{memo.md,notes.md}` ✓。

## 方法与口径锁定

- 先读 WT786-P513MEMO/memo.md 全文（42/42 对照表、§3 折叠规则、§4 漂移清单、§5.3 B-01Δ 范围），再读 B-01 原册三件：MODULE_MATRIX.csv（header=feature_id,name,module_path,status,jtbd,journey_map,data_truth,reachability_evidence,v3_surface,source_sha）、portfolio.json（baseline_sha=a2d8a10c；counts CORE15/CONTEXTUAL18/LABS5/HIDDEN4）、REVIEW_RECEIPT.md（判定口径=路由注册 GoRoute+挂载行×外部字符串导航入口文件:行×深链映射×DB/curl；五态=可达性×产品面实际状态；E1 GJ 框架歧义、E11 shop 入口跟踪）。
- 硬约束遵守：不碰运行栈 → DB 行数/curl 全部未复测，data_truth 记「继承/未复测」；未改 B-01 原产物/台账/MODULE_PORTFOLIO；未 push；未碰 /tmp/northstar_ns001_real_drive_state.json；主仓只读（worktree 内产出）。
- 深链核查方法：`grep -n "onboarding|journey|stuck|self-anchor|photon" mobile/lib/core/services/deep_link_service.dart` = 0 命中（五项全部无深链映射，与 B-01 口径一致记录）。

## 逐项证据命令实录（worktree 内）

1. **全集计数**：`ls mobile/lib/features/` = 43 目录（−onboarding +journey +recovery）；`find mobile/lib/features/leaderboard -type f` = 5 文件（routes/repo/model/provider/screen，全 self-anchor 族；旧 leaderboard_screen.dart 不存在）。
2. **leaderboard**：`cat leaderboard_routes.dart`（selfAnchor 常量+GoRoute）；`grep -n LeaderboardRoutes mobile/lib/app/routes.dart` → :29 import、:411 挂载（含 rule-comm-lb ignore 注释）；`grep -n "context.push(LeaderboardRoutes.selfAnchor)"` → sprint_screen.dart:64、squad_detail_screen.dart:295；`ls scripts/guards/check_rule_comm_lb_leaderboard_unrouted.py` 在树；KNOWN_CODE_DEBT_LEDGER #3 = D-COMM-1/D-COMM-4 销账原文（1143 行删除、保留 leaderboardsSelfAnchor 常量与 12 个 l10n 键）；后端 router.py:276 include /leaderboards、proxy_routes.go:1078-1083 网关组。
3. **photon**：`cat photon_routes.dart`（history+redeemPro 两条；transfer 撤路由注释=PHOTON 卡 #10 反刷，屏文件保留已登记债务）；挂载 routes.dart:429；`grep -n "context.push(PhotonRoutes.redeemPro)"` → profile_screen.dart:697、shop_screen.dart:64；redeem 屏二级入口 photon_redeem_pro_screen.dart:272；`grep -rln PhotonBalanceCard` = 0（已删，c69c6879）；shop 不可达复核：`push('/shop')` 外部 0、deep link 0、settings.py:144 RELEASE_ENABLE_SHOP=False、router.py:283-290 旗控 403 → shop_screen.dart:64 入口不计（RECEIPT §3.4 同口径）。
4. **onboarding**：`ls features | grep onboard` 无；`git ls-tree -r --name-only a2d8a10c -- mobile/lib/features/onboarding/` = 3 文件（barrel+interactive 屏+动画，即 FIX-342 删除面）；persona/modeling 屏基线即在 user feature（user_routes.dart:20 import modeling_chat_screen）；常量 user_routes.dart:35-36、GoRoute :74-77 区段、挂载 routes.dart:425；实入口 onboarding_resume_card.dart:86（context.go）、user_persona_screen.dart:893（push）；链内 402/448/624；**J-02 软化原文 routes.dart:211-219**（「注册墙从全域硬重定向改放行+提醒…价值先于画像」）→ B-01 CORE 唯一 reachability 证据（强制重定向必达）已删除 → 改判 CONTEXTUAL。
5. **journey**：`find features/journey` = 5 文件（2 repo/1 model/2 widget，无 routes）；FirstActionCard 唯一外部挂载 dashboard_screen.dart:1168（hasNoGoals 分支可见+自守门 shrink，注释见 :1160-1167）；后端 router.py:71/212；创建提交 02b82cd2/7bd6ade3 提交文全读；**`grep -rn "HybridJourneySheet|hybrid_journey" -l` 全 lib 仅 journey 自身 3 文件；showHybridJourneySheet 外部 0 调用；hybrid_journey_repository 0 外部消费者 → J-06 移动面孤儿=新缺陷**。
6. **recovery**：`find features/recovery` = 4 文件（无 routes）；`grep -rn StuckJourneySheet`（排除自身）= 恰 3 处调用 today_cockpit_card.dart:305 / goal_detail_screen.dart:509 / task_execution_screen.dart:544（surface 参数 home/goal/task 各带真实 id）；后端 /experience/stuck-journey start|answer|correct（c4c36ead）。

## 新缺陷登记

- **V3-FIX-535**（自本号起；533/534 已被主会话占用，grep 台账复核空闲）：J-06 HybridJourneySheet（mobile/lib/features/journey/presentation/widgets/hybrid_journey_sheet.dart）+ hybrid_journey_repository 全仓零生产消费者——后端 /journey/hybrid 四端点活但移动 UI 无任何入口（showHybridJourneySheet 0 外部调用），构成「用户不可达的已建成面」与 journey feature 的 CONTEXTUAL 判定并存张力。7bd6ade3 提交文自述「mobile 统一 Runtime/UI 不另起交接面」，但未留任何挂载点。处置建议：挂载点裁决（cockpit/FirstActionCard 扩展位）或降级注记。**只登记于本 notes，不动台账。**

## 诚实声明

- DB 行数/curl/模拟器巡检零执行（硬约束）；五项 data_truth 均为「继承基线或提交文转引」，合入后如需 gate 级 data 证据须补运行时探测。
- J-04/J-06/J-05 的「后端活」判定基于 router include 静态行+提交文，未发请求。
- main 在我审计期间可能继续前进；A/B 类结论由历史提交因果支撑应稳，行号证据以 27bd05e5 为准。
- 未做 42 项全量重跑（卡面明确排除）；memo §4 C/D 类证据勘误未落入本 delta CSV（超范围，建议随真源合入文字层处理）。
