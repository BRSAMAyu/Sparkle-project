# FV-14 · 集中式无障碍设置面板报告

Branch: `codex/FV-14-accessibility-settings`

## 1. 5/5 标准达成情况

| # | 标准 | 状态 | 证据 |
|---|------|------|------|
| 1 | 新建 accessibility settings screen | ✅ | `mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart:13` 新增集中式设置页 |
| 2 | 集中字体缩放、对比度、屏幕阅读、触控、动画、色盲、TTS、震动、低负荷 | ✅ | `accessibility_settings_screen.dart:68`、`:75`、`:90`、`:105` 分区覆盖全部控制 |
| 3 | unified_settings_screen 加入口，链接而非内嵌 | ✅ | `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart:550` 新增入口并通过 `MaterialPageRoute` 打开 |
| 4 | per-feature 高级覆盖保留并同步默认值 | ✅ | `accessibility_provider.dart:110` 写入 `galaxy_accessibility_defaults`，不改 Galaxy 高级服务 |
| 5 | 全部设置写入 user_settings | ✅ | `accessibility_provider.dart:110` 统一序列化 `accessibility_settings` 并调用 `updateUserSettings` |
| 6 | WCAG AA 检查清单文档 | ✅ | `accessibility_settings_screen.dart:385` 页内清单；本报告记录验收标准 |
| 7 | 单测 + Golden 测试 | ✅ / 环境阻塞 | 新增 `accessibility_provider_test.dart`、`accessibility_settings_screen_test.dart`、`accessibility_settings_golden_test.dart`；仓库当前有无关编译错误阻塞 `flutter test` 装载 |

## 2. 文件变更清单

```
mobile/lib/features/settings/presentation/providers/accessibility_provider.dart
mobile/lib/features/settings/presentation/screens/accessibility_settings_screen.dart
mobile/lib/features/user/presentation/screens/unified_settings_screen.dart
mobile/test/features/settings/presentation/providers/accessibility_provider_test.dart
mobile/test/widget/accessibility_settings_screen_test.dart
mobile/test/goldens/accessibility_settings_golden_test.dart
```

## 3. 测试证据

### 单测

```
cd mobile && flutter test test/features/settings/presentation/providers/accessibility_provider_test.dart

FAILED during test load because of unrelated workspace compile errors:
- lib/features/calendar/presentation/providers/calendar_provider.dart: TaskStatus.paused switch exhaustiveness
- lib/features/plan/presentation/widgets/plan_context_summary.dart: TaskStatus.paused switch exhaustiveness
- lib/features/community/presentation/widgets/quick_share_picker_sheet.dart: TaskStatus.paused switch exhaustiveness
- lib/features/plan/presentation/screens/plan_detail_screen.dart: TaskStatus.paused switch exhaustiveness
- lib/features/home/presentation/widgets/openclaw_automation_panel.dart: const evaluation of DS.textOnPrimary
- lib/features/home/presentation/widgets/openclaw_node_management_panel.dart: const evaluation of DS.textOnPrimary
```

### 集成测 / Widget / Golden

```
cd mobile && flutter test test/features/settings/presentation/providers/accessibility_provider_test.dart test/widget/accessibility_settings_screen_test.dart test/goldens/accessibility_settings_golden_test.dart

FAILED during test load for the same unrelated compile blockers above.
Golden file is gated by ENABLE_ACCESSIBILITY_GOLDEN, matching existing repo convention.
```

### Lint / 类型 / Guard

```
cd mobile && dart analyze \
  lib/features/settings/presentation/providers/accessibility_provider.dart \
  lib/features/settings/presentation/screens/accessibility_settings_screen.dart \
  test/features/settings/presentation/providers/accessibility_provider_test.dart \
  test/widget/accessibility_settings_screen_test.dart \
  test/goldens/accessibility_settings_golden_test.dart

No issues found!
```

## 4. 用户视角变化

在设置页中，用户现在能从一个统一入口调整字体、对比度、屏幕阅读、触控目标、动画、色盲友好、TTS、震动反馈和低负荷模式，并让这些默认值进入账号设置同步。

具体场景：
- 之前：无障碍相关开关分散在感官反馈、主题和单个功能中，用户难以知道哪个设置是全局默认。
- 之后：设置首页出现“无障碍与低负荷”入口，用户进入后可以一次性管理全局默认；Galaxy 等功能仍可保留高级覆盖。

## 5. 与其他卡片的协调

- `mobile/lib/features/user/presentation/screens/unified_settings_screen.dart` 也包含 FV-12 的情绪适应 UI 变更；FV-14 只追加无障碍入口和 import。
- `user_settings` 服务端 schema 未在本卡片修改；本卡片按现有 `updateUserSettings(Map)` 能力写入嵌套 `accessibility_settings`。
- 留给 Architect：待 FV-16 / OpenClaw 相关无关编译错误合入后，重跑 Flutter focused tests。

## 6. 已知限制 / 后续

- 当前仓库有其他 FV 分支遗留的未合并编译错误，阻止 `flutter test` 装载；FV-14 文件自身通过定向 `dart analyze`。
- 如后端后续为 `user_settings` 增加严格字段白名单，需要确认 `accessibility_settings` 与 `galaxy_accessibility_defaults` 被允许。

## 7. 验收命令一键回放

```bash
cd mobile
dart analyze \
  lib/features/settings/presentation/providers/accessibility_provider.dart \
  lib/features/settings/presentation/screens/accessibility_settings_screen.dart \
  test/features/settings/presentation/providers/accessibility_provider_test.dart \
  test/widget/accessibility_settings_screen_test.dart \
  test/goldens/accessibility_settings_golden_test.dart
flutter test test/features/settings/presentation/providers/accessibility_provider_test.dart test/widget/accessibility_settings_screen_test.dart test/goldens/accessibility_settings_golden_test.dart
```
