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
              ? '责任伙伴'
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
            itemBuilder: (_) => const [
              PopupMenuItem(
                value: 'end',
                child: Text('结束伙伴关系'),
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
                  '伙伴工作台加载失败',
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
                  label: '重试',
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
    return partner?.displayName ?? '责任伙伴';
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
            '已通过站内提醒发送，对方在线时会实时看到';
        AppFeedback.success(context, deliverySummary);
      }
    } catch (e) {
      if (mounted) {
        final message = e.toString();
        if (message.contains('429') || message.contains('cooldown')) {
          AppFeedback.info(
            context,
            '刚提醒过，冷却期内不会重复发送。提醒会以站内提示的形式送达，对方在线时会实时看到。',
          );
        } else {
          AppFeedback.error(context, '提醒发送失败，请稍后再试');
        }
      }
    }
  }

  Future<void> _confirmEnd() async {
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('结束伙伴关系'),
        content: const Text('确定要结束这段责任伙伴关系吗？'),
        actions: [
          SparkleButton.ghost(
            label: '取消',
            onPressed: () => Navigator.pop(ctx, false),
          ),
          SparkleButton(
            label: '结束',
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
          AppFeedback.success(context, '伙伴关系已结束');
        }
      } catch (e) {
        if (mounted) {
          AppFeedback.error(context, '操作失败: $e');
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
    final partnerName = partner?.displayName ?? '责任伙伴';
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
                  title: '我的目标',
                  goal: isInitiator
                      ? partnership.initiatorGoal
                      : partnership.partnerGoal ?? '还没有填写目标',
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: dashboard.foresightHint?.hintText?.isNotEmpty ?? false
                    ? 5
                    : 4,
                child: _GoalPanel(
                  title: '$partnerName 的目标',
                  goal: isInitiator
                      ? partnership.partnerGoal ?? '对方还没填写目标'
                      : partnership.initiatorGoal,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: dashboard.foresightHint?.hintText?.isNotEmpty ?? false
                    ? 6
                    : 5,
                child: _SectionCard(
                  title: '伙伴共成长',
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
                    title: '最近分享',
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
                                          share['title']?.toString() ?? '已分享内容',
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
                  title: '月度打卡热力图',
                  child: AccountabilityHeatmap(
                    year: (dashboard.heatmap['year'] as int?) ??
                        DateTime.now().year,
                    heatmap: ((dashboard.heatmap['heatmap']
                                as List<dynamic>?) ??
                            const [])
                        .map((item) => Map<String, dynamic>.from(item as Map))
                        .toList(),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              SparkleStaggerItem(
                index: 6,
                child: _SectionCard(
                  title: '伙伴成就',
                  child: partnerAchievements.isEmpty
                      ? Text(
                          '伙伴还没有解锁专属成就，先互相打卡一轮试试看。',
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
                '最近打卡',
                style: DS.titleLarge.copyWith(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.spacing8),
              if (dashboard.timeline.isEmpty)
                _SectionCard(
                  title: '还没有打卡记录',
                  child: Text(
                    '今天先发一条简短进展，伙伴关系就会开始有温度。',
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
              label: stats.myCheckedInToday ? '今天已打卡' : '今日打卡',
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
                      name: '我',
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
                            '一起坚持了 ${relationshipSummary['days_together'] ?? 0} 天',
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
                                  '总打卡',
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
                      name: 'TA',
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
                      label: stats.myCheckedInToday ? '已打卡' : '打卡',
                      onTap: onCheckin,
                    ),
                    _HeroAction(
                      icon: Icons.bolt_outlined,
                      label: '提醒',
                      onTap: onNudge,
                    ),
                    _HeroAction(
                      icon: Icons.share_outlined,
                      label: '分享',
                      onTap: onShare,
                    ),
                    _HeroAction(
                      icon: Icons.chat_bubble_outline,
                      label: '聊天',
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
    final partnerName = partner?.displayName ?? '责任伙伴';
    final isPending = partnership.status == AccountabilityStatus.pending;
    final message = isPending
        ? (isInitiator ? '邀请已发出，等待对方确认后才能进入伙伴工作台。' : '这条伙伴邀请还待你确认，先去邀请页处理后再回来。')
        : '当前伙伴关系暂时不可进入完整工作台。';

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
                isPending ? '伙伴邀请待处理' : '伙伴工作台暂不可用',
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
                      label: isInitiator ? '查看状态' : '去处理邀请',
                      onPressed: () =>
                          unawaited(context.pushNamed('friendRequests')),
                    ),
                  if (canChat)
                    SparkleButton.ghost(
                      label: '继续聊天',
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
              label: '我 ${relationshipSummary['my_streak_days'] ?? 0} 天',
            ),
            _TinyMetric(
              label: 'TA ${relationshipSummary['partner_streak_days'] ?? 0} 天',
            ),
            _TinyMetric(label: '我解锁 $myAchievements 个成就'),
            _TinyMetric(label: 'TA 解锁 $partnerAchievements 个成就'),
          ],
        ),
        if (streakBoard.isNotEmpty) ...[
          const SizedBox(height: DS.spacing12),
          Text(
            '连续打卡榜：你第 ${streakBoard['my_rank'] ?? '-'}，伙伴第 ${streakBoard['partner_rank'] ?? '-'}',
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
            '$streakDays 天',
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
        ? '当前没有待执行的问责策略。'
        : nextTriggerAt == null
            ? '已有 $count 条策略就绪，等待事件触发。'
            : '已有 $count 条策略待执行，下一次触发在 ${DateFormat('M月d日 HH:mm').format(nextTriggerAt)}。';
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
                '待执行策略',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            count <= 0 ? '0 条' : '$count 条',
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
        ? '最近还没有新的跨事件反思。'
        : lastAt == null
            ? '最近已生成 $count 条反思摘要。'
            : '最近一次聚焦 ${_labelForCategory(lastCategory)}，更新时间 ${DateFormat('M月d日 HH:mm').format(lastAt)}。';
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
                '近期反思',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            count <= 0 ? '0 条' : '$count 条',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  fontWeight: DS.fontWeightBold,
                ),
          ),
          if ((lastCategory ?? '').isNotEmpty) ...[
            const SizedBox(height: DS.spacing6),
            _TinyMetric(label: _labelForCategory(lastCategory)),
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

  static String _labelForCategory(String? category) {
    switch (category) {
      case 'intervention_ineffective':
        return '干预未奏效';
      case 'plan_stall':
        return '计划停滞';
      case 'overload':
        return '负荷过载';
      case 'too_difficult':
        return '任务过难';
      case 'unclear':
        return '任务不清晰';
      case 'abandoned':
        return '中途放下';
      default:
        return '反思摘要';
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
    final confidenceItems = summary?.attractorConfidences ?? const [];
    final subtitle = [
      if (deviationCount > 0) '检测到 $deviationCount 个偏离',
      if (generatedAt != null) '更新时间 ${DateFormat('M月d日 HH:mm').format(generatedAt)}',
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
                '前瞻提示',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            hintText ?? '暂无前瞻提示。',
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
                          '${_labelForDim(item.dim)} ${item.confidence.toStringAsFixed(2)}',
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }

  static String _labelForDim(String dim) {
    switch (dim) {
      case 'study_pace':
        return '节奏';
      case 'completion_rate':
        return '完成率';
      case 'engagement_level':
        return '投入度';
      case 'mood_valence':
        return '情绪';
      case 'plan_adherence':
        return '计划跟随';
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

const _checkinMoodVisuals = <_CheckinMoodVisual>[
  _CheckinMoodVisual(
    icon: Icons.sentiment_very_dissatisfied_rounded,
    label: '低落',
    color: Color(0xFFE57373),
  ),
  _CheckinMoodVisual(
    icon: Icons.sentiment_dissatisfied_rounded,
    label: '一般',
    color: Color(0xFFFFB74D),
  ),
  _CheckinMoodVisual(
    icon: Icons.sentiment_neutral_rounded,
    label: '平稳',
    color: Color(0xFF90A4AE),
  ),
  _CheckinMoodVisual(
    icon: Icons.sentiment_satisfied_alt_rounded,
    label: '不错',
    color: Color(0xFF66BB6A),
  ),
  _CheckinMoodVisual(
    icon: Icons.mood_rounded,
    label: '很棒',
    color: Color(0xFF26A69A),
  ),
];

_CheckinMoodVisual _resolveCheckinMoodVisual(int mood) =>
    _checkinMoodVisuals[(mood - 1).clamp(0, _checkinMoodVisuals.length - 1)];

class _CheckinTile extends ConsumerWidget {
  const _CheckinTile({required this.checkin, required this.isMe});

  final AccountabilityCheckinInfo checkin;
  final bool isMe;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dateStr = DateFormat('MM-dd HH:mm').format(checkin.createdAt);
    final moodVisual = _resolveCheckinMoodVisual(checkin.mood);
    final authorName = checkin.author?.displayName ?? (isMe ? '我' : '伙伴');

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
                  '${checkin.minutes}分钟',
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
                  label: const Text('点赞'),
                ),
                TextButton.icon(
                  onPressed: () => _encourageCheckin(context, ref),
                  icon: const Icon(Icons.bolt_outlined, size: 16),
                  label: const Text('鼓励'),
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
        AppFeedback.success(context, '已为伙伴点亮鼓励');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '点赞失败: $e');
      }
    }
  }

  Future<void> _encourageCheckin(BuildContext context, WidgetRef ref) async {
    final controller = TextEditingController();
    final message = await showSensoryDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('发送鼓励'),
        content: TextField(
          controller: controller,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText: '写一句你想对伙伴说的话',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('发送'),
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
        AppFeedback.success(context, '鼓励已送达');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '发送失败: $e');
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
              const Text(
                '今日打卡',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: DS.fontSizeLg,
                ),
              ),
              const SizedBox(height: DS.spacing16),
              TextField(
                controller: _contentController,
                decoration: const InputDecoration(
                  hintText: '今日进展...',
                  border: OutlineInputBorder(),
                ),
                maxLines: 3,
                autofocus: true,
              ),
              const SizedBox(height: DS.spacing16),
              const Text(
                '今日心情:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.sm),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: List.generate(5, (i) {
                  final selected = _mood == i + 1;
                  final moodVisual = _checkinMoodVisuals[i];
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
                '投入时长: $_minutes 分钟',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              Slider(
                value: _minutes.toDouble(),
                max: 360,
                divisions: 72,
                label: '$_minutes 分钟',
                onChanged: (v) => setState(() => _minutes = v.toInt()),
              ),
              const SizedBox(height: DS.spacing16),
              SizedBox(
                width: double.infinity,
                child: SparkleButton(
                  label: '发布打卡',
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
      AppFeedback.info(context, '请写一句今天的进展');
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
        AppFeedback.success(context, '打卡成功，伙伴已经能看到了');
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '打卡失败: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }
}
