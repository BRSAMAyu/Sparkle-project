import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/home/data/models/prediction_insight_data.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';

class ChatPredictionDock extends ConsumerStatefulWidget {
  const ChatPredictionDock({
    required this.promptStarters,
    required this.onPromptSelected,
    this.compact = false,
    super.key,
  });

  final List<String> promptStarters;
  final ValueChanged<String> onPromptSelected;
  final bool compact;

  @override
  ConsumerState<ChatPredictionDock> createState() => _ChatPredictionDockState();
}

class _ChatPredictionDockState extends ConsumerState<ChatPredictionDock> {
  static const _expandedPrefKey = 'chat.prediction_dock.expanded';

  bool _isExpanded = true;
  int _followupRefreshAttempts = 0;
  Timer? _followupRefreshTimer;

  @override
  void initState() {
    super.initState();
    unawaited(_loadExpandedPreference());
  }

  Future<void> _loadExpandedPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final expanded = prefs.getBool(_expandedPrefKey) ?? true;
    if (!mounted) return;
    setState(() {
      _isExpanded = expanded;
    });
  }

  Future<void> _setExpanded(bool value) async {
    if (_isExpanded == value) {
      return;
    }
    setState(() {
      _isExpanded = value;
    });
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_expandedPrefKey, value);
  }

  @override
  void dispose() {
    _followupRefreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dashboardState = ref.watch(dashboardProvider);
    final predictionState = ref.watch(intentPredictionProvider);
    final isTyping =
        predictionState.isTyping && predictionState.currentInput.trim().isNotEmpty;
    final insight = isTyping
        ? predictionState.typingInsight
        : dashboardState.nextIntentForecast;
    final predictions = isTyping
        ? predictionState.typingPredictions
        : predictionState.idlePredictions;
    final visiblePredictions = predictions.take(isTyping ? 3 : 4).toList();
    final promptStarters = widget.promptStarters
        .where((prompt) => prompt.trim().isNotEmpty)
        .take(isTyping ? 2 : 2)
        .toList(growable: false);
    final sourceBadge = _sourceBadge(insight, isTyping: isTyping);
    final compactHeadline = _buildCompactHeadline(
      insight: insight,
      isTyping: isTyping,
      isLoading: dashboardState.isLoading,
    );
    final hasContent = insight != null ||
        visiblePredictions.isNotEmpty ||
        promptStarters.isNotEmpty ||
        dashboardState.isLoading;

    _ensureFollowupRefresh(
      isTyping: isTyping,
      insight: insight,
      isLoading: dashboardState.isLoading,
    );

    if (!hasContent) {
      return const SizedBox.shrink();
    }

    if (!_isExpanded) {
      return _CollapsedDock(
        compact: widget.compact,
        title: compactHeadline,
        sourceBadge: sourceBadge,
        onExpand: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          unawaited(_setExpanded(true));
        },
      );
    }

    return MaterialStyler(
      material: AppMaterials.neoGlass.copyWith(
        backgroundColor: DS.surfacePanel.withValues(alpha: 0.72),
        borderColor: DS.borderSubtle.withValues(alpha: 0.8),
        shadows: [
          BoxShadow(
            color: DS.info.withValues(alpha: 0.05),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      borderRadius: DS.borderRadius16,
      padding: EdgeInsets.symmetric(
        horizontal: widget.compact ? DS.spacing10 : DS.spacing12,
        vertical: widget.compact ? DS.spacing8 : DS.spacing10,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 26,
                height: 26,
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.psychology_alt_rounded,
                  size: 14,
                  color: DS.info,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  compactHeadline,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: DS.labelLarge.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
              if (sourceBadge != null) _MetaBadge(label: sourceBadge),
              if (sourceBadge != null) const SizedBox(width: DS.spacing8),
              InkWell(
                borderRadius: BorderRadius.circular(999),
                onTap: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  unawaited(_setExpanded(false));
                },
                child: Padding(
                  padding: const EdgeInsets.all(2),
                  child: Icon(
                    Icons.visibility_off_rounded,
                    size: 17,
                    color: DS.textSecondary,
                  ),
                ),
              ),
            ],
          ),
          if (visiblePredictions.isNotEmpty || promptStarters.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            SparkleStaggerWrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: visiblePredictions
                  .map(
                    (prediction) => _DockActionChip(
                      label: prediction.label,
                      icon: prediction.icon,
                      color: prediction.color ?? DS.brandPrimary,
                      onTap: prediction.action,
                    ),
                  )
                  .followedBy(
                    promptStarters
                        .map(
                          (prompt) => _DockActionChip(
                            label: prompt,
                            icon: Icons.chat_bubble_outline_rounded,
                            color: DS.prismBlue,
                            onTap: () => widget.onPromptSelected(prompt),
                          ),
                        ),
                  )
                  .toList(growable: false),
            ),
          ],
          if (dashboardState.isLoading &&
              visiblePredictions.isEmpty &&
              promptStarters.isEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              '预测更新中...',
              style: DS.labelSmall.copyWith(
                color: DS.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _buildCompactHeadline({
    required PredictionInsightData? insight,
    required bool isTyping,
    required bool isLoading,
  }) {
    if (isLoading) {
      return '预测更新中';
    }
    if (insight != null) {
      final raw = insight.title.trim().isNotEmpty
          ? insight.title.trim()
          : insight.summary.trim();
      final compact = raw
          .replaceFirst(RegExp('^系统预测'), '')
          .replaceFirst(RegExp('^你接下来'), '')
          .replaceFirst(RegExp('^最适合'), '')
          .replaceFirst(RegExp('^更适合'), '')
          .replaceFirst(RegExp('^会'), '')
          .replaceFirst(RegExp('^想'), '')
          .trim();
      if (compact.isNotEmpty) {
        return compact;
      }
    }
    return isTyping ? '下一步建议' : '推荐下一步';
  }

  String? _sourceBadge(PredictionInsightData? insight, {required bool isTyping}) {
    if (insight == null) {
      return isTyping ? '在线骨架' : null;
    }
    if (insight.horizon == 'realtime') {
      if (!insight.fallbackUsed) {
        return '在线AI';
      }
      return '在线兜底';
    }
    if (insight.predictionSource == 'glm_batch') {
      return '后台增强';
    }
    return '长期骨架';
  }

  void _ensureFollowupRefresh({
    required bool isTyping,
    required PredictionInsightData? insight,
    required bool isLoading,
  }) {
    if (isTyping || isLoading) {
      return;
    }
    if (insight != null && insight.predictionSource != 'rules') {
      return;
    }
    if (_followupRefreshTimer != null || _followupRefreshAttempts >= 2) {
      return;
    }

    _followupRefreshAttempts += 1;
    _followupRefreshTimer = Timer(const Duration(seconds: 18), () async {
      _followupRefreshTimer = null;
      if (!mounted) {
        return;
      }
      await ref.read(dashboardProvider.notifier).refresh();
    });
  }
}

class _CollapsedDock extends StatelessWidget {
  const _CollapsedDock({
    required this.title,
    required this.onExpand,
    this.sourceBadge,
    this.compact = false,
  });

  final String title;
  final String? sourceBadge;
  final VoidCallback onExpand;
  final bool compact;

  @override
  Widget build(BuildContext context) => MaterialStyler(
        material: AppMaterials.neoGlass.copyWith(
          backgroundColor: DS.surfacePanel.withValues(alpha: 0.72),
          borderColor: DS.borderSubtle.withValues(alpha: 0.78),
        ),
        borderRadius: DS.borderRadiusFull,
        padding: EdgeInsets.symmetric(
          horizontal: compact ? DS.spacing10 : 12,
          vertical: compact ? DS.spacing6 : DS.spacing8,
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(999),
          onTap: onExpand,
          child: Row(
            children: [
              Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  Icons.auto_awesome_rounded,
                  size: 13,
                  color: DS.info,
                ),
              ),
              const SizedBox(width: DS.spacing8),
              Expanded(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: DS.labelLarge.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ),
              if (sourceBadge != null) ...[
                _MetaBadge(label: sourceBadge!),
                const SizedBox(width: DS.spacing8),
              ],
              Icon(
                Icons.unfold_more_rounded,
                size: 18,
                color: DS.textSecondary,
              ),
            ],
          ),
        ),
      );
}

class _MetaBadge extends StatelessWidget {
  const _MetaBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing6,
          vertical: 3,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceOverlay,
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Text(
          label,
          style: DS.labelSmall.copyWith(
            color: DS.textSecondary,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      );
}

class _DockActionChip extends StatefulWidget {
  const _DockActionChip({
    required this.label,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  State<_DockActionChip> createState() => _DockActionChipState();
}

class _DockActionChipState extends State<_DockActionChip> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      onTap: widget.onTap,
        child: AnimatedScale(
          scale: _isPressed ? 0.98 : 1,
          duration: DS.durationFast,
          curve: DS.curveEaseOut,
          child: Container(
            constraints: const BoxConstraints(
            minHeight: 34,
            maxWidth: 220,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            color: isDark
                ? DS.surfaceTertiary.withValues(alpha: 0.94)
                : DS.surfaceOverlay,
            borderRadius: DS.borderRadius16,
            border: Border.all(
              color: widget.color.withValues(alpha: _isPressed ? 0.28 : 0.18),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                widget.icon,
                size: DS.iconSizeXs,
                color: widget.color,
              ),
              const SizedBox(width: DS.spacing6),
              Flexible(
                child: Text(
                  widget.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: DS.bodySmall.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
