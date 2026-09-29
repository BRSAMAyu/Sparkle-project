import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';

/// PatternListScreen - Cognitive Prism Details v2.3
///
/// Displays all behavior patterns with deep space theme
class PatternListScreen extends ConsumerStatefulWidget {
  const PatternListScreen({this.highlightId, super.key});
  final String? highlightId;

  @override
  ConsumerState<PatternListScreen> createState() => _PatternListScreenState();
}

class _PatternListScreenState extends ConsumerState<PatternListScreen> {
  @override
  void initState() {
    super.initState();
    // 🔧 Riverpod修复：使用addPostFrameCallback在widget构建完成后加载数据
    // 避免在build过程中修改provider状态
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_loadPatterns());
    });
  }

  Future<void> _loadPatterns() async {
    await ref.read(cognitiveProvider.notifier).loadPatterns();
  }

  @override
  Widget build(BuildContext context) {
    final cognitiveState = ref.watch(cognitiveProvider);

    return SparklePageScaffold(
      role: SparklePageRole.immersive,
      safeArea: false,
      child: SafeArea(
        child: Column(
          children: [
            _buildAppBar(context),
            Expanded(
              child: SparkleRefreshIndicator(
                onRefresh: _loadPatterns,
                child:
                    cognitiveState.isLoading && cognitiveState.patterns.isEmpty
                        ? const Center(
                            child: LoadingIndicator(),
                          )
                        : cognitiveState.patterns.isEmpty
                            ? _buildEmptyState()
                            : _buildPatternList(cognitiveState.patterns),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAppBar(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing8,
          DS.spacing8,
          DS.spacing16,
          DS.spacing16,
        ),
        child: Row(
          children: [
            // 甲式（A11Y-BATCH6B）：SparkleIconButton semanticLabel 单节点。
            SparkleIconButton(
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.navigation),
                );
                context.pop();
              },
              icon: const Icon(Icons.arrow_back_ios_rounded),
              semanticLabel: context.l10n.back,
              variant: ButtonVariant.ghost,
            ),
            Expanded(
              child: Text(
                context.l10n.patternListTitle,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: DS.prismPurple.withAlpha(40),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.diamond_outlined,
                color: DS.brandPrimaryConst,
                size: 20,
              ),
            ),
          ],
        ),
      );

  Widget _buildEmptyState() => SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(DS.xxl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const SizedBox(height: 80),
            Container(
              padding: const EdgeInsets.all(DS.xl),
              decoration: BoxDecoration(
                color: DS.prismPurple.withAlpha(30),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.psychology_alt_rounded,
                size: 64,
                color: DS.prismPurple.withAlpha(150),
              ),
            ),
            const SizedBox(height: DS.xl),
            Text(
              context.l10n.patternListEmptyTitle,
              style: TextStyle(
                fontSize: 18,
                fontWeight: DS.fontWeightBold,
                color: DS.textPrimary,
              ),
            ),
            const SizedBox(height: DS.sm),
            Text(
              context.l10n.patternListEmptySubtitle,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 14,
                color: DS.textSecondary,
                height: 1.5,
              ),
            ),
            // N39（A-SPEC7 §4）空态必答下一步：诊断空态曾是「图标+标题+
            // 副标题」死胡同；补「开始首次诊断」直达入口——聊天即诊断输入
            // （S4 建模访谈已证可行），prompt 预填照 home 首目标空态模式。
            const SizedBox(height: DS.lg),
            SparkleButton.primary(
              label: context.l10n.patternListEmptyCta,
              icon: const Icon(Icons.psychology_alt_rounded, size: 18),
              expand: true,
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.navigation),
                );
                context.go(
                  '/chat?prompt=${Uri.encodeComponent(context.l10n.patternListEmptyDiagnosisPrompt)}',
                );
              },
            ),
          ],
        ),
      );

  Widget _buildPatternList(List<BehaviorPatternModel> patterns) =>
      ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
        itemCount: patterns.length,
        itemBuilder: (context, index) => Padding(
          padding: const EdgeInsets.only(bottom: DS.spacing16),
          child: SparkleStaggerItem(
            index: index,
            child: _PatternCard(pattern: patterns[index]),
          ),
        ),
      );
}

/// Pattern Card with glassmorphism style
class _PatternCard extends StatelessWidget {
  const _PatternCard({required this.pattern});
  final BehaviorPatternModel pattern;

  @override
  Widget build(BuildContext context) => ClipRRect(
        borderRadius: DS.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            decoration: BoxDecoration(
              color: DS.glassBackground,
              borderRadius: DS.borderRadius20,
              border: Border.all(color: DS.glassBorder),
            ),
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header
                Row(
                  children: [
                    // V4-G05 类型章：类型色只上图标（非文字件 ≥3:1 四风格
                    // 逐对复算通过），底 tint 撤除——classic brandSecondary
                    // 系在自身 tint 上 2.88:1（<3:1 图形阈值）。
                    Container(
                      padding: const EdgeInsets.all(10),
                      child: Icon(
                        _getTypeIcon(pattern.patternType),
                        color: _getTypeColor(pattern.patternType),
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: DS.md),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            pattern.patternName,
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: DS.fontWeightBold,
                              color: DS.brandPrimaryConst,
                            ),
                          ),
                          const SizedBox(height: 2),
                          // V4-G05 类型标签文本走 textSecondary（类型色在
                          // classic 上 3.19:1 <4.5:1；类型辨识由图标形状+
                          // 颜色承载，文本不做颜色唯一载体）。
                          Text(
                            _getTypeLabel(pattern.patternType),
                            // V4-G03：彩色 12sp 标签对 tint 合成底在
                            // classic-light 4.32:1 <4.5；类型文字走
                            // textSecondary（全档 ≥4.8:1），色相辨识由图标承担。
                            style: TextStyle(
                              fontSize: 12,
                              color: DS.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    // V4-U13 假精确清理（M-10 置信黑话清除同律）：无真实
                    // 定义的「AI 置信 N%」不上屏；观察档从真实计数
                    // （frequency）派生——原始数值（次数）与推断（定式名）
                    // 拆开，样本有真实定义。
                    _buildMetaBadge(
                      icon: Icons.show_chart_rounded,
                      label: _observationTierLabel(context, pattern.frequency),
                      color: DS.prismBlue,
                    ),
                    const SizedBox(width: DS.spacing8),
                    _buildMetaBadge(
                      icon: Icons.repeat_rounded,
                      label: context.l10n.cogPatternFreq(pattern.frequency),
                      color: DS.prismGreen,
                    ),
                    if (pattern.isArchived)
                      // V4-G03 四风格对比度复算：success 10sp 标签对 0.157
                      // tint 合成底在 classic 两档仅 4.01–4.45:1，且低于
                      // 12sp 字阶下限；0.06 tint + textPrimary 全档 ≥8.45:1，
                      // 归档态辨识由 tint 容器 + 实色描边（≥3:1 图形）承担。
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: DS.success.withValues(alpha: 0.06),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: DS.success.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Text(
                          context.l10n.patternArchived,
                          style: TextStyle(
                            fontSize: DS.fontSizeXs,
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                      ),
                  ],
                ),

                // Description
                if (pattern.description != null) ...[
                  const SizedBox(height: DS.lg),
                  // V4-G05 描述正文禁「透明度压文字」（SPEC §1.3.1）：
                  // brand@200 在 classic/paperDay 3.44/3.69:1 <4.5:1，
                  // 走 textSecondary 语义槽（四风格 ≥5.29:1）。
                  Text(
                    pattern.description!,
                    // V4-G03 四风格对比度复算：正文 brandPrimary@0.784 衰减
                    // 在 classic 两档/paperDay 仅 3.25–3.90:1；描述是正文，
                    // 走 textSecondary（全档 ≥4.85:1），品牌色相不承载正文。
                    style: TextStyle(
                      fontSize: 14,
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
                  ),
                ],

                // Solution
                if (pattern.solutionText != null) ...[
                  const SizedBox(height: DS.lg),
                  Container(
                    padding: const EdgeInsets.all(DS.md),
                    decoration: BoxDecoration(
                      color: DS.success.withAlpha(20),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: DS.success.withAlpha(50),
                      ),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.lightbulb_outline_rounded,
                          color: DS.success,
                          size: 18,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            pattern.solutionText!,
                            // V4-G03 四风格对比度复算：successLight 13sp 对
                            // 0.078 tint 合成底在浅色三档仅 2.12–2.88:1；
                            // 方案是关键正文，走 textPrimary（全档 ≥8.07:1），
                            // 语义色保留在灯泡图标（全档 ≥4.46:1）与 tint 容器。
                            style: TextStyle(
                              fontSize: 13,
                              color: DS.textPrimary,
                              height: 1.4,
                            ),
                          ),
                      ],
                    ),
                  ),

                  const SizedBox(height: DS.md),
                  // Action Button (Phase 6.2)
                  Align(
                    alignment: Alignment.centerRight,
                    child: SparkleButton.ghost(
                      label: context.l10n.patternTakeAction,
                      onPressed: () {
                        // Smart routing based on pattern type could be added here
                        unawaited(context.push('/focus'));
                      },
                      icon: const Icon(Icons.arrow_forward),
                    ),
                  ),
                ],

                // Date
                const SizedBox(height: DS.md),
                // V4-G05 页脚时间戳走 textTertiary 定标槽（brand@100 透明度
                // 压文字四风格 1.73–2.71:1 全失败；textTertiary 定标
                // ≥4.5:1 on S0/S1，四风格实测 4.63–9.33:1）。
                Text(
                  _buildFooterText(context),
                  // V4-G03 四风格对比度复算：brandPrimary@0.392 衰减文字在
                  // 五档仅 1.71–2.38:1（全档崩）；脚注走 textSecondary
                  // （全档 ≥4.85:1）。
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildMetaBadge({
    required IconData icon,
    required String label,
    required Color color,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        // V4-G03 四风格对比度复算：彩色 11sp 标签对 0.11 tint 合成底在
        // classic 两档 4.27–4.35:1 且低于 12sp 字阶下限；0.06 tint +
        // textPrimary 标签全档 ≥8.45:1，色相辨识由图标（0.06 tint 上
        // 全档 ≥4.55:1）承担。
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: DS.textPrimary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ],
        ),
      );

  String _buildFooterText(BuildContext context) {
    final discovered = context.l10n.patternDiscoveredOn(
      Formatters.formatDateShort(pattern.createdAt),
    );
    if (pattern.lastObservedAt == null) {
      return discovered;
    }
    final lastObserved = Formatters.formatRelativeTime(pattern.lastObservedAt!);
    return '$discovered · ${context.l10n.patternLastObserved(lastObserved)}';
  }

  /// 类型色（V4-G03 四风格复算）：
  /// - emotional 原 brandSecondary（退役别名槽）在 classic-light 玻璃面对
  ///   图标仅 2.72:1（<3:1 图形门）；改 taskReflection（柔紫语义槽，
  ///   四档 ≥4.3:1，B2-3a 定标色），紫系辨识度保留。
  /// - 12sp 类型文字标签一律 textSecondary（彩色 12sp 对 withAlpha(40)
  ///   tint 在 classic-light 4.32:1 <4.5）；色相辨识由图标与 tint 容器
  ///   承载（图标全档 ≥3:1）。
  Color _getTypeColor(PatternType type) {
    switch (type) {
      case PatternType.cognitive:
        return DS.prismBlue;
      case PatternType.emotional:
        return DS.taskReflection;
      case PatternType.execution:
        return DS.prismGreen;
      default:
        return DS.neutral400;
    }
  }

  IconData _getTypeIcon(PatternType type) {
    switch (type) {
      case PatternType.cognitive:
        return Icons.psychology_rounded;
      case PatternType.emotional:
        return Icons.mood_rounded;
      case PatternType.execution:
        return Icons.bolt_rounded;
      default:
        return Icons.diamond_outlined;
    }
  }

  String _getTypeLabel(PatternType type) {
    switch (type) {
      case PatternType.cognitive:
        return I18nService.instance.l10n.patternTypeCognitive;
      case PatternType.emotional:
        return I18nService.instance.l10n.patternTypeEmotional;
      case PatternType.execution:
        return I18nService.instance.l10n.patternTypeExecution;
      default:
        return I18nService.instance.l10n.patternTypeDefault;
    }
  }

  /// V4-U13 观察档（真实计数派生的定性词，M-10 同律）：样本 = frequency
  /// （真实出现次数，由相邻「出现 N 次」徽章如实承载）；不做任何置信
  /// 百分比换算。
  String _observationTierLabel(BuildContext context, int frequency) {
    final l10n = context.l10n;
    if (frequency >= 3) {
      return l10n.cogPatternTierRepeated;
    }
    if (frequency == 2) {
      return l10n.cogPatternTierTwice;
    }
    if (frequency == 1) {
      return l10n.cogPatternTierSingle;
    }
    return l10n.cogPatternTierNone;
  }
}
