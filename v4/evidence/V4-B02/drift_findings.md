# V4-B02 漂移发现登记（矩阵↔代码 @ 3c4618cc）

> 本卡只登记不修复。矩阵修订归 B-01 线；路由/入口处置归各 owner 卡。
> 分类：[矩阵滞后] = 矩阵描述与当前代码不符；[路由无入边] = 注册但 0 UI 入口；[深链歧义] = sparkle:// 映射缺陷；[确认未变] = 矩阵已知债务复核无变化。

## 新发现（10）

### DF-01 [矩阵滞后] F33 shop 最后 UI 入口已消失
- 矩阵 F33："可达但孤立: /shop 已注册 + streak_details_screen 1 处入口"。
- 代码：全库 `ShopRoutes.*` / `'/shop'` 引用仅剩挂载点 routes.dart:435；streak_details_screen 无 shop 导航。/shop 0 UI 入边（HIDDEN 不自动开放验收反而更符合，但矩阵"1 入口"已失真）。

### DF-02 [矩阵滞后] F41 visual_elements 双入口已被 U-07 摘除
- 矩阵 F41："profile+unified settings 2 处引用(可达)"。
- 代码：profile_screen.dart:709 与 unified_settings_screen.dart:822 均留有"U-07：visual-elements 入口摘除（视觉实验属 LABS）"注释；/visual-elements 0 UI 入边，仅 shared visual_element_provider 数据消费。

### DF-03 [矩阵滞后] F23 notification-analytics 路由已摘除
- 矩阵 F23："注册 /notification-center /notification-analytics"。
- 代码：notification_center_routes.dart:17 注释"NAV-IA P-3：/notification-analytics 已从路由表摘除（0 入边孤儿面…）"；屏与 provider 文件保留（KNOWN_CODE_DEBT_LEDGER）。现仅 /notification-center 注册且有 5 处字符串导航。

### DF-04 [矩阵滞后] F32 settings 四能力面挂载方式与矩阵不符
- 矩阵 F32："/settings/transparency 字符串导航 1；4 屏(transparency/openclaw/data-usage/accessibility)经 UserRoutes 与 profile/settings 挂载"。
- 代码：`/settings/transparency` 全库 0 命中（transparency 改为 unified_settings_screen.dart:516 起内联 transparencyLevelProvider）；accessibility 经 MaterialPageRoute（unified_settings_screen.dart:693）非 UserRoutes；settings feature 自带 OpenclawSettingsScreen 0 外部消费者（孤儿屏）；/profile/openclaw-settings 路由实际构建 OpenClawHubScreen（openclaw feature）而非 settings 屏。

### DF-05 [路由无入边] F16 home 的 /notifications
- routes 注册（HomeRoutes.notifications，home_routes）但 0 UI 入边；通知卡实际 push `/notification-center`（home_notification_card.dart:65）。

### DF-06 [路由无入边] F07 community 四条子路由
- `/community/favorites`、`/community/groups/search`、`/community/users/search`、`/community/groups/:id/moderation`：屏仅被 community_routes.dart 实例化（路由定义自身），全库 0 UI 导航。矩阵 F07"21 条子路由 13 个外部文件引用"为整组口径，未覆盖此四条的孤儿化。

### DF-07 [路由无入边] F38 tools 的 /tools/:toolId
- 全库无 `/tools/${id}` 动态 push；工具经 tool_registry routeBuilder 直达原生功能路由（/focus、/errors、/learning/forecast 等）；实际唯一入口是精确路径 `/tools/library`（cognitive_tool_hub_card ×3、tool_host_screen:152）。参数路由仅深链/手工 URL 理论可达。

### DF-08 [深链歧义] F01 achievement milestone id-less 深链落错屏
- deep_link_service.dart:82-89：`sparkle://milestone` 无 id 时映射 `/achievements/milestone`；该精确路径未注册（仅 `/achievements/milestone/:milestoneId`），GoRouter 会匹配 `/achievements/:id`（id='milestone'）落入成就详情屏而非报 404——静默错屏。带 id 时正常达 milestone 庆祝屏（该路由 UI 0 入边、深链专用）。

### DF-09 [深链歧义-已勘误] F19/F14 sparkle://node id-less 静默 no-op
- 【R1-C1 勘误 2026-09-28：原述「落 404 兜底」不实】`sparkle://node` 无 id 有 null 守卫（deep_link_service.dart:97-98），resolveRoute 返回 null → 不发生导航，真实行为=静默 no-op。带 id 正常（knowledge_detail_screen）。降级为记录性发现（无错屏危害）。

### DF-10 [路由无入边] F09 documents 的 /documents
- `/documents` 与 `/library` 双路径同组注册（documents_routes.dart:7-8,12,21）；UI 仅用 `/library`（profile_screen.dart:674、unified_settings_screen.dart:831），/documents 0 入边。备播双面，建议矩阵注记或 B-01 裁决收敛。

## 确认未变（2）

### DF-11 [确认未变] F28 reflection /reflection/summary 孤儿（HIDDEN by design）
- 与矩阵一致：仅 routes.dart 挂载、0 外部引用、0 字符串导航。维持 HIDDEN 处置。

### DF-12 [确认未变] F43 journey HybridJourneySheet 全仓 0 外部调用
- 与矩阵/V3-FIX-535 一致：J-06 移动面仍无生产入口；J-04 FirstActionCard 嵌入 dashboard 正常（行号与矩阵锚点一致）。

## 深链覆盖小结

deep_link_service.dart `_routeMapping` 10 类型：8 类解析到已注册路由（achievement/task/plan/insights/capsule/prism/openclaw/openclaw-settings）；2 类有 id-less 歧义（DF-08、DF-09）。`universal_share_service.dart:62-68` 生成的 7 种分享深链全部落在上述映射内，闭合。
