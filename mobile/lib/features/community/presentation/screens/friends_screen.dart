import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/accountability_model.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
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
    final friendsState = ref.watch(friendsProvider);
    final partnershipsState = ref.watch(myPartnershipsProvider);

    return Column(
      children: [
        // 责任伙伴入口卡片（置顶）
        _AccountabilityPartnersCard(partnershipsState: partnershipsState),
        // 好友列表
        Expanded(
          child: friendsState.when(
            data: (friends) {
              if (friends.isEmpty) {
                return const Center(
                  child: CompactEmptyState(
                    message: 'No friends yet',
                    icon: Icons.people_outline,
                  ),
                );
              }
              return RefreshIndicator(
                onRefresh: () => ref.read(friendsProvider.notifier).refresh(),
                child: ListView.builder(
                  itemCount: friends.length,
                  padding: const EdgeInsets.all(DS.lg),
                  itemBuilder: (context, index) {
                    final friendInfo = friends[index];
                    final friend = friendInfo.friend;
                    return InkWell(
                      onTap: () {
                        context.push(
                          '/chat/private/${friend.id}?name=${Uri.encodeComponent(friend.displayName)}',
                        );
                      },
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        child: Row(
                          children: [
                            DecoratedBox(
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                    color: DS.brandPrimaryConst, width: 2),
                                boxShadow: [
                                  BoxShadow(
                                    color: DS.brandPrimaryConst
                                        .withValues(alpha: 0.05),
                                    blurRadius: 4,
                                    offset: const Offset(0, 2),
                                  ),
                                ],
                              ),
                              child: CircleAvatar(
                                backgroundImage: friend.avatarUrl != null
                                    ? NetworkImage(friend.avatarUrl!)
                                    : null,
                                child: friend.avatarUrl == null
                                    ? Text(friend.displayName[0])
                                    : null,
                              ),
                            ),
                            const SizedBox(width: DS.md),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    friend.displayName,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w500,
                                      fontSize: 16,
                                    ),
                                  ),
                                  Text(
                                    'Lv.${friend.flameLevel}',
                                    style: TextStyle(
                                      color: DS.brandPrimaryConst,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            SparkleIconButton(
                              variant: ButtonVariant.ghost,
                              size: 32,
                              icon: Icon(
                                Icons.person_outline,
                                size: 18,
                                color: DS.neutral500,
                              ),
                              onPressed: () {
                                context.push(
                                  '/community/users/${friend.id}?name=${Uri.encodeComponent(friend.displayName)}',
                                );
                              },
                            ),
                            Icon(
                              Icons.chevron_right,
                              size: 20,
                              color: DS.brandPrimaryConst,
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
                onRetry: () => ref.read(friendsProvider.notifier).refresh(),
              ),
            ),
          ),
        ),
      ],
    );
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
