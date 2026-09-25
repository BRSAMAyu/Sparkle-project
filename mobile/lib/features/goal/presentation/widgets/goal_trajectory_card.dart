import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/goal/presentation/providers/goal_trajectory_provider.dart';

/// J-08 · Goal 页「从想法到成果」轨迹卡。
///
/// 数据源 = `/journey/trajectory`（后端 goal_trajectory_service 只读投影），
/// 与星图面（GalaxyNodeModel.outcomeEvidenceIds / graph_event_sources）读
/// 同一批 outcome id——同一成果两面呈现数据同源。
///
/// 价值叙事 = 证据与成果（成果数/证据数/反思数/点亮节点数），刻意不展示
/// 分钟/streak（卡面 work 3：时长统计不作主叙事）。反思行只回声用户自报
/// 内容（stuck_point 等），零性格推断。
class GoalTrajectoryCard extends ConsumerWidget {
  const GoalTrajectoryCard({required this.goalId, super.key});

  final String goalId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final trajectory = ref.watch(goalTrajectoryProvider(goalId));
    final l10n = context.l10n;
    return trajectory.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (data) {
        if (!data.hasAnyProgress) {
          // 空态不渲染空壳卡：完成第一步后轨迹才有内容。
          return const SizedBox.shrink();
        }
        return _TrajectorySection(
          title: l10n.goalTrajectoryTitle,
          children: [
            _IdeaLine(idea: data.idea),
            const SizedBox(height: DS.spacing12),
            ..._milestoneRows(context, data),
            ..._outcomeRows(context, data),
            ..._reflectionRows(context, data),
            if (data.galaxyNodesLit > 0) ...[
              const SizedBox(height: DS.spacing8),
              _TrajectoryRow(
                icon: Icons.auto_awesome,
                text: l10n.goalTrajectoryGalaxyLit(data.galaxyNodesLit),
                iconColor: DS.success,
                emphasized: true,
              ),
            ],
            const SizedBox(height: DS.spacing12),
            Text(
              l10n.goalTrajectoryValueSummary(
                data.outcomesFormed,
                data.reflectionsCount,
                data.experienceCandidatesCount,
              ),
              style: DS.labelLarge.copyWith(color: DS.textSecondary),
            ),
          ],
        );
      },
    );
  }

  List<Widget> _milestoneRows(BuildContext context, GoalTrajectoryData data) =>
      [
        for (final milestone in data.milestones.take(4))
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: _TrajectoryRow(
              icon: milestone.reached
                  ? Icons.check_circle
                  : Icons.radio_button_unchecked,
              text: '${milestone.title} · '
                  '${milestone.reached ? context.l10n.goalTrajectoryMilestoneReached : context.l10n.goalTrajectoryMilestoneOngoing}',
              iconColor: milestone.reached ? DS.success : DS.textTertiary,
              emphasized: milestone.reached,
            ),
          ),
      ];

  List<Widget> _outcomeRows(BuildContext context, GoalTrajectoryData data) =>
      [
        for (final outcome
            in data.outcomes.where((o) => o.ledgerVerified).take(3))
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: _TrajectoryRow(
              icon: outcome.isNegative
                  ? Icons.flag_outlined
                  : Icons.verified_outlined,
              text: '${outcome.taskTitle} · '
                  '${context.l10n.goalTrajectoryEvidenceCount(outcome.evidenceCount)}',
              iconColor:
                  outcome.isNegative ? DS.textTertiary : DS.success,
              emphasized: !outcome.isNegative,
            ),
          ),
      ];

  List<Widget> _reflectionRows(BuildContext context, GoalTrajectoryData data) =>
      [
        for (final reflection
            in data.reflections.where((r) => r.hasContent).take(2))
          Padding(
            padding: const EdgeInsets.only(bottom: DS.spacing8),
            child: _TrajectoryRow(
              icon: Icons.chat_bubble_outline,
              text: context.l10n.goalTrajectoryReflectionLine(
                reflection.stuckPoint ?? '',
              ),
              iconColor: DS.textTertiary,
              emphasized: false,
            ),
          ),
      ];
}

class _TrajectorySection extends StatelessWidget {
  const _TrajectorySection({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.timeline, color: DS.brandPrimary),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    title,
                    style: DS.titleMedium.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),
            ...children,
          ],
        ),
      );
}

class _IdeaLine extends StatelessWidget {
  const _IdeaLine({required this.idea});

  final GoalTrajectoryIdea idea;

  @override
  Widget build(BuildContext context) {
    final motivation = idea.motivation?.trim();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          idea.title,
          style: DS.bodyMedium.copyWith(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        if (motivation != null && motivation.isNotEmpty) ...[
          const SizedBox(height: DS.spacing4),
          Text(
            motivation,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ],
    );
  }
}

class _TrajectoryRow extends StatelessWidget {
  const _TrajectoryRow({
    required this.icon,
    required this.text,
    required this.iconColor,
    required this.emphasized,
  });

  final IconData icon;
  final String text;
  final Color iconColor;
  final bool emphasized;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: DS.iconSizeXs, color: iconColor),
          const SizedBox(width: DS.spacing8),
          Expanded(
            child: Text(
              text,
              style: DS.bodyMedium.copyWith(
                color: emphasized ? DS.textPrimary : DS.textSecondary,
              ),
            ),
          ),
        ],
      );
}
