# Phase 1: 执行体验原生化 — "让OpenClaw说Sparkle的语言"

> **交给Coding Agent执行的完整指令**
> **预计改动**: 3个新文件, 4个修改文件 (全部Flutter)
> **依赖**: 无外部依赖, 基于现有代码

---

## 背景

当前执行UI位于 `mobile/lib/features/task/presentation/screens/task_execution_screen.dart` 的 `_BottomControls` widget (lines 1338-1923)。现状是纯色圆点+文字标签+扁平按钮, 与Sparkle其他模块(聊天AI状态指示器、confetti庆祝、感官反馈系统)的精致体验严重脱节。

本阶段目标: 将执行UI的视觉和交互质量提升到与聊天模块同等水准, 使用Sparkle已有的设计系统组件。

---

## 任务 1.1: 创建执行状态指示器组件

**创建文件**: `mobile/lib/features/task/presentation/widgets/execution_status_indicator.dart`

### 设计规格

这是一个独立StatefulWidget, 接收 `ExecutionIntentStatus` 和可选的 `DateTime? dispatchedAt`, 渲染为一个带动画的状态指示器。

#### 构造函数
```dart
const ExecutionStatusIndicator({
  required ExecutionIntentStatus status,
  DateTime? dispatchedAt,
  double size = 48.0,
  Key? key,
})
```

#### 状态→视觉映射

| 状态 | 主色 | 图标 | 动画 |
|------|------|------|------|
| draft | DS.textTertiary | Icons.edit_note_rounded | 无(静态) |
| ready | DS.info | Icons.check_circle_outline_rounded | 无(静态) |
| dispatched | DS.info | Icons.send_rounded | SparkleAttentionPulse(active: true, glowColor: DS.info) |
| running | DS.semanticWarning | Icons.autorenew_rounded | 持续旋转动画(AnimationController repeat, 1200ms周期) + SparkleAttentionPulse |
| waitingApproval | DS.semanticWarning | Icons.pending_actions_rounded | SparkleAttentionPulse(active: true, glowColor: DS.semanticWarning, scaleRange: 0.024) — 更强烈的脉冲吸引注意 |
| succeeded | DS.semanticSuccess | Icons.check_circle_rounded | 静态, 首次进入时播放scale弹跳(1.0→1.15→1.0, 300ms, Curves.elasticOut) |
| partial | DS.semanticWarning | Icons.rule_rounded | 静态 |
| failed | DS.semanticError | Icons.error_outline_rounded | 静态, 首次进入时播放水平shake(-4→4→-2→2→0, 400ms) |
| canceled | DS.textTertiary | Icons.cancel_outlined | 静态 |
| timedOut | DS.semanticError | Icons.timer_off_rounded | 静态 |
| handedBack | DS.textSecondary | Icons.undo_rounded | 静态 |

#### 经过时间计时器

当 `dispatchedAt != null` 且状态为 dispatched/running/waitingApproval 时:
- 在图标下方显示已用时间, 格式 "Xs" 或 "X:XX"(超过60秒时)
- 使用 `Timer.periodic(Duration(seconds: 1))` 更新
- 字体: `TextStyle(fontSize: 11, fontFeatures: [FontFeature.tabularFigures()], color: 主色.withOpacity(0.8))`
- 终态时停止计时器, 显示最终耗时

#### 状态切换动画

用 `AnimatedSwitcher(duration: DS.normal, switchInCurve: Curves.easeOutCubic, switchOutCurve: Curves.easeInCubic)` 包裹整个图标区域。状态变化时旧图标淡出+缩小, 新图标淡入+放大。

#### 无障碍

- 用 `Semantics(label: '执行状态: ${status.statusLabel}')` 包裹
- 检查 `MediaQuery.of(context).disableAnimations` — 如果为true, 所有动画降级为简单opacity

#### 必要import
```dart
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
```

---

## 任务 1.2: 创建审批预览卡组件

**创建文件**: `mobile/lib/features/task/presentation/widgets/execution_approval_card.dart`

### 设计规格

当执行处于 `waitingApproval` 状态且有 `ExecutionRecordModel` 时, 替代当前的简单确认/拒绝按钮, 展示一个富交互审批卡片。

#### 构造函数
```dart
const ExecutionApprovalCard({
  required ExecutionRecordModel record,
  required ExecutionIntentModel intent,
  required VoidCallback onConfirm,
  required VoidCallback onReject,
  bool isLoading = false,
  Key? key,
})
```

#### 布局结构 (从上到下)

**1. 目标对比区** (intent.goal vs record.parsedOutput)
- 左侧小标签 "目标" + intent.goal 文本(最多2行, overflow ellipsis)
- 右侧小标签 "AI结果" + parsedOutput 的摘要(取前200字符)
- 两者之间用虚线箭头连接
- 容器: `Container` with `DS.surfaceSecondary` 背景, `BorderRadius.circular(12)`, padding `DS.spacing12`

**2. 执行指标区** (单行横排, 均匀分布)
- 耗时: `record.durationMs` 转为可读格式("2.3秒"/"1分12秒")
- 工具调用: `record.toolCallsCount` 次
- 信任等级: `record.trustLevel` 用对应颜色的小圆点+文字
- 字体: `DS.textSecondary` 色, fontSize 12

**3. 输出预览区** (可展开)
- 默认折叠, 显示 parsedOutput 前3个字段的key:value
- 点击 "查看详情" 展开完整 parsedOutput (用 `AnimatedCrossFade` 切换)
- 如果有 `record.artifacts` 且非空, 显示文件图标列表

**4. 操作区** (双按钮)
- 确认按钮: 填充色 `DS.semanticSuccess`, 文字 "采纳结果", 圆角20, 高度48
  - 点击时播放 `SensoryFeedbackEvent.confirm`
- 拒绝按钮: 描边色 `DS.semanticError`, 文字 "退回修改", 圆角20, 高度48
  - 点击时播放 `SensoryFeedbackEvent.warning`
- 两按钮等宽, 间距 `DS.spacing12`
- `isLoading` 为true时两按钮均disabled, 确认按钮内显示小CircularProgressIndicator

#### 整体容器
- 使用 `SparkleStaggerItem(index: 0)` 包裹实现入场动画
- 容器: `DS.surfacePrimary` 背景, `BorderRadius.circular(16)`, `DS.spacing16` padding
- 底部微阴影: `BoxShadow(color: DS.textPrimary.withOpacity(0.06), blurRadius: 8, offset: Offset(0, 2))`

#### 必要import
```dart
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_motion_primitives.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';
import 'package:sparkle/features/task/data/models/execution_record_model.dart';
```

---

## 任务 1.3: 创建模板选择卡片组件

**创建文件**: `mobile/lib/features/task/presentation/widgets/execution_template_card.dart`

### 设计规格

替代当前的 ChoiceChip 列表, 用更丰富的卡片展示模板。

#### 构造函数
```dart
const ExecutionTemplateCard({
  required ExecutionTemplateModel template,
  required bool isSelected,
  required VoidCallback onTap,
  Key? key,
})
```

#### 模板→视觉映射

| templateId | 图标 | 颜色标记 |
|------------|------|---------|
| web_research_brief | Icons.travel_explore_rounded | DS.info |
| document_digest | Icons.summarize_rounded | DS.semanticSuccess |
| shell_diagnostics | Icons.terminal_rounded | DS.semanticWarning |
| browser_form_prepare | Icons.edit_document | DS.brandPrimary |
| cross_device_capture | Icons.devices_rounded | DS.brandSecondary |
| (其他/未知) | Icons.smart_toy_rounded | DS.textSecondary |

#### 布局

- 横向卡片, 高度72
- 左侧: 40x40圆形图标容器(背景色为颜色标记.withOpacity(0.12), 图标色为颜色标记)
- 中间: 上方 template.name (fontSize 14, fontWeight 500), 下方 template.description (fontSize 12, DS.textSecondary, maxLines 1)
- 右侧: 匹配度环形指示器(如果 matchScore > 0)
  - 用 `SizedBox(width: 36, height: 36)` + `CircularProgressIndicator(value: matchScore, strokeWidth: 3, color: 颜色标记)`
  - 中间显示 "${(matchScore * 100).round()}%"(fontSize 10)
- 右下角: 模式标签 template.modeLabel (fontSize 10, 对应颜色背景pill)

#### 选中态

- 未选中: `DS.surfaceSecondary` 背景, 无边框
- 选中: `DS.surfacePrimary` 背景, 2px border色为颜色标记, 轻微scale(1.02)
- 切换时 `AnimatedContainer(duration: DS.quick)` 平滑过渡
- 点击时播放 `SensoryFeedbackEvent.selection`

#### 空状态

当模板列表为空时, 组件不渲染(由父级处理空状态文案)。

---

## 任务 1.4: 重构 _BottomControls 集成新组件

**修改文件**: `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`

### 精确修改指令

#### 1. 添加import (文件顶部)

在现有import区域末尾添加:
```dart
import 'package:sparkle/features/task/presentation/widgets/execution_status_indicator.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_approval_card.dart';
import 'package:sparkle/features/task/presentation/widgets/execution_template_card.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';
```

#### 2. 替换模板选择区域 (约lines 1709-1770)

找到当前使用 ChoiceChip/Wrap 渲染模板的代码块, 替换为:
```dart
// 模板选择区域
if (templates.isNotEmpty && latestExecution == null) ...[
  Padding(
    padding: const EdgeInsets.only(bottom: DS.spacing8),
    child: Text(
      '选择执行模板',
      style: TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w500,
        color: DS.textSecondary,
      ),
    ),
  ),
  ...templates.asMap().entries.map((entry) {
    final idx = entry.key;
    final tpl = entry.value;
    return Padding(
      padding: EdgeInsets.only(bottom: idx < templates.length - 1 ? DS.spacing8 : 0),
      child: SparkleStaggerItem(
        index: idx,
        child: ExecutionTemplateCard(
          template: tpl,
          isSelected: selectedTemplateId == tpl.templateId,
          onTap: () => ref.read(taskListProvider.notifier).selectExecutionTemplate(taskId, tpl.templateId),
        ),
      ),
    );
  }),
  const SizedBox(height: DS.spacing12),
],
```

#### 3. 替换执行状态显示区域 (约lines 1771-1857)

找到当前用 Card/Row 显示状态圆点+标题+副标题的代码块, 替换为:
```dart
// 执行状态区域
if (latestExecution != null) ...[
  SparkleStaggerItem(
    index: 0,
    child: Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          ExecutionStatusIndicator(
            status: latestExecution.status,
            dispatchedAt: latestExecution.dispatchedAt,
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  latestExecution.status.statusLabel,
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: DS.textPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  _executionStatusSubtitle(latestExecution, record),
                  style: TextStyle(
                    fontSize: 13,
                    color: DS.textSecondary,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  ),
  const SizedBox(height: DS.spacing12),
],
```

#### 4. 替换确认/拒绝按钮区域 (约lines 1858-1888)

找到当前的确认/拒绝按钮代码, 替换为:
```dart
// 审批区域
if (latestExecution != null && latestExecution.isWaitingApproval && record != null)
  ExecutionApprovalCard(
    record: record,
    intent: latestExecution,
    onConfirm: () => _confirmAiResult(ref, taskId),
    onReject: () => _rejectAiResult(ref, taskId),
    isLoading: isDecisionLoading,
  ),
```

#### 5. 增强handoff按钮 (约lines 1889-1900)

替换现有的handoff按钮为带感官反馈的版本:
```dart
if (canHandoff)
  SizedBox(
    width: double.infinity,
    height: 48,
    child: FilledButton.icon(
      onPressed: isHandoffLoading ? null : () {
        SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
        _handoffTask(ref, taskId);
      },
      icon: isHandoffLoading
          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
          : const Icon(Icons.smart_toy_rounded, size: 20),
      label: Text(_handoffButtonText(latestExecution, selectedTemplateId, templates)),
      style: FilledButton.styleFrom(
        backgroundColor: DS.brandPrimary,
        foregroundColor: DS.onBrandPrimary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
    ),
  ),
```

#### 6. 添加执行成功confetti

在 `_BottomControls` 的build方法的最外层, 在返回的Column外面包裹一层Stack, 加入confetti:

```dart
return Stack(
  children: [
    Column(
      // ... 现有内容
    ),
    if (latestExecution?.status == ExecutionIntentStatus.succeeded)
      Positioned.fill(
        child: IgnorePointer(
          child: SparkleConfetti(
            play: true,
            intensity: SparkleCelebrationIntensity.medium,
            enableSensory: true,
          ),
        ),
      ),
  ],
);
```

注意: confetti只在状态首次变为succeeded时播放一次。需要在StatefulWidget中用一个 `_hasPlayedConfetti` bool 控制, 或者利用SparkleConfetti的onComplete回调。由于_BottomControls当前是ConsumerWidget(无状态), 可以改为ConsumerStatefulWidget, 添加 `_celebrationPlayed` flag, 在didUpdateWidget中检测状态变化。

#### 7. 删除不再需要的辅助方法

`_executionStatusColor()` (lines 1523-1546) 和 `_executionStatusIcon()` (lines 1548-1571) 可以删除, 因为状态视觉映射已经移入 `ExecutionStatusIndicator`。

保留 `_executionStatusTitle()`, `_executionStatusSubtitle()`, `_executionOutputPreview()`, `_executionMetaPreview()`, `_handoffButtonText()` — 这些仍在使用。

---

## 任务 1.5: 感官反馈绑定到执行生命周期

**修改文件**: `mobile/lib/features/task/presentation/providers/task_provider.dart`

### 精确修改指令

在以下方法中添加感官反馈:

#### handoffTaskToAi() (约line 543)

在成功发起handoff后(约line 575, intent存入state之后):
```dart
SensoryFeedbackService.emit(SensoryFeedbackEvent.messageSend);
```

#### _decideExecutionResult() — confirm路径 (约line 728)

在confirm成功后(result返回后):
```dart
SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
```

#### _decideExecutionResult() — reject路径

在reject成功后:
```dart
SensoryFeedbackService.emit(SensoryFeedbackEvent.warning);
```

#### loadTaskExecutionState() (约line 475)

在检测到状态从非终态变为终态时(需要与旧状态比较):
```dart
final oldExecution = state.taskExecutions[taskId];
// ... 加载新状态后
final newExecution = state.taskExecutions[taskId];
if (oldExecution != null && newExecution != null &&
    !oldExecution.isTerminal && newExecution.isTerminal) {
  if (newExecution.status == ExecutionIntentStatus.succeeded) {
    SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
  } else if (newExecution.status == ExecutionIntentStatus.failed ||
             newExecution.status == ExecutionIntentStatus.timedOut) {
    SensoryFeedbackService.emit(SensoryFeedbackEvent.error);
  }
}
```

在检测到状态变为 waitingApproval 时:
```dart
if (oldExecution != null && newExecution != null &&
    oldExecution.status != ExecutionIntentStatus.waitingApproval &&
    newExecution.status == ExecutionIntentStatus.waitingApproval) {
  SensoryFeedbackService.emit(SensoryFeedbackEvent.warning);
}
```

需要在文件顶部添加import:
```dart
import 'package:sparkle/core/services/sensory_feedback_service.dart';
```

---

## 任务 1.6: 拒绝理由收集

**修改文件**: `mobile/lib/features/task/presentation/screens/task_execution_screen.dart`

### 精确修改指令

修改 `_rejectAiResult` 方法(约line 1392), 在调用provider的reject之前弹出底部sheet收集理由:

```dart
void _rejectAiResult(WidgetRef ref, String taskId) async {
  final reason = await showModalBottomSheet<String>(
    context: context,  // 注意: 需要通过参数传入context, 或者改为在StatefulWidget中调用
    backgroundColor: DS.surfacePrimary,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => _RejectReasonSheet(),
  );
  // reason为null表示用户取消了sheet
  if (reason != null) {
    ref.read(taskListProvider.notifier).rejectTaskExecutionResult(
      taskId,
      reason: reason.isEmpty ? null : reason,
    );
  }
}
```

创建 `_RejectReasonSheet` 作为同文件的私有widget:
```dart
class _RejectReasonSheet extends StatefulWidget {
  @override
  State<_RejectReasonSheet> createState() => _RejectReasonSheetState();
}

class _RejectReasonSheetState extends State<_RejectReasonSheet> {
  String? _selectedPreset;
  final _customController = TextEditingController();

  static const _presets = [
    '结果不够准确',
    '信息不完整',
    '有安全顾虑',
    '我想自己完成',
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: DS.spacing16,
        right: DS.spacing16,
        top: DS.spacing16,
        bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 36, height: 4,
              decoration: BoxDecoration(
                color: DS.textTertiary.withOpacity(0.3),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Text('退回原因', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: DS.textPrimary)),
          const SizedBox(height: DS.spacing4),
          Text('帮助AI下次做得更好', style: TextStyle(fontSize: 13, color: DS.textSecondary)),
          const SizedBox(height: DS.spacing16),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: _presets.map((p) => ChoiceChip(
              label: Text(p),
              selected: _selectedPreset == p,
              onSelected: (selected) => setState(() {
                _selectedPreset = selected ? p : null;
              }),
              selectedColor: DS.brandPrimary.withOpacity(0.15),
              labelStyle: TextStyle(
                color: _selectedPreset == p ? DS.brandPrimary : DS.textSecondary,
                fontSize: 13,
              ),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            )).toList(),
          ),
          const SizedBox(height: DS.spacing12),
          TextField(
            controller: _customController,
            decoration: InputDecoration(
              hintText: '补充说明（可选）',
              hintStyle: TextStyle(color: DS.textTertiary, fontSize: 13),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              contentPadding: const EdgeInsets.symmetric(horizontal: DS.spacing12, vertical: DS.spacing10),
            ),
            maxLines: 2,
            style: TextStyle(fontSize: 14, color: DS.textPrimary),
          ),
          const SizedBox(height: DS.spacing16),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: FilledButton(
              onPressed: () {
                final reason = [
                  if (_selectedPreset != null) _selectedPreset!,
                  if (_customController.text.trim().isNotEmpty) _customController.text.trim(),
                ].join(': ');
                Navigator.pop(context, reason);
              },
              style: FilledButton.styleFrom(
                backgroundColor: DS.semanticError.withOpacity(0.9),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              ),
              child: const Text('确认退回'),
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _customController.dispose();
    super.dispose();
  }
}
```

---

## 验收标准

运行以下命令确认无编译错误:
```bash
cd mobile && flutter analyze --no-fatal-infos
```

### 视觉验收 (人工)

1. [ ] 执行状态指示器: dispatched时蓝色脉冲, running时橙色旋转, waitingApproval时金色强脉冲, succeeded时绿色check+confetti
2. [ ] 计时器: dispatched后开始计时, 终态停止, 数字使用tabular figures不跳动
3. [ ] 模板卡片: 图标+名称+匹配度环形指示器, 选中态有边框高亮
4. [ ] 审批卡片: 目标对比+指标行+输出预览+确认/拒绝双按钮
5. [ ] 拒绝理由: 底部sheet弹出, 4个预设chip+自由文本
6. [ ] 感官反馈: handoff播放confirm音效, 成功播放success+confetti, 失败播放error, waitingApproval播放warning
7. [ ] 动画: 所有状态切换平滑过渡, 无突变闪烁

### 功能验收

1. [ ] handoff流程正常: 选模板→点击按钮→状态更新→轮询→终态
2. [ ] 审批流程正常: waitingApproval→显示审批卡→确认/拒绝→状态更新
3. [ ] 拒绝理由正确传递到provider的rejectTaskExecutionResult(reason:)
4. [ ] confetti只播放一次(不因重建widget重复播放)
5. [ ] 终态后轮询停止(现有逻辑不变)
