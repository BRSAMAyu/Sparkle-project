# V4-B02 报告：43 模块及在用路由映射增量

- 卡：V4-B02（verification · normal · 1 独立审查 · HEAVY=False）
- 执行：wtB02（agent/v4/b02）@ source_sha `3c4618cc1d23b79792e330f87114484434a410ed`
- 日期：2026-09-28
- 性质：**只读核验 + 增量映射**。产品代码零修改；矩阵未改（漂移归 B-01 线处置）。

## 1. 结论（可失败判据逐条）

| 验收 | 结果 |
|---|---|
| 当前 feature 集合 exact match，无遗漏/幽灵 onboarding 目录 | **PASS**：`mobile/lib/features/` 43 目录 == B-01Δ 矩阵 43 行（F01–F44，无 F24）；双向差集为空（程序化比对，脚本见 run_manifest）；onboarding 归 user（`/onboarding/persona`、`/onboarding/modeling-chat` 定义于 user_routes.dart，无独立 feature 目录） |
| HIDDEN/LABS 不自动开放；所有活跃入口均有迁移负责人 | **PASS（含注记）**：shop(HIDDEN)/visual_elements(LABS) 现存 0 UI 入口（U-07/入口摘除后）；reflection(HIDDEN) 0 入边；simulation/theater/seed_library(LABS) 保持 const 级受控入口无自动开放。入口归属按 mapping.csv `entry_evidence` 列逐条给出 owner 文件 |
| 每个页面记录 route/deeplink/数据真源/当前证据层级 | **PASS**：43/43 特征行含 entry_routes / reachability / entry_evidence / deep_links / data_provider_anchor 列；136 条注册路由含 defined_in/name/入边计数（route_inventory.csv） |

## 2. 覆盖率（一行）

**43/43 特征（100%）完成"真实入口路由×可达性×深链×数据 provider 锚点"映射；136 条注册路由全部分类：5 tab_shell + 116 active_entry + 4 legacy_redirect + 1 deep_link_only + 10 registered_no_ui_entry；32/32 路由组均挂载、0 孤儿路由文件；11 个无路由特征全部取得数据层/嵌入面消费证据。**

## 3. 交付物

- `mapping.csv` — 43 特征 × 入口路由/可达性/证据/深链/provider 锚点/漂移注记
- `route_inventory.csv` — 136 注册路由 × 定义位置/类别/入边计数/核验注记
- `drift_findings.md` — 矩阵↔代码漂移登记（本卡发现，不修矩阵）
- 卡要求 5 件：diff_or_evidence_only.md / run_manifest.json / test_results.json / review_receipt.json / limitations.md

## 4. 方法（程序化为主 + 人工抽样 ≥10）

程序化四趟扫描（Python，全部命令与 exit code 见 run_manifest.json）：
1. 解析 32 个 `*_routes.dart`：路径常量（含 `$base` 插值求值）+ GoRoute(path,name) → 136 路径；`app/routes.dart` 5 Branch 内联 + 32 组挂载点。
2. 全库字符串导航（多行/泛型感知 `push<T>('...')`）→ 61 个去重目标；Uri(path:) 构造型与 `route:`/`routeBuilder:` 配置型单独扫描。
3. 路由常量跨文件引用（`Class.const` + `static String xxxPath()` helper）解析入边；`sparkle://` 深链表（deep_link_service.dart:14-25）与 10 类映射解析。
4. 静态未达集合（19 项）逐项人工复核，6 项证实用非常规通道可达后重分类（见 route_inventory.csv verification_note 列）。

人工抽样核对（17 项，全部以 file:line 复核）：
leaderboard 自我锚双入口（sprint_screen:64 / squad_detail:295）、photon 兑换（profile:697）、journey FirstActionCard 嵌入（dashboard import+FIX-540 注释）、recovery 三宿主 sheet（305/544/509 行号与矩阵精确一致）、mirofish 三宿主、settings 四能力面挂载方式、vocabulary 工具注册（tool_registry:216）、aurora 数据层消费、splash 初始路由+防开放重定向、auth 公开路径守卫、documents /library 双入口、visual-elements U-07 摘除注释、shop 0 入口、reflection 孤儿、galaxy drafts/review const、notification-analytics 摘除（NAV-IA P-3 注释）、HybridJourneySheet 0 外部调用。

## 5. 可达性口径

- `tab_shell`：五 Tab（/home /galaxy /chat /community /profile，routes.dart:228-399；plan 的 shellRoutes 挂 Branch-0）。
- `active_entry`：注册且有 ≥1 静态入边（字符串导航/常量引用/配置引用/深链）。
- `legacy_redirect`：chat 旧路径 4 条兼容 shim（定义即 redirect，chat_routes.dart:103-149）。
- `deep_link_only`：仅深链可达（/achievements/milestone/:milestoneId）。
- `registered_no_ui_entry`：注册但 0 UI 入边（10 条，见漂移登记 DF-05~DF-10）。
- 嵌入面（无路由）：sheet（recovery）、card（journey）、dialog、tab 内组件、数据层（aurora/intent/knowledge/experience/document/file/vocabulary/mirofish）。

## 6. 与 B-01Δ 矩阵的关系

本卡不修改矩阵。漂移如实登记于 `drift_findings.md`：**10 条新发现**（矩阵滞后 4：shop 入口消失、visual-elements 双入口被 U-07 摘除、notification-analytics 路由被 NAV-IA P-3 摘除、settings transparency 面改内联；路由无入边 5 组；深链歧义 2 条——milestone id-less 落 `/achievements/:id`、node id-less 落 404 兜底）+ **2 条确认未变**（reflection HIDDEN 孤儿、journey HybridJourneySheet 0 调用）。处置归 B-01 线与相应 owner 卡。

## 7. 自我锚与受限光子出口（卡片要求保留项）

- leaderboard：仅 `/leaderboards/self-anchor` 路由面（D-COMM-1），全站榜无路由——核验一致，未发现回潮。
- photon：`/photon/redeem-pro`（D-COMM-2 兑换出口）+ `/photon/history` 挂载在案；`/photon/transfer` 保持撤除（PHOTON #10），屏文件留置已登记债务——核验一致。
