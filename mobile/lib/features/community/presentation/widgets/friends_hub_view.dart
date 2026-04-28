import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

class FriendsHubView extends ConsumerWidget {
  const FriendsHubView({
    this.padding = const EdgeInsets.fromLTRB(12, 12, 12, 24),
    super.key,
  });

  final EdgeInsets padding;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final friendsAsync = ref.watch(friendsProvider);
    final overviewAsync = ref.watch(accountabilityOverviewProvider);
    final pendingAsync = ref.watch(pendingRequestsProvider);

    if (friendsAsync.isLoading &&
        !friendsAsync.hasValue &&
        overviewAsync.isLoading &&
        !overviewAsync.hasValue) {
      return const Center(child: LoadingIndicator());
    }

    final friends = friendsAsync.valueOrNull ?? const <FriendshipInfo>[];
    final overview = overviewAsync.valueOrNull;
    final pending = pendingAsync.valueOrNull ?? const <FriendshipInfo>[];

    return RefreshIndicator(
      onRefresh: () async {
        await ref.read(friendsProvider.notifier).refresh();
        await ref.read(pendingRequestsProvider.notifier).refresh();
        await ref.read(myPartnershipsProvider.notifier).load();
        ref.invalidate(accountabilityOverviewProvider);
      },
      child: ListView(
        padding: padding,
        children: [
          _PartnerHero(overview: overview),
          if (overview?.inAppHints.isNotEmpty ?? false) ...[
            const SizedBox(height: 12),
            _InAppHintBanner(hint: overview!.inAppHints.first),
          ],
          if (pending.isNotEmpty) ...[
            const SizedBox(height: 12),
            _PendingInviteBanner(count: pending.length),
          ],
          const SizedBox(height: 18),
          Text(
            context.l10n.communityFriends,
            style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          if (friendsAsync.hasError)
            _InlineError(message: friendsAsync.error.toString())
          else if (friends.isEmpty)
            _EmptyFriendsCard(overview: overview)
          else
            ...friends.map(
              (friendship) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _FriendCard(friendship: friendship, overview: overview),
              ),
            ),
        ],
      ),
    );
  }
}

class _InAppHintBanner extends ConsumerWidget {
  const _InAppHintBanner({required this.hint});

  final AccountabilityInAppHintInfo hint;

  @override
  Widget build(BuildContext context, WidgetRef ref) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.panel,
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: DS.success.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                Icons.visibility_outlined,
                color: DS.success,
                size: 20,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                hint.message,
                style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightBold),
              ),
            ),
            const SizedBox(width: 8),
            SparkleButton.ghost(
              label: context.l10n.communityGotIt,
              onPressed: () async {
                await ref
                    .read(accountabilityActionsProvider)
                    .dismissInAppHint(ref, hint.id);
                if (context.mounted) {
                  AppFeedback.success(context, context.l10n.communityCollapsed);
                }
              },
            ),
          ],
        ),
      );
}

class _PartnerHero extends ConsumerWidget {
  const _PartnerHero({required this.overview});

  final AccountabilityOverviewInfo? overview;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final active = overview?.activePartnership;
    final relationshipSummary = overview?.relationshipSummary;
    if (active == null) {
      final pendingCount = overview?.pendingPartnerships.length ?? 0;
      return GraphiteCardSurface(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(
                    Icons.handshake_outlined,
                    color: DS.brandPrimary,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.communityCorePartner,
                        style: DS.titleLarge.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        pendingCount > 0
                            ? context.l10n.communityPendingInvitesCount(pendingCount)
                            : context.l10n.communityPartnerDescription,
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            SparkleButton(
              label: pendingCount > 0 ? context.l10n.communityViewPartnerInvites : context.l10n.communityChoosePartner,
              expand: true,
              onPressed: () {
                if (pendingCount > 0) {
                  unawaited(context.pushNamed('friendRequests'));
                  return;
                }
                unawaited(context.pushNamed('friendsDiscover'));
              },
            ),
          ],
        ),
      );
    }

    final partnerDisplay = relationshipSummary?['partner_name']?.toString() ??
        active.partner?.displayName ??
        active.initiator?.displayName ??
        context.l10n.communityPartnerFallback;

    return GraphiteCardSurface(
      padding: const EdgeInsets.all(18),
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(22),
          gradient: LinearGradient(
            colors: [
              DS.brandPrimary.withValues(alpha: 0.18),
              DS.surfaceSecondary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.22),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: DS.brandPrimary.withValues(alpha: 0.14),
                    child: Text(
                      partnerDisplay.isEmpty
                          ? context.l10n.communityPartnerFallback
                          : partnerDisplay.characters.first,
                      style: TextStyle(
                        color: DS.brandPrimary,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Wrap(
                          spacing: 8,
                          runSpacing: 6,
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 180),
                              child: Text(
                                partnerDisplay,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: DS.titleLarge.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            _Pill(
                              label: context.l10n.communityCorePartnerLabel,
                              color: DS.brandPrimary,
                            ),
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          relationshipSummary == null
                              ? context.l10n.communityWorkspaceReady
                              : context.l10n.communityTogetherDays(relationshipSummary['days_together'] ?? 0),
                          style: DS.bodySmall.copyWith(color: DS.textSecondary),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _MetricChip(
                    label: context.l10n.communityMe,
                    value: context.l10n.communityMyStreakDays(relationshipSummary?['my_streak_days'] ?? 0),
                  ),
                  _MetricChip(
                    label: 'TA',
                    value:
                        context.l10n.communityPartnerStreakDays(relationshipSummary?['partner_streak_days'] ?? 0),
                  ),
                  _MetricChip(
                    label: context.l10n.communityTotalCheckins.split('{count}').first.trim(),
                    value: context.l10n.communityTotalCheckins(relationshipSummary?['total_checkins'] ?? 0),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      label: context.l10n.communityChat,
                      onPressed: () => context.push(
                        '/chat/private/${relationshipSummary?['partner_id'] ?? active.partnerId}?name=${Uri.encodeComponent(partnerDisplay)}',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: SparkleButton.ghost(
                      label: context.l10n.communityRemind,
                      onPressed: () async {
                        try {
                          final result = await ref
                              .read(accountabilityActionsProvider)
                              .nudgePartner(ref, active.id);
                          final deliverySummary =
                              (result['delivery_summary'] as String?) ??
                                  context.l10n.communityNudgeDelivered;
                          if (context.mounted) {
                            AppFeedback.success(
                              context,
                              deliverySummary,
                            );
                          }
                        } catch (e) {
                          if (context.mounted) {
                            final message = e.toString();
                            if (message.contains('429') ||
                                message.contains('cooldown')) {
                              AppFeedback.info(
                                context,
                                context.l10n.communityNudgeCooldown,
                              );
                            } else {
                              AppFeedback.error(context, context.l10n.communityNudgeFailed(e.toString()));
                            }
                          }
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: SparkleButton(
                      label: context.l10n.communityWorkshop,
                      onPressed: () => context.push(
                        CommunityRoutes.accountabilityDetail
                            .replaceFirst(':id', active.id),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PendingInviteBanner extends StatelessWidget {
  const _PendingInviteBanner({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        child: Row(
          children: [
            Icon(Icons.mark_email_unread_outlined, color: DS.warning),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                context.l10n.communityPartnerRequestCount(count),
                style: DS.bodyMedium.copyWith(fontWeight: DS.fontWeightSemibold),
              ),
            ),
            SparkleButton.ghost(
              label: context.l10n.communityViewRequests,
              onPressed: () => context.pushNamed('friendRequests'),
            ),
          ],
        ),
      );
}

class _FriendCard extends StatelessWidget {
  const _FriendCard({
    required this.friendship,
    required this.overview,
  });

  final FriendshipInfo friendship;
  final AccountabilityOverviewInfo? overview;

  @override
  Widget build(BuildContext context) {
    final friend = friendship.friend;
    final accountability = friendship.accountability;
    final isDemoMode = DemoDataService.isDemoMode;
    final isCorePartner = accountability?.status == 'active' &&
        accountability?.partnershipId == overview?.activePartnership?.id;

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isCorePartner
              ? DS.brandPrimary.withValues(alpha: 0.45)
              : DS.neutral200,
          width: isCorePartner ? 1.6 : 1,
        ),
        gradient: isCorePartner
            ? LinearGradient(
                colors: [
                  DS.brandPrimary.withValues(alpha: 0.14),
                  DS.surfacePrimary,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
      ),
      child: GraphiteCardSurface(
        onTap: () {
          if (accountability?.isPending == true) {
            unawaited(context.pushNamed('friendRequests'));
            return;
          }
          unawaited(context.push(
            '/chat/private/${friend.id}?name=${Uri.encodeComponent(friend.displayName)}',
          ));
        },
        child: Row(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundImage: friend.avatarUrl != null
                  ? NetworkImage(friend.avatarUrl!)
                  : null,
              child: friend.avatarUrl == null
                  ? Text(friend.displayName.characters.first)
                  : null,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          friend.displayName,
                          overflow: TextOverflow.ellipsis,
                          style: DS.bodyLarge.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                        ),
                      ),
                      if (isCorePartner) ...[
                        const SizedBox(width: 8),
                        _Pill(label: context.l10n.communityAccountabilityPartner, color: DS.brandPrimary),
                      ] else if (accountability?.isPending == true) ...[
                        const SizedBox(width: 8),
                        _Pill(label: context.l10n.communityPendingConfirm, color: DS.warning),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(
                        friend.status == UserStatus.online
                            ? Icons.circle
                            : Icons.circle_outlined,
                        size: 10,
                        color: friend.status == UserStatus.online
                            ? DS.success
                            : DS.neutral400,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        isDemoMode
                            ? (friend.status == UserStatus.online
                                ? context.l10n.communityDemoOnline
                                : context.l10n.communityDemoOffline)
                            : (friend.status == UserStatus.online
                                ? context.l10n.communityOnline
                                : context.l10n.communityOffline),
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'Lv.${friend.flameLevel}',
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                    ],
                  ),
                  if (accountability != null) ...[
                    const SizedBox(height: 8),
                    Text(
                      accountability.goalPreview?.isNotEmpty == true
                          ? accountability.goalPreview!
                          : context.l10n.communityPartnerEstablished,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        if (accountability.myStreakDays != null)
                          _TinyMetric(
                            label: context.l10n.communityMyDays(accountability.myStreakDays ?? 0),
                          ),
                        if (accountability.partnerStreakDays != null)
                          _TinyMetric(
                            label: context.l10n.communityPartnerDays(accountability.partnerStreakDays ?? 0),
                          ),
                        if (accountability.partnerCheckedInToday != null)
                          _TinyMetric(
                            label: accountability.partnerCheckedInToday!
                                ? context.l10n.communityPartnerCheckedIn
                                : context.l10n.communityPartnerNotCheckedIn,
                          ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  icon: const Icon(Icons.person_outline),
                  onPressed: () => context.pushNamed(
                    'userProfile',
                    pathParameters: {'id': friend.id},
                    queryParameters: {'name': friend.displayName},
                  ),
                ),
                if (accountability?.partnershipId != null)
                  SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    icon: Icon(
                      accountability?.isPending == true
                          ? Icons.mark_email_unread_outlined
                          : Icons.handshake_outlined,
                    ),
                    onPressed: () {
                      if (accountability?.isPending == true) {
                        unawaited(context.pushNamed('friendRequests'));
                        return;
                      }
                      unawaited(context.push(
                        CommunityRoutes.accountabilityDetail.replaceFirst(
                          ':id',
                          accountability!.partnershipId,
                        ),
                      ));
                    },
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.82),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(
                '$label · $value',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: DS.bodySmall.copyWith(fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      );
}

class _TinyMetric extends StatelessWidget {
  const _TinyMetric({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          label,
          style: DS.labelSmall.copyWith(color: DS.textSecondary),
        ),
      );
}

class _Pill extends StatelessWidget {
  const _Pill({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: DS.labelSmall.copyWith(
            color: color,
            fontWeight: DS.fontWeightBold,
          ),
        ),
      );
}

class _InlineError extends StatelessWidget {
  const _InlineError({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        child: Text(
          message,
          style: DS.bodySmall.copyWith(color: DS.error),
        ),
      );
}

class _EmptyFriendsCard extends StatelessWidget {
  const _EmptyFriendsCard({required this.overview});

  final AccountabilityOverviewInfo? overview;

  @override
  Widget build(BuildContext context) {
    final hasPending = (overview?.pendingPartnerships.length ?? 0) > 0;
    return GraphiteCardSurface(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.people_outline, size: 42, color: DS.neutral400),
          const SizedBox(height: 12),
          Text(
            hasPending ? context.l10n.communityPendingFirst : context.l10n.communityNoFriendsYet,
            style: DS.bodyLarge.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            context.l10n.communityChooseCorePartner,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: 14),
          SparkleButton(
            label: context.l10n.communityDiscoverFriends,
            onPressed: () => context.pushNamed('friendsDiscover'),
          ),
        ],
      ),
    );
  }
}
