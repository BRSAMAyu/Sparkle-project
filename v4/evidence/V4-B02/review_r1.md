# V4-B02 独立审查 receipt（一审）

- 审查会话：wtB02R（未参与 wtB02 实现）
- 审查对象：`agent/v4/b02` @ `235fd0fe`（source_sha `3c4618cc1d23b79792e330f87114484434a410ed`）
- 日期：2026-09-28
- 方式：只读核验（本仓 routes.dart / feature 源码 grep+读码，file:line 级）；不改产品码、不 push

## 总裁决：PASS_WITH_CHALLENGES

卡面三条可失败验收全部核验通过，映射主体（43 特征行、136 路由、挂载点、入口锚点）抽验全部属实且行号精确。但 `drift_findings.md` 有 **2 项事实错误**（C1、C2）与 **1 项分类口径不一致**（C3）、1 项重分类计数不可追溯（C4，轻微）。这些漂移结论会被 B-01 线消费，**须勘误后方可作为 B-01 修订输入**；勘误不触及 mapping.csv 主体与 route_inventory.csv 路径清单（C3 仅动 1 行 category 列与派生计数 4/10→5/9）。

## 1. 映射抽验（抽 9 行，覆盖全部 4 类；要求 8 行）

| 特征 | 类别 | 核验点 | 结果 |
|---|---|---|---|
| F01 achievement | active_entry + deep_link_only | 挂载 routes.dart:427；shell_navigation.dart:288 `push('/achievements/${…}')`；unified_notification_card.dart:518；milestone 路由注册于 achievement_routes.dart（`$milestone/:milestoneId`） | 全部行号精确命中 |
| F03 auth | active_entry | publicAuthPaths 恰为 routes.dart:153-160 六路径；redirect 守卫 192-209 区间；authProvider routes.dart:91 | 命中 |
| F07 community | tab_shell | Branch-3 `path: '/community'` = routes.dart:368 | 命中 |
| F09 documents | active_entry + no_ui_entry | profile_screen.dart:674、unified_settings_screen.dart:831 均 `push(DocumentLibraryRoutes.library)`；/documents 0 UI 入边 | 命中（分类问题见 C3） |
| F14 galaxy | tab_shell | Branch-1 `path: '/galaxy'` = routes.dart:259 | 命中 |
| F27 plan | active_entry（含 shellRoutes） | `...PlanRoutes.shellRoutes` 挂 Branch-0 = routes.dart:252；plan_detail_screen.dart:251 `Uri(path: '/exam-sprint/completion')` | 命中 |
| F28 reflection | registered_no_ui_entry | 挂载 routes.dart:430；全库仅挂载点+定义文件（api_endpoints 为后端路径非导航） | 命中 |
| F33 shop | registered_no_ui_entry（HIDDEN） | 挂载 routes.dart:435；全库无 ShopRoutes 消费；streak_details_screen.dart:106 仅余"CTA 已移除"注释 | 命中 |
| F36 task | active_entry | TaskRoutes 常量定义；全库 65 处 `/tasks*` 导航调用点 | 命中 |

另核 5 处挂载行号 415/416/427/430/435 与 Branch-4 /profile = routes.dart:385，全部精确。

## 2. 漂移发现抽验（抽 5 项；要求 4 项）

- **DF-01 shop 入口消失**：属实。ShopRoutes/'/shop' 引用仅剩挂载点 routes.dart:435 与定义文件；streak_details 无 shop 导航（仅 FIX-05 摘除注释）。
- **DF-05 /notifications 0 入边**：属实。唯一其他命中为 notification_repository.dart:56（数据层 API 路径，非 UI 导航）；通知卡实推 /notification-center（home_notification_card.dart:65，NAV-IA P-3 注释在案）。
- **DF-06 community 四条孤儿**：属实。favorites/groups/search/users/search/groups/:id/moderation 在 community_routes.dart 之外 0 导航引用。
- **DF-08 milestone id-less 静默错屏**：属实。deep_link_service.dart:16 `'milestone': '/achievements/milestone'` + :87-89 id-less 分支放行该路径；achievement_routes.dart 无 `/achievements/milestone` 精确路由，GoRouter 语义下落 `/achievements/:id`（id='milestone'）→ 错屏推演成立（limitations.md 已如实注记未运行时验证）。
- **DF-10 /documents 无入边**：现状属实（0 UI 入边），但**漏报关键事实**——/documents 是"定义即 redirect→/library"（documents_routes.dart:21-22），并非独立备播死面。由此引发 C3。

## 3. 分类完备性

- route_inventory.csv 实测 136 行（路径全唯一）；5 tab_shell + 116 active_entry + 4 legacy_redirect + 1 deep_link_only + 10 registered_no_ui_entry = 136，与 mapping_report §2、commit message、test_results.json 三处一致。
- `mobile/lib/features/` 磁盘 43 目录 == mapping.csv 43 行（F01–F44 无 F24）；onboarding 路由确在 user_routes（inventory /onboarding/persona、/onboarding/modeling-chat 两行）。
- **挑战 C3**：/documents 按 report §5 自定口径"legacy_redirect＝定义即 redirect"应归 legacy_redirect（与 chat 4 条同型），正确分布应为 5 legacy_redirect + 9 registered_no_ui_entry（总数不变）。

## 4. 诚实性

- **零产品码改动**：`git show --stat 235fd0fe` 仅 v4/evidence/V4-B02/*（9 文件）+ v4/04_tasks/tasks.json（仅 B02 implementation_state NOT_STARTED→REVIEW_READY 一处状态元数据）。矩阵未改属实。
- **八件套 sha256**：run_manifest.json 所列 8 个 artifact 哈希全部复算一致。
- **review_receipt.json 未代填**：verdict/reviewer 留空 PENDING，符合"自称完成不算完成"。
- **静态分析局限已如实登记**（limitations.md 第 1、7 条：动态下发路由不产生静态入边、深链歧义为静态推演未运行时验证）。
- **挑战 C4（轻微）**：mapping_report §4 称"静态未达 19 项…6 项重分类"，test_results.json 称"3 项推翻静态误报"，而 route_inventory.csv verification_note 可追溯的重分类实锚仅 4-5 处（/achievements/:id、/exam-sprint/completion、/learning-path、/learning/forecast，另 milestone→deep_link_only）。三处口径不齐，"6"无法逐条对账。不怀疑复核本身，但登记链不闭合。

## CHALLENGED 列表（须实现会话勘误）

| # | 位置 | 问题 | 实证 |
|---|---|---|---|
| C1 | drift_findings.md DF-09（及 mapping.csv F14 drift_note） | "sparkle://node 无 id → /galaxy/node → errorBuilder 404 兜底"不成立。deep_link_service.dart:97-98 `'node' => id != null ? … : null`：id-less 时 resolveRoute 返回 null → handleDeepLink 返回 false → **根本不发生导航，无 404**。真实行为是静默 no-op | deep_link_service.dart:76-98、:29-31 |
| C2 | drift_findings.md 深链覆盖小结 | "universal_share_service.dart:62-68 生成的 7 种分享深链全部落在上述映射内，闭合"为假。`sparkle://report`（:67，learningReport）不在 _routeMapping（:14-25 十键）→ _resolveResourceType 返回 null → 深链死亡。闭合为 6/7，非 7/7 | universal_share_service.dart:61-69、deep_link_service.dart:14-25、:132/:142 |
| C3 | route_inventory.csv /documents 行；DF-10 | /documents 为"定义即 redirect→/library"（documents_routes.dart:21-22），按 report §5 自有口径应归 legacy_redirect；分类应为 5/9 而非 4/10。DF-10"备播双面"表述应改为"redirect 别名" | documents_routes.dart:7-8、12、21-22 |
| C4（轻微） | mapping_report §4 vs test_results.json | 重分类计数 6 vs 3 互相矛盾，verification_note 仅可追溯 4-5 处 | 见 §4 |

DF-08（milestone 歧义）复核**成立**，维持；DF-09 按C1 改写为"node id-less 为静默 no-op（有 null 守卫），milestone id-less 才是错屏"。

## 结论

- 卡面验收 1（feature 集合 exact match）：**PASS**（独立复算）。
- 卡面验收 2（HIDDEN/LABS 不自动开放 + 入口 owner）：**PASS**（shop/visual_elements/reflection 0 入口独立复现；simulation/theater/seed_library const 受控）。
- 卡面验收 3（每页面 route/deeplink/数据真源记录）：**PASS（含 C3 一处分类勘误）**。
- 漂移登记质量：10 项中抽 5 项，4 项属实、1 项（DF-10）部分属实；另深链小结 1 项错误（C2）。
- 处置建议：实现会话按 C1-C4 勘误 drift_findings.md/route_inventory.csv（单 commit，不改产品码）；勘误后本卡可判 DONE，B-01 线以勘误版为准。
