import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

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
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(widget.displayName ?? '好友详情'),
      ),
      child: FutureBuilder<FriendProfileDetail>(
        future: _profileFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.error_outline, color: DS.error, size: 48),
                  const SizedBox(height: DS.md),
                  Text(
                    'Failed to load profile',
                    style: theme.textTheme.bodyMedium
                        ?.copyWith(color: DS.textSecondary),
                  ),
                  const SizedBox(height: DS.md),
                  CustomButton.secondary(
                    text: 'Retry',
                    onPressed: () => setState(() {
                      _profileFuture = ref
                          .read(communityRepositoryProvider)
                          .getFriendProfile(widget.userId);
                    }),
                  ),
                ],
              ),
            );
          }
          final profile = snapshot.data!;
          return _buildContent(context, profile);
        },
      ),
    );
  }

  Widget _buildContent(BuildContext context, FriendProfileDetail profile) {
    final theme = Theme.of(context);
    final user = profile.user;
    final relationshipSummary = profile.relationshipSummary ?? const {};
    final achievementsSummary = profile.achievementsSummary ?? const {};
    final accountability = profile.accountability ?? const {};
    final quickActions = profile.quickActions;
    final canOpenDashboard =
        quickActions['can_open_dashboard'] == true &&
        accountability['id'] != null;
    final canInviteAccountability =
        quickActions['can_invite_accountability'] != false;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(DS.spacing24),
      child: Column(
        children: [
          const SizedBox(height: DS.spacing16),
          DecoratedBox(
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
          const SizedBox(height: DS.spacing16),
          Text(
            user.displayName,
            style: theme.textTheme.headlineSmall
                ?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: DS.xs),
          Text(
            '@${user.username}',
            style:
                theme.textTheme.bodyMedium?.copyWith(color: DS.textSecondary),
          ),
          const SizedBox(height: DS.spacing16),
          Container(
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
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing24),
          if (relationshipSummary.isNotEmpty || achievementsSummary.isNotEmpty)
            _RelationshipPanel(
              relationshipSummary: relationshipSummary,
              achievementsSummary: achievementsSummary,
              recentShares: profile.recentShares,
              hasAccountability: accountability.isNotEmpty,
            ),
          const SizedBox(height: DS.spacing24),
          Row(
            children: [
              Expanded(
                child: CustomButton.primary(
                  text: 'Message',
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
                  text: canOpenDashboard ? '工作台' : '分享',
                  icon: canOpenDashboard
                      ? Icons.handshake_outlined
                      : Icons.share_outlined,
                  onPressed: () {
                    if (canOpenDashboard) {
                      final id = accountability['id']?.toString();
                      if (id == null) return;
                      context.push(
                        CommunityRoutes.accountabilityDetail
                            .replaceFirst(':id', id),
                      );
                    } else {
                      context.push('/achievements');
                    }
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.md),
          SizedBox(
            width: double.infinity,
            child: CustomButton.secondary(
              text: canInviteAccountability ? '发起责任伙伴' : '进入伙伴工作台',
              icon: Icons.handshake_outlined,
              onPressed: () {
                if (canInviteAccountability) {
                  _showAccountabilityInvite(context, user);
                  return;
                }
                final id = accountability['id']?.toString();
                if (id == null) return;
                context.push(
                  CommunityRoutes.accountabilityDetail.replaceFirst(':id', id),
                );
              },
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
          title: const Text('发起责任伙伴邀请'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '邀请 ${user.displayName} 成为你的责任伙伴',
                style: TextStyle(color: DS.textSecondary, fontSize: 13),
              ),
              const SizedBox(height: DS.spacing16),
              TextField(
                controller: goalController,
                decoration: const InputDecoration(
                  labelText: '我的目标',
                  hintText: '例如：每天学习英语 30 分钟',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
              const SizedBox(height: DS.spacing16),
              const Text(
                '打卡频率:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: DS.xs),
              Wrap(
                spacing: DS.sm,
                children: [1, 2, 3, 7].map((d) {
                  final selected = checkInDays == d;
                  return FilterChip(
                    label: Text(d == 1 ? '每天' : '每 $d 天'),
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
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('发送邀请'),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return;
    final goal = goalController.text.trim();
    if (goal.isEmpty) {
      if (context.mounted) AppFeedback.info(context, '请填写目标');
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
        AppFeedback.success(context, '责任伙伴邀请已发送！');
      }
    } catch (e) {
      if (context.mounted) AppFeedback.error(context, '发送失败: $e');
    }
  }
}

class _RelationshipPanel extends StatelessWidget {
  const _RelationshipPanel({
    required this.relationshipSummary,
    required this.achievementsSummary,
    required this.recentShares,
    required this.hasAccountability,
  });

  final Map<String, dynamic> relationshipSummary;
  final Map<String, dynamic> achievementsSummary;
  final List<Map<String, dynamic>> recentShares;
  final bool hasAccountability;

  @override
  Widget build(BuildContext context) {
    return Container(
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
                hasAccountability ? '责任伙伴关系' : '好友关系',
                style: DS.titleMedium.copyWith(fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _InfoChip('一起 ${relationshipSummary['days_together'] ?? 0} 天'),
              _InfoChip('我 ${relationshipSummary['my_streak_days'] ?? 0} 天'),
              _InfoChip('TA ${relationshipSummary['partner_streak_days'] ?? 0} 天'),
            ],
          ),
          if (achievementsSummary.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(
              '伙伴共成长',
              style: DS.labelLarge.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              '我解锁了 ${achievementsSummary['my_total_unlocked'] ?? 0} 个责任伙伴成就，TA 解锁了 ${achievementsSummary['partner_total_unlocked'] ?? 0} 个。',
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            ),
          ],
          if (recentShares.isNotEmpty) ...[
            const SizedBox(height: 14),
            Text(
              '最近共享',
              style: DS.labelLarge.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            ...recentShares.take(2).map(
                  (share) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text(
                      '• ${share['title'] ?? '已分享内容'}',
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip(this.label);

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: DS.brandPrimary.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: DS.labelSmall.copyWith(
          color: DS.brandPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}
