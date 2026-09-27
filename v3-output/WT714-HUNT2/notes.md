# WT714-HUNT2 notes — 移动端诚实性/未兑现承诺专项猎缺（第二轮）

- Agent: wt714（node-b，猎缺双轮机制第一轮为本 worktree；主线仓库只读，本分支 `agent/node-b/wt714/hunt2`，base main@6f4d3233）
- 日期: 2026-09-25
- 范围: `mobile/lib`（1288 dart 文件）为主，后端仅作承诺-现实对照（只 grep 不修改）
- 猎场: ①空态/占位/骨架屏伪装 ②承诺-现实断裂 ③设置项无效面 ④按钮/入口死路 ⑤数字自述脱钩
- 铁律遵守: 只登记不修码；无 widget 测试产物（按「只动台账与 v3-output」约束全部以静态证据钉死）；未 push

## 1. 登记（存活发现）

### V3-FIX-421（P2）统一设置「透明模式/透明度等级」零消费死设置

- 猎场: ③+②双命中
- 问题: `unified_settings_screen.dart:1946-2003` 的「启用透明模式」开关副标承诺「显示状态与资源消耗概览」（app_zh.arb:134-135），开启后露出 basic/standard/advanced 等级下拉，写 `transparencyLevelProvider`（settings_provider.dart:910-972，本地 prefs 持久化 + 服务端 `user_settings.transparency_level` 双向同步）。但两级值全 app 零行为读者：`transparentModeProvider` 唯一读者是设置页自身 :515（仅控制等级下拉显隐），等级值 0-3 除 :516 规范化外无读取。真正的 chat 过程透明面走另一套无耦合的 `TransparencyPreferencesNotifier`（transparency_preferences.dart:130-232；消费者 chat_screen.dart:1387/3056、chat_bubble.dart:820、透明胶囊），唯一写面在 chat 设置页（chat_settings_screen.dart:165）。后端 `transparency_level` 仅存储回显（backend/app/models/user_settings.py:13、api/v1/user_settings.py），无 orchestration 消费。
- 复现: 登录态 → 统一设置 → 开「启用透明模式」→ 应用无任何新概览/视觉变化；下拉切 basic/standard/advanced → 零行为差异。
- 四重反证排查均过: lib+test 全 grep；存储键 `settings_transparent_mode`/`settings_transparency_level` 仅 settings_provider 触达；台账 `transparencyLevel/transparentMode/透明模式` 0 命中（非重复）。
- 处置建议: 最小修=撤下该设置卡（含 l10n 两键）；可选=改接真 TransparencyPreferences 作第二入口（需先裁单一事实源）；服务端存量字段去留随卡评估。

## 2. 撤下的高似真候选（防重复机制命中）

### 候选 C（撤）: chat 挂载 proposal 卡 unknown/conflict 态「刷新结果/再看一遍」零行为

- 自查发现 `action_card.dart:261-267` 发射 `action_proposal_review`/`action_proposal_refresh`，而 `chat_notifier_actions.dart:291-297` 只接 approve/reject/cancel 三 case，review/refresh 落 default debugPrint 静默丢弃；task 侧同卡（pending_proposal_section.dart:56-59）接线完好（invalidate 重取）——看似 FIX-378 残留新面。
- **撤下原因**: 台账 **V3-FIX-379②**（wt687 登记，OPEN）已原文在挂此问题（「chat 挂载 conflict 态『再看一遍』…/unknown 态『刷新结果』…仍落 handleWidgetAction default 静默分支」）。登记前 grep 台账 `action_proposal_review` 命中 329 行确认重复。不重复登记。

## 3. 未成立清单（排查过、证据不支持、不入账）

1. **GOV-015 数据使用面（data_usage_dashboard_screen.dart）「你的控制权」三条目无 handler**：「隐藏编年史条目/请求删除数据/导出你的数据」渲染为无 onTap 的 `_ControlTile`，文案承诺三个控制动作；但全仓（lib+test）对该 screen **0 引用、0 路由、0 实例化**——孤儿屏不可达，构不成用户可复现的受骗 UI 面。真控制入口在统一设置 `SettingsDataControlsCard`（settings_behavior_explanation.dart:202 起，export/delete/hide 全接线）。留档为死代码卫生项（207 行 + dataUsage* l10n 键面），宁缺毋滥不入账。
2. **status_awareness_bar.dart:136/149 加载/未激活态 onTap 空**: 信息条非按钮 affordance（无 ripple、无 chevron），用户预期弱。
3. **assistant_message_metadata_tray.dart:64/75 onTap 空**: 带 `enabled: false`，`ChatAccessoryPill onTap: enabled ? onTap : null`——禁用态传递，非死路。
4. **message_detail_view.dart:104 onTap 空**: 模态内容层屏障防误关（背景点击关闭），惯例正当。
5. **WeeklyGrowthNarrative 非 demo 回 placeholder（growth_narrative_repository.dart:50）**: dashboard 响应缺 `weekly_narrative` 字段时返回 placeholder——但 `isPlaceholder: true` 诚实标注，UI 按 `hasData == false` 走空态（learning_insights_overview_screen.dart:53、weekly_growth_narrative_card.dart:64/87 info 色），非伪装。
6. **专注离线保存承诺「稍后会自动重试同步」（focusOfflineSaved）**: `focus_statistics_provider.dart` sync() 在启动 + 连通性恢复双钩子真实兑现（getUnsyncedSessions→logFocusSession→markAsSynced），承诺成立。
7. **intent_prediction_provider 硬编码置信度（0.9-0.3）**: 仅内部排序用，UI（intent_prediction_bar/unified_omni_bar/multi_agent_bar）零处渲染 confidence，不构成数字自述。
8. **demo 门控卫生**: GrowthDashboard.placeholder / predictive mock（predictive_service）/ mock_community_repository / learning_path mock 全部 `DemoDataService.isDemoMode` 门控在位；社区 feed 断网回退走 ListReadCache 带「截至 X」时点标记（诚实）。
9. **无障碍设置 8 字段全有真消费**: fontScale/screenReaderOptimized/lowLoadMode→app.dart 根应用；highContrast/colorBlindFriendly→themeManager；reduceMotion→reduceMotion 消费面（FIX-384 族）；touchTargetSize→sparkle_button_v2 经 `minimumTouchTargetSize` getter（:573）；hapticFeedback→patch 内桥接 `SensoryFeedbackService.setHapticEnabled`（accessibility_provider.dart:264）；ttsEnabled→tts_service.dart:41。
10. **dashboard 错误态**: `DashboardState.error` 走 R5-F04 显式错误 UI（dashboard_screen.dart:1016-1085），失败自动重试 M6-08 指数退避真实接线（dashboard_provider.dart:690）；weather 'sunny' 仅背景装饰层。
11. **systemUpdateLevelProvider**: chat_provider.dart:384-392 真消费（silent/summary/detailed 过滤系统更新消息），非死设置。
12. **weeklyAgenda/learningPreferences（深度/好奇心）**: 服务端消费链在位（backend preference_consumption_service/scheduler_service/prompts 均读 schedule_preferences 与 depth_preference），非死设置。

## 4. 方法与覆盖

- grep 策略: Future.delayed 全量过筛（动画/防抖/反馈清理判真）；confidence/百分比硬编码池；`_mock|MockData|sampleData|dummy` 池（逐个核门控）；空 handler（`onTap/onPressed: () {}` perl 全扫 + `enabled:false` 甄别）；debugPrint-only handler 反查；settings 家族 provider 逐一反向 grep 消费（settings_provider 14 provider + accessibility 8 字段 + galaxy/memory/openclaw/smart_push）；承诺词扫描（加密/同步/备份/稍后重试/自动重试 l10n 池，抽验 retry 真实路径）；ledger 先扫（383-420 预占段 + 五态/门控/占位串已知项）。
- 未覆盖（如实声明）: 需真机/长时序才能定性的「加载态永不结束」面仅做了静态可达性核对；golden/视觉层不在本轮。

## 5. verify

```
python3 scripts/devtools/ledger_union_merge.py --verify v3/06_agent_fleet/DYNAMIC_ISSUES.md
verify：298 行 V3-FIX 行，裸管分布 {8: 298}，多数形态 8
verify 通过：零冲突标记残留，8 裸管形态合法（多数容差开），ID 无重号，状态枚举合法
```
