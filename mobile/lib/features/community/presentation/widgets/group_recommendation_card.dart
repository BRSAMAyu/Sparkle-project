import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';

class GroupRecommendationCard extends StatelessWidget {
  const GroupRecommendationCard({
    required this.recommendation,
    super.key,
    this.onTap,
    this.onJoin,
    this.onDismiss,
    this.onFeedback,
  });

  final GroupRecommendationItem recommendation;
  final VoidCallback? onTap;
  final VoidCallback? onJoin;
  final VoidCallback? onDismiss;
  final VoidCallback? onFeedback;

  @override
  Widget build(BuildContext context) {
    final group = recommendation.group;
    final isSprint = group.isSprint;
    final reasons = recommendation.reasons.take(2).toList();
    final joinLabel = recommendation.requiresApproval ? 'Apply' : 'Join';

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: context.space.edge(all: context.space.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Icon(
                        isSprint ? Icons.timer_outlined : Icons.group_outlined,
                        color: DS.textSecondary,
                      ),
                    ),
                    SizedBox(width: context.space.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            isSprint ? 'Sprint group' : 'Squad',
                            style: context.typo.labelSmall
                                .copyWith(color: DS.textSecondary),
                          ),
                          SizedBox(height: context.space.xs),
                          Text(
                            group.name,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          SizedBox(height: context.space.xs),
                          Text(
                            '${group.memberCount} members | ${group.totalFlamePower} flame',
                            style: context.typo.bodyMedium
                                .copyWith(color: DS.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    if (onDismiss != null)
                      SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        icon: const Icon(Icons.close),
                        onPressed: onDismiss,
                      ),
                  ],
                ),
                if (reasons.isNotEmpty) ...[
                  SizedBox(height: context.space.sm),
                  Wrap(
                    spacing: context.space.xs,
                    runSpacing: context.space.xs,
                    children: reasons
                        .map(
                          (reason) => SemanticPill(
                            label: _reasonLabel(reason),
                            tone: _reasonTone(reason),
                            icon: _reasonIcon(reason),
                            dense: true,
                          ),
                        )
                        .toList(),
                  ),
                ],
                if (group.description != null &&
                    group.description!.isNotEmpty) ...[
                  SizedBox(height: context.space.sm),
                  Text(
                    group.description!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: context.typo.bodyMedium
                        .copyWith(color: DS.textSecondary, height: 1.35),
                  ),
                ],
                SizedBox(height: context.space.md),
                Row(
                  children: [
                    if (group.focusTags.isNotEmpty)
                      Expanded(
                        child: Text(
                          group.focusTags.take(2).join(' / '),
                          style: context.typo.bodyMedium
                              .copyWith(color: DS.textSecondary),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      )
                    else
                      const Spacer(),
                    if (onFeedback != null) ...[
                      SparkleButton(
                        label: '评价',
                        size: ButtonSize.small,
                        variant: ButtonVariant.secondary,
                        onPressed: onFeedback,
                      ),
                      SizedBox(width: context.space.xs),
                    ],
                    SparkleButton(
                      label: joinLabel,
                      size: ButtonSize.small,
                      onPressed: onJoin,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _reasonLabel(GroupRecommendationReason reason) {
    switch (reason.type) {
      case 'friend_overlap':
        final count = (reason.data?['friend_count'] as num?)?.toInt() ?? 0;
        return count > 0 ? '$count friends inside' : 'Friends inside';
      case 'tag_overlap':
        final tags = reason.data?['tags'];
        if (tags is List && tags.isNotEmpty) {
          return 'Matches: ${tags.take(2).join('/')}';
        }
        return 'Matches your focus';
      case 'trending':
        return 'Trending now';
      case 'fresh':
        return 'New group';
      case 'approval_required':
        return 'Approval needed';
      default:
        return 'Recommended';
    }
  }

  IconData? _reasonIcon(GroupRecommendationReason reason) {
    switch (reason.type) {
      case 'friend_overlap':
        return Icons.group_outlined;
      case 'tag_overlap':
        return Icons.auto_awesome;
      case 'trending':
        return Icons.local_fire_department_outlined;
      case 'fresh':
        return Icons.fiber_new_outlined;
      case 'approval_required':
        return Icons.verified_outlined;
      default:
        return null;
    }
  }

  PillTone _reasonTone(GroupRecommendationReason reason) {
    switch (reason.type) {
      case 'friend_overlap':
        return PillTone.success;
      case 'tag_overlap':
        return PillTone.brand;
      case 'trending':
        return PillTone.warning;
      case 'fresh':
        return PillTone.info;
      case 'approval_required':
        return PillTone.neutral;
      default:
        return PillTone.neutral;
    }
  }
}
