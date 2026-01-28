import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

class UserSearchScreen extends ConsumerStatefulWidget {
  const UserSearchScreen({super.key});

  @override
  ConsumerState<UserSearchScreen> createState() => _UserSearchScreenState();
}

class _UserSearchScreenState extends ConsumerState<UserSearchScreen> {
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _handleSearch() {
    final query = _searchController.text.trim();
    if (query.isNotEmpty) {
      ref.read(userSearchProvider.notifier).search(query);
    }
  }

  void _showUserOptions(UserBrief user) {
    showModalBottomSheet<void>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: CircleAvatar(
                backgroundImage: user.avatarUrl != null
                    ? NetworkImage(user.avatarUrl!)
                    : null,
                child: user.avatarUrl == null
                    ? Text(user.displayName.substring(0, 1).toUpperCase())
                    : null,
              ),
              title: Text(user.displayName),
              subtitle: Text('@${user.username}'),
            ),
            const Divider(),
            ListTile(
              leading: Icon(Icons.person_add, color: DS.primaryBase),
              title: const Text('Send Friend Request'),
              onTap: () async {
                Navigator.pop(context);
                try {
                  await ref.read(friendRecommendationsProvider.notifier)
                      .sendRequest(user.id);
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Friend request sent to ${user.displayName}'),
                        backgroundColor: DS.success,
                      ),
                    );
                  }
                } catch (e) {
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Failed to send request: $e'),
                        backgroundColor: DS.error,
                      ),
                    );
                  }
                }
              },
            ),
            ListTile(
              leading: Icon(Icons.chat, color: DS.primaryBase),
              title: const Text('Send Message'),
              onTap: () {
                Navigator.pop(context);
                context.push(
                  '/chat/private/${user.id}?name=${Uri.encodeComponent(user.displayName)}',
                );
              },
            ),
            const SizedBox(height: DS.spacing8),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final searchState = ref.watch(userSearchProvider);

    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _searchController,
          autofocus: true,
          decoration: InputDecoration(
            hintText: 'Search users by name or username...',
            border: InputBorder.none,
            hintStyle: TextStyle(color: DS.brandPrimary70),
          ),
          style: TextStyle(color: DS.brandPrimary),
          onSubmitted: (_) => _handleSearch(),
          textInputAction: TextInputAction.search,
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: _handleSearch,
          ),
        ],
      ),
      body: searchState.when(
        data: (users) {
          if (users.isEmpty) {
            return Center(
              child: CompactEmptyState(
                message: _searchController.text.isEmpty
                    ? 'Search for users by name or username'
                    : 'No users found',
                icon: Icons.search,
              ),
            );
          }
          return ContentConstraint(
            child: RefreshIndicator(
              onRefresh: () async {
                if (_searchController.text.isNotEmpty) {
                  _handleSearch();
                }
              },
              child: ListView.separated(
                padding: const EdgeInsets.all(DS.lg),
                itemCount: users.length,
                separatorBuilder: (context, index) => const SizedBox(height: DS.md),
                itemBuilder: (context, index) {
                  final user = users[index];
                  return Card(
                    elevation: 2,
                    child: ListTile(
                      leading: Stack(
                        children: [
                          CircleAvatar(
                            backgroundImage: user.avatarUrl != null
                                ? NetworkImage(user.avatarUrl!)
                                : null,
                            child: user.avatarUrl == null
                                ? Text(user.displayName.substring(0, 1).toUpperCase())
                                : null,
                          ),
                          if (user.status == UserStatus.online)
                            Positioned(
                              right: 0,
                              bottom: 0,
                              child: Container(
                                width: 12,
                                height: 12,
                                decoration: BoxDecoration(
                                  color: DS.success,
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                    color: DS.brandPrimaryConst,
                                    width: 2,
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                      title: Text(
                        user.displayName,
                        style: const TextStyle(fontWeight: FontWeight.w500),
                      ),
                      subtitle: Text('@${user.username}'),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: DS.warning.shade100,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              'Lv.${user.flameLevel}',
                              style: TextStyle(
                                color: DS.warning.shade700,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                          const SizedBox(width: DS.sm),
                          Icon(Icons.chevron_right, color: DS.brandPrimary),
                        ],
                      ),
                      onTap: () => _showUserOptions(user),
                    ),
                  );
                },
              ),
            ),
          );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, s) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: DS.error),
              const SizedBox(height: DS.lg),
              Text('Error: $e'),
              const SizedBox(height: DS.md),
              ElevatedButton(
                onPressed: _handleSearch,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
