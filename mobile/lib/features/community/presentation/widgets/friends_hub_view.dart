import 'dart:async';

import 'package:flutter/material.dart';
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
          if (pending.isNotEmpty) ...[
            const SizedBox(height: 12),
            _PendingInviteBanner(count: pending.length),
          ],
          const SizedBox(height: 18),
          Text(
            '好友',
            style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 10),
          if (friendsAsync.hasError)
            _InlineError(message: friendsAsync.error.toString())
          else if (friends.isEmpty)
            _EmptyFriendsCard(overview: overview)
          else
            ...friends.map((friendship) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _FriendCard(friendship: friendship, overview: overview),
                ),),
        ],
      ),
    );
  }
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
                        '核心责任伙伴',
                        style: DS.titleLarge.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        pendingCount > 0
                            ? '你有 $pendingCount 条伙伴邀请待处理'
                            : '把最重要的学习伙伴放到最前面，打卡、监督和成长都围绕 TA 展开。',
                        style: DS.bodySmall.copyWith(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            SparkleButton(
              label: pendingCount > 0 ? '查看伙伴邀请' : '去挑选责任伙伴',
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

    final partnerDisplay =
        relationshipSummary?['partner_name']?.toString() ??
            active.partner?.displayName ??
            active.initiator?.displayName ??
            '责任伙伴';

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
                      partnerDisplay.isEmpty ? '伙' : partnerDisplay.characters.first,
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
                        Row(
                          children: [
                            Text(
                              partnerDisplay,
                              style: DS.titleLarge.copyWith(
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(width: 8),
                            _Pill(
                              label: '核心伙伴',
                              color: DS.brandPrimary,
                            ),
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          relationshipSummary == null
                              ? '伙伴工作台已准备好'
                              : '一起坚持了 ${relationshipSummary['days_together'] ?? 0} 天',
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
                    label: '我',
                    value: '${relationshipSummary?['my_streak_days'] ?? 0} 天连胜',
                  ),
                  _MetricChip(
                    label: 'TA',
                    value: '${relationshipSummary?['partner_streak_days'] ?? 0} 天连胜',
                  ),
                  _MetricChip(
                    label: '总打卡',
                    value: '${relationshipSummary?['total_checkins'] ?? 0} 次',
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      label: '聊天',
                      onPressed: () => context.push(
                        '/chat/private/${relationshipSummary?['partner_id'] ?? active.partnerId}?name=${Uri.encodeComponent(partnerDisplay)}',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: SparkleButton.ghost(
                      label: '提醒',
                      onPressed: () async {
                        try {
                          final result = await ref
                              .read(accountabilityActionsProvider)
                              .nudgePartner(ref, active.id);
                          final deliverySummary =
                              (result['delivery_summary'] as String?) ??
                                  '已通过站内提醒发送，对方在线时会实时看到';
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
                                '刚提醒过，冷却期内不会重复发送。提醒会以站内提示的形式送达，对方在线时会实时看到。',
                              );
                            } else {
                              AppFeedback.error(context, '提醒失败: $e');
                            }
                          }
                        }
                      },
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: SparkleButton(
                      label: '工作台',
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
              '$count 条责任伙伴/好友请求待处理',
              style: DS.bodyMedium.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
          SparkleButton.ghost(
            label: '查看',
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
        accountability?.partnershipId ==
            overview?.activePartnership?.id;

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
              backgroundImage:
                  friend.avatarUrl != null ? NetworkImage(friend.avatarUrl!) : null,
              child: friend.avatarUrl == null ? Text(friend.displayName.characters.first) : null,
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
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      if (isCorePartner) ...[
                        const SizedBox(width: 8),
                        _Pill(label: '责任伙伴', color: DS.brandPrimary),
                      ] else if (accountability?.isPending == true) ...[
                        const SizedBox(width: 8),
                        _Pill(label: '待确认', color: DS.warning),
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
                                ? '演示在线'
                                : '演示离线')
                            : (friend.status == UserStatus.online ? '在线' : '离线'),
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
                          : '已建立责任伙伴关系',
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
                            label: '我 ${accountability.myStreakDays} 天',
                          ),
                        if (accountability.partnerStreakDays != null)
                          _TinyMetric(
                            label: 'TA ${accountability.partnerStreakDays} 天',
                          ),
                        if (accountability.partnerCheckedInToday != null)
                          _TinyMetric(
                            label: accountability.partnerCheckedInToday!
                                ? 'TA 今天已打卡'
                                : 'TA 今天未打卡',
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
          Text(
            '$label · ',
            style: DS.labelSmall.copyWith(color: DS.textSecondary),
          ),
          Text(
            value,
            style: DS.bodySmall.copyWith(fontWeight: FontWeight.bold),
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
        style: DS.labelSmall.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
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
            hasPending ? '先处理伙伴邀请，再扩展你的好友网络' : '还没有好友',
            style: DS.bodyLarge.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 6),
          Text(
            '从好友里挑出最重要的一位，建立你的核心责任伙伴关系。',
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: 14),
          SparkleButton(
            label: '去发现好友',
            onPressed: () => context.pushNamed('friendsDiscover'),
          ),
        ],
      ),
    );
  }
}
