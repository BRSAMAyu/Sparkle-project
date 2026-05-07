import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
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
                        ? Center(
                            child: CircularProgressIndicator(
                              valueColor: AlwaysStoppedAnimation<Color>(
                                DS.brandPrimary70,
                              ),
                            ),
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
            SparkleIconButton(
              onPressed: () {
                unawaited(
                  SensoryFeedbackService.emit(SensoryFeedbackEvent.navigation),
                );
                context.pop();
              },
              icon: const Icon(Icons.arrow_back_ios_rounded),
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
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: _getTypeColor(pattern.patternType).withAlpha(40),
                        borderRadius: BorderRadius.circular(12),
                      ),
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
                          Text(
                            _getTypeLabel(pattern.patternType),
                            style: TextStyle(
                              fontSize: 12,
                              color: _getTypeColor(pattern.patternType),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    _buildMetaBadge(
                      icon: Icons.show_chart_rounded,
                      label:
                          '置信 ${(pattern.confidenceScore * 100).clamp(0, 100).toStringAsFixed(0)}%',
                      color: DS.prismBlue,
                    ),
                    const SizedBox(width: DS.spacing8),
                    _buildMetaBadge(
                      icon: Icons.repeat_rounded,
                      label: context.l10n.cogPatternFreq(pattern.frequency),
                      color: DS.prismGreen,
                    ),
                    if (pattern.isArchived)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: DS.success.withAlpha(40),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          context.l10n.patternArchived,
                          style: TextStyle(
                            fontSize: 10,
                            color: DS.success,
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                      ),
                  ],
                ),

                // Description
                if (pattern.description != null) ...[
                  const SizedBox(height: DS.lg),
                  Text(
                    pattern.description!,
                    style: TextStyle(
                      fontSize: 14,
                      color: DS.brandPrimary.withAlpha(200),
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
                            style: TextStyle(
                              fontSize: 13,
                              color: DS.successLight,
                              height: 1.4,
                            ),
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
                Text(
                  _buildFooterText(context),
                  style: TextStyle(
                    fontSize: 11,
                    color: DS.brandPrimary.withAlpha(100),
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
        decoration: BoxDecoration(
          color: color.withAlpha(28),
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
                fontSize: 11,
                color: color,
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
    return I18nService.instance.isChinese
        ? '$discovered · 最近观察 $lastObserved'
        : '$discovered · Last observed $lastObserved';
  }

  Color _getTypeColor(PatternType type) {
    switch (type) {
      case PatternType.cognitive:
        return DS.prismBlue;
      case PatternType.emotional:
        return DS.prismPurple;
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
}
