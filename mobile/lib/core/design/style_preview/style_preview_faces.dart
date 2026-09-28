/// V4-F05 · 五个 preview 面（首页 / 卡住 sheet / 记忆 / 长回答 / 星图）。
///
/// **面 = 真实表面组件 + 确定性 seed**（非重新绘制、非 HTML 参考图移植）：
/// 每面直接挂载对应产品面的真实 widget（import 自 features/ 只读依赖），
/// 数据来自 [style_preview_seed] 的冻结 seed；主题一律走既有 ThemeManager →
/// AppThemes → DS/context.sparkleTheme 管道（F01 preview 通道），本文件不
/// 生产任何颜色/字号字面量（UI-TOKENS 棘轮 + 唯一令牌体系约束）。
///
/// 绑定真实路径（卡面「先按既有规范绑定本卡真实路径」）：
/// - 首页面：`features/home/presentation/widgets/today_cockpit_card.dart`
///   （首页 hero 面真实组件；provider 钉 seed，离线不拉真源）。
/// - 卡住 sheet 面：`features/chat/presentation/widgets/task_stuck_card.dart`
///   （卡住干预真实承载卡）+ 真实 `showModalBottomSheet`（sheet 形态本体）。
/// - 记忆面：`features/memory/presentation/widgets/memory_evidence_badge.dart`
///   （证据徽章 + quick peek 真实组件）。
/// - 长回答面：`core/widgets/sparkle_markdown.dart`（聊天气泡内长回答的
///   真实内容渲染器；气泡容器依赖会话 provider/网络面，preview 离线合同
///   不接，见 limitations）。
/// - 星图面：`features/galaxy/presentation/widgets/galaxy/` 的
///   [TiledSectorBackground] + [GalaxyNodePreviewCard]（星图真实组件；
///   整屏 GalaxyScreen 依赖相机/空间索引/回放计划，preview 不重建画布）。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/design/style_preview/style_preview_seed.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/presentation/widgets/task_stuck_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/galaxy_node_preview_card.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_background_painter.dart';
import 'package:sparkle/features/home/presentation/providers/home_growth_provider.dart';
import 'package:sparkle/features/home/presentation/providers/today_cockpit_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/today_cockpit_card.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

/// 五面的展示名（preview 页自身是未批准提案的开发预览面，隐藏于默认
/// flag 之后的开发者入口；中文先行的字符串随 F02 故事页先例，arb 词条
/// 在设计批准转正时一并落）。
enum StylePreviewFace {
  home('首页'),
  stuckSheet('卡住 sheet'),
  memory('记忆'),
  longAnswer('长回答'),
  starMap('星图');

  const StylePreviewFace(this.title);

  final String title;
}

/// 每面的「当前流步」可视锚：流步 → 面内真实组件状态的真实映射。
/// - home：runActive=骨架加载；committed=推进态；其余=内容态。
/// - stuck/memory/longAnswer/starMap：见各 face。
TodayCockpitVm seedCockpitVm(StylePreviewFlowStep step) {
  final loading = step == StylePreviewFlowStep.runActive;
  return TodayCockpitVm(
    isLoading: loading,
    mode: step == StylePreviewFlowStep.versionConflict
        ? TodayCockpitMode.stalled
        : (kSeedCockpitHasGoal
            ? (step == StylePreviewFlowStep.runActive
                ? TodayCockpitMode.fresh
                : TodayCockpitMode.active)
            : TodayCockpitMode.noGoal),
    action: step == StylePreviewFlowStep.versionConflict
        ? TodayCockpitAction.stuckRecovery
        : TodayCockpitAction.startTask,
    goalTitle: kSeedGoalTitle,
    goalProgress: 0.62,
    planName: kSeedPlanName,
    tasksTotal: kSeedTasksTotal,
    tasksCompleted:
        step == StylePreviewFlowStep.committed ? kSeedTasksCommitted : 3,
    goalTasksTotal: kSeedTasksTotal,
    goalTasksCompleted:
        step == StylePreviewFlowStep.committed ? kSeedTasksCommitted : 3,
    runIsActive: step == StylePreviewFlowStep.runActive,
    runLabel: step == StylePreviewFlowStep.runActive ? '特征值专项 · 运行中' : null,
    staleGuard: step == StylePreviewFlowStep.versionConflict,
  );
}

/// 星图节点 seed（流步 → 掌握度真实映射：committed 步回执抬升掌握度）。
GalaxyNodeModel seedGalaxyNode(StylePreviewFlowStep step) => GalaxyNodeModel(
      id: 'seed-node-eigen',
      name: kSeedGalaxy.nodeName,
      importance: 4,
      sector: SectorEnum.tech,
      isUnlocked: true,
      masteryScore: step == StylePreviewFlowStep.committed
          ? kSeedGalaxy.masteryCommitted
          : kSeedGalaxy.masteryBase,
      description: '特征值 / 特征向量 / 广义特征向量链',
      reviewUrgencyScore: step == StylePreviewFlowStep.committed
          ? 0
          : kSeedGalaxy.reviewUrgency,
      isReviewRecommended: step != StylePreviewFlowStep.committed,
      reviewUrgencyReason:
          step == StylePreviewFlowStep.committed ? null : 'review_window',
      daysSinceMasteryUpdate: step == StylePreviewFlowStep.committed ? 0 : 6,
    );

/// 记忆面徽章状态（真实 [MemoryEvidenceStatus]；流步只挪视觉，不改语义——
/// 记忆证据 status 与任务回执解耦）。
MemoryEvidenceStatus seedMemoryStatus(StylePreviewFlowStep step) =>
    step == StylePreviewFlowStep.versionConflict
        ? MemoryEvidenceStatus.missing
        : MemoryEvidenceStatus.ok;

/// ---------------------------------------------------------------------------
/// 面容器：统一的面壳（标题 + 流步锚），五面共用（同一状态流的承载件）。
/// ---------------------------------------------------------------------------

class StylePreviewFaceCard extends StatelessWidget {
  const StylePreviewFaceCard({
    required this.face,
    required this.frame,
    required this.child,
    super.key,
  });

  final StylePreviewFace face;

  /// 当前流步的呈现投影（所有面同源）。
  final StylePreviewFlowFrame frame;

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkle.colors;
    return Card(
      margin: const EdgeInsets.fromLTRB(DS.spacing16, 0, DS.spacing16, DS.spacing16),
      elevation: 0,
      clipBehavior: Clip.antiAlias,
      color: colors.surfaceSecondary,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(DS.borderRadiusLG),
        side: frame.isHighlight
            ? BorderSide(color: colors.semanticSuccess, width: 2)
            : BorderSide(color: colors.neutralOutline),
      ),
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    face.title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: colors.textPrimary,
                        ),
                  ),
                ),
                // 状态视觉（F02 徽章族；success 单载体）+ F03 冻结文案
                // 并列呈现：徽章承载视觉语义，文案承载可读语义——同一
                // 流步在五个面逐字一致（同一状态流的可视锚）。
                if (frame.visualState != null)
                  PixelStateBadge(state: frame.visualState!),
                if (frame.copy.isNotEmpty) ...[
                  const SizedBox(width: DS.spacing8),
                  Text(
                    frame.copy,
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          color: frame.isHighlight
                              ? colors.semanticSuccess
                              : colors.textSecondary,
                        ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: DS.spacing12),
            child,
          ],
        ),
      ),
    );
  }
}

/// ---------------------------------------------------------------------------
/// 五面 builder（真实组件 + seed；style_preview_page 按 [StylePreviewFace]
/// 选择装配）。
/// ---------------------------------------------------------------------------

/// 首页面：真实 [TodayCockpitCard]。provider 钉 seed（[todayCockpitProvider]
/// override），按流步重挂（ProviderScope 覆写集合创建后不可变——preview 面
/// 用 ValueKey 按步重挂，代价仅限该隐藏 preview 页）。
class StylePreviewHomeFace extends StatelessWidget {
  const StylePreviewHomeFace({required this.step, super.key});

  final StylePreviewFlowStep step;

  @override
  Widget build(BuildContext context) => ProviderScope(
      key: ValueKey('style-preview-cockpit-$step'),
      overrides: [
        todayCockpitProvider.overrideWithValue(seedCockpitVm(step)),
        // V4-U01：接续条消费面（episodeResumeProvider → 回执读面/today
        // 选择流）在 preview 离线合同内钉死——回执读面 off（modeGated）、
        // growth 读面空态，零网络（与 F05「provider 钉 seed，离线不拉真源」
        // 同一合同；接续条如实缺席）。
        homeGrowthStateProvider.overrideWith(
          (ref) => const HomeGrowthState.empty(),
        ),
        contextReceiptProvider.overrideWith(
          (ref) => _PreviewContextReceiptNotifier(),
        ),
      ],
      child: const TodayCockpitCard(),
    );
}

/// preview 离线合同：回执读面钉 off（modeGated），零网络。
class _PreviewContextReceiptNotifier extends ContextReceiptNotifier {
  _PreviewContextReceiptNotifier() : super(_PreviewUnreachableApiClient()) {
    // 构造期即钉 modeGated（provider 工厂被覆写后无人调用 load()）。
    state = const ContextReceiptState(
      phase: ContextReceiptPhase.modeGated,
      mode: 'off',
    );
  }

  @override
  Future<void> load() async {}

  @override
  Future<void> refresh() async {}
}

class _PreviewUnreachableApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('style preview must not hit network');
}

/// 卡住 sheet 面：真实 [TaskStuckCard] 内嵌 + 真实 `showModalBottomSheet`
/// 打开入口（sheet 形态本体即产品路径 [showModalBottomSheet]）。
class StylePreviewStuckSheetFace extends StatelessWidget {
  const StylePreviewStuckSheetFace({super.key});

  /// 打开真实 sheet（页面级入口；证据采集也走这里，保证截图即真实形态）。
  static Future<void> openSheet(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(DS.spacing16, DS.spacing8,
              DS.spacing16, DS.spacing24,),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '卡住 sheet · 真实干预卡',
                style: Theme.of(sheetContext).textTheme.titleSmall,
              ),
              const SizedBox(height: DS.spacing12),
              TaskStuckCard(
                data: kSeedStuckCardData,
                onWidgetAction: (_, __) async {},
              ),
            ],
          ),
        ),
      ),
    );

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkle.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TaskStuckCard(
          data: kSeedStuckCardData,
          onWidgetAction: (_, __) async {},
        ),
        const SizedBox(height: DS.spacing12),
        OutlinedButton.icon(
          icon: const Icon(Icons.open_in_new, size: 16),
          label: const Text('以真实 bottomSheet 打开'),
          onPressed: () => openSheet(context),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          'sheet 顶层形态进证据截图（同 build 同 seed）。',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: colors.textSecondary,
              ),
        ),
      ],
    );
  }
}

/// 记忆面：真实 [MemoryEvidenceBadge] + [EvidenceQuickPeek]。
class StylePreviewMemoryFace extends StatelessWidget {
  const StylePreviewMemoryFace({required this.step, super.key});

  final StylePreviewFlowStep step;

  @override
  Widget build(BuildContext context) {
    final status = seedMemoryStatus(step);
    final colors = context.sparkle.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MemoryEvidenceBadge(
          status: status,
          evidenceCount: kSeedMemory.evidenceCount,
          quickPeekSummaries: kSeedMemory.summaries,
        ),
        const SizedBox(height: DS.spacing12),
        EvidenceQuickPeek(summaries: kSeedMemory.summaries, status: status),
        const SizedBox(height: DS.spacing8),
        Text(
          'F03 分层路由：memory.saved=高亮，永不成功面孔（见流步锚）。',
          style: Theme.of(context)
              .textTheme
              .labelSmall
              ?.copyWith(color: colors.textSecondary),
        ),
      ],
    );
  }
}

/// 长回答面：真实 [SparkleMarkdown]（聊天气泡同款内容渲染器）。
class StylePreviewLongAnswerFace extends StatelessWidget {
  const StylePreviewLongAnswerFace({required this.step, super.key});

  final StylePreviewFlowStep step;

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkle.colors;
    final streaming = step == StylePreviewFlowStep.runActive;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SparkleMarkdown(
          content: streaming ? kSeedLongAnswerPartial : kSeedLongAnswerFull,
          textColor: colors.textPrimary,
          codeBackgroundColor: colors.surfaceTertiary,
          linkColor: colors.semanticInfo,
        ),
        if (streaming) ...[
          const SizedBox(height: DS.spacing8),
          Row(
            children: [
              // 静态指示（非动画）：preview 证据采集要求可 pumpAndSettle
              // 落定；流式真动画在会话面本体，不在本预览面。
              Icon(Icons.more_horiz, size: 14, color: colors.semanticInfo),
              const SizedBox(width: DS.spacing8),
              Text(
                '生成中（部分可见，不伪装完成态）',
                style: Theme.of(context)
                    .textTheme
                    .labelSmall
                    ?.copyWith(color: colors.textSecondary),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

/// 星图面：真实 [TiledSectorBackground] + [GalaxyNodePreviewCard]。
class StylePreviewStarMapFace extends StatelessWidget {
  const StylePreviewStarMapFace({required this.step, super.key});

  final StylePreviewFlowStep step;

  @override
  Widget build(BuildContext context) {
    final colors = context.sparkle.colors;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(DS.borderRadiusMD),
          child: const SizedBox(
            height: 120,
            width: double.infinity,
            child: TiledSectorBackground(
              width: 720,
              height: 240,
            ),
          ),
        ),
        const SizedBox(height: DS.spacing12),
        GalaxyNodePreviewCard(
          node: seedGalaxyNode(step),
          onFocus: () {},
          onInspectConnections: () {},
          onViewDetails: () {},
          onStartReview: () {},
          onLaunchPrediction: () {},
        ),
        const SizedBox(height: DS.spacing8),
        Text(
          'committed 回执 = 掌握度 ${kSeedGalaxy.masteryBase}→${kSeedGalaxy.masteryCommitted}（真实映射，非装饰）。',
          style: Theme.of(context)
              .textTheme
              .labelSmall
              ?.copyWith(color: colors.textSecondary),
        ),
      ],
    );
  }
}
