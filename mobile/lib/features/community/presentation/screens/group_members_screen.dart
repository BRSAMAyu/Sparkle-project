import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/shared/entities/user_brief.dart';

class GroupMembersScreen extends ConsumerStatefulWidget {
  const GroupMembersScreen({
    required this.groupId,
    required this.groupName,
    this.myRole,
    super.key,
  });

  final String groupId;
  final String groupName;
  final GroupRole? myRole;

  @override
  ConsumerState<GroupMembersScreen> createState() => _GroupMembersScreenState();
}

class _GroupMembersScreenState extends ConsumerState<GroupMembersScreen> {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  bool get _canManage => widget.myRole == GroupRole.owner || widget.myRole == GroupRole.admin;

  @override
  Widget build(BuildContext context) {
    final membersState = ref.watch(groupMembersProvider(widget.groupId));

    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.groupName} - Members'),
        actions: [
          if (_canManage)
            IconButton(
              icon: const Icon(Icons.person_add),
              onPressed: () {
                // TODO: Navigate to invite members screen
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Invite members feature coming soon')),
                );
              },
            ),
        ],
      ),
      body: ContentConstraint(
        child: Column(
          children: [
            // Search bar
            Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search members...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                        },
                      )
                    : null,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(DS.borderRadiusMD),
                ),
                filled: true,
                fillColor: DS.neutral50,
              ),
              onChanged: (value) => setState(() => _searchQuery = value.toLowerCase()),
            ),
          ),

          // Members list
          Expanded(
            child: membersState.when(
              data: (members) {
                final filteredMembers = _searchQuery.isEmpty
                    ? members
                    : members.where((m) =>
                        m.user.username.toLowerCase().contains(_searchQuery) ||
                        (m.user.nickname?.toLowerCase().contains(_searchQuery) ?? false),
                      ).toList();

                if (filteredMembers.isEmpty) {
                  return Center(
                    child: Text(
                      _searchQuery.isEmpty ? 'No members yet' : 'No members found',
                      style: TextStyle(color: DS.neutral500, fontSize: 16),
                    ),
                  );
                }

                // Group by role
                final owners = filteredMembers.where((m) => m.role == GroupRole.owner).toList();
                final admins = filteredMembers.where((m) => m.role == GroupRole.admin).toList();
                final regularMembers = filteredMembers.where((m) => m.role == GroupRole.member).toList();

                return ListView(
                  children: [
                    if (owners.isNotEmpty) ...[
                      _buildSectionHeader('Owner (${owners.length})'),
                      ...owners.map(_buildMemberTile),
                    ],
                    if (admins.isNotEmpty) ...[
                      _buildSectionHeader('Admins (${admins.length})'),
                      ...admins.map(_buildMemberTile),
                    ],
                    if (regularMembers.isNotEmpty) ...[
                      _buildSectionHeader('Members (${regularMembers.length})'),
                      ...regularMembers.map(_buildMemberTile),
                    ],
                  ],
                );
              },
              loading: () => const Center(
                child: CircularProgressIndicator(),
              ),
              error: (e, st) => Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.error_outline, size: 64, color: DS.error),
                    const SizedBox(height: DS.md),
                    Text(
                      'Failed to load members',
                      style: TextStyle(color: DS.error, fontSize: 16),
                    ),
                    const SizedBox(height: DS.md),
                    ElevatedButton(
                      onPressed: () =>
                          ref.read(groupMembersProvider(widget.groupId).notifier).refresh(),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) => Padding(
      padding: const EdgeInsets.fromLTRB(DS.spacing16, DS.lg, DS.spacing16, DS.sm),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: DS.neutral600,
        ),
      ),
    );

  Widget _buildMemberTile(GroupMemberInfo member) {
    final isOwner = member.role == GroupRole.owner;
    final isAdmin = member.role == GroupRole.admin;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: DS.spacing16, vertical: DS.xs),
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: BorderRadius.circular(DS.borderRadiusMD),
        border: Border.all(color: DS.neutral200),
      ),
      child: ListTile(
        leading: Stack(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: _getFlameColor(member.flameContribution),
              child: member.user.avatarUrl != null
                  ? ClipOval(
                      child: Image.network(
                        member.user.avatarUrl!,
                        width: 48,
                        height: 48,
                        fit: BoxFit.cover,
                        errorBuilder: (ctx, err, stack) => _buildDefaultAvatar(member.user),
                      ),
                    )
                  : _buildDefaultAvatar(member.user),
            ),
            // Online status indicator
            if (member.user.status == UserStatus.online)
              Positioned(
                right: 0,
                bottom: 0,
                child: Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: DS.success,
                    shape: BoxShape.circle,
                    border: Border.all(color: DS.brandPrimaryConst, width: 2),
                  ),
                ),
              ),
          ],
        ),
        title: Row(
          children: [
            Flexible(
              child: Text(
                member.user.displayName,
                style: TextStyle(
                  fontWeight: isOwner || isAdmin ? FontWeight.bold : FontWeight.normal,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (isOwner) ...[
              const SizedBox(width: DS.xs),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: DS.warning,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'OWNER',
                  style: TextStyle(fontSize: 10, color: DS.neutral900, fontWeight: FontWeight.bold),
                ),
              ),
            ] else if (isAdmin) ...[
              const SizedBox(width: DS.xs),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: DS.primaryBase,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  'ADMIN',
                  style: TextStyle(fontSize: 10, color: DS.brandPrimaryConst, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '@${member.user.username}',
              style: TextStyle(fontSize: 12, color: DS.neutral500),
            ),
            const SizedBox(height: DS.xs),
            Row(
              children: [
                Icon(Icons.local_fire_department, size: 14, color: DS.warning),
                const SizedBox(width: 4),
                Text(
                  '${member.flameContribution} flame · ${member.tasksCompleted} tasks · ${member.checkinStreak} day streak',
                  style: TextStyle(fontSize: 11, color: DS.neutral600),
                ),
              ],
            ),
          ],
        ),
        trailing: _canManage && member.role != GroupRole.owner
            ? PopupMenuButton<String>(
                icon: Icon(Icons.more_vert, color: DS.neutral400),
                onSelected: (choice) => _handleMemberAction(member, choice),
                itemBuilder: (context) {
                  final items = <PopupMenuEntry<String>>[];

                  if (widget.myRole == GroupRole.owner) {
                    if (member.role == GroupRole.admin) {
                      items.add(const PopupMenuItem(
                        value: 'demote',
                        child: Row(
                          children: [
                            Icon(Icons.arrow_downward, size: 18),
                            SizedBox(width: DS.sm),
                            Text('Demote to Member'),
                          ],
                        ),
                      ),);
                    } else {
                      items.add(const PopupMenuItem(
                        value: 'promote',
                        child: Row(
                          children: [
                            Icon(Icons.arrow_upward, size: 18),
                            SizedBox(width: DS.sm),
                            Text('Promote to Admin'),
                          ],
                        ),
                      ),);
                    }
                    items.add(PopupMenuItem(
                      value: 'transfer',
                      child: Row(
                        children: [
                          Icon(Icons.supervisor_account, size: 18, color: DS.warning),
                          const SizedBox(width: DS.sm),
                          Text('Transfer Ownership', style: TextStyle(color: DS.warning)),
                        ],
                      ),
                    ),);
                  }

                  items.add(const PopupMenuDivider());

                  items.add(PopupMenuItem(
                    value: 'kick',
                    child: Row(
                      children: [
                        Icon(Icons.person_remove, size: 18, color: DS.error),
                        const SizedBox(width: DS.sm),
                        Text('Remove from Group', style: TextStyle(color: DS.error)),
                      ],
                    ),
                  ),);

                  return items;
                },
              )
            : null,
        onTap: () {
          // TODO: Navigate to user profile
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('View ${member.user.displayName}\'s profile')),
          );
        },
      ),
    );
  }

  Widget _buildDefaultAvatar(UserBrief user) => CircleAvatar(
      backgroundColor: _getFlameColor(user.flameLevel),
      child: Text(
        user.displayName.substring(0, 1).toUpperCase(),
        style: TextStyle(
          color: DS.brandPrimaryConst,
          fontWeight: FontWeight.bold,
          fontSize: 20,
        ),
      ),
    );

  Color _getFlameColor(int flamePower) {
    if (flamePower >= 10000) return DS.error;
    if (flamePower >= 5000) return DS.warning;
    if (flamePower >= 2000) return DS.primaryBase;
    return DS.neutral300;
  }

  Future<void> _handleMemberAction(GroupMemberInfo member, String action) async {
    switch (action) {
      case 'promote':
        final confirmed = await _showConfirmDialog(
          'Promote ${member.user.displayName}?',
          'This member will become an admin and can manage the group.',
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref.read(groupMembersProvider(widget.groupId).notifier).promoteMember(member.user.id);
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('${member.user.displayName} promoted to admin')),
              );
            }
          } catch (e) {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to promote: $e')),
              );
            }
          }
        }

      case 'demote':
        final confirmed = await _showConfirmDialog(
          'Demote ${member.user.displayName}?',
          'This admin will become a regular member.',
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref.read(groupMembersProvider(widget.groupId).notifier).demoteMember(member.user.id);
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('${member.user.displayName} demoted to member')),
              );
            }
          } catch (e) {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to demote: $e')),
              );
            }
          }
        }

      case 'transfer':
        final confirmed = await _showConfirmDialog(
          'Transfer ownership to ${member.user.displayName}?',
          'You will become a regular member. This action cannot be undone.',
          isDestructive: true,
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref.read(groupMembersProvider(widget.groupId).notifier).transferOwnership(member.user.id);
            if (mounted) {
              context.pop(); // Go back to group detail
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Ownership transferred to ${member.user.displayName}')),
              );
            }
          } catch (e) {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to transfer: $e')),
              );
            }
          }
        }

      case 'kick':
        final confirmed = await _showConfirmDialog(
          'Remove ${member.user.displayName}?',
          'This member will be removed from the group.',
          isDestructive: true,
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref.read(groupMembersProvider(widget.groupId).notifier).kickMember(member.user.id);
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('${member.user.displayName} removed from group')),
              );
            }
          } catch (e) {
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Failed to remove: $e')),
              );
            }
          }
        }
    }
  }

  Future<bool?> _showConfirmDialog(String title, String message, {bool isDestructive = false}) => showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: isDestructive ? DS.error : DS.primaryBase),
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
}
