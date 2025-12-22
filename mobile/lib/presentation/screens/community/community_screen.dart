import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class CommunityScreen extends StatelessWidget {
  const CommunityScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('社群'),
          centerTitle: true,
          actions: [
            IconButton(
              icon: const Icon(Icons.search),
              onPressed: () {
                context.push('/community/groups/search');
              },
            ),
          ],
          bottom: const TabBar(
            tabs: [
              Tab(text: '我的群组', icon: Icon(Icons.groups_rounded, size: 20)),
              Tab(text: '好友', icon: Icon(Icons.people_rounded, size: 20)),
            ],
            indicatorColor: AppDesignTokens.primaryBase,
            labelColor: AppDesignTokens.primaryBase,
          ),
        ),
        body: const TabBarView(
          children: [
            _GroupsTab(),
            _FriendsTab(),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: () {
            context.push('/community/groups/create');
          },
          icon: const Icon(Icons.add),
          label: const Text('创建群组'),
          backgroundColor: AppDesignTokens.primaryBase,
        ),
      ),
    );
  }
}

class _GroupsTab extends ConsumerWidget {
  const _GroupsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsState = ref.watch(myGroupsProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return groupsState.when(
      data: (groups) {
        if (groups.isEmpty) {
          return Center(
            child: CompactEmptyState(
              message: '还没有加入任何群组',
              icon: Icons.group_outlined,
              actionText: '发现群组',
              onAction: () {
                context.push('/community/groups/search');
              },
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: () => ref.read(myGroupsProvider.notifier).refresh(),
          child: ListView.builder(
            padding: const EdgeInsets.all(AppDesignTokens.spacing16),
            itemCount: groups.length,
            itemBuilder: (context, index) {
              final group = groups[index];
              return _GroupCard(group: group, isDark: isDark);
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator()),
      error: (error, stack) => Center(
        child: CustomErrorWidget.page(
          message: error.toString(),
          onRetry: () => ref.read(myGroupsProvider.notifier).refresh(),
        ),
      ),
    );
  }
}

class _GroupCard extends StatelessWidget {
  final GroupListItem group;
  final bool isDark;

  const _GroupCard({required this.group, required this.isDark});

  @override
  Widget build(BuildContext context) {
    final isSprint = group.isSprint;

    return Card(
      margin: const EdgeInsets.only(bottom: AppDesignTokens.spacing12),
      child: InkWell(
        onTap: () {
          context.push('/community/groups/${group.id}');
        },
        borderRadius: AppDesignTokens.borderRadius12,
        child: Padding(
          padding: const EdgeInsets.all(AppDesignTokens.spacing16),
          child: Row(
            children: [
              // Group Avatar
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: isSprint
                      ? const LinearGradient(colors: [Color(0xFFFF6B35), Color(0xFFFF8C5A)])
                      : const LinearGradient(colors: [Color(0xFF5C6BC0), Color(0xFF7986CB)]),
                ),
                child: Icon(
                  isSprint ? Icons.timer_rounded : Icons.school_rounded,
                  color: Colors.white,
                  size: 24,
                ),
              ),
              const SizedBox(width: AppDesignTokens.spacing12),
              // Group Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            group.name,
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 15,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (isSprint && group.daysRemaining != null)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.red.shade50,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Text(
                              '${group.daysRemaining}天',
                              style: TextStyle(
                                color: Colors.red.shade700,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.local_fire_department_rounded, size: 14, color: Colors.orange.shade400),
                        const SizedBox(width: 4),
                        Text(
                          '${group.totalFlamePower}',
                          style: TextStyle(
                            fontSize: 12,
                            color: isDark ? Colors.white70 : Colors.grey.shade600,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Icon(Icons.people_alt_rounded, size: 14, color: isDark ? Colors.white54 : Colors.grey.shade500),
                        const SizedBox(width: 4),
                        Text(
                          '${group.memberCount}人',
                          style: TextStyle(
                            fontSize: 12,
                            color: isDark ? Colors.white70 : Colors.grey.shade600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppDesignTokens.neutral400),
            ],
          ),
        ),
      ),
    );
  }
}

class _FriendsTab extends ConsumerWidget {
  const _FriendsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final friendsState = ref.watch(friendsProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return friendsState.when(
      data: (friends) {
        if (friends.isEmpty) {
          return const Center(
            child: CompactEmptyState(
              message: '还没有好友',
              icon: Icons.people_outline,
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: () => ref.read(friendsProvider.notifier).refresh(),
          child: ListView.builder(
            padding: const EdgeInsets.all(AppDesignTokens.spacing16),
            itemCount: friends.length,
            itemBuilder: (context, index) {
              final friendInfo = friends[index];
              final friend = friendInfo.friend;
              return Card(
                margin: const EdgeInsets.only(bottom: AppDesignTokens.spacing8),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundImage: friend.avatarUrl != null ? NetworkImage(friend.avatarUrl!) : null,
                    backgroundColor: AppDesignTokens.primaryBase.withOpacity(0.2),
                    child: friend.avatarUrl == null
                        ? Text(
                            friend.displayName[0].toUpperCase(),
                            style: const TextStyle(
                              color: AppDesignTokens.primaryBase,
                              fontWeight: FontWeight.bold,
                            ),
                          )
                        : null,
                  ),
                  title: Text(
                    friend.displayName,
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  ),
                  subtitle: Text(
                    'Lv.${friend.flameLevel} · ${friendInfo.status}',
                    style: TextStyle(
                      fontSize: 12,
                      color: isDark ? Colors.white54 : Colors.grey.shade600,
                    ),
                  ),
                  trailing: IconButton(
                    icon: const Icon(
                      Icons.chat_bubble_outline,
                      color: AppDesignTokens.primaryBase,
                    ),
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('私聊功能开发中')),
                      );
                    },
                  ),
                  onTap: () {
                    // Navigate to friend profile or chat
                  },
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: LoadingIndicator()),
      error: (error, stack) => Center(
        child: CustomErrorWidget.page(
          message: error.toString(),
          onRetry: () => ref.read(friendsProvider.notifier).refresh(),
        ),
      ),
    );
  }
}
