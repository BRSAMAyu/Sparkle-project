import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/empty_state.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class GroupListScreen extends ConsumerWidget {
  const GroupListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsState = ref.watch(myGroupsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('我的社群'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () {
              context.push('/community/groups/search');
            },
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          context.push('/community/groups/create');
        },
        icon: const Icon(Icons.add),
        label: const Text('创建/加入'),
        backgroundColor: AppDesignTokens.primaryColor,
      ),
      body: groupsState.when(
        data: (groups) {
          if (groups.isEmpty) {
            return Center(
              child: CompactEmptyState(
                message: '你还没有加入任何社群',
                icon: Icons.group_outlined,
                actionText: '去发现',
                onAction: () {
                  context.push('/community/groups/search');
                },
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              return ref.read(myGroupsProvider.notifier).refresh();
            },
            child: ListView.separated(
              padding: const EdgeInsets.all(AppDesignTokens.spacing16),
              itemCount: groups.length,
              separatorBuilder: (context, index) =>
                  const SizedBox(height: AppDesignTokens.spacing12),
              itemBuilder: (context, index) {
                final group = groups[index];
                return _GroupListTile(group: group);
              },
            ),
          );
        },
        loading: () => const Center(
          child: LoadingIndicator.circular(showText: true),
        ),
        error: (error, stackTrace) => Center(
          child: CustomErrorWidget.page(
            message: error.toString(),
            onRetry: () {
              ref.read(myGroupsProvider.notifier).refresh();
            },
          ),
        ),
      ),
    );
  }
}

class _GroupListTile extends StatelessWidget {
  final GroupListItem group;

  const _GroupListTile({required this.group});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppDesignTokens.borderRadius12),
      ),
      child: InkWell(
        onTap: () {
          context.push('/community/groups/${group.id}');
        },
        borderRadius: BorderRadius.circular(AppDesignTokens.borderRadius12),
        child: Padding(
          padding: const EdgeInsets.all(AppDesignTokens.spacing16),
          child: Row(
            children: [
              // Avatar placeholder or actual avatar
              CircleAvatar(
                radius: 24,
                backgroundColor: group.isSprint ? Colors.orange.shade100 : Colors.blue.shade100,
                child: Icon(
                   group.isSprint ? Icons.timer : Icons.school,
                   color: group.isSprint ? Colors.orange : Colors.blue,
                ),
              ),
              const SizedBox(width: AppDesignTokens.spacing16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      group.name,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(Icons.local_fire_department,
                            size: 14, color: Colors.orange.shade700),
                        const SizedBox(width: 4),
                        Text(
                          '${group.totalFlamePower}',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(width: 12),
                        Icon(Icons.people, size: 14, color: Colors.grey.shade600),
                        const SizedBox(width: 4),
                        Text(
                          '${group.memberCount}人',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                    if (group.isSprint && group.daysRemaining != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 4.0),
                        child: Text(
                          '距离截止还有 ${group.daysRemaining} 天',
                          style: TextStyle(
                            color: Colors.red.shade700,
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.grey),
            ],
          ),
        ),
      ),
    );
  }
}
