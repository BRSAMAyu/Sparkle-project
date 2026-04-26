import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/repositories/accountability_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/accountability_heatmap.dart';
import 'package:sparkle/features/community/presentation/widgets/achievement_badge.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

/// 责任伙伴工作台
class AccountabilityDetailScreen extends ConsumerStatefulWidget {
  const AccountabilityDetailScreen({
    required this.partnershipId,
    super.key,
  });

  final String partnershipId;

  @override
  ConsumerState<AccountabilityDetailScreen> createState() =>
      _AccountabilityDetailScreenState();
}

class _AccountabilityDetailScreenState
    extends ConsumerState<AccountabilityDetailScreen> {
  bool _quickActionEnabled(
    Map<String, dynamic> actions,
    String key, {
    String? legacyKey,
  }) =>
      actions[key] == true || (legacyKey != null && actions[legacyKey] == true);

  @override
  Widget build(BuildContext context) {
    final dashboardAsync =
        ref.watch(accountabilityDashboardProvider(widget.partnershipId));
    final currentUserId = ref.watch(currentUserProvider)?.id ?? '';

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(
          dashboardAsync.valueOrNull == null
              ? context.l10n.accountabilityPartnerDefault
              : _partnerName(
                  dashboardAsync.valueOrNull!.partnership,
                  currentUserId,
                ),
        ),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'end') {
                unawaited(_confirmEnd());
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem(
                value: 'end',
                child: Text(context.l10n.accountabilityEndPartnership),
              ),
            ],
          ),
        ],
      ),
      child: dashboardAsync.when(
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error_outline, size: 42, color: DS.error),
                const SizedBox(height: DS.spacing12),
                Text(
                  context.l10n.accountabilityDashboardLoadFailed,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  '$e',
                  style: DS.bodySmall.copyWith(color: DS.textSecondary),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DS.spacing12),
                SparkleButton.primary(
                  label: context.l10n.retry,
                  onPressed: () => ref.invalidate(
                    accountabilityDashboardProvider(widget.partnershipId),
                  ),
                ),
              ],
            ),
          ),
        ),
        data: (dashboard) {
          final canCheckin = _quickActionEnabled(
            dashboard.quickActions,
            'can_check_in',
            legacyKey: 'can_checkin',
          );
          final canNudge =
              _quickActionEnabled(dashboard.quickActions, 'can_nudge');
          final canShare =
              _quickActionEnabled(dashboard.quickActions, 'can_share');
          final canChat =
              _quickActionEnabled(dashboard.quickActions, 'can_chat');
          final canOpenDashboard = _quickActionEnabled(
            dashboard.quickActions,
            'can_open_dashboard',
          );

          if (!canOpenDashboard ||
              dashboard.partnership.status != AccountabilityStatus.active) {
            return _InactiveDashboardView(
              dashboard: dashboard,
              currentUserId: currentUserId,
              canChat: canChat,
            );
          }

          return _DashboardView(
            dashboard: dashboard,
            currentUserId: currentUserId,
            onCheckin: canCheckin ? _showCheckinSheet : null,
            onNudge: canNudge ? () => _sendNudge(widget.partnershipId) : null,
            onShare: canShare
                ? () => unawaited(context.push('/achievements'))
                : null,
            onChat: canChat
                ? () {
                    final partnerId =
                        dashboard.partnership.initiatorId == currentUserId
                            ? dashboard.partnership.partnerId
                            : dashboard.partnership.initiatorId;
                    final partnerName = _partnerName(
                      dashboard.partnership,
                      currentUserId,
                    );
                    unawaited(context.push(
                      '/chat/private/$partnerId?name=${Uri.encodeComponent(partnerName)}',
                    ));
                  }
                : null,
          );
        },
      ),
    );
  }

  String _partnerName(
    AccountabilityPartnershipInfo partnership,
    String currentUserId,
  ) {
    final isInitiator = partnership.initiatorId == currentUserId;
    final partner = isInitiator ? partnership.partner : partnership.initiator;
    return partner?.displayName ?? context.l10n.accountabilityPartnerDefault;
  }

  void _showCheckinSheet() {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (ctx) => AccountabilityCheckinSheet(
          partnershipId: widget.partnershipId,
          onDone: () {
            ref.invalidate(myPartnershipsProvider);
            ref.invalidate(accountabilityOverviewProvider);
            ref.invalidate(
                accountabilityDashboardProvider(widget.partnershipId));
          },
        ),
      ),
    );
  }

  Future<void> _sendNudge(String partnershipId) async {
    try {
      final result = await ref
          .read(accountabilityActionsProvider)
          .nudgePartner(ref, partnershipId);
      if (mounted) {
        final deliverySummary = (result['delivery_summary'] as String?) ??
            (result['message'] as String?) ??
            context.l10n.accountabilityNudgeSentDefault;
        AppFeedback.success(context, deliverySummary);
      }
    } catch (e) {
      if (mounted) {
        final message = e.toString();
        if (message.contains('429') || message.contains('cooldown')) {
          AppFeedback.info(
            context,
            context.l10n.accountabilityNudgeCooldown,
          );
        } else {
          AppFeedback.error(context, context.l10n.accountabilityNudgeFailed);
        }
      }
    }
  }

  Future<void> _confirmEnd() async {
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(context.l10n.accountabilityEndPartnership),
        content: Text(context.l10n.accountabilityEndPartnershipConfirm),
        actions: [
          SparkleButton.ghost(
            label: context.l10n.cancel,
            onPressed: () => Navigator.pop(ctx, false),
          ),
          SparkleButton(
            label: context.l10n.accountabilityEnd,
            onPressed: () => Navigator.pop(ctx, true),
            variant: ButtonVariant.destructive,
          ),
        ],
      ),
    );

    if (confirmed ?? false) {
      try {
        await ref
            .read(myPartnershipsProvider.notifier)
            .endPartnership(widget.partnershipId);
        ref.invalidate(accountabilityOverviewProvider);
        ref.invalidate(accountabilityDashboardProvider(widget.partnershipId));
        if (mounted) {
          context.pop();
          AppFeedback.success(context, context.l10n.accountabilityPartnershipEnded);
        }
      } catch (e) {
        if (mounted) {
          AppFeedback.error(context, '${context.l10n.accountabilityOperationFailed}: $e');
        }
      }
    }
  }
}

class _DashboardView extends StatelessWidget {
  const _DashboardView({
    required this.dashboard,
    required this.currentUserId,
    required this.onCheckin,
    required this.onNudge,
    required this.onShare,
    required this.onChat,
  });

  final AccountabilityDashboardInfo dashboard;
  final String currentUserId;
  final VoidCallback? onCheckin;
  final VoidCallback? onNudge;
  final VoidCallback? onShare;
  final VoidCallback? onChat;

  @override
  Widget build(BuildContext context) {
    final partnership = dashboard.partnership;
    final stats = dashboard.stats;
    final isInitiator = partnership.initiatorId == currentUserId;
    final partner = isInitiator ? partnership.partner : partnership.initiator;
    final partnerName = partner?.displayName ?? context.l10n.accountabilityPartnerDefault;
    final partnerAchievements =
        ((dashboard.achievements['achievements'] as List<dynamic>?) ?? const [])
            .where(
              (item) => (item as Map)['partner_unlocked'] == true,
            )
            .map(
              (item) => AchievementInfo.fromJson(
                Map<String, dynamic>.from(item as Map),
              ),
            )
            .toList();

    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(DS.spacing16),
            children: [
              SparkleStaggerItem(
                index: 0,
                motionToken: SparkleMotionToken.scene,
                child: _DashboardHero(
                  partnerName: partnerName,
                  stats: stats,
                  relationshipSummary: dashboard.relationshipSummary,
                  onCheckin: stats.myCheckedInToday ? null : onCheckin,
                  onNudge: onNudge,
                  onShare: onShare,
                  onChat: onChat,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: 1,
                child: _PendingPoliciesCard(summary: dashboard.pendingPolicies),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: 2,
                child: _RecentReflectionsCard(
                  summary: dashboard.recentReflections,
                ),
              ),
              if (dashboard.foresightHint?.hintText?.isNotEmpty ?? false) ...[
                const SizedBox(height: DS.spacing12),
                SparkleStaggerItem(
                  index: 3,
                  child: _ForesightHintCard(summary: dashboard.foresightHint),
                ),
              ],
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: dashboard.foresightHint?.hintText?.isNotEmpty ?? false
                    ? 4
                    : 3,
                child: _GoalPanel(
                  title: context.l10n.accountabilityMyGoal,
                  goal: isInitiator
                      ? partnership.initiatorGoal
                      : partnership.partnerGoal ?? context.l10n.accountabilityGoalNotSet,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: dashboard.foresightHint?.hintText?.isNotEmpty ?? false
                    ? 5
                    : 4,
                child: _GoalPanel(
                  title: context.l10n.accountabilityPartnerGoal(partnerName),
                  goal: isInitiator
                      ? partnership.partnerGoal ?? context.l10n.accountabilityPartnerGoalNotSet
                      : partnership.initiatorGoal,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: dashboard.foresightHint?.hintText?.isNotEmpty ?? false
                    ? 6
                    : 5,
                child: _SectionCard(
                  title: context.l10n.accountabilityGrowingTogether,
                  child: _GrowthSummary(
                    relationshipSummary: dashboard.relationshipSummary,
                    leaderboardSummary: dashboard.leaderboardSummary,
                    achievements: dashboard.achievements,
                  ),
                ),
              ),
              if (dashboard.recentShares.isNotEmpty) ...[
                const SizedBox(height: DS.spacing12),
                SparkleStaggerItem(
                  index: dashboard.foresightHint?.hintText?.isNotEmpty ?? false
                      ? 7
                      : 6,
                  child: _SectionCard(
                    title: context.l10n.accountabilityRecentShares,
                    child: Column(
                      children: dashboard.recentShares
                          .take(3)
                          .map(
                            (share) => Padding(
                              padding:
                                  const EdgeInsets.only(bottom: DS.spacing12),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(
                                    Icons.share_outlined,
                                    size: 18,
                                    color: DS.brandPrimary,
                                  ),
                                  const SizedBox(width: DS.spacing8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          share['title']?.toString() ?? context.l10n.accountabilitySharedItem,
                                          style: DS.bodyMedium.copyWith(
                                            fontWeight: DS.fontWeightSemibold,
                                          ),
                                        ),
                                        if ((share['comment'] ?? '')
                                            .toString()
                                            .isNotEmpty) ...[
                                          const SizedBox(height: 4),
                                          Text(
                                            share['comment'].toString(),
                                            style: DS.bodySmall.copyWith(
                                              color: DS.textSecondary,
                                            ),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: 7,
                child: _SectionCard(
                  title: context.l10n.accountabilityMonthlyHeatmap,
                  child: AccountabilityHeatmap(
                    year: (dashboard.heatmap['year'] as int?) ??
                        DateTime.now().year,
                    heatmap: ((dashboard.heatmap['heatmap']
                                as List<dynamic>?) ??
                            [])
                        .map((item) => Map<String, dynamic>.from(item as Map))
                        .toList(),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: 6,
                child: _SectionCard(
                  title: context.l10n.accountabilityPartnerAchievements,
                  child: partnerAchievements.isEmpty
                      ? Text(
                          context.l10n.accountabilityPartnerNoAchievements,
                          style: TextStyle(color: DS.textSecondary),
                        )
                      : AchievementGrid(
                          achievements: partnerAchievements,
                          crossAxisCount: 1,
                        ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                context.l10n.accountabilityRecentCheckins,
                style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.spacing8),
              if (dashboard.timeline.isEmpty)
                _SectionCard(
                  title: context.l10n.accountabilityNoCheckinRecords,
                  child: Text(
                    context.l10n.accountabilityNoCheckinHint,
                    style: TextStyle(color: DS.textSecondary),
                  ),
                )
              else
                ...dashboard.timeline.map(
                  (checkin) => _CheckinTile(
                    checkin: checkin,
                    isMe: checkin.userId == currentUserId,
                  ),
                ),
              const SizedBox(height: DS.spacing24),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: SizedBox(
            width: double.infinity,
            child: SparkleButton(
              label: stats.myCheckedInToday ? context.l10n.accountabilityCheckedInToday : context.l10n.accountabilityCheckInToday,
              onPressed: stats.myCheckedInToday ? null : onCheckin,
              disabled: stats.myCheckedInToday || onCheckin == null,
              expand: true,
            ),
          ),
        ),
      ],
    );
  }
}

class _DashboardHero extends StatelessWidget {
  const _DashboardHero({
    required this.partnerName,
    required this.stats,
    required this.relationshipSummary,
    required this.onCheckin,
    required this.onNudge,
    required this.onShare,
    required this.onChat,
  });

  final String partnerName;
  final AccountabilityStatsInfo stats;
  final Map<String, dynamic> relationshipSummary;
  final VoidCallback? onCheckin;
  final VoidCallback? onNudge;
  final VoidCallback? onShare;
  final VoidCallback? onChat;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
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
                    _PersonStat(
                      name: context.l10n.accountabilityMe,
                      streakDays: stats.myStreakDays,
                      checkedInToday: stats.myCheckedInToday,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        children: [
                          Text(
                            partnerName,
                            style: DS.titleLarge.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            context.l10n.accountabilityDaysTogether((relationshipSummary['days_together'] as Object?) ?? 0),
                            style:
                                DS.bodySmall.copyWith(color: DS.textSecondary),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 10),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 8,
                            ),
                            decoration: BoxDecoration(
                              color: DS.surfacePrimary.withValues(alpha: 0.72),
                              borderRadius: BorderRadius.circular(14),
                            ),
                            child: Column(
                              children: [
                                Text(
                                  '${relationshipSummary['total_checkins'] ?? stats.totalCheckins}',
                                  style: DS.titleLarge.copyWith(
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                Text(
                                  context.l10n.accountabilityTotalCheckins,
                                  style: DS.bodySmall.copyWith(
                                    color: DS.textSecondary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    _PersonStat(
                      name: context.l10n.accountabilityThem,
                      streakDays: stats.partnerStreakDays,
                      checkedInToday: stats.partnerCheckedInToday,
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _HeroAction(
                      icon: Icons.check_circle_outline,
                      label: stats.myCheckedInToday ? context.l10n.accountabilityCheckedIn : context.l10n.accountabilityCheckin,
                      onTap: onCheckin,
                    ),
                    _HeroAction(
                      icon: Icons.bolt_outlined,
                      label: context.l10n.accountabilityNudge,
                      onTap: onNudge,
                    ),
                    _HeroAction(
                      icon: Icons.share_outlined,
                      label: context.l10n.accountabilityShare,
                      onTap: onShare,
                    ),
                    _HeroAction(
                      icon: Icons.chat_bubble_outline,
                      label: context.l10n.accountabilityChat,
                      onTap: onChat,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );
}

class _HeroAction extends StatelessWidget {
  const _HeroAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: onTap == null
                ? DS.surfaceSecondary.withValues(alpha: 0.7)
                : DS.surfacePrimary.withValues(alpha: 0.8),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: DS.neutral200),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 16,
                color: onTap == null ? DS.textTertiary : DS.brandPrimary,
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: DS.labelSmall.copyWith(
                  fontWeight: DS.fontWeightBold,
                  color: onTap == null ? DS.textTertiary : null,
                ),
              ),
            ],
          ),
        ),
      );
}

class _InactiveDashboardView extends StatelessWidget {
  const _InactiveDashboardView({
    required this.dashboard,
    required this.currentUserId,
    required this.canChat,
  });

  final AccountabilityDashboardInfo dashboard;
  final String currentUserId;
  final bool canChat;

  @override
  Widget build(BuildContext context) {
    final partnership = dashboard.partnership;
    final isInitiator = partnership.initiatorId == currentUserId;
    final partner = isInitiator ? partnership.partner : partnership.initiator;
    final partnerName = partner?.displayName ?? context.l10n.accountabilityPartnerDefault;
    final isPending = partnership.status == AccountabilityStatus.pending;
    final message = isPending
        ? (isInitiator ? context.l10n.accountabilityInviteSentWait : context.l10n.accountabilityInvitePendingConfirm)
        : context.l10n.accountabilityDashboardNotAvailable;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(DS.spacing24),
        child: GraphiteCardSurface(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isPending ? Icons.schedule_outlined : Icons.info_outline,
                size: 40,
                color: DS.brandPrimary,
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                isPending ? context.l10n.accountabilityInvitePending : context.l10n.accountabilityDashboardUnavailable,
                style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                message,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.spacing16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: [
                  if (isPending)
                    SparkleButton.primary(
                      label: isInitiator ? context.l10n.accountabilityViewStatus : context.l10n.accountabilityHandleInvite,
                      onPressed: () =>
                          unawaited(context.pushNamed('friendRequests')),
                    ),
                  if (canChat)
                    SparkleButton.ghost(
                      label: context.l10n.accountabilityContinueChat,
                      onPressed: () => unawaited(context.push(
                        '/chat/private/${partner?.id ?? ''}?name=${Uri.encodeComponent(partnerName)}',
                      )),
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

class _GrowthSummary extends StatelessWidget {
  const _GrowthSummary({
    required this.relationshipSummary,
    required this.leaderboardSummary,
    required this.achievements,
  });

  final Map<String, dynamic> relationshipSummary;
  final Map<String, dynamic> leaderboardSummary;
  final Map<String, dynamic> achievements;

  @override
  Widget build(BuildContext context) {
    final myAchievements = achievements['my_total_unlocked'] ??
        achievements['total_unlocked'] ??
        0;
    final partnerAchievements = achievements['partner_total_unlocked'] ?? 0;
    final streakBoard =
        (leaderboardSummary['streak'] as Map<String, dynamic>?) ?? const {};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _TinyMetric(
              label: context.l10n.accountabilityMyStreakDays((relationshipSummary['my_streak_days'] as Object?) ?? 0),
            ),
            _TinyMetric(
              label: context.l10n.accountabilityPartnerStreakDays((relationshipSummary['partner_streak_days'] as Object?) ?? 0),
            ),
            _TinyMetric(label: context.l10n.accountabilityMyAchievementsUnlocked(myAchievements as Object)),
            _TinyMetric(label: context.l10n.accountabilityPartnerAchievementsUnlocked(partnerAchievements as Object)),
          ],
        ),
        if (streakBoard.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            context.l10n.accountabilityStreakRank((streakBoard['my_rank'] ?? '-') as Object, (streakBoard['partner_rank'] ?? '-') as Object),
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ],
    );
  }
}

class _PersonStat extends StatelessWidget {
  const _PersonStat({
    required this.name,
    required this.streakDays,
    required this.checkedInToday,
  });

  final String name;
  final int streakDays;
  final bool checkedInToday;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Stack(
            children: [
              CircleAvatar(
                radius: 30,
                backgroundColor: DS.brandPrimary.withValues(alpha: 0.15),
                child: Text(
                  name,
                  style: TextStyle(
                    color: DS.brandPrimary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              if (checkedInToday)
                Positioned(
                  right: 0,
                  bottom: 0,
                  child: Container(
                    width: 18,
                    height: 18,
                    decoration: BoxDecoration(
                      color: DS.success,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 2),
                    ),
                    child: const Icon(
                      Icons.check,
                      size: 10,
                      color: Colors.white,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: DS.xs),
          Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
          Text(
            context.l10n.accountabilityStreakDays(streakDays),
            style: TextStyle(fontSize: DS.fontSizeXs, color: DS.brandPrimary),
          ),
        ],
      );
}

class _GoalPanel extends StatelessWidget {
  const _GoalPanel({required this.title, required this.goal});

  final String title;
  final String goal;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.panel,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: DS.fontSizeSm,
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(height: DS.xs),
            Text(goal),
          ],
        ),
      );
}

class _PendingPoliciesCard extends StatelessWidget {
  const _PendingPoliciesCard({required this.summary});

  final PendingPoliciesSummaryInfo? summary;

  @override
  Widget build(BuildContext context) {
    final count = summary?.count ?? 0;
    final nextTriggerAt = summary?.nextTriggerAt;
    final subtitle = count <= 0
        ? context.l10n.accountabilityNoPendingPolicies
        : nextTriggerAt == null
            ? context.l10n.accountabilityPoliciesReady(count)
            : context.l10n.accountabilityPoliciesPending(count, DateFormat('M月d日 HH:mm').format(nextTriggerAt));
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.panel,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.policy_outlined, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.accountabilityPendingPolicies,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            count <= 0 ? context.l10n.accountabilityZeroItems : '$count 条',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          const SizedBox(height: DS.spacing4),
          Text(
            subtitle,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _RecentReflectionsCard extends StatelessWidget {
  const _RecentReflectionsCard({required this.summary});

  final RecentReflectionsSummaryInfo? summary;

  @override
  Widget build(BuildContext context) {
    final count = summary?.count ?? 0;
    final lastCategory = summary?.lastCategory;
    final lastAt = summary?.lastAt;
    final subtitle = count <= 0
        ? context.l10n.accountabilityNoRecentReflections
        : lastAt == null
            ? context.l10n.accountabilityReflectionsGenerated(count)
            : context.l10n.accountabilityReflectionsLatest(_labelForCategory(context, lastCategory), DateFormat('M月d日 HH:mm').format(lastAt));
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.panel,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_stories_outlined, color: DS.taskReflection),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.accountabilityRecentReflections,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            count <= 0 ? context.l10n.accountabilityZeroItems : '$count 条',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          if ((lastCategory ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing6),
            _TinyMetric(label: _labelForCategory(context, lastCategory)),
          ],
          const SizedBox(height: DS.spacing4),
          Text(
            subtitle,
            style: DS.bodySmall.copyWith(color: DS.textSecondary),
          ),
        ],
      ),
    );
  }

  String _labelForCategory(BuildContext context, String? category) {
    switch (category) {
      case 'intervention_ineffective':
        return context.l10n.accountabilityInterventionIneffective;
      case 'plan_stall':
        return context.l10n.accountabilityPlanStall;
      case 'overload':
        return context.l10n.accountabilityOverload;
      case 'too_difficult':
        return context.l10n.accountabilityTooDifficult;
      case 'unclear':
        return context.l10n.accountabilityUnclear;
      case 'abandoned':
        return context.l10n.accountabilityAbandoned;
      default:
        return context.l10n.accountabilityReflectionSummary;
    }
  }
}

class _ForesightHintCard extends StatelessWidget {
  const _ForesightHintCard({required this.summary});

  final ForesightHintSummaryInfo? summary;

  @override
  Widget build(BuildContext context) {
    final hintText = summary?.hintText;
    final generatedAt = summary?.generatedAt;
    final deviationCount = summary?.deviationCount ?? 0;
    final confidenceItems = summary?.attractorConfidences ?? [];
    final subtitle = [
      if (deviationCount > 0) context.l10n.accountabilityDeviationsDetected(deviationCount),
      if (generatedAt != null) context.l10n.accountabilityUpdatedAt(DateFormat('M月d日 HH:mm').format(generatedAt)),
    ].join(' · ');
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.panel,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.visibility_outlined, color: DS.brandPrimary),
              const SizedBox(width: DS.spacing8),
              Text(
                context.l10n.accountabilityForesightHint,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            hintText ?? context.l10n.accountabilityNoForesightHint,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          if (subtitle.isNotEmpty) ...[
            const SizedBox(height: DS.spacing6),
            Text(
              subtitle,
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
          ],
          if (confidenceItems.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: confidenceItems
                  .take(3)
                  .map(
                    (item) => _TinyMetric(
                      label:
                          '${_labelForDim(context, item.dim)} ${item.confidence.toStringAsFixed(2)}',
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }

  String _labelForDim(BuildContext context, String dim) {
    switch (dim) {
      case 'study_pace':
        return context.l10n.accountabilityDimPace;
      case 'completion_rate':
        return context.l10n.accountabilityDimCompletionRate;
      case 'engagement_level':
        return context.l10n.accountabilityDimEngagement;
      case 'mood_valence':
        return context.l10n.accountabilityDimMood;
      case 'plan_adherence':
        return context.l10n.accountabilityDimPlanAdherence;
      default:
        return dim;
    }
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.panel,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: DS.spacing12),
            child,
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

class _CheckinMoodVisual {
  const _CheckinMoodVisual({
    required this.icon,
    required this.label,
    required this.color,
  });

  final IconData icon;
  final String label;
  final Color color;
}

List<_CheckinMoodVisual> _checkinMoodVisuals(BuildContext context) => [
  _CheckinMoodVisual(
    icon: Icons.sentiment_very_dissatisfied_rounded,
    label: context.l10n.accountabilityMoodLow,
    color: Color(0xFFE57373),
  ),
  _CheckinMoodVisual(
    icon: Icons.sentiment_dissatisfied_rounded,
    label: context.l10n.accountabilityMoodOkay,
    color: Color(0xFFFFB74D),
  ),
  _CheckinMoodVisual(
    icon: Icons.sentiment_neutral_rounded,
    label: context.l10n.accountabilityMoodSteady,
    color: Color(0xFF90A4AE),
  ),
  _CheckinMoodVisual(
    icon: Icons.sentiment_satisfied_alt_rounded,
    label: context.l10n.accountabilityMoodGood,
    color: Color(0xFF66BB6A),
  ),
  _CheckinMoodVisual(
    icon: Icons.mood_rounded,
    label: context.l10n.accountabilityMoodGreat,
    color: Color(0xFF26A69A),
  ),
];

_CheckinMoodVisual _resolveCheckinMoodVisual(BuildContext context, int mood) {
  final visuals = _checkinMoodVisuals(context);
  return visuals[(mood - 1).clamp(0, visuals.length - 1)];
}

class _CheckinTile extends ConsumerWidget {
  const _CheckinTile({required this.checkin, required this.isMe});

  final AccountabilityCheckinInfo checkin;
  final bool isMe;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dateStr = DateFormat('MM-dd HH:mm').format(checkin.createdAt);
    final moodVisual = _resolveCheckinMoodVisual(context, checkin.mood);
    final authorName = checkin.author?.displayName ?? (isMe ? context.l10n.accountabilityMe : context.l10n.accountabilityPartner);

    return Container(
      margin: const EdgeInsets.only(bottom: DS.sm),
      padding: const EdgeInsets.all(DS.md),
      decoration: BoxDecoration(
        color: isMe
            ? DS.brandPrimary.withValues(alpha: 0.08)
            : DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                authorName,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: isMe ? DS.brandPrimary : DS.textPrimary,
                  fontSize: DS.fontSizeSm,
                ),
              ),
              const SizedBox(width: DS.sm),
              Icon(
                moodVisual.icon,
                size: 16,
                color: moodVisual.color,
              ),
              const SizedBox(width: DS.xs),
              Text(
                moodVisual.label,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textSecondary,
                ),
              ),
              const SizedBox(width: DS.sm),
              if (checkin.minutes > 0)
                Text(
                  context.l10n.accountabilityCheckinMinutes(checkin.minutes),
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.textSecondary,
                  ),
                ),
              const Spacer(),
              Text(
                dateStr,
                style: TextStyle(fontSize: DS.fontSizeXs, color: DS.neutral400),
              ),
            ],
          ),
          const SizedBox(height: DS.xs),
          Text(
            checkin.content,
            style: const TextStyle(fontSize: DS.fontSizeSm),
          ),
          const SizedBox(height: DS.spacing12),
          Row(
            children: [
              Icon(Icons.favorite, size: 16, color: DS.error),
              const SizedBox(width: DS.xs),
              Text(
                '${checkin.likes}',
                style: TextStyle(color: DS.textSecondary),
              ),
              const SizedBox(width: DS.spacing16),
              Icon(Icons.chat_bubble_outline, size: 16, color: DS.neutral500),
              const SizedBox(width: DS.xs),
              Text(
                '${checkin.encouragements.length}',
                style: TextStyle(color: DS.textSecondary),
              ),
              const Spacer(),
              if (!isMe) ...[
                TextButton.icon(
                  onPressed: () => _likeCheckin(context, ref),
                  icon: const Icon(Icons.thumb_up_alt_outlined, size: 16),
                  label: Text(context.l10n.accountabilityLike),
                ),
                TextButton.icon(
                  onPressed: () => _encourageCheckin(context, ref),
                  icon: const Icon(Icons.bolt_outlined, size: 16),
                  label: Text(context.l10n.accountabilityEncourage),
                ),
              ],
            ],
          ),
          if (checkin.encouragements.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              runSpacing: DS.xs,
              children: checkin.encouragements
                  .map(
                    (item) => Container(
                      width: double.infinity,
                      margin: const EdgeInsets.only(bottom: DS.xs),
                      padding: const EdgeInsets.all(DS.sm),
                      decoration: BoxDecoration(
                        color: DS.surfaceTertiary,
                        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                      ),
                      child: Text(
                        item.message,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textSecondary,
                        ),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _likeCheckin(BuildContext context, WidgetRef ref) async {
    try {
      await ref
          .read(accountabilityActionsProvider)
          .likeCheckin(ref, checkin.id);
      ref.invalidate(accountabilityDashboardProvider(checkin.partnershipId));
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.accountabilityEncourageSent);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '${context.l10n.accountabilityLikeFailed}: $e');
      }
    }
  }

  Future<void> _encourageCheckin(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final message = await showSensoryDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(context.l10n.accountabilitySendEncourage),
        content: TextField(
          controller: controller,
          maxLines: 3,
          decoration: InputDecoration(
            hintText: context.l10n.accountabilityEncourageHint,
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(context.l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: Text(context.l10n.accountabilitySend),
          ),
        ],
      ),
    );
    if (message == null || message.isEmpty) return;
    try {
      await ref
          .read(accountabilityActionsProvider)
          .encourageCheckin(ref, checkin.id, message);
      ref.invalidate(accountabilityDashboardProvider(checkin.partnershipId));
      if (context.mounted) {
        AppFeedback.success(context, context.l10n.accountabilityEncourageDelivered);
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '${context.l10n.accountabilitySendFailed}: $e');
      }
    }
  }
}

/// 打卡 BottomSheet
class AccountabilityCheckinSheet extends ConsumerStatefulWidget {
  const AccountabilityCheckinSheet({
    required this.partnershipId,
    required this.onDone,
    super.key,
  });

  final String partnershipId;
  final VoidCallback onDone;

  @override
  ConsumerState<AccountabilityCheckinSheet> createState() =>
      _AccountabilityCheckinSheetState();
}

class _AccountabilityCheckinSheetState
    extends ConsumerState<AccountabilityCheckinSheet> {
  final _contentController = TextEditingController();
  int _mood = 3;
  int _minutes = 30;
  bool _isLoading = false;

  @override
  void dispose() {
    _contentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: SingleChildScrollView(
          padding: EdgeInsets.only(
            left: DS.spacing16,
            right: DS.spacing16,
            top: DS.spacing16,
            bottom: MediaQuery.of(context).viewInsets.bottom + DS.spacing16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.accountabilityCheckInToday,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: DS.fontSizeLg,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              TextField(
                controller: _contentController,
                decoration: InputDecoration(
                  hintText: context.l10n.accountabilityTodayProgressHint,
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
                autofocus: true,
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                context.l10n.accountabilityTodayMood,
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.sm),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: List.generate(5, (i) {
                  final selected = _mood == i + 1;
                  final moodVisual = _checkinMoodVisuals(context)[i];
                  return GestureDetector(
                    onTap: () => setState(() => _mood = i + 1),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 200),
                      width: 64,
                      height: 64,
                      padding: const EdgeInsets.symmetric(vertical: DS.xs),
                      decoration: BoxDecoration(
                        color: selected
                            ? DS.brandPrimary.withValues(alpha: 0.15)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                        border: selected
                            ? Border.all(color: DS.brandPrimary, width: 2)
                            : Border.all(color: Colors.transparent),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            moodVisual.icon,
                            size: 22,
                            color:
                                selected ? DS.brandPrimary : moodVisual.color,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            moodVisual.label,
                            style: TextStyle(
                              fontSize: DS.fontSizeXs,
                              color:
                                  selected ? DS.brandPrimary : DS.textSecondary,
                              fontWeight: selected
                                  ? DS.fontWeightSemibold
                                  : DS.fontWeightMedium,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                context.l10n.accountabilityInvestedTime(_minutes),
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              Slider(
                value: _minutes.toDouble(),
                max: 360,
                divisions: 72,
                label: context.l10n.accountabilityMinutes(_minutes),
                onChanged: (v) => setState(() => _minutes = v.toInt()),
              ),
              const SizedBox(height: DS.spacing16),
              SizedBox(
                width: double.infinity,
                child: SparkleButton(
                  label: context.l10n.accountabilityPublishCheckin,
                  loading: _isLoading,
                  onPressed: _submit,
                  expand: true,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    final content = _contentController.text.trim();
    if (content.isEmpty) {
      AppFeedback.info(context, context.l10n.accountabilityProgressRequired);
      return;
    }

    setState(() => _isLoading = true);
    try {
      await ref.read(accountabilityRepositoryProvider).dailyCheckin(
            widget.partnershipId,
            content: content,
            mood: _mood,
            minutes: _minutes,
          );
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.checkin));
      widget.onDone();
      if (mounted) {
        Navigator.pop(context);
        AppFeedback.success(context, context.l10n.accountabilityCheckinSuccess);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '${context.l10n.accountabilityCheckinFailed}: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }
}
