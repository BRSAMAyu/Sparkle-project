import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';

/// 我的责任伙伴列表
class AccountabilityScreen extends ConsumerWidget {
  const AccountabilityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(myPartnershipsProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('责任伙伴'),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.refresh),
            onPressed: () =>
                ref.read(myPartnershipsProvider.notifier).load(),
          ),
        ],
      ),
      child: state.when(
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text('加载失败: $e', style: TextStyle(color: DS.error)),
              const SizedBox(height: DS.md),
              SparkleButton.primary(
                label: '重试',
                onPressed: () =>
                    ref.read(myPartnershipsProvider.notifier).load(),
              ),
            ],
          ),
        ),
        data: (partnerships) {
          if (partnerships.isEmpty) {
            return const Center(
              child: CompactEmptyState(
                message: '还没有责任伙伴\n从好友列表发起邀请',
                icon: Icons.people_outline,
              ),
            );
          }

          final currentUserId =
              ref.watch(currentUserProvider)?.id ?? '';

          return ContentConstraint(
            child: ListView.separated(
              padding: const EdgeInsets.all(DS.spacing16),
              itemCount: partnerships.length,
              separatorBuilder: (_, __) =>
                  const SizedBox(height: DS.spacing12),
              itemBuilder: (ctx, i) => _PartnershipCard(
                partnership: partnerships[i],
                currentUserId: currentUserId,
              ),
            ),
          );
        },
      ),
    );
  }
}

class _PartnershipCard extends ConsumerWidget {
  const _PartnershipCard({
    required this.partnership,
    required this.currentUserId,
  });

  final AccountabilityPartnershipInfo partnership;
  final String currentUserId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isPending =
        partnership.status == AccountabilityStatus.pending;
    final isActive = partnership.status == AccountabilityStatus.active;
    final isInitiator = partnership.initiatorId == currentUserId;

    final partner =
        isInitiator ? partnership.partner : partnership.initiator;
    final myGoal = isInitiator
        ? partnership.initiatorGoal
        : partnership.partnerGoal ?? '(未设置)';

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      child: InkWell(
        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        onTap: isActive
            ? () => context.push(
                  CommunityRoutes.accountabilityDetail
                      .replaceFirst(':id', partnership.id),
                )
            : null,
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 24,
                    backgroundColor: DS.brandPrimary.withValues(alpha: 0.15),
                    child: Text(
                      (partner?.displayName ?? '?')
                          .substring(0, 1)
                          .toUpperCase(),
                      style: TextStyle(
                          color: DS.brandPrimary,
                          fontWeight: FontWeight.bold,
                          fontSize: 18,),
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          partner?.displayName ?? '未知用户',
                          style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: DS.fontSizeBase,),
                        ),
                        const SizedBox(height: DS.xs),
                        _StatusChip(status: partnership.status),
                      ],
                    ),
                  ),
                  if (isPending && !isInitiator)
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SparkleButton.primary(
                          label: '接受',
                          onPressed: () => _accept(context, ref),
                        ),
                        const SizedBox(width: DS.sm),
                        SparkleButton.ghost(
                          label: '拒绝',
                          onPressed: () => _decline(context, ref),
                        ),
                      ],
                    ),
                ],
              ),
              const SizedBox(height: DS.spacing12),
              _GoalRow(label: '我的目标', goal: myGoal),
              if (isActive) ...[
                const SizedBox(height: DS.spacing8),
                _StreakRow(partnership: partnership),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _accept(
      BuildContext context, WidgetRef ref,) async {
    try {
      await ref
          .read(accountabilityRepositoryProvider)
          .respondToPartnership(partnership.id, accept: true);
      await ref.read(myPartnershipsProvider.notifier).load();
      if (context.mounted) AppFeedback.success(context, '已接受责任伙伴邀请！');
    } catch (e) {
      if (context.mounted) AppFeedback.error(context, '操作失败: $e');
    }
  }

  Future<void> _decline(
      BuildContext context, WidgetRef ref,) async {
    try {
      await ref
          .read(accountabilityRepositoryProvider)
          .respondToPartnership(partnership.id, accept: false);
      await ref.read(myPartnershipsProvider.notifier).load();
      if (context.mounted) AppFeedback.info(context, '已拒绝邀请');
    } catch (e) {
      if (context.mounted) AppFeedback.error(context, '操作失败: $e');
    }
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.status});
  final AccountabilityStatus status;

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      AccountabilityStatus.pending => ('待确认', DS.warning),
      AccountabilityStatus.active => ('进行中', DS.success),
      AccountabilityStatus.paused => ('已暂停', DS.neutral500),
      AccountabilityStatus.ended => ('已结束', DS.neutral400),
    };

    return Container(
      padding:
          const EdgeInsets.symmetric(horizontal: DS.sm, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(label,
          style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: color,
              fontWeight: FontWeight.bold,),),
    );
  }
}

class _GoalRow extends StatelessWidget {
  const _GoalRow({required this.label, required this.goal});
  final String label;
  final String goal;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$label: ',
              style: TextStyle(
                  fontSize: DS.fontSizeSm, color: DS.textSecondary,),),
          Expanded(
            child: Text(goal,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: DS.fontSizeSm),),
          ),
        ],
      );
}

class _StreakRow extends ConsumerWidget {
  const _StreakRow({required this.partnership});
  final AccountabilityPartnershipInfo partnership;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hasSummary = partnership.myCheckedInToday != null ||
        partnership.partnerCheckedInToday != null;
    final statsAsync = hasSummary
        ? AsyncValue.data(
            AccountabilityStatsInfo(
              myStreakDays: partnership.myStreakDays ?? 0,
              partnerStreakDays: partnership.partnerStreakDays ?? 0,
              myCheckedInToday: partnership.myCheckedInToday ?? false,
              partnerCheckedInToday: partnership.partnerCheckedInToday ?? false,
              totalCheckins: 0,
            ),
          )
        : ref.watch(partnershipStatsProvider(partnership.id));
    return statsAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
      data: (stats) => Row(
        children: [
          Icon(Icons.local_fire_department,
              size: 16, color: DS.brandPrimary,),
          const SizedBox(width: DS.xs),
          Text(
            '我: ${stats.myStreakDays} 天 · 伙伴: ${stats.partnerStreakDays} 天',
            style: TextStyle(
                fontSize: DS.fontSizeSm, color: DS.brandPrimary,),
          ),
          const Spacer(),
          if (stats.partnerCheckedInToday)
            Icon(Icons.check_circle, size: 16, color: DS.success)
          else
            Icon(Icons.access_time, size: 16, color: DS.neutral500),
          const SizedBox(width: DS.xs),
          Text(
            stats.partnerCheckedInToday ? '伙伴已打卡' : '伙伴未打卡',
            style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: stats.partnerCheckedInToday
                    ? DS.success
                    : DS.neutral500,),
          ),
        ],
      ),
    );
  }
}
