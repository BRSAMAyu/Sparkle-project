# 中英文混排清理执行计划

> **创建**: 2026-04-28 | **状态**: 进行中
> **目标**: 全仓库中英文混排问题清理，确保两种语言的模式极其完善

---

## 概览

| 层 | 文件数 | 中文字符串数 | 优先级 |
|---|--------|-------------|--------|
| Flutter (`mobile/lib/`) | ~250 | ~12,000 (排除 l10n 文件) | P0 |
| Python (`backend/app/`) | ~250 | ~8,800 | P1 |
| Go (`backend/gateway/`) | ~16 | ~146 | P2 |

## 问题类型

### 类型 1：中文硬编码字符串（UI 层）
硬编码在 Dart 代码中的中文字符串，应使用 `context.l10n.xxx` 或 `S.xxx`
- Position: Flutter `.dart` 文件
- 模式: `'加载中...'`, `'暂无数据'`, `'确认删除？'`
- 示例: `mobile/lib/core/design/widgets/error_widget.dart` 中的 `S.errorDefaultTitle`

### 类型 2：中文注释（各层）
中英文混排的注释，应统一为英文
- Position: 全仓库 `.dart`, `.py`, `.go` 文件
- 模式: `/// 加载指示器类型`, `# 检查 user 状态`
- 示例: `mobile/lib/core/design/widgets/loading_indicator.dart`

### 类型 3：中文文档字符串（Python）
Python docstring 中的中文，应统一为英文
- Position: `backend/app/` 下 `.py` 文件
- 模式: `"""中文描述"""`

### 类型 4：中文日志/错误消息（Python/Go）
日志消息、错误响应中的中文，应统一为英文
- Position: `backend/app/`, `backend/gateway/`
- 模式: `logger.error("中文错误")`, `c.JSON(400, "中文")`

---

## 执行阶段

### Phase 1: Flutter 核心层（设计系统、通用组件、工具类）
**文件数**: ~50 | **并行度**: 3 agents

| Agent | 范围 | 文件 |
|-------|------|------|
| 1.1 | design/widgets + extensions + utils | loading_indicator, error_widget, charts, etc. |
| 1.2 | core/services | notification_service, bgm_service, etc. |
| 1.3 | core/network + core/constants | api_client, error_messages, etc. |

### Phase 2: Flutter Feature 层（聊天、主页、计划、任务）
**文件数**: ~80 | **并行度**: 3 agents

| Agent | 范围 |
|-------|------|
| 2.1 | chat features |
| 2.2 | home + plan + task features |
| 2.3 | auth + calendar + focus features |

### Phase 3: Flutter Feature 层（社群、成就、星图等）
**文件数**: ~80 | **并行度**: 3 agents

| Agent | 范围 |
|-------|------|
| 3.1 | community + galaxy features |
| 3.2 | achievement + insights + cognitive features |
| 3.3 | remaining features (tools, settings, etc.) |

### Phase 4: Python 后端
**文件数**: ~250 | **并行度**: 3 agents

### Phase 5: Go 网关
**文件数**: ~16 | **并行度**: 1 agent

### Phase 6: 注释清理 + 文档
全仓库统一检查

---

## 修复规范

### Dart 文件中文字符串替换

```
Before:  Text('加载中...')
After:   Text(context.l10n.commonLoading)

Before:  '暂无数据'
After:   S.noData  // in non-widget code
         context.l10n.noData  // in widget build
```

### 注释清理

```
Before:  /// 加载指示器类型
After:   /// Loading indicator types

Before:  // 检查 user 是否 active
After:   // Check if user is active
```

### l10n 键新增规则

When adding new l10n keys, BOTH `app_localizations_en.dart` AND `app_localizations_zh.dart` must be updated:

```dart
// In app_localizations.dart (abstract):
String get newKey;

// In app_localizations_en.dart:
@override
String get newKey => 'English Text';

// In app_localizations_zh.dart:
@override
String get newKey => '中文文本';
```

---

## 日志

### 2026-04-28: Phase 1 Start
- Created execution plan
- Started Phase 1.1: design/widgets + extensions + utils

### Phase 1 Results:
- Agent A (Design Widgets): ✅ DONE — 10 files cleaned
- Agent B (Services/Utils): ✅ DONE — 13 files cleaned
- Agent C (Shared Entities): ✅ DONE — 18 files cleaned

### 2026-04-28: Phase 1 Complete ✅
- 41 files fixed, 646 insertions / 613 deletions
- Commit: `07702f70` — `fix(i18n): Phase 1 — clean Chinese/English mixing in Flutter core layer`
- Dart analyze: 0 errors, 0 warnings ✅

### 2026-04-28: Phase 2 Start
- 3 agents launched for Flutter feature layer:
  - Agent 2A: Chat features (22 files)
  - Agent 2B: Home + Task features (25 files)
  - Agent 2C: Plan + Auth + Calendar + Focus features (24 files)
