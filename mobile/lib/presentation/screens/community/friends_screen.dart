import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class FriendsScreen extends StatelessWidget {
  const FriendsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Friends'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'My Friends'),
              Tab(text: 'Requests'),
              Tab(text: 'Discover'),
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
          return const Center(child: EmptyState(message: 'No friends yet', icon: Icons.people_outline));
        }
        return RefreshIndicator(
          onRefresh: () => ref.read(friendsProvider.notifier).refresh(),
          child: ListView.builder(
            itemCount: friends.length,
            padding: const EdgeInsets.all(16),
            itemBuilder: (context, index) {
              final friendInfo = friends[index];
              final friend = friendInfo.friend;
              return ListTile(
                leading: CircleAvatar(
                  backgroundImage: friend.avatarUrl != null ? NetworkImage(friend.avatarUrl!) : null,
                  child: friend.avatarUrl == null ? Text(friend.displayName[0]) : null,
                ),
                title: Text(friend.displayName),
                subtitle: Text('Level ${friend.flameLevel} • ${friendInfo.status}'),
                trailing: const Icon(Icons.chat_bubble_outline),
                onTap: () {
                  // TODO: Navigate to chat with friend
                },
              );
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator.circular()),
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
            padding: const EdgeInsets.all(16),
            itemBuilder: (context, index) {
              final request = requests[index];
              final user = request.friend; // In pending requests, 'friend' is the other user
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundImage: user.avatarUrl != null ? NetworkImage(user.avatarUrl!) : null,
                    child: user.avatarUrl == null ? Text(user.displayName[0]) : null,
                  ),
                  title: Text(user.displayName),
                  subtitle: request.matchReason != null 
                    ? Text('Match: ${request.matchReason.toString()}') 
                    : const Text('Wants to be your friend'),
                  trailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.check, color: Colors.green),
                        onPressed: () {
                          ref.read(pendingRequestsProvider.notifier).respondToRequest(request.id, true);
                          // Refresh friends list if accepted
                          ref.read(friendsProvider.notifier).refresh();
                        },
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.red),
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
      loading: () => const Center(child: LoadingIndicator.circular()),
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
            padding: const EdgeInsets.all(16),
            itemBuilder: (context, index) {
              final rec = recommendations[index];
              return Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundImage: rec.user.avatarUrl != null ? NetworkImage(rec.user.avatarUrl!) : null,
                    child: rec.user.avatarUrl == null ? Text(rec.user.displayName[0]) : null,
                  ),
                  title: Text(rec.user.displayName),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Match: ${(rec.matchScore * 100).toInt()}%'),
                      if (rec.matchReasons.isNotEmpty)
                        Text(rec.matchReasons.join(', '), style: const TextStyle(fontSize: 12, color: Colors.grey)),
                    ],
                  ),
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
      loading: () => const Center(child: LoadingIndicator.circular()),
      error: (e, s) => Center(child: CustomErrorWidget.page(message: e.toString(), onRetry: () => ref.read(friendRecommendationsProvider.notifier).refresh())),
    );
  }
}
