# 国际化开发指南

## 添加新翻译

1. 在 `mobile/lib/l10n/app_zh.arb` 和 `app_en.arb` 中添加键
2. 运行 `flutter gen-l10n` 重新生成
3. Widget 中使用 `context.l10n.keyName`
4. 非 Widget 中使用 `S.of(context).keyName`

## 命名规范

- camelCase 格式
- 按功能前缀分组：`errorBook*`, `community*`, `auth*`, `knowledge*`, `translation*`, `memory*`, `seedLibrary*`, `plan*`, `tools*`, `taskMonitor*`
- 通用键使用 `common*` 前缀

## 翻译键类别

### 通用键 (common*)
- 按钮：commonConfirm, commonCancel, commonSave, commonDelete, commonRetry
- 状态：loadingFailed, noData, operationSuccess, operationFailed
- 对话框：confirmDeleteTitle, confirmDeleteMessage, featureInDevelopment

### 模块专用键

#### 错题本 (errorBook*)
- errorBookTitle: 错题档案
- errorBookTabAll: 全部
- errorBookTabNeedReview: 待复习

#### 社群 (community*)
- communityTitle: 星火社群
- communitySearch: 搜索用户/群组
- communityStatusOnline/Offline: 在线/离线

#### 知识 (knowledge*)
- knowledgeLoadFailed: 知识节点加载失败
- knowledgeGeneratePath: 生成学习路径
- knowledgeRelatedNodes: 相关节点

#### 翻译 (translation*)
- translationHistoryTitle: 翻译历史
- translationClearHistory: 清空历史
- translationOriginal/Translated: 原文/译文

#### 记忆 (memory*)
- memoryEvidenceChain: 证据链
- memoryVersionHistory: 版本历史
- memoryCorrectionActions: 纠错操作

#### 种子库 (seedLibrary*)
- seedLibraryTitle: 种子库
- seedLibraryCreate: 创建种子库
- seedLibraryContent: 内容

#### 计划 (plan*)
- planHistoryTitle: 历史计划
- planTypeSprint/Growth: 冲刺计划/成长计划

#### 工具 (tools*)
- toolsLibraryTitle: 工具库
- toolsCategoryInput/Study/Efficiency/Cognition: 工具分类

#### 任务监控 (taskMonitor*)
- taskMonitorTitle: 后台任务监控
- taskMonitorFilterAll/Running/Completed/Failed: 过滤器

## 占位符参数

使用 `{variable}` 语法，并在 ARB 中定义类型：

```json
"knowledgeDaysLater": "{days}天后",
"@knowledgeDaysLater": {
  "placeholders": {
    "days": {
      "type": "int"
    }
  }
}
```

## 提交前检查

1. 切换语言测试
2. 运行 `dart scripts/i18n_coverage_check.dart`
3. 确保覆盖率 ≥ 95%
4. 运行 `flutter analyze` 确保无编译错误

## 检测脚本

### 翻译覆盖率检查
```bash
dart scripts/i18n_coverage_check.dart
```

### 硬编码字符串检测
```bash
./scripts/check_hardcoded_strings.sh
```

## 常见模式

### 文本替换
```dart
// Before
Text('错题档案')

// After
Text(context.l10n.errorBookTitle)
```

### 对话框按钮
```dart
// Before
TextButton(
  child: Text('确定'),
  onPressed: () => Navigator.pop(context),
)

// After
TextButton(
  child: Text(context.l10n.commonConfirm),
  onPressed: () => Navigator.pop(context),
)
```

### 带参数的翻译
```dart
// Before
Text('${days}天后')

// After
Text(context.l10n.knowledgeDaysLater(days))
```

### 枚举转翻译
```dart
// 在枚举中添加方法
enum FilterType {
  all, running, completed;

  String label(BuildContext context) {
    switch (this) {
      case FilterType.all: return context.l10n.taskMonitorFilterAll;
      case FilterType.running: return context.l10n.taskMonitorFilterRunning;
      case FilterType.completed: return context.l10n.taskMonitorFilterCompleted;
    }
  }
}

// 使用
Text(filterType.label(context))
```

## 排除范围

以下文件保持中文硬编码，不做国际化：
- `demo_data_service.dart` 等演示数据文件
- 测试文件中的测试数据
- 仅用于调试的日志输出

## CI/CD 集成

建议在 PR 流程中添加检查：

```yaml
# .github/workflows/flutter.yml
- name: Check i18n coverage
  run: dart scripts/i18n_coverage_check.dart

- name: Check hardcoded strings
  run: |
    chmod +x scripts/check_hardcoded_strings.sh
    ./scripts/check_hardcoded_strings.sh
```

## 更新日志

- 2026-03-15: 完成Phase 1-3，覆盖error_book, community, task_monitor, plan, auth, tools, knowledge, seed_library, translation, memory模块
- 新增约150+翻译键
- 建立长期维护机制
