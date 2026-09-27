# wt786 FIX-513 调解备忘 — 命令与证据实录

- 日期：2026-09-27；分支 `agent/node-b/wt786/p513memo`（自 main @ `16ac17b4` 切出；`6a289d6a` = 「v0.6——13/13 线深挖完成」在其父）
- worktree：`/Users/brsama/code/GitHub/Sparkle-sysrev/wt786-p513memo`
- 全程只读四源；无 docker/服务/模拟器操作；未 push。

## 1. 环境确认

```
cd /Users/brsama/code/GitHub/Sparkle-project && git log --oneline -1
# → 6a289d6a docs(v4-handoff): v0.6——13/13 线深挖完成（…）  main
git worktree add -b agent/node-b/wt786/p513memo /Users/brsama/code/GitHub/Sparkle-sysrev/wt786-p513memo main
# → HEAD is now at 16ac17b4 state(fleet): 轮#274 v0.6 达成 13/13 线+看门狗上岗+补位 wt786/787
#   （两次调用间 main 前进 1 个 fleet state 提交，不影响文档结论）
```

## 2. 三源+第 4 源全读

- `v3/V3_DEFINITION_OF_DONE.md` Gate V3-0 原文：「42 个 feature 有唯一 portfolio 状态：CORE / CONTEXTUAL / LABS / HIDDEN / RETIRE；不存在用户可达的半成品入口。」五态、无逐项值。
- `v3/00_context/MODULE_PORTFOLIO.md` 全文 42 行表。词表实计数：CORE 15/CONTEXTUAL 15/LABS 5/SECONDARY 3(achievement,photon,shop)/CORE_OPTIONAL 1(community)/HIDDEN 1(leaderboard)/INTERNAL 1(intent)/INTERNAL_CAPABILITY 1(openclaw)。头注：「"desired role" 是 V3 产品方向；B-01 必须用当前 HEAD 填实际状态。」
- `v3-output/B-01/MODULE_MATRIX.csv`（42 数据行）+ `portfolio.json`（counts: CONTEXTUAL 18/CORE 15/HIDDEN 4/LABS 5, total 42）+ `REPORT.md` + `REVIEW_RECEIPT.md`（verdict ACCEPT；§7 状态过渡记录：achievement SECONDARY→CONTEXTUAL、photon/shop SECONDARY→HIDDEN、reflection CONTEXTUAL→HIDDEN 授权内偏离、intent INTERNAL→CONTEXTUAL 枚举所限）。
- **第 4 源**（任务书外发现，RECEIPT §7 引为「权威模板」）：`v3/00_context/MODULE_MATRIX.csv`，42 行 desired_v3_role 与 PORTFOLIO 逐值一致，B-01_current_state 列全 TO_VERIFY 从未回填。
- FIX-513 台账原文：`v3/06_agent_fleet/DYNAMIC_ISSUES.md:405`。

## 3. 逐 feature 对照（产出见 memo.md §2）

手工逐行比对 42 项（PORTFOLIO vs B-01 CSV status 列）：一致 35、分歧 7。分歧逐项核对 v3_surface 列与 RECEIPT §7，均有出处记录。

## 4. 漂移面圈定与亲证（a2d8a10c..HEAD）

```
git log --oneline a2d8a10c..HEAD | wc -l        # → 1509
git log a2d8a10c..HEAD --name-only --format= | grep -E "^mobile/lib/features/" | cut -d/ -f4 | sort | uniq -c
# → 42 目录全部被触及（粗粒度不可用），另见 journey/recovery 两个非册内目录
git log a2d8a10c..HEAD --diff-filter=D --name-only --format= -- "mobile/lib/features/*.dart" 分目录统计
# → user 7 / onboarding 3 / leaderboard 3 / settings 2 / home 2 / photon 1 / insights 1 / goal 1
```

删除归因（逐 commit 亲证）：
- leaderboard：`4d353132` 删 1143 行死链三件套（screen/provider/repo）[LEADERBOARD-DEBT]；KNOWN_CODE_DEBT_LEDGER #3 = D-COMM-1/D-COMM-4 销账原文（v3-output/D-COMMUNITY/DESIGN.md §2.2/§3.2）。
- onboarding：`e610853e` FIX-342 删 interactive 4 屏整链（含 barrel）→ 目录消失。
- photon：`c69c6879` 余额卡删除（交易历史屏先迁出）、/photon/transfer 删、redeem-pro 面。commit 明言 "transaction history reachable"。
- settings：`8e837e8a` FIX-440/GOV-015 data_usage_dashboard（655 行）；`aa6a9667` FIX-182/183 transparency_settings_screen。
- user：`4a7c3414` FIX-489 WS6 全链（2636 行）；`a29ed3f1` FIX-490 learning_mode（166+393 行）。
- insights：`667001e6` PredictiveInsightsCard 假精确面删除。home：`7729f5a1` omnibar/visual_renderer。goal：`8772260d` 仅 l10n widget（饰面）。

HEAD 开文件亲证（可达性翻转）：
```
grep -n "LeaderboardRoutes\|PhotonRoutes\|ReflectionRoutes\|ShopRoutes" mobile/lib/app/routes.dart
# → :411 ...LeaderboardRoutes.routes / :429 PhotonRoutes / :430 ReflectionRoutes / :435 ShopRoutes（四组均仍挂载）
cat mobile/lib/features/leaderboard/leaderboard_routes.dart
# → /leaderboards/self-anchor 注册；"全站综合榜保持 D17 隐藏不建路由；本文件只挂自我锚"
grep -rn "selfAnchor" mobile/lib --include="*.dart" | grep -v features/leaderboard
# → plan/sprint_screen.dart:64 与 community/squad_detail_screen.dart:295 两处 context.push（真实入口）
grep -rn "PhotonRoutes\." mobile/lib --include="*.dart" | grep -v features/photon
# → shop/shop_screen.dart:64 与 user/profile_screen.dart:697 push redeemPro（真实入口）
grep -rn "ShopRoutes\." / "ReflectionRoutes." （排除挂载行）→ 均仅 routes.dart 挂载行（零入口，维持）
grep -n "shop" mobile/lib/features/achievement/presentation/screens/streak_details_screen.dart → 0（FIX-05 入口已移除）
grep -n "photon|shop|reflection|leaderboard" mobile/lib/core/services/deep_link_service.dart → 0 映射
```

全集亲证：
```
ls mobile/lib/features/ | wc -l   # → 43
git ls-tree a2d8a10c 对比 diff    # → +journey +recovery −onboarding（基线=42）
# journey：J-04 02b82cd2 / J-06 7bd6ade3（2026-09-25），FirstActionCard 挂 home dashboard 可达
# recovery：J-05 c4c36ead（2026-09-25），StuckJourneySheet 三入口（home cockpit/goal 详情/task 执行屏）
grep -n "personaOnboarding\|modelingChat" mobile/lib/features/user/user_routes.dart
# → :35-36 常量、:76-77 GoRoute 挂载（onboarding 功能本体活在 user feature）
```

intent 消费复核（omnibar 删除后）：
```
grep -rn "features/intent/" mobile/lib --include="*.dart" | grep -v "^mobile/lib/features/intent/"
# → chat/presentation/widgets/intent_preview_dialog.dart:9-10、intent_analysis_button.dart:8-9 直连 repository/models
# → CONTEXTUAL 状态仍立，仅 B-01 证据行（omnibar 消费）过时
```

FIX-05 销账原文：DYNAMIC_ISSUES.md:11 `FIXED@e3ff2df9`（入口整块移除 + 后端 RELEASE_ENABLE_SHOP 默认 False→403 先于鉴权 + 红测实录）。visual_elements 旗控：backend/app/api/v1/router.py:306 RELEASE_ENABLE_VISUAL_ELEMENTS。

真源文件零变更证明：
```
git log --oneline a2d8a10c..HEAD -- v3/V3_DEFINITION_OF_DONE.md v3/00_context/MODULE_PORTFOLIO.md v3/00_context/MODULE_MATRIX.csv
# → 空（三份 0 变更）
```

## 5. 新发现缺陷登记（只记本 notes，不占台账——按任务硬约束）

编号空闲性 grep 复核（2026-09-27）：`V3-FIX-533`~`536` 在 DYNAMIC_ISSUES.md 与全 v3/ v3-output/ 均 0 命中（WT783-HUMANINBOX/notes.md:81-84 亦曾核 533 空闲未占用）。

- **V3-FIX-533（候选登记）**：portfolio 42 全集漂移——HEAD `mobile/lib/features/`=43 目录（+journey +recovery −onboarding）；journey（J-04/J-06）与 recovery（J-05）均为用户可达成品面但不在 DoD 42 册/PORTFOLIO/B-01 任何一册；onboarding 目录已删（FIX-342）而功能本体活在 user feature（/onboarding/persona、/onboarding/modeling-chat）。「42 个 feature 有唯一 portfolio 状态」对当前代码库字面不可满足。证据：本 notes §4 全集亲证。
- **V3-FIX-534（候选登记）**：B-01 HIDDEN 判定两项已失效——leaderboard 死链删除（4d353132）后 /leaderboards/self-anchor 注册且 2 实入口（sprint_screen:64、squad_detail_screen:295）；photon /photon/redeem-pro 注册且 2 实入口（profile_screen:697、shop_screen:64）+历史二级入口，孤儿前提（PhotonBalanceCard/transfer）已删（c69c6879）。Q-08 若按 B-01 现值判这两项即过判。

## 6. 交付物

- `v3-output/WT786-P513MEMO/memo.md`（裁决材料正文：§2 对照表 42 行、§3 映射表、§4 漂移清单 13 项、§5 裁决建议、§6 Q-08 影响面）
- 本 notes.md
- commit：`docs(p513): wt786 …`（分支 agent/node-b/wt786/p513memo，不 push）

## 7. 未做与移交

- 未复测 DB 行数/未 curl（无运行栈触碰权约束）；B-01Δ 卡应含 B-01 原 retest_needed 5 项 + leaderboard/photon 新态运行时巡检。
- 未做模拟器运行时巡检；深链旁路（deep_link_service resolveRoute 裸路径直通）在 HEAD 仍无 photon/shop/leaderboard 映射（grep 0 命中）。
- main 若在终门继续前进：A/B 类漂移结论由历史提交因果支撑仍稳；C 类证据行数可能再漂。
