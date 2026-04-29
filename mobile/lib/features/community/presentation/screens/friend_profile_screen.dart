import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';

class FriendProfileScreen extends ConsumerStatefulWidget {
  const FriendProfileScreen({
    required this.userId,
    this.displayName,
    super.key,
  });
  final String userId;
  final String? displayName;

  @override
  ConsumerState<FriendProfileScreen> createState() =>
      _FriendProfileScreenState();
}

class _FriendProfileScreenState extends ConsumerState<FriendProfileScreen> {
  late Future<FriendProfileDetail> _profileFuture;

  @override
  void initState() {
    super.initState();
    _profileFuture =
        ref.read(communityRepositoryProvider).getFriendProfile(widget.userId);
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.content,
        appBar: AppBar(
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(widget.displayName ?? context.l10n.fpTitle),
        ),
        child: FutureBuilder<FriendProfileDetail>(
          future: _profileFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return _buildContent(
                context,
                FriendProfileDetail(
                  user: UserBrief(
                    id: widget.userId,
                    username: widget.displayName ?? context.l10n.fpDefaultName,
                    nickname: widget.displayName,
                  ),
                  friendship: const <String, dynamic>{},
                  quickActions: const {
                    'can_invite_accountability': false,
                    'can_open_dashboard': false,
                    'can_chat': true,
                    'can_share': false,
                  },
                ),
              );
            }
            final profile = snapshot.data!;
            return _buildContent(context, profile);
          },
        ),
      );

  Widget _buildContent(BuildContext context, FriendProfileDetail profile) {
    final theme = Theme.of(context);
    final user = profile.user;
    final relationshipSummary = profile.relationshipSummary ?? const {};
    final achievementsSummary = profile.achievementsSummary ?? const {};
    final leaderboardSummary = profile.leaderboardSummary ?? const {};
    final accountability = profile.accountability ?? const {};
    final quickActions = profile.quickActions;
    final partnershipId =
        (accountability['id'] ?? accountability['partnership_id'])?.toString();
    final canOpenDashboard =
        quickActions['can_open_dashboard'] == true && partnershipId != null;
    final canInviteAccountability =
        quickActions['can_invite_accountability'] != false;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(DS.spacing24),
      child: Column(
        children: [
          SparkleStaggerItem(
            index: 0,
            motionToken: SparkleMotionToken.scene,
            child: Column(
              children: [
                const SizedBox(height: DS.spacing16),
                SparkleAttentionPulse(
                  glowColor: DS.brandPrimary,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: DS.brandPrimaryConst, width: 3),
                      boxShadow: DS.shadowMd,
                    ),
                    child: SparkleAvatar(
                      radius: 48,
                      url: user.avatarUrl,
                      fallbackText: user.displayName,
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                Text(
                  user.displayName,
                  style: theme.textTheme.headlineSmall
                      ?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: DS.xs),
                Text(
                  '@${user.username}',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: DS.textSecondary),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          SparkleStaggerItem(
            index: 1,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing12,
                vertical: DS.xs,
              ),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: DS.brandPrimary.withValues(alpha: 0.3),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.local_fire_department,
                    size: 16,
                    color: DS.brandPrimaryConst,
                  ),
                  const SizedBox(width: DS.xs),
                  Text(
                    'Flame Lv.${user.flameLevel}',
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontWeight: DS.fontWeightSemibold,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: DS.spacing24),
          if (accountability.isNotEmpty) ...[
            SparkleStaggerItem(
              index: 2,
              child: _SimplePanel(
                title: context.l10n.fpPartnerGoals,
                icon: Icons.flag_outlined,
                body: Text(
                  (accountability['partner_goal'] ??
                          accountability['initiator_goal'] ??
                          context.l10n.fpNoSyncedGoals)
                      .toString(),
                  style: DS.bodyMedium,
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
          ],
          if (relationshipSummary.isNotEmpty || achievementsSummary.isNotEmpty)
            SparkleStaggerItem(
              index: 3,
              child: _RelationshipPanel(
                relationshipSummary: relationshipSummary,
                achievementsSummary: achievementsSummary,
                leaderboardSummary: leaderboardSummary,
                recentShares: profile.recentShares,
                hasAccountability: accountability.isNotEmpty,
              ),
            ),
          const SizedBox(height: DS.spacing24),
          SparkleStaggerItem(
            index: 4,
            child: Row(
              children: [
                Expanded(
                  child: CustomButton.primary(
                    text: context.l10n.fpChat,
                    icon: Icons.chat_bubble_outline,
                    onPressed: () {
                      context.push(
                        '/chat/private/${user.id}?name=${Uri.encodeComponent(user.displayName)}',
                      );
                    },
                  ),
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: CustomButton.secondary(
                    text: canOpenDashboard ? context.l10n.fpEnterWorkbench : context.l10n.fpViewAchievements,
                    icon: canOpenDashboard
                        ? Icons.handshake_outlined
                        : Icons.emoji_events_outlined,
                    onPressed: () {
                      if (canOpenDashboard) {
                        context.push(
                          CommunityRoutes.accountabilityDetail
                              .replaceFirst(':id', partnershipId),
                        );
                      } else {
                        context.push('/achievements');
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.md),
          SparkleStaggerItem(
            index: 5,
            child: SizedBox(
              width: double.infinity,
              child: CustomButton.secondary(
                text: canInviteAccountability ? context.l10n.fpInviteAccountability : context.l10n.fpEnterPartnerWorkbench,
                icon: Icons.handshake_outlined,
                onPressed: () {
                  if (canInviteAccountability) {
                    _showAccountabilityInvite(context, user);
                    return;
                  }
                  final id = partnershipId;
                  if (id == null) return;
                  context.push(
                    CommunityRoutes.accountabilityDetail
                        .replaceFirst(':id', id),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _showAccountabilityInvite(
    BuildContext context,
    UserBrief user,
  ) async {
    final goalController = TextEditingController();
    var checkInDays = 1;

    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: Text(context.l10n.fpInviteDialogTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.fpInviteMessage(user.displayName),
                style: TextStyle(color: DS.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: DS.spacing16),
              TextField(
                controller: goalController,
                decoration: InputDecoration(
                  labelText: context.l10n.fpMyGoal,
                  hintText: context.l10n.communityFriendGoalHint,
                  border: const OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                context.l10n.fpCheckinFrequency,
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.xs),
              Wrap(
                spacing: DS.sm,
                children: [1, 2, 3, 7].map((d) {
                  final selected = checkInDays == d;
                  return FilterChip(
                    label: Text(d == 1 ? context.l10n.fpEveryDay : context.l10n.fpEveryNDays(d)),
                    selected: selected,
                    onSelected: (_) => setState(() => checkInDays = d),
                  );
                }).toList(),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: Text(context.l10n.fpCancel),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(context.l10n.fpSendInvite),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return;
    final goal = goalController.text.trim();
    if (goal.isEmpty) {
      if (context.mounted) AppFeedback.info(context, context.l10n.fpGoalRequired);
      return;
    }

    try {
      await ref.read(myPartnershipsProvider.notifier).requestPartnership(
            partnerId: user.id,
            initiatorGoal: goal,
            checkInDays: checkInDays,
          );
      ref.invalidate(accountabilityOverviewProvider);
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.fpInviteSent);
      }
    } catch (e) {
      if (context.mounted) AppFeedback.error(context, context.l10n.fpInviteFailed(e.toString()));
    }
  }
}

class _RelationshipPanel extends StatelessWidget {
  const _RelationshipPanel({
    required this.relationshipSummary,
    required this.achievementsSummary,
    required this.leaderboardSummary,
    required this.recentShares,
    required this.hasAccountability,
  });

  final Map<String, dynamic> relationshipSummary;
  final Map<String, dynamic> achievementsSummary;
  final Map<String, dynamic> leaderboardSummary;
  final List<Map<String, dynamic>> recentShares;
  final bool hasAccountability;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.18),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  hasAccountability
                      ? Icons.handshake_outlined
                      : Icons.people_outline,
                  color: DS.brandPrimary,
                ),
                const SizedBox(width: 8),
                Text(
                  hasAccountability ? context.l10n.fpAccountabilityRelation : context.l10n.fpFriendRelation,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _InfoChip(context.l10n.fpDaysTogether((relationshipSummary['days_together'] ?? 0) as int)),
                _InfoChip(context.l10n.fpMyStreak((relationshipSummary['my_streak_days'] ?? 0) as int)),
                _InfoChip(
                  context.l10n.fpPartnerStreak((relationshipSummary['partner_streak_days'] ?? 0) as int),
                ),
              ],
            ),
            if (achievementsSummary.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                context.l10n.fpGrowTogether,
                style: DS.labelLarge.copyWith(fontWeight: DS.fontWeightBold),
              ),
              const SizedBox(height: 6),
              Text(
                context.l10n.fpAchievementSummary((achievementsSummary['my_total_unlocked'] ?? 0) as int, (achievementsSummary['partner_total_unlocked'] ?? 0) as int),
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
            ],
            if (leaderboardSummary.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                context.l10n.fpMotivationSummary,
                style: DS.labelLarge.copyWith(fontWeight: DS.fontWeightBold),
              ),
              const SizedBox(height: 6),
              Text(
                context.l10n.fpStreakLeaderboard('${(leaderboardSummary['streak'] as Map?)?['my_rank'] ?? '-'}', '${(leaderboardSummary['streak'] as Map?)?['partner_rank'] ?? '-'}'),
                style: DS.bodySmall.copyWith(color: DS.textSecondary),
              ),
            ],
            if (recentShares.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(
                context.l10n.fpRecentShares,
                style: DS.labelLarge.copyWith(fontWeight: DS.fontWeightBold),
              ),
              const SizedBox(height: 6),
              ...recentShares.take(2).map(
                    (share) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 5,
                            height: 5,
                            margin: const EdgeInsets.only(top: 7, right: 8),
                            decoration: BoxDecoration(
                              color: DS.textSecondary,
                              shape: BoxShape.circle,
                            ),
                          ),
                          Expanded(
                            child: Text(
                              share['title']?.toString() ?? context.l10n.fpSharedContent,
                              style: DS.bodySmall
                                  .copyWith(color: DS.textSecondary),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
            ],
          ],
        ),
      );
}

class _SimplePanel extends StatelessWidget {
  const _SimplePanel({
    required this.title,
    required this.icon,
    required this.body,
  });

  final String title;
  final IconData icon;
  final Widget body;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: DS.neutral200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: DS.brandPrimary),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            body,
          ],
        ),
      );
}

class _InfoChip extends StatelessWidget {
  const _InfoChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: DS.labelSmall.copyWith(
            color: DS.brandPrimary,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}
