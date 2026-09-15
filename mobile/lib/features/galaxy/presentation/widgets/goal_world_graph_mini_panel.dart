import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/galaxy/presentation/providers/goal_graph_overlay_provider.dart';
import 'package:sparkle/features/plan/presentation/providers/active_goal_provider.dart';

class GoalWorldGraphMiniPanel extends ConsumerStatefulWidget {
  const GoalWorldGraphMiniPanel({
    super.key,
    this.goalId,
    this.isGoalWorldMode = false,
    this.onViewModeToggle,
  });

  final String? goalId;
  final bool isGoalWorldMode;
  final VoidCallback? onViewModeToggle;

  @override
  ConsumerState<GoalWorldGraphMiniPanel> createState() =>
      _GoalWorldGraphMiniPanelState();
}

class _GoalWorldGraphMiniPanelState
    extends ConsumerState<GoalWorldGraphMiniPanel> {
  bool _expanded = false;

  @override
  void didUpdateWidget(GoalWorldGraphMiniPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isGoalWorldMode && !_expanded) {
      _expanded = true;
    }
  }

  @override
  Widget build(BuildContext context) {
    final goalId = widget.goalId ?? ref.watch(activeGoalHeaderProvider);
    final scheme = Theme.of(context).colorScheme;

    return Align(
      alignment: Alignment.topRight,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        constraints: BoxConstraints(
          maxWidth: _expanded ? 390 : 230,
          maxHeight: _expanded ? MediaQuery.sizeOf(context).height * 0.52 : 56,
        ),
        decoration: BoxDecoration(
          color: scheme.surface.withValues(alpha: 0.92),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: widget.isGoalWorldMode
                ? scheme.primary.withValues(alpha: 0.6)
                : scheme.outlineVariant,
            width: widget.isGoalWorldMode ? 1.5 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: (widget.isGoalWorldMode ? scheme.primary : scheme.shadow)
                  .withValues(alpha: widget.isGoalWorldMode ? 0.18 : 0.24),
              blurRadius: widget.isGoalWorldMode ? 22 : 18,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              _Header(
                expanded: _expanded,
                hasGoal: goalId != null,
                isGoalWorldMode: widget.isGoalWorldMode,
                onToggle: () => setState(() => _expanded = !_expanded),
                onViewModeToggle: widget.onViewModeToggle,
              ),
              AnimatedCrossFade(
                firstChild: const SizedBox.shrink(),
                secondChild: goalId == null
                    ? const _NoGoalState()
                    : _GraphBody(goalId: goalId),
                crossFadeState: _expanded
                    ? CrossFadeState.showSecond
                    : CrossFadeState.showFirst,
                duration: const Duration(milliseconds: 180),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.expanded,
    required this.hasGoal,
    required this.isGoalWorldMode,
    required this.onToggle,
    this.onViewModeToggle,
  });

  final bool expanded;
  final bool hasGoal;
  final bool isGoalWorldMode;
  final VoidCallback onToggle;
  final VoidCallback? onViewModeToggle;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: context.l10n.goalGraphPanelSemantics,
      child: InkWell(
        onTap: onToggle,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.account_tree_outlined,
                color: isGoalWorldMode
                    ? scheme.primary
                    : hasGoal
                        ? scheme.onSurfaceVariant
                        : scheme.onSurfaceVariant,
                size: 18,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  context.l10n.goalGraphPanelTitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                        color: scheme.onSurface,
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ),
              if (onViewModeToggle != null)
                Semantics(
                  button: true,
                  label: isGoalWorldMode ? context.l10n.goalGraphToggleToStarMap : context.l10n.goalGraphToggleToGoalWorld,
                  child: InkWell(
                    borderRadius: BorderRadius.circular(6),
                    onTap: onViewModeToggle,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: isGoalWorldMode
                            ? scheme.primary.withValues(alpha: 0.18)
                            : scheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: isGoalWorldMode
                              ? scheme.primary.withValues(alpha: 0.48)
                              : scheme.outlineVariant,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            isGoalWorldMode
                                ? Icons.visibility_off_rounded
                                : Icons.auto_awesome_rounded,
                            size: 14,
                            color: isGoalWorldMode
                                ? scheme.primary
                                : scheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            isGoalWorldMode ? context.l10n.goalGraphToggleStarMap : context.l10n.goalGraphToggleGoal,
                            style:
                                Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: isGoalWorldMode
                                          ? scheme.primary
                                          : scheme.onSurfaceVariant,
                                      fontWeight: FontWeight.w600,
                                    ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              const SizedBox(width: 4),
              Icon(
                expanded
                    ? Icons.expand_less_rounded
                    : Icons.expand_more_rounded,
                color: scheme.onSurfaceVariant,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _GraphBody extends ConsumerWidget {
  const _GraphBody({required this.goalId});

  final String goalId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(goalGraphOverlayProvider(goalId));
    final scheme = Theme.of(context).colorScheme;

    return state.when(
      loading: () => Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
        child: Row(
          children: [
            SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: scheme.primary,
              ),
            ),
            const SizedBox(width: 10),
            Text(
              context.l10n.goalGraphLoading,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: scheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      ),
      error: (_, __) => Padding(
        padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        child: OutlinedButton.icon(
          onPressed: () => ref.invalidate(goalGraphOverlayProvider(goalId)),
          icon: const Icon(Icons.refresh_rounded),
          label: Text(context.l10n.goalGraphRetry),
        ),
      ),
      data: (data) {
        if (!data.active || data.nodes.isEmpty) {
          return const _EmptyGraphState();
        }

        final bottleneckCount = data.bottleneckNodes.length;
        final totalNodes = data.nodes.length;
        final masteredCount = data.masteredNodes.length;
        final masteryAverage = totalNodes > 0
            ? (data.nodes.fold<double>(0, (s, n) => s + n.mastery) / totalNodes)
            : 0.0;

        return ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.44,
          ),
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _GapAnalysisSummary(
                  totalNodes: totalNodes,
                  bottleneckCount: bottleneckCount,
                  masteredCount: masteredCount,
                  masteryAverage: masteryAverage,
                ),
                const SizedBox(height: 10),
                _LegendRow(data: data),
                const SizedBox(height: 10),
                _NodeSection(
                  title: context.l10n.goalGraphBottlenecks,
                  nodes: data.bottleneckNodes,
                  state: GoalGraphNodeState.bottleneck,
                ),
                _NodeSection(
                  title: context.l10n.goalGraphLearning,
                  nodes: data.learningNodes,
                  state: GoalGraphNodeState.learning,
                ),
                _NodeSection(
                  title: context.l10n.goalGraphMastered,
                  nodes: data.masteredNodes,
                  state: GoalGraphNodeState.mastered,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _GapAnalysisSummary extends StatelessWidget {
  const _GapAnalysisSummary({
    required this.totalNodes,
    required this.bottleneckCount,
    required this.masteredCount,
    required this.masteryAverage,
  });

  final int totalNodes;
  final int bottleneckCount;
  final int masteredCount;
  final double masteryAverage;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final coveragePercent = totalNodes > 0
        ? ((masteredCount / totalNodes) * 100).round()
        : 0;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.l10n.goalGraphGapAnalysis,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: scheme.onSurface,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _GapStat(
                label: context.l10n.goalGraphCoverage,
                value: '$coveragePercent%',
                color: coveragePercent >= 60
                    ? scheme.primary
                    : coveragePercent >= 30
                        ? scheme.tertiary
                        : scheme.error,
              ),
              const SizedBox(width: 16),
              _GapStat(
                label: context.l10n.goalGraphBottlenecks,
                value: '$bottleneckCount',
                color: bottleneckCount == 0 ? scheme.primary : scheme.error,
              ),
              const SizedBox(width: 16),
              _GapStat(
                label: context.l10n.goalGraphMastery,
                value: '${(masteryAverage * 100).round()}%',
                color: masteryAverage >= 0.6
                    ? scheme.primary
                    : masteryAverage >= 0.3
                        ? scheme.tertiary
                        : scheme.error,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _GapStat extends StatelessWidget {
  const _GapStat({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            value,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: scheme.onSurfaceVariant,
                ),
          ),
        ],
      ),
    );
  }
}

class _LegendRow extends StatelessWidget {
  const _LegendRow({required this.data});

  final GoalGraphOverlayData data;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [
          _LegendChip(
            label: context.l10n.goalGraphLegendBottleneck(
              data.bottleneckNodes.length,
            ),
            state: GoalGraphNodeState.bottleneck,
          ),
          _LegendChip(
            label: context.l10n.goalGraphLegendLearning(
              data.learningNodes.length,
            ),
            state: GoalGraphNodeState.learning,
          ),
          _LegendChip(
            label: context.l10n.goalGraphLegendMastered(
              data.masteredNodes.length,
            ),
            state: GoalGraphNodeState.mastered,
          ),
        ],
      );
}

class _LegendChip extends StatelessWidget {
  const _LegendChip({
    required this.label,
    required this.state,
  });

  final String label;
  final GoalGraphNodeState state;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = _stateColor(scheme, state);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.38)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: scheme.onSurface,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}

class _NodeSection extends StatelessWidget {
  const _NodeSection({
    required this.title,
    required this.nodes,
    required this.state,
  });

  final String title;
  final List<GoalGraphOverlayNode> nodes;
  final GoalGraphNodeState state;

  @override
  Widget build(BuildContext context) {
    if (nodes.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurface,
                  fontWeight: FontWeight.w700,
                ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: nodes
                .map(
                  (node) => _NodeChip(
                    node: node,
                    state: state,
                    onTap: () => _showNodeDetails(context, node),
                  ),
                )
                .toList(growable: false),
          ),
        ],
      ),
    );
  }
}

class _NodeChip extends StatelessWidget {
  const _NodeChip({
    required this.node,
    required this.state,
    required this.onTap,
  });

  final GoalGraphOverlayNode node;
  final GoalGraphNodeState state;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = _stateColor(scheme, state);
    return Semantics(
      button: true,
      label: context.l10n.goalGraphNodeSemantics(node.label),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(maxWidth: 168),
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: color.withValues(alpha: 0.48)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                node.label,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: scheme.onSurface,
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 5),
              LinearProgressIndicator(
                value: node.mastery.clamp(0, 1),
                minHeight: 4,
                backgroundColor: scheme.surfaceContainerHighest,
                color: color,
              ),
              const SizedBox(height: 4),
              Text(
                context.l10n.goalGraphMasteryPercent(
                  (node.mastery * 100).round(),
                ),
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: scheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NoGoalState extends StatelessWidget {
  const _NoGoalState();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Text(
        context.l10n.goalGraphNoGoal,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: scheme.onSurfaceVariant,
            ),
      ),
    );
  }
}

class _EmptyGraphState extends StatelessWidget {
  const _EmptyGraphState();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: Text(
        context.l10n.goalGraphEmpty,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: scheme.onSurfaceVariant,
            ),
      ),
    );
  }
}

void _showNodeDetails(BuildContext context, GoalGraphOverlayNode node) {
  final scheme = Theme.of(context).colorScheme;
  unawaited(
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      backgroundColor: scheme.surface,
      builder: (context) => Padding(
        padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              node.label,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: scheme.onSurface,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 12),
            _DetailRow(
              label: context.l10n.goalGraphNodeType,
              value: node.nodeType,
            ),
            _DetailRow(
              label: context.l10n.goalGraphMastery,
              value: context.l10n.goalGraphMasteryPercent(
                (node.mastery * 100).round(),
              ),
            ),
            if ((node.relationship ?? '').isNotEmpty)
              _DetailRow(
                label: context.l10n.goalGraphRelationship,
                value: node.relationship!,
              ),
            if (node.examWeight != null)
              _DetailRow(
                label: context.l10n.goalGraphExamWeight,
                value: context.l10n.goalGraphPercentValue(
                  (node.examWeight! * 100).round(),
                ),
              ),
            if (node.difficulty != null)
              _DetailRow(
                label: context.l10n.goalGraphDifficulty,
                value: context.l10n.goalGraphPercentValue(
                  (node.difficulty! * 100).round(),
                ),
              ),
            if (node.trainability != null)
              _DetailRow(
                label: context.l10n.goalGraphTrainability,
                value: context.l10n.goalGraphPercentValue(
                  (node.trainability! * 100).round(),
                ),
              ),
            if (node.mistakes != null)
              _DetailRow(
                label: context.l10n.goalGraphMistakes,
                value: node.mistakes.toString(),
              ),
          ],
        ),
      ),
    ),
  );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 96,
            child: Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: scheme.onSurfaceVariant,
                  ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: scheme.onSurface,
                    height: 1.35,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

Color _stateColor(ColorScheme scheme, GoalGraphNodeState state) {
  switch (state) {
    case GoalGraphNodeState.bottleneck:
      return scheme.error;
    case GoalGraphNodeState.mastered:
      return scheme.primary;
    case GoalGraphNodeState.learning:
      return scheme.tertiary;
  }
}
