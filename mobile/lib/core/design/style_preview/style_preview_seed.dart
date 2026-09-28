/// V4-F05 · 可替换设计 Preview 的确定性数据 seed 与状态流定义。
///
/// **PROPOSED_NOT_APPROVED**（状态源：`v4/02_design/TOKENS.proposal.json`
/// `status`；权限源：`v4/README_START_HERE.md`）。本文件只服务
/// `style_preview_page.dart` 的 preview 通道：数据全部为确定性 seed
/// （固定日期/固定文本/固定数值），不订阅任何事件流、不打任何网络——
/// F03 二审 CH-4 守门口径：事件只经认证通道，preview 面消费冻结 seed，
/// 不新增投递路径。
///
/// 「同一状态流」：四步封闭流（[StylePreviewFlowStep]），文案一律取自
/// F03 冻结表 [kExperienceCopyTable]（键集封闭，不拼自由文本），状态
/// 视觉一律经 F02 [PixelStateBadge] 族（success 单载体）。五个 preview
/// 面共享同一控制器推进，切 profile 只换主题不换流。
library;

import 'package:flutter/material.dart';

import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/experience/experience_feedback_adapter.dart';

/// 数据 seed 版本（进 run_manifest.json；截图证据必须同 seed）。
const String kStylePreviewSeedVersion = 'seed-2026-09-28-v1';

/// 一次状态流的步骤（封闭枚举；语义全部落在 F03 冻结表既有键上）。
enum StylePreviewFlowStep {
  /// 运行进行中：`state.syncing` →「同步中」（中性，无成功视觉）。
  runActive,

  /// 任务回执：`task.committed` →「任务已更新」（task ∈ 成功面孔封闭集，
  /// 唯一允许 success 徽章的步骤）。
  committed,

  /// 记忆保存：`memory.saved` →「记忆已保存」（高亮 + 可选轻触，
  /// **永不**成功面孔——F03 验收 2 的分层路由）。
  memorySaved,

  /// 版本冲突：`err.version_conflict` →「你的设置已更新，需要重新生成」
  /// （失败族徽章 + 警示触语义，无庆祝）。
  versionConflict,
}

/// 步骤的呈现投影（视觉/文案路由结果；与 F03 [ExperienceFeedbackOutcome]
/// 同口径的只读投影，preview 面不重复实现路由逻辑，只消费冻结结论）。
class StylePreviewFlowFrame {
  const StylePreviewFlowFrame({
    required this.step,
    required this.copy,
    this.visualState,
    this.isHighlight = false,
  });

  /// 按封闭映射组装（success 仅 committed；memory 仅高亮无徽章）。
  factory StylePreviewFlowFrame.of(StylePreviewFlowStep step) {
    switch (step) {
      case StylePreviewFlowStep.runActive:
        return StylePreviewFlowFrame(
          step: step,
          copy: kExperienceCopyTable['state.syncing'] ?? '',
        );
      case StylePreviewFlowStep.committed:
        return StylePreviewFlowFrame(
          step: step,
          copy: kExperienceCopyTable['task.committed'] ?? '',
          visualState: PixelRunState.success,
        );
      case StylePreviewFlowStep.memorySaved:
        return StylePreviewFlowFrame(
          step: step,
          copy: kExperienceCopyTable['memory.saved'] ?? '',
          isHighlight: true,
        );
      case StylePreviewFlowStep.versionConflict:
        return StylePreviewFlowFrame(
          step: step,
          copy: kExperienceCopyTable['err.version_conflict'] ?? '',
          visualState: PixelRunState.conflict,
        );
    }
  }

  final StylePreviewFlowStep step;

  /// F03 冻结表文案（逐字，不改写）。
  final String copy;

  /// 状态徽章（null = 无徽章；success 经 [PixelStateBadge] 内部路由到
  /// [PixelSuccessBadge] 唯一庆祝载体）。
  final PixelRunState? visualState;

  /// memory.saved 的高亮呈现（非成功面孔）。
  final bool isHighlight;

  /// 是否庆祝（F03 口径：success 徽章即庆祝；高亮不算）。
  bool get celebrates => visualState == PixelRunState.success;
}

/// 封闭流的固定顺序（重放 = 从头推进）。
const List<StylePreviewFlowStep> kStylePreviewFlowSteps = <StylePreviewFlowStep>[
  StylePreviewFlowStep.runActive,
  StylePreviewFlowStep.committed,
  StylePreviewFlowStep.memorySaved,
  StylePreviewFlowStep.versionConflict,
];

/// ---------------------------------------------------------------------------
/// 五面 seed（全部常量；改动即 seed 版本变更，须重出全部截图）。
/// ---------------------------------------------------------------------------

/// 首页面 · 真实 [TodayCockpitCard] 的 VM seed（按流步派生）。
/// 字段构造规则见 today_cockpit_provider.dart 的 lineage 表；preview 只
/// 钉展示值，不接派生 provider（离线合同）。
const bool kSeedCockpitHasGoal = true;
const String kSeedGoalTitle = '线性代数期中冲刺';
const String kSeedPlanName = '三周特征值专项';
const int kSeedTasksTotal = 6;
const int kSeedTasksCommitted = 4;

/// 卡住 sheet 面 · 真实 [TaskStuckCard] 的 `Map<String, dynamic>` seed
/// （该组件的真实入参形态：intervention 载荷）。
const Map<String, dynamic> kSeedStuckCardData = <String, dynamic>{
  'intervention_id': 'seed-intervention-001',
  'message': '你在「特征向量」这一步已经停了 12 分钟，要换个拆法吗？',
  'observed_pattern': '连续 3 次在同一小节停留超过 10 分钟',
  'task_titles': ['例 2：广义特征向量', '习题 3.4 第 5 题'],
};

/// 记忆面 · 真实 [MemoryEvidenceBadge]/[EvidenceQuickPeek] seed。
const MemoryFaceSeed kSeedMemory = MemoryFaceSeed(
  evidenceCount: 3,
  summaries: <String>[
    '经验 #12：晚间 21-23 点专注完成率最高（近 7 天 5/7）',
    '经验 #31：把证明题拆成 25 分钟小段后中途放弃率下降',
    '来源：本周学习会话 3 次纠正记录（可追溯）',
  ],
);

/// 长回答面 · 真实 [SparkleMarkdown] seed（长回答正文，含标题/列表/引用/
/// 代码四种真实渲染路径）。
const String kSeedLongAnswerFull = r'''
先把「重根」这件事拆开，不急着算：

## 一、为什么 λ=3 是重根
特征多项式 $\\det(A-\\lambda I)=(2-\\lambda)(3-\\lambda)^2$，λ=3 出现两次，
所以几何重数 ≤ 代数重数 2。**关键结论**：特征向量不够用时，要补广义特征向量。

## 二、三步求法
1. 解 $(A-3I)x=0$，得到第一组特征向量 $v_1$；
2. 解 $(A-3I)x=v_1$，得到广义特征向量 $v_2$；
3. 若还差，继续解 $(A-3I)x=v_2$（链式）。

> 注意：第 2 步可能无解，说明几何重数已经到顶，直接停。

## 三、本题答案
- λ=2：$x=t(1,0,0)^\\top$
- λ=3：$x=t(0,1,0)^\\top$ 与 $x=t(0,1,1)^\\top$ 组成链

```text
校验：A v2 = v1 + 3 v2 ✓
若尔当标准形 J = diag(2, J2(3))
```

记不住就记一句：**重根不缺向量，缺的是"链"。**
''';

/// 长回答进行中的部分文本（runActive 步：截断 + 同步中，不伪装完成态）。
const String kSeedLongAnswerPartial = r'''
先把「重根」这件事拆开，不急着算：

## 一、为什么 λ=3 是重根
特征多项式 $\\det(A-\\lambda I)=(2-\\lambda)(3-\\lambda)^2$，λ=3 出现两次''';

/// 星图面 · 真实 [GalaxyNodePreviewCard] seed（committed 步掌握度抬升）。
const GalaxyFaceSeed kSeedGalaxy = GalaxyFaceSeed(
  nodeName: '特征值与特征向量',
  masteryBase: 45,
  masteryCommitted: 82,
  reviewUrgency: 0.88,
  reviewReason: '近 6 天未更新掌握度，且处于遗忘曲线高衰减区',
);

@immutable
class MemoryFaceSeed {
  const MemoryFaceSeed({
    required this.evidenceCount,
    required this.summaries,
  });

  final int evidenceCount;
  final List<String> summaries;
}

@immutable
class GalaxyFaceSeed {
  const GalaxyFaceSeed({
    required this.nodeName,
    required this.masteryBase,
    required this.masteryCommitted,
    required this.reviewUrgency,
    required this.reviewReason,
  });

  final String nodeName;
  final int masteryBase;
  final int masteryCommitted;
  final double reviewUrgency;
  final String reviewReason;
}
