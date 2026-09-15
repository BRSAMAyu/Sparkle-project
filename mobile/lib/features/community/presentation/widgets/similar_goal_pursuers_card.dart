import 'package:cached_network_image/cached_network_image.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/goal_value_chip.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';

/// Model for a user pursuing a similar goal.
class SimilarGoalPursuer {
  const SimilarGoalPursuer({
    required this.userId,
    required this.displayName,
    required this.goalTitle,
    this.avatarUrl,
    this.goalType = 'general',
    this.goalProgress = 0.0,
    this.similarity = 0.0,
    this.lastActive,
    this.mutualFriendsCount = 0,
  });

  factory SimilarGoalPursuer.fromJson(Map<String, dynamic> json) =>
      SimilarGoalPursuer(
        userId: json['user_id'] as String,
        displayName: json['display_name'] as String,
        goalTitle: json['goal_title'] as String,
        avatarUrl: json['avatar_url'] as String?,
        goalType: json['goal_type'] as String? ?? 'general',
        goalProgress: (json['goal_progress'] as num?)?.toDouble() ?? 0.0,
        similarity: (json['similarity'] as num?)?.toDouble() ?? 0.0,
        lastActive: json['last_active'] as String?,
        mutualFriendsCount:
            (json['mutual_friends_count'] as num?)?.toInt() ?? 0,
      );

  final String userId;
  final String displayName;
  final String? avatarUrl;
  final String goalTitle;
  final String goalType;
  final double goalProgress;
  final double similarity;
  final String? lastActive;
  final int mutualFriendsCount;
}

/// Provider that fetches similar goal pursuers.
final similarGoalPursuersProvider = FutureProvider.family
    .autoDispose<List<SimilarGoalPursuer>, String>((ref, goalId) async {
  final apiClient = ref.watch(apiClientProvider);
  final response = await apiClient.get<dynamic>(
    ApiEndpoints.similarGoalPursuers(goalId),
  );

  final data = response.data;
  if (data is! List) return [];

  return data
      .whereType<Map<Object?, Object?>>()
      .map(
        (item) => SimilarGoalPursuer.fromJson(Map<String, dynamic>.from(item)),
      )
      .toList();
});

/// Card showing users pursuing similar goals.
///
/// Displays up to 5 avatar chips with progress rings,
/// a "查看全部" button, and friend/group invite actions.
class SimilarGoalPursuersCard extends ConsumerWidget {
  const SimilarGoalPursuersCard({
    required this.goalId,
    super.key,
    this.onViewAll,
    this.onAddFriend,
  });

  final String goalId;
  final VoidCallback? onViewAll;
  final void Function(String userId)? onAddFriend;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = context.l10n;
    final pursuersAsync = ref.watch(similarGoalPursuersProvider(goalId));

    return Semantics(
      container: true,
      label: l10n.communitySimilarGoalPursuers,
      child: pursuersAsync.when(
        data: (pursuers) {
          if (pursuers.isEmpty) return const SizedBox.shrink();

          final display = pursuers.take(5).toList();

          return Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: DS.borderRadius12,
              border: Border.all(color: DS.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.group_outlined,
                        size: 16, color: DS.brandPrimary),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        l10n.communitySimilarGoalPursuersCount(pursuers.length),
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              fontWeight: FontWeight.w600,
                              color: DS.brandPrimary,
                            ),
                      ),
                    ),
                  ],
                ),
                if (pursuers.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  GoalValueChip(text: pursuers.first.goalTitle),
                ],
                const SizedBox(height: 10),
                // Avatar row
                SizedBox(
                  height: 64,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: display.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 10),
                    itemBuilder: (context, index) => _PursuerChip(
                      pursuer: display[index],
                      onTap: () => unawaited(
                        _handlePursuerTap(context, ref, display[index]),
                      ),
                    ),
                  ),
                ),
                if (pursuers.length > 5 || onViewAll != null) ...[
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: onViewAll ??
                          () => _showAllPursuers(context, ref, pursuers),
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      child: Text(
                        l10n.communityViewAll,
                        style: TextStyle(fontSize: 12, color: DS.brandPrimary),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          );
        },
        loading: () => const SizedBox.shrink(),
        error: (_, __) => CompactErrorCard(
          onRetry: () => ref.invalidate(similarGoalPursuersProvider(goalId)),
        ),
      ),
    );
  }

  Future<void> _handlePursuerTap(
    BuildContext context,
    WidgetRef ref,
    SimilarGoalPursuer pursuer,
  ) async {
    if (onAddFriend != null) {
      onAddFriend!(pursuer.userId);
      return;
    }
    final l10n = context.l10n;
    try {
      await ref.read(communityRepositoryProvider).sendFriendRequest(
            pursuer.userId,
            message: l10n.communitySimilarGoalConnectMessage,
          );
      if (!context.mounted) return;
      AppFeedback.success(
        context,
        l10n.communityFriendRequestSent,
      );
    } catch (error) {
      if (!context.mounted) return;
      AppFeedback.error(
        context,
        l10n.communityFriendRequestFailed,
      );
    }
  }

  void _showAllPursuers(
    BuildContext context,
    WidgetRef ref,
    List<SimilarGoalPursuer> pursuers,
  ) {
    final l10n = context.l10n;
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        builder: (sheetContext) => SafeArea(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            itemCount: pursuers.length + 1,
            separatorBuilder: (_, index) =>
                index == 0 ? const SizedBox.shrink() : const Divider(height: 1),
            itemBuilder: (context, index) {
              if (index == 0) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    l10n.communitySimilarGoalPursuers,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                );
              }
              final pursuer = pursuers[index - 1];
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: _ProgressAvatar(pursuer: pursuer, size: 44),
                title: Text(pursuer.displayName),
                subtitle: Text(
                  '${pursuer.goalTitle} · ${(pursuer.goalProgress * 100).round()}%',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: TextButton(
                  onPressed: () {
                    Navigator.of(sheetContext).pop();
                    unawaited(_handlePursuerTap(context, ref, pursuer));
                  },
                  child: Text(l10n.communityAddFriend),
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

/// Single pursuer chip with avatar, progress ring, and name.
class _PursuerChip extends StatelessWidget {
  const _PursuerChip({
    required this.pursuer,
    this.onTap,
  });

  final SimilarGoalPursuer pursuer;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;

    return InkWell(
      onTap: onTap,
      borderRadius: DS.borderRadius8,
      child: SizedBox(
        width: 64,
        child: Column(
          children: [
            _ProgressAvatar(pursuer: pursuer),
            const SizedBox(height: 4),
            Text(
              pursuer.displayName,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    fontSize: 10,
                  ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
            ),
            if (pursuer.mutualFriendsCount > 0)
              Text(
                l10n.communityMutualFriendsCount(pursuer.mutualFriendsCount),
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      fontSize: 8,
                      color: DS.textTertiary,
                    ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
          ],
        ),
      ),
    );
  }
}

class _ProgressAvatar extends StatelessWidget {
  const _ProgressAvatar({
    required this.pursuer,
    this.size = 40,
  });

  final SimilarGoalPursuer pursuer;
  final double size;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: size,
        height: size,
        child: Stack(
          alignment: Alignment.center,
          children: [
            CircularProgressIndicator(
              value: pursuer.goalProgress.clamp(0.0, 1.0),
              strokeWidth: 2,
              backgroundColor: DS.border,
              valueColor: AlwaysStoppedAnimation<Color>(DS.brandPrimary),
            ),
            CircleAvatar(
              radius: (size / 2) - 5,
              backgroundColor: DS.surfaceTertiary,
              backgroundImage: pursuer.avatarUrl != null
                  ? CachedNetworkImageProvider(pursuer.avatarUrl!)
                  : null,
              child: pursuer.avatarUrl == null
                  ? Text(
                      pursuer.displayName.isNotEmpty
                          ? pursuer.displayName[0].toUpperCase()
                          : '?',
                      style: const TextStyle(fontSize: 12),
                    )
                  : null,
            ),
          ],
        ),
      );
}
