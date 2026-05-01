# Reviewer B — E14: Calculator→学习上下文→AI感知
Timestamp: 2026-04-26T14:50:00+08:00
Chain Index: 28

## Chain Flow Summary
计算器是一个纯客户端 Flutter widget，使用 `math_expressions` 包本地解析和求值。支持括号、ANS 回填、最近 6 条历史。后端完全没有感知——`behavior_signal_collector`、`context_manager`、`tool_history_service` 均不记录计算器使用。Aurora 不知道用户用了计算器。

## Critical Issues 🔴

**1. 计算器使用完全不可见——后端零感知**
- **File**: `mobile/lib/features/tools/presentation/widgets/calculator_tool.dart`（全文 357 行）
- **Expected**: 用户使用计算器时，行为被记录、Aurora 可感知、可能影响任务难度推荐
- **Actual**: 计算器是纯本地 widget，无任何后端调用——
  - 无 API 调用：整个文件唯一 import 是 `flutter/services.dart`（仅用于剪贴板复制），无 `dio`、无 `repository`、无 backend provider
  - 历史不持久化：`_history` 是 `List<String>` 内存列表，最多保留 6 条（line 31, 74-77），退出页面即丢失
  - `backend/app/services/behavior_signal_collector.py` 无任何 calculator/tool_use 相关代码（grep 零匹配）
  - `backend/app/core/context_manager.py` 无任何 calculator/tool_history 相关代码（grep 零匹配）
  - `backend/app/services/tool_history_service.py` 有 `record_tool_execution()` 方法，但计算器从未调用
- **Evidence**: grep `api|http|dio|repository` 在 calculator_tool.dart 仅匹配 `import 'package:flutter/services.dart'`（系统 Clipboard，非 HTTP）
- **Impact**: Aurora 对"用户在什么任务上用了计算器"完全无知。如果用户在数学题上频繁用计算器，AI 教练无法据此判断是计算薄弱还是概念薄弱。E14 链路描述的三个问题（计算历史保存？Aurora感知？难度推荐？）全部为 NO

## Major Issues 🟡

None beyond the critical issue above.

## Minor Issues 🟢

**2. 计算器历史仅 6 条且不持久**
- **File**: `mobile/lib/features/tools/presentation/widgets/calculator_tool.dart:74-77`
- **Expected**: 计算历史跨会话保留
- **Actual**: `_history.insert(0, ...)` 后 `if (_history.length > 6) _history.removeLast()`，纯内存存储
- **Impact**: 低——辅助功能，不持久化影响有限

## Working Well ✅

- **工具注册完整**: 计算器在 `ToolRegistry` 正确注册，支持 `taskQuickPanel` 和三种 launch context（`tool_registry.dart:118-134`）
- **UI 质量高**: 表达式显示、ANS 回填、复制结果、键盘布局自适应宽度
- **ToolShell 集成**: 使用统一 `ToolShell` 包装，与其他工具一致
- **后端 tool_history 基础设施已存在**: `ToolHistoryService.record_tool_execution()` + EventBus 发布 `tool_history_recorded` + 成功率视图——接线点已就绪，但无调用方

## Files Examined
- `mobile/lib/features/tools/presentation/widgets/calculator_tool.dart`（全文 357 行）
- `mobile/lib/features/tools/tool_registry.dart`（全文 380 行）
- `backend/app/services/tool_history_service.py`（record_tool_execution 方法）
- `backend/app/services/behavior_signal_collector.py`（grep calculator/tool_use — 零结果）
- `backend/app/core/context_manager.py`（grep calculator/tool_history — 零结果）

## Confidence: High — 所有关键 finding 通过直接读取源码和精确 grep 验证。计算器从移动端到后端完全无数据流通。
