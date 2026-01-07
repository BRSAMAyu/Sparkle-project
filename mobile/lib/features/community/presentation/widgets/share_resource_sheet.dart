import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';

Future<void> showShareResourceSheet(
  BuildContext context, {
  required String resourceType,
  required String resourceId,
  required String title,
  String? subtitle,
}) async {
  await showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => ShareResourceSheet(
      resourceType: resourceType,
      resourceId: resourceId,
      title: title,
      subtitle: subtitle,
    ),
  );
}

class ShareResourceSheet extends ConsumerStatefulWidget {
  const ShareResourceSheet({
    required this.resourceType,
    required this.resourceId,
    required this.title,
    this.subtitle,
    super.key,
  });

  final String resourceType;
  final String resourceId;
  final String title;
  final String? subtitle;

  @override
  ConsumerState<ShareResourceSheet> createState() => _ShareResourceSheetState();
}

class _ShareResourceSheetState extends ConsumerState<ShareResourceSheet>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _commentController = TextEditingController();

  String? _selectedUserId;
  String? _selectedGroupId;
  bool _isSharing = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _commentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final friendsState = ref.watch(friendsProvider);
    final groupsState = ref.watch(myGroupsProvider);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: EdgeInsets.only(
            left: DS.lg,
            right: DS.lg,
            top: DS.lg,
            bottom: MediaQuery.of(context).viewInsets.bottom + DS.lg,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: DS.neutral300,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
              const SizedBox(height: DS.md),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '分享到社群',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              const SizedBox(height: DS.sm),
              _buildResourcePreview(),
              const SizedBox(height: DS.md),
              TabBar(
                controller: _tabController,
                labelColor: DS.brandPrimary,
                tabs: const [
                  Tab(text: '好友'),
                  Tab(text: '群组'),
                ],
              ),
              SizedBox(
                height: 220,
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildFriendsList(friendsState),
                    _buildGroupsList(groupsState),
                  ],
                ),
              ),
              const SizedBox(height: DS.sm),
              TextField(
                controller: _commentController,
                maxLines: 2,
                decoration: const InputDecoration(
                  hintText: '添加分享留言（可选）',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: DS.md),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isSharing ? null : _share,
                  child: _isSharing
                      ? const LoadingIndicator(size: 20)
                      : const Text('立即分享'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResourcePreview() => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: DS.neutral200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.title,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            if (widget.subtitle != null && widget.subtitle!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                widget.subtitle!,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: DS.textSecondary, fontSize: 12),
              ),
            ],
          ],
        ),
      );

  Widget _buildFriendsList(AsyncValue<List<FriendshipInfo>> state) =>
      state.when(
        data: (friends) => friends.isEmpty
            ? _buildEmpty('暂无好友')
            : ListView.separated(
                itemCount: friends.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final friend = friends[index].friend;
                  final isSelected = _selectedUserId == friend.id;
                  return ListTile(
                    leading: SparkleAvatar(
                      radius: 16,
                      url: friend.avatarUrl,
                      fallbackText: friend.displayName,
                    ),
                    title: Text(friend.displayName),
                    trailing: Icon(
                      isSelected ? Icons.check_circle : Icons.circle_outlined,
                      color: isSelected ? DS.brandPrimary : DS.neutral400,
                    ),
                    onTap: () {
                      setState(() {
                        _selectedUserId = friend.id;
                        _selectedGroupId = null;
                      });
                    },
                  );
                },
              ),
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, _) => _buildEmpty('加载失败: $e'),
      );

  Widget _buildGroupsList(AsyncValue<List<GroupListItem>> state) => state.when(
        data: (groups) => groups.isEmpty
            ? _buildEmpty('暂无群组')
            : ListView.separated(
                itemCount: groups.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final group = groups[index];
                  final isSelected = _selectedGroupId == group.id;
                  return ListTile(
                    leading: CircleAvatar(
                      radius: 16,
                      backgroundColor: DS.brandPrimary.withValues(alpha: 0.2),
                      child: const Icon(Icons.groups, size: 16),
                    ),
                    title: Text(group.name),
                    subtitle: Text('${group.memberCount} members'),
                    trailing: Icon(
                      isSelected ? Icons.check_circle : Icons.circle_outlined,
                      color: isSelected ? DS.brandPrimary : DS.neutral400,
                    ),
                    onTap: () {
                      setState(() {
                        _selectedGroupId = group.id;
                        _selectedUserId = null;
                      });
                    },
                  );
                },
              ),
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, _) => _buildEmpty('加载失败: $e'),
      );

  Widget _buildEmpty(String message) => Center(
        child: Text(
          message,
          style: TextStyle(color: DS.textSecondary),
        ),
      );

  Future<void> _share() async {
    if (_selectedGroupId == null && _selectedUserId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请选择好友或群组')),
      );
      return;
    }

    setState(() => _isSharing = true);
    try {
      await ref.read(communityShareRepositoryProvider).shareResource(
            resourceType: widget.resourceType,
            resourceId: widget.resourceId,
            targetGroupId: _selectedGroupId,
            targetUserId: _selectedUserId,
            comment: _commentController.text.trim().isEmpty
                ? null
                : _commentController.text.trim(),
          );

      if (!mounted) return;
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('分享成功')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('分享失败: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => _isSharing = false);
      }
    }
  }
}
