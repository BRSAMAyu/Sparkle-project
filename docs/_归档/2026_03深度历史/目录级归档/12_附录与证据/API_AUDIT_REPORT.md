# 前后端 API 衔接审查报告

**审查日期**: 2026-03-17
**审查范围**: Flutter 前端与 Python/Go 后端 API 衔接

---

## 1. 已修复的问题

### 1.1 AI 聊天流超时问题 (严重)
- **问题描述**: AI 聊天时出现卡住，一直显示"正在生成回复"，导致无法输入新消息
- **根本原因**: Flutter 的 `await for` 流处理会无限期等待，如果后端没有发送完成信号，`isSending` 状态永远不会重置
- **修复方案**: 添加 120 秒流超时保护机制
- **修改文件**:
  - `mobile/lib/features/chat/presentation/providers/chat_provider.dart`
  - `mobile/lib/core/utils/error_messages.dart`

### 1.2 社群分享类型不匹配 (严重)
- **问题描述**: 分享计划和任务到社群时出现错误
- **根本原因**: Flutter 的 `ShareableContentType.stringValue` 与后端 API 期望的 `resource_type` 值不匹配
- **修复内容**:
  - `knowledgeNode` → `'knowledge_node'`
  - `capsule` → `'curiosity_capsule'`
  - `cognitivePrism` → `'cognitive_prism_pattern'`
- **修改文件**:
  - `mobile/lib/core/services/universal_share_service.dart`
  - `mobile/lib/core/design/widgets/universal_share_bottom_sheet.dart`
  - `mobile/lib/l10n/app_zh.arb`
  - `mobile/lib/l10n/app_en.arb`

### 1.3 API 端点缺失
- **问题描述**: 缺少 `/chat/confirm` 端点定义
- **修复**: 添加 `chatConfirm` 端点到 `api_endpoints.dart`
- **修改文件**: `mobile/lib/core/network/api_endpoints.dart`

### 1.4 Plan 模型字段缺失 (严重)
- **问题描述**: Flutter 的 PlanModel 缺少后端定义的关键字段
- **修复内容**:
  - 添加 `PlanStage` 枚举 (sprint, daily, review, paused)
  - 添加 `PlanPriority` 枚举 (critical, high, normal, low)
  - 在 `PlanModel` 中添加 `planStage`, `priority`, `isPrimary` 字段
  - 在 `PlanCreate` 中添加 `priority` 字段
  - 在 `PlanUpdate` 中添加 `priority`, `planStage` 字段
  - 在 `PlanProgress` 中添加 `totalMinutesSpent`, `estimatedRemainingHours` 字段
- **修改文件**: `mobile/lib/features/plan/data/models/plan_model.dart`

### 1.5 聊天会话历史 API 端点缺失 (严重)
- **问题描述**: 后端缺少 Flutter 端调用的聊天会话列表和历史消息端点
- **修复内容**:
  - 在后端添加 `GET /chat/sessions` 端点获取会话列表
  - 在后端添加 `GET /chat/history/{session_id}` 端点获取历史消息
  - 在 Flutter 端添加 `chatHistory` 端点定义
  - 修复 `getConversationHistory` 方法的响应解析逻辑
- **修改文件**:
  - `backend/app/api/v1/chat.py`
  - `mobile/lib/core/network/api_endpoints.dart`
  - `mobile/lib/features/chat/data/repositories/chat_repository.dart`

### 1.6 Riverpod Provider 初始化顺序问题 (严重)
- **问题描述**: `unified_calendar_provider.dart` 中 Provider 在初始化期间修改其他 Provider，导致运行时错误
- **错误信息**: `Providers are not allowed to modify other providers during their initialization`
- **根本原因**: `todayAggregateProvider` 和 `currentMonthAggregateProvider` 在初始化时直接调用 `ref.read(unifiedCalendarProvider.notifier).loadMonth()`
- **修复方案**: 实现延迟加载机制
  - 添加 `initializeIfNeeded()` 方法到 `UnifiedCalendarNotifier`
  - 使用 `Future.delayed` 延迟触发初始化
  - 在 Provider 中使用 `Future.microtask` 延迟调用
- **修改文件**:
  - `mobile/lib/features/calendar/presentation/providers/unified_calendar_provider.dart`

---

## 2. 已确认一致的部分

### 2.1 Task 模型
- `TaskStatus` 枚举: PENDING, IN_PROGRESS, COMPLETED, ABANDONED ✓
- `TaskType` 枚举: LEARNING, TRAINING, ERROR_FIX, REFLECTION, SOCIAL, PLANNING, OCR ✓
- 字段映射正确，使用 `@JsonKey` 注解处理命名转换

### 2.2 Achievement 模型
- `AchievementRarity` 枚举: common, rare, epic, legendary ✓
- `AchievementType` 枚举: milestone, streak, mastery, task_complete, hidden, social, contract, study_time, node_explore, sprint ✓
- 字段映射正确

### 2.3 User 模型
- 字段映射正确，使用 `@JsonKey(name: 'xxx_xxx')` 处理 snake_case 转换

### 2.4 Calendar Event 模型
- 颜色转换逻辑已正确处理 (int ↔ string hex)
- 字段映射正确

---

## 3. 建议后续关注的问题

### 3.1 Focus Session 状态枚举
- **位置**: `mobile/lib/features/focus/data/models/focus_session_model.dart`
- **问题**: `status` 字段使用 String 类型，建议定义枚举并添加 `@JsonValue` 注解
- **后端枚举**: COMPLETED, ABANDONED, INTERRUPTED

### 3.2 Visual Element 国际化字段
- **位置**: `mobile/lib/shared/entities/visual_element_model.dart`
- **问题**: 后端支持 `name_i18n`, `description_i18n` 多语言字段，Flutter 端未使用
- **建议**: 如需多语言支持，添加相应字段

### 3.3 枚举值大小写一致性
- **建议**: 统一使用 `@JsonValue` 注解明确指定序列化值，避免隐式转换

---

## 4. 最佳实践建议

### 4.1 字段命名
- Flutter 使用 camelCase
- 后端使用 snake_case
- 使用 `@JsonKey(name: 'snake_case')` 进行映射

### 4.2 枚举定义
```dart
enum ExampleEnum {
  @JsonValue('value_one')
  valueOne,
  @JsonValue('value_two')
  valueTwo,
}
```

### 4.3 可选字段
- 使用 `?` 标记可空类型
- 提供 `defaultValue` 或在构造函数中设置默认值

### 4.4 API 端点管理
- 集中在 `api_endpoints.dart` 中定义
- 使用静态方法生成动态路径
- 保持与后端路由文件同步

---

## 5. 审查方法

本次审查使用以下方法：

1. **枚举值对比**: 检查所有枚举的 `@JsonValue` 与后端枚举值是否一致
2. **字段映射**: 检查 `@JsonKey(name:)` 与后端字段名是否一致
3. **必填/可选**: 对比前后端字段的必填性
4. **端点匹配**: 对比 `api_endpoints.dart` 与后端路由定义

---

**审查人**: Claude Opus 4.6
**状态**: 已完成初步修复，建议持续监控
