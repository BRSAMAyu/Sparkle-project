import 'package:cached_network_image/cached_network_image.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/models/community_accountability_hub_model.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_hub_provider.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/experience/presentation/widgets/community_accountability_hub_card.dart';

/// Partners tab — the default landing view for the Community section.
///
/// Surfaces accountability partnerships, commitments, partner progress,
/// and friend discovery in a single scrollable list.
class PartnersTab extends ConsumerWidget {
  const PartnersTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final partnershipsAsync = ref.watch(myPartnershipsProvider);
    final hubAsync = ref.watch(accountabilityHubProvider);
    final friendsAsync = ref.watch(friendsProvider);

    return ContentConstraint(
      child: SparkleRefreshIndicator(
        onRefresh: () async {
          await ref.read(myPartnershipsProvider.notifier).load();
          ref.invalidate(accountabilityHubProvider);
          ref.invalidate(accountabilityOverviewProvider);
          await ref.read(friendsProvider.notifier).refresh();
        },
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            // Accountability hub card
            SliverToBoxAdapter(
              child: SparkleStaggerItem(
                index: 0,
                child: CommunityAccountabilityHubCard(
                  onCreateCommitment: () =>
                      context.push(CommunityRoutes.accountability),
                  onFindPartners: () => context.push(CommunityRoutes.friends),
                ),
              ),
            ),

            // Active partnerships
            SliverToBoxAdapter(
              child: SparkleStaggerItem(
                index: 1,
                child: partnershipsAsync.when(
                  data: (partnerships) {
                    final active = partnerships
                        .where((p) => p.status == AccountabilityStatus.active)
                        .toList();
                    if (active.isEmpty) return const SizedBox.shrink();
                    return _PartnershipsSection(
                      partnerships: active,
                      currentUserId: ref.watch(currentUserProvider)?.id ?? '',
                    );
                  },
                  loading: () => const Padding(
                    padding: EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.md),
                    child: SparkleListSkeleton(count: 2),
                  ),
                  error: (_, __) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: DS.lg),
                    child: CompactErrorCard(
                      onRetry: () => ref.invalidate(myPartnershipsProvider),
                    ),
                  ),
                ),
              ),
            ),

            // Hub data: commitments, progress, risks, helpable
            SliverToBoxAdapter(
              child: SparkleStaggerItem(
                index: 2,
                child: hubAsync.when(
                  data: (hub) {
                    if (hub.isEmpty) return const SizedBox.shrink();
                    return _HubSections(hub: hub);
                  },
                  loading: () => const Padding(
                    padding: EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.md),
                    child: SparkleListSkeleton(count: 2),
                  ),
                  error: (_, __) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: DS.lg),
                    child: CompactErrorCard(
                      onRetry: () => ref.invalidate(accountabilityHubProvider),
                    ),
                  ),
                ),
              ),
            ),

            // Friends list
            SliverToBoxAdapter(
              child: SparkleStaggerItem(
                index: 3,
                child: friendsAsync.when(
                  data: (friends) {
                    if (friends.isEmpty) return const SizedBox.shrink();
                    return _FriendsSection(friends: friends);
                  },
                  loading: () => const Padding(
                    padding: EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.md),
                    child: SparkleListSkeleton(count: 3),
                  ),
                  error: (_, __) => Padding(
                    padding: const EdgeInsets.symmetric(horizontal: DS.lg),
                    child: CompactErrorCard(
                      onRetry: () => ref.invalidate(friendsProvider),
                    ),
                  ),
                ),
              ),
            ),

            // Empty state when no partners/friends at all
            SliverToBoxAdapter(
              child: _buildEmptyIfNeeded(
                context,
                ref,
                partnershipsAsync,
                hubAsync,
                friendsAsync,
              ),
            ),

            const SliverPadding(padding: EdgeInsets.only(bottom: 80)),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyIfNeeded(
    BuildContext context,
    WidgetRef ref,
    AsyncValue<List<AccountabilityPartnershipInfo>> partnershipsAsync,
    AsyncValue<CommunityAccountabilityHub> hubAsync,
    AsyncValue<List<FriendshipInfo>> friendsAsync,
  ) {
    final hasPartners = partnershipsAsync.valueOrNull
            ?.any((p) => p.status == AccountabilityStatus.active) ??
        false;
    final hasHubData = !(hubAsync.valueOrNull?.isEmpty ?? true);
    final hasFriends = friendsAsync.valueOrNull?.isNotEmpty ?? false;

    if (hasPartners || hasHubData || hasFriends) return const SizedBox.shrink();

    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing32),
      child: EmptyState(
        title: zh ? '找到你的学习伙伴' : 'Find your study partners',
        description: zh
            ? '和一个目标相近的伙伴结对，互相监督，坚持率翻倍。'
            : 'Pair up with someone pursuing similar goals. Accountability doubles consistency.',
        icon: Icons.handshake_outlined,
        actionText: zh ? '发现伙伴' : 'Discover partners',
        onAction: () => unawaited(context.push(CommunityRoutes.friends)),
      ),
    );
  }
}

// ─── Subsections ────────────────────────────────────────────────────────────

class _PartnershipsSection extends StatelessWidget {
  const _PartnershipsSection({required this.partnerships, required this.currentUserId});
  final List<AccountabilityPartnershipInfo> partnerships;
  final String currentUserId;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.md, DS.lg, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SectionTitle(
            icon: Icons.people_rounded,
            title: zh ? '我的伙伴' : 'My Partners',
          ),
          const SizedBox(height: DS.sm),
          ...partnerships.map((p) => _PartnershipCard(partnership: p, currentUserId: currentUserId)),
        ],
      ),
    );
  }
}

class _PartnershipCard extends StatelessWidget {
  const _PartnershipCard({required this.partnership, required this.currentUserId});
  final AccountabilityPartnershipInfo partnership;
  final String currentUserId;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final isInitiator = partnership.initiatorId == currentUserId;
    final partner = isInitiator ? partnership.partner : partnership.initiator;
    final goalLabel = isInitiator
        ? (partnership.partnerGoal ?? partnership.initiatorGoal)
        : partnership.initiatorGoal;
    final streak = partnership.myStreakDays ?? 0;
    final partnerCheckedIn = partnership.partnerCheckedInToday ?? false;

    return Padding(
      padding: const EdgeInsets.only(bottom: DS.sm),
      child: GestureDetector(
        onTap: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          unawaited(
            context.push(
              CommunityRoutes.accountabilityDetail
                  .replaceFirst(':id', partnership.id),
            ),
          );
        },
        child: Semantics(
          button: true,
          label: '${partner?.nickname ?? (zh ? "伙伴" : "Partner")}, $streak day streak',
          child: Container(
            padding: const EdgeInsets.all(DS.md),
            decoration: BoxDecoration(
              color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
              borderRadius: BorderRadius.circular(DS.radius12),
              border: Border.all(color: DS.borderSubtle),
            ),
            child: Row(
              children: [
                _PartnerAvatar(
                  avatarUrl: partner?.avatarUrl,
                  name: partner?.nickname ?? partner?.username ?? '?',
                  isOnline: partnerCheckedIn,
                ),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        partner?.nickname ??
                            partner?.username ??
                            (zh ? '伙伴' : 'Partner'),
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: DS.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        goalLabel,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    if (streak > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing8,
                          vertical: DS.spacing4,
                        ),
                        decoration: BoxDecoration(
                          color: DS.warning.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(DS.radius8),
                        ),
                        child: Text(
                          '$streak ${zh ? '天连续' : 'd streak'}',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: DS.warning,
                          ),
                        ),
                      ),
                    const SizedBox(height: 4),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color:
                                partnerCheckedIn ? DS.success : DS.textTertiary,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          partnerCheckedIn
                              ? (zh ? '今日已打卡' : 'Checked in')
                              : (zh ? '今日未打卡' : 'Not yet today'),
                          style: TextStyle(
                            fontSize: 11,
                            color:
                                partnerCheckedIn ? DS.success : DS.textTertiary,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _HubSections extends StatelessWidget {
  const _HubSections({required this.hub});
  final CommunityAccountabilityHub hub;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.md, DS.lg, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Commitments
          if (hub.myCommitments.isNotEmpty) ...[
            _SectionTitle(
              icon: Icons.flag_rounded,
              title: zh ? '我的承诺' : 'My Commitments',
            ),
            const SizedBox(height: DS.sm),
            ...hub.myCommitments.map((c) => _CommitmentCard(commitment: c)),
            const SizedBox(height: DS.md),
          ],

          // Partner progress
          if (hub.partnerProgress.isNotEmpty) ...[
            _SectionTitle(
              icon: Icons.trending_up_rounded,
              title: zh ? '伙伴进度' : 'Partner Progress',
            ),
            const SizedBox(height: DS.sm),
            ...hub.partnerProgress.map((p) => _ProgressCard(item: p)),
            const SizedBox(height: DS.md),
          ],

          // Needs attention (squad risks)
          if (hub.squadRisks.isNotEmpty) ...[
            _SectionTitle(
              icon: Icons.warning_amber_rounded,
              title: zh ? '需要关注' : 'Needs Attention',
            ),
            const SizedBox(height: DS.sm),
            ...hub.squadRisks.map((r) => _RiskCard(item: r)),
            const SizedBox(height: DS.md),
          ],

          // Helpable partners
          if (hub.helpable.isNotEmpty) ...[
            _SectionTitle(
              icon: Icons.favorite_outline,
              title: zh ? '鼓励一下' : 'Encourage',
            ),
            const SizedBox(height: DS.sm),
            ...hub.helpable.map((h) => _HelpableCard(item: h)),
          ],
        ],
      ),
    );
  }
}

class _CommitmentCard extends StatelessWidget {
  const _CommitmentCard({required this.commitment});
  final CommitmentCardPayload commitment;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.sm),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              commitment.summary,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontWeight: FontWeight.w500,
                color: DS.textPrimary,
              ),
            ),
            const SizedBox(height: DS.sm),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: commitment.progress,
                backgroundColor: DS.surfaceTertiary,
                valueColor: AlwaysStoppedAnimation(DS.brandPrimary),
                minHeight: 4,
              ),
            ),
            const SizedBox(height: DS.spacing4),
            Text(
              '${(commitment.progress * 100).toStringAsFixed(0)}%',
              style: TextStyle(fontSize: 11, color: DS.textTertiary),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProgressCard extends StatelessWidget {
  const _ProgressCard({required this.item});
  final PartnerProgressItem item;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.sm),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.partnerName,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: DS.textPrimary,
                    ),
                  ),
                  Text(
                    item.goalSummary,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12, color: DS.textSecondary),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${(item.weeklyProgress * 100).toStringAsFixed(0)}%',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                    color: item.todayDone ? DS.success : DS.textSecondary,
                  ),
                ),
                Text(
                  item.todayDone
                      ? (zh ? '今日完成' : 'Done today')
                      : (zh ? '今日未完成' : 'Pending'),
                  style: TextStyle(
                    fontSize: 11,
                    color: item.todayDone ? DS.success : DS.textTertiary,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _RiskCard extends StatelessWidget {
  const _RiskCard({required this.item});
  final SquadRiskItem item;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    final severityColor = switch (item.severity) {
      'high' => DS.error,
      'medium' => DS.warning,
      _ => DS.textSecondary,
    };
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.sm),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: severityColor.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(color: severityColor.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: severityColor, size: 20),
            const SizedBox(width: DS.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.memberName,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: DS.textPrimary,
                    ),
                  ),
                  Text(
                    item.reason,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12, color: DS.textSecondary),
                  ),
                ],
              ),
            ),
            SparkleButton.ghost(
              label: zh ? '关心' : 'Nudge',
              onPressed: () => unawaited(
                context.push(
                  CommunityRoutes.accountabilityDetail
                      .replaceFirst(':id', item.partnershipId),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HelpableCard extends StatelessWidget {
  const _HelpableCard({required this.item});
  final HelpableItem item;

  @override
  Widget build(BuildContext context) {
    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.sm),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          borderRadius: BorderRadius.circular(DS.radius12),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Icon(Icons.favorite_outline, color: DS.brandPrimary, size: 20),
            const SizedBox(width: DS.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.memberName,
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: DS.textPrimary,
                    ),
                  ),
                  Text(
                    item.need,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12, color: DS.textSecondary),
                  ),
                ],
              ),
            ),
            SparkleButton.ghost(
              label: zh ? '鼓励' : 'Cheer',
              onPressed: () => unawaited(
                context.push(
                  CommunityRoutes.accountabilityDetail
                      .replaceFirst(':id', item.partnershipId),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FriendsSection extends ConsumerWidget {
  const _FriendsSection({required this.friends});
  final List<FriendshipInfo> friends;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final zh = I18nService.instance.isChinese;
    return Padding(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.md, DS.lg, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _SectionTitle(
                icon: Icons.group_outlined,
                title: zh ? '好友' : 'Friends',
              ),
              SparkleButton.ghost(
                label: zh ? '查看全部' : 'View all',
                onPressed: () =>
                    unawaited(context.push(CommunityRoutes.friends)),
              ),
            ],
          ),
          const SizedBox(height: DS.sm),
          ...friends.take(5).map((f) => _FriendTile(friend: f)),
          if (friends.length > 5)
            Padding(
              padding: const EdgeInsets.only(top: DS.sm),
              child: Center(
                child: SparkleButton.ghost(
                  label: zh
                      ? '还有 ${friends.length - 5} 位好友'
                      : '${friends.length - 5} more friends',
                  onPressed: () =>
                      unawaited(context.push(CommunityRoutes.friends)),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _FriendTile extends StatelessWidget {
  const _FriendTile({required this.friend});
  final FriendshipInfo friend;

  @override
  Widget build(BuildContext context) {
    final user = friend.friend;
    return Padding(
      padding: const EdgeInsets.only(bottom: DS.sm),
      child: GestureDetector(
        onTap: () {
          unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
          unawaited(
            context.push(CommunityRoutes.userProfile.replaceFirst(':id', user.id)),
          );
        },
        child: Container(
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
            borderRadius: BorderRadius.circular(DS.radius12),
            border: Border.all(color: DS.borderSubtle),
          ),
          child: Row(
            children: [
              CircleAvatar(
                radius: 18,
                backgroundColor: DS.brandPrimary12,
                backgroundImage: user.avatarUrl != null
                    ? CachedNetworkImageProvider(user.avatarUrl!)
                    : null,
                child: user.avatarUrl == null
                    ? Text(
                        (user.displayName.isNotEmpty ? user.displayName[0] : '?').toUpperCase(),
                        style: TextStyle(
                          color: DS.brandPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                      )
                    : null,
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Text(
                  user.displayName,
                  style: TextStyle(
                      fontWeight: FontWeight.w500, color: DS.textPrimary),
                ),
              ),
              Icon(Icons.chevron_right_rounded,
                  color: DS.textTertiary, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Shared building blocks ─────────────────────────────────────────────────

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.icon, required this.title});
  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(icon, size: 18, color: DS.brandPrimary),
          const SizedBox(width: DS.sm),
          Text(
            title,
            style: TextStyle(
              fontSize: 15,
              fontWeight: DS.fontWeightBold,
              color: DS.textPrimary,
            ),
          ),
        ],
      );
}

class _PartnerAvatar extends StatelessWidget {
  const _PartnerAvatar({
    required this.avatarUrl,
    required this.name,
    this.isOnline = false,
  });
  final String? avatarUrl;
  final String name;
  final bool isOnline;

  @override
  Widget build(BuildContext context) => Stack(
        children: [
          CircleAvatar(
            radius: 22,
            backgroundColor: DS.brandPrimary12,
            backgroundImage: avatarUrl != null
                ? CachedNetworkImageProvider(avatarUrl!)
                : null,
            child: avatarUrl == null
                ? Text(
                    name[0].toUpperCase(),
                    style: TextStyle(
                      color: DS.brandPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                  )
                : null,
          ),
          if (isOnline)
            Positioned(
              right: 0,
              bottom: 0,
              child: Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: DS.success,
                  border: Border.all(color: DS.surfacePrimary, width: 2),
                ),
              ),
            ),
        ],
      );
}

