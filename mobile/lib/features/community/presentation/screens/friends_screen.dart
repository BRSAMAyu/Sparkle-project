import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/friends_hub_view.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class FriendsScreen extends StatelessWidget {
  const FriendsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(l10n.community),
          bottom: TabBar(
            tabs: [
              Tab(text: l10n.languageChinese == '简体中文' ? '我的好友' : 'My Friends'),
              Tab(text: l10n.languageChinese == '简体中文' ? '好友请求' : 'Requests'),
              Tab(text: l10n.languageChinese == '简体中文' ? '发现' : 'Discover'),
            ],
          ),
        ),
        body: const ContentConstraint(
          child: TabBarView(
            children: [
              _MyFriendsTab(),
              _PendingRequestsTab(),
              _RecommendationsTab(),
            ],
          ),
        ),
      ),
    );
  }
}

class _MyFriendsTab extends ConsumerWidget {
  const _MyFriendsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const FriendsHubView(
      padding: EdgeInsets.fromLTRB(16, 16, 16, 24),
    );
  }

  void _showFriendContextMenu(
    BuildContext context,
    WidgetRef ref,
    FriendshipInfo friendInfo,
  ) {
    final friend = friendInfo.friend;
    unawaited(showSensoryModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        decoration: BoxDecoration(
          color: Theme.of(ctx).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header with user info
              Padding(
                padding: const EdgeInsets.all(DS.spacing16),
                child: Row(
                  children: [
                    CircleAvatar(
                      backgroundImage: friend.avatarUrl != null
                          ? NetworkImage(friend.avatarUrl!)
                          : null,
                      child: friend.avatarUrl == null
                          ? Text(friend.displayName[0])
                          : null,
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            friend.displayName,
                            style: DS.titleLarge
                                .copyWith(fontWeight: FontWeight.bold),
                          ),
                          Text(
                            'Lv.${friend.flameLevel}',
                            style: DS.bodySmall
                                .copyWith(color: DS.brandPrimaryConst),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(height: 1),
              // Delete friend option
              ListTile(
                leading: Icon(Icons.person_remove, color: DS.neutral600),
                title: const Text('删除好友'),
                onTap: () {
                  Navigator.pop(ctx);
                  _handleDeleteFriend(context, ref, friendInfo);
                },
              ),
              // Block user option
              ListTile(
                leading: Icon(Icons.block, color: DS.error),
                title: Text('拉黑用户', style: TextStyle(color: DS.error)),
                onTap: () {
                  Navigator.pop(ctx);
                  _handleBlockUser(context, ref, friendInfo);
                },
              ),
              // Blocked users management
              ListTile(
                leading: Icon(Icons.block_outlined, color: DS.neutral600),
                title: const Text('黑名单管理'),
                onTap: () {
                  Navigator.pop(ctx);
                  context.push(CommunityRoutes.blockedUsers);
                },
              ),
              const SizedBox(height: DS.spacing8),
            ],
          ),
        ),
      ),
    ));
  }

  Future<void> _handleDeleteFriend(
    BuildContext context,
    WidgetRef ref,
    FriendshipInfo friendInfo,
  ) async {
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除好友'),
        content: Text('确定要删除好友 ${friendInfo.friend.displayName} 吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: DS.error),
            child: const Text('删除'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref.read(friendsProvider.notifier).deleteFriend(friendInfo.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('已删除 ${friendInfo.friend.displayName}'),
              backgroundColor: DS.success,
            ),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('删除失败: $e'),
              backgroundColor: DS.error,
            ),
          );
        }
      }
    }
  }

  Future<void> _handleBlockUser(
    BuildContext context,
    WidgetRef ref,
    FriendshipInfo friendInfo,
  ) async {
    final confirmed = await showSensoryDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('拉黑用户'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('拉黑 ${friendInfo.friend.displayName} 后:'),
            const SizedBox(height: 8),
            const Text('• 从好友列表移除'),
            const Text('• 无法发送消息给你'),
            const Text('• 无法发送好友请求'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: DS.error),
            child: const Text('拉黑'),
          ),
        ],
      ),
    );

    if (confirmed == true && context.mounted) {
      try {
        await ref
            .read(friendsProvider.notifier)
            .blockUser(friendInfo.friend.id);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('已拉黑 ${friendInfo.friend.displayName}'),
              backgroundColor: DS.success,
            ),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('拉黑失败: $e'),
              backgroundColor: DS.error,
            ),
          );
        }
      }
    }
  }
}

class _PendingRequestsTab extends ConsumerWidget {
  const _PendingRequestsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requestsState = ref.watch(pendingRequestsProvider);

    return requestsState.when(
      data: (requests) {
        if (requests.isEmpty) {
          return const Center(child: Text('No pending requests'));
        }
        return RefreshIndicator(
          onRefresh: () => ref.read(pendingRequestsProvider.notifier).refresh(),
          child: ListView.builder(
            itemCount: requests.length,
            padding: const EdgeInsets.all(DS.lg),
            itemBuilder: (context, index) {
              final request = requests[index];
              final user = request.friend;
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundImage: user.avatarUrl != null
                        ? NetworkImage(user.avatarUrl!)
                        : null,
                    child: user.avatarUrl == null
                        ? Text(user.displayName[0])
                        : null,
                  ),
                  title: Text(user.displayName),
                  subtitle: const Text('Wants to be your friend'),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        size: 36,
                        icon: Icon(Icons.check, color: DS.success),
                        onPressed: () {
                          ref
                              .read(pendingRequestsProvider.notifier)
                              .respondToRequest(request.id, true);
                          ref.read(friendsProvider.notifier).refresh();
                        },
                      ),
                      SparkleIconButton(
                        variant: ButtonVariant.ghost,
                        size: 36,
                        icon: Icon(Icons.close, color: DS.error),
                        onPressed: () {
                          ref
                              .read(pendingRequestsProvider.notifier)
                              .respondToRequest(request.id, false);
                        },
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator()),
      error: (e, s) => Center(
        child: CustomErrorWidget.page(
          context: context,
          message: e.toString(),
          onRetry: () => ref.read(pendingRequestsProvider.notifier).refresh(),
        ),
      ),
    );
  }
}

class _RecommendationsTab extends ConsumerWidget {
  const _RecommendationsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recommendationsState = ref.watch(friendRecommendationsProvider);

    return recommendationsState.when(
      data: (recommendations) {
        if (recommendations.isEmpty) {
          return const Center(child: Text('No recommendations available'));
        }
        return RefreshIndicator(
          onRefresh: () =>
              ref.read(friendRecommendationsProvider.notifier).refresh(),
          child: ListView.builder(
            itemCount: recommendations.length,
            padding: const EdgeInsets.all(DS.lg),
            itemBuilder: (context, index) {
              final rec = recommendations[index];
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundImage: rec.user.avatarUrl != null
                        ? NetworkImage(rec.user.avatarUrl!)
                        : null,
                    child: rec.user.avatarUrl == null
                        ? Text(rec.user.displayName[0])
                        : null,
                  ),
                  title: Text(rec.user.displayName),
                  subtitle: Text('Match: ${(rec.matchScore * 100).toInt()}%'),
                  trailing: SparkleIconButton(
                    variant: ButtonVariant.ghost,
                    size: 36,
                    icon: const Icon(Icons.person_add),
                    onPressed: () {
                      ref
                          .read(friendRecommendationsProvider.notifier)
                          .sendRequest(rec.user.id);
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Request sent')),
                      );
                    },
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator()),
      error: (e, s) => Center(
        child: CustomErrorWidget.page(
          context: context,
          message: e.toString(),
          onRetry: () =>
              ref.read(friendRecommendationsProvider.notifier).refresh(),
        ),
      ),
    );
  }
}

/// 责任伙伴入口卡片（显示在好友列表顶部）
class _AccountabilityPartnersCard extends StatelessWidget {
  const _AccountabilityPartnersCard({required this.partnershipsState});

  final AsyncValue<List<AccountabilityPartnershipInfo>> partnershipsState;

  @override
  Widget build(BuildContext context) {
    return partnershipsState.when(
      loading: _buildSkeleton,
      error: (_, __) => const SizedBox.shrink(), // 静默失败，不影响好友列表
      data: (partnerships) {
        final activeCount = partnerships
            .where((p) => p.status == AccountabilityStatus.active)
            .length;
        final pendingCount = partnerships
            .where((p) => p.status == AccountabilityStatus.pending)
            .length;

        return GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          margin: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, DS.sm),
          onTap: () => context.push(CommunityRoutes.accountability),
          child: Row(
            children: [
              // 图标
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                ),
                child: Icon(
                  Icons.handshake_outlined,
                  color: DS.brandPrimaryConst,
                ),
              ),
              const SizedBox(width: DS.md),
              // 文字
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '我的责任伙伴',
                      style: DS.titleLarge.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: DS.xs),
                    Text(
                      _buildSubtitle(activeCount, pendingCount),
                      style: DS.bodySmall.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
              // 箭头
              Icon(Icons.chevron_right, color: DS.neutral400),
            ],
          ),
        );
      },
    );
  }

  String _buildSubtitle(int active, int pending) {
    if (active == 0 && pending == 0) {
      return '点击添加责任伙伴，互相监督成长';
    }
    final parts = <String>[];
    if (active > 0) parts.add('$active 位进行中');
    if (pending > 0) parts.add('$pending 位待确认');
    return parts.join(' · ');
  }

  Widget _buildSkeleton() => Container(
        margin: const EdgeInsets.fromLTRB(DS.lg, DS.lg, DS.lg, DS.sm),
        height: 80,
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        ),
      );
}
