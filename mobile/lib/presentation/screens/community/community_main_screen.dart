import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/widgets/community/community_widgets.dart';
import 'package:sparkle/core/design/sparkle_theme.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';

class CommunityMainScreen extends ConsumerWidget {
  const CommunityMainScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('星火社群', style: TextStyle(fontWeight: FontWeight.bold)),
          centerTitle: false,
          actions: [
            IconButton(icon: const Icon(Icons.search), onPressed: () {}),
            IconButton(icon: const Icon(Icons.person_add_outlined), onPressed: () {}),
          ],
          bottom: const TabBar(
            tabs: [Tab(text: '好友'), Tab(text: '群组')],
            indicatorColor: SparkleTheme.primary,
            labelStyle: TextStyle(fontWeight: FontWeight.bold),
          ),
        ),
        body: TabBarView(
          children: [
            _buildFriendsList(ref),
            _buildGroupsList(ref),
          ],
        ),
        floatingActionButton: FloatingActionButton(
          onPressed: () {},
          child: const Icon(Icons.add),
        ),
      ),
    );
  }

  Widget _buildFriendsList(WidgetRef ref) {
    final friendsAsync = ref.watch(friendsProvider);
    return friendsAsync.when(
      data: (friends) => ListView.builder(
        padding: const EdgeInsets.symmetric(vertical: 8),
        itemCount: friends.length,
        itemBuilder: (context, index) {
          final f = friends[index];
          return ListTile(
            leading: StatusAvatar(status: f.friend.status, url: f.friend.avatarUrl),
            title: Text(f.friend.displayName),
            subtitle: Text(f.friend.status == UserStatus.online ? '在线' : '离线'),
            trailing: const Icon(Icons.chevron_right, size: 20),
            onTap: () => context.push('/community/chat/private/${f.friend.id}'),
          );
        },
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }

  Widget _buildGroupsList(WidgetRef ref) {
    final groupsAsync = ref.watch(myGroupsProvider);
    return groupsAsync.when(
      data: (groups) => GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
          maxCrossAxisExtent: 400,
          mainAxisExtent: 100,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
        ),
        itemCount: groups.length,
        itemBuilder: (context, index) {
          final g = groups[index];
          return Card(
            child: ListTile(
              leading: SparkleAvatar(
                radius: 20,
                backgroundColor: SparkleTheme.primary.withValues(alpha: 0.1),
                fallbackText: g.name,
              ),
              title: Text(g.name, style: const TextStyle(fontWeight: FontWeight.bold)),
              subtitle: Text('${g.memberCount} 成员 · 火力 ${g.totalFlamePower}'),
              onTap: () => context.push('/community/chat/group/${g.id}'),
            ),
          );
        },
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }
}
