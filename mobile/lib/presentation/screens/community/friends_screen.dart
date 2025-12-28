import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class FriendsScreen extends StatelessWidget {
  const FriendsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.community),
          bottom: TabBar(
            tabs: [
              Tab(text: l10n.languageChinese == '简体中文' ? '我的好友' : 'My Friends'),
              Tab(text: l10n.languageChinese == '简体中文' ? '好友请求' : 'Requests'),
              Tab(text: l10n.languageChinese == '简体中文' ? '发现' : 'Discover'),
            ],
          ),
        ),
        body: const TabBarView(
          children: [
            _MyFriendsTab(),
            _PendingRequestsTab(),
            _RecommendationsTab(),
          ],
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

    return friendsState.when(
      data: (friends) {
        if (friends.isEmpty) {
          return const Center(child: CompactEmptyState(message: 'No friends yet', icon: Icons.people_outline));
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
                  context.push('/community/chat/private/${friend.id}?name=${Uri.encodeComponent(friend.displayName)}');
                },
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Row(
                    children: [
                      DecoratedBox(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: DS.brandPrimary, width: 2),
                          boxShadow: [
                            BoxShadow(color: DS.brandPrimary.withValues(alpha: 0.05), blurRadius: 4, offset: const Offset(0, 2)),
                          ],
                        ),
                        child: CircleAvatar(
                          backgroundImage: friend.avatarUrl != null ? NetworkImage(friend.avatarUrl!) : null,
                          child: friend.avatarUrl == null ? Text(friend.displayName[0]) : null,
                        ),
                      ),
                      const SizedBox(width: DS.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(friend.displayName, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 16)),
                            Text('Lv.${friend.flameLevel}', style: const TextStyle(color: DS.brandPrimary, fontSize: 12)),
                          ],
                        ),
                      ),
                      const Icon(Icons.chevron_right, size: 20, color: DS.brandPrimary),
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator()),
      error: (e, s) => Center(child: CustomErrorWidget.page(message: e.toString(), onRetry: () => ref.read(friendsProvider.notifier).refresh())),
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
                    backgroundImage: user.avatarUrl != null ? NetworkImage(user.avatarUrl!) : null,
                    child: user.avatarUrl == null ? Text(user.displayName[0]) : null,
                  ),
                  title: Text(user.displayName),
                  subtitle: const Text('Wants to be your friend'),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.check, color: DS.success),
                        onPressed: () {
                          ref.read(pendingRequestsProvider.notifier).respondToRequest(request.id, true);
                          ref.read(friendsProvider.notifier).refresh();
                        },
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: DS.error),
                        onPressed: () {
                          ref.read(pendingRequestsProvider.notifier).respondToRequest(request.id, false);
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
      error: (e, s) => Center(child: CustomErrorWidget.page(message: e.toString(), onRetry: () => ref.read(pendingRequestsProvider.notifier).refresh())),
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
          onRefresh: () => ref.read(friendRecommendationsProvider.notifier).refresh(),
          child: ListView.builder(
            itemCount: recommendations.length,
            padding: const EdgeInsets.all(DS.lg),
            itemBuilder: (context, index) {
              final rec = recommendations[index];
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundImage: rec.user.avatarUrl != null ? NetworkImage(rec.user.avatarUrl!) : null,
                    child: rec.user.avatarUrl == null ? Text(rec.user.displayName[0]) : null,
                  ),
                  title: Text(rec.user.displayName),
                  subtitle: Text('Match: ${(rec.matchScore * 100).toInt()}%'),
                  trailing: IconButton(
                    icon: const Icon(Icons.person_add),
                    onPressed: () {
                       ref.read(friendRecommendationsProvider.notifier).sendRequest(rec.user.id);
                       ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Request sent')));
                    },
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator()),
      error: (e, s) => Center(child: CustomErrorWidget.page(message: e.toString(), onRetry: () => ref.read(friendRecommendationsProvider.notifier).refresh())),
    );
  }
}