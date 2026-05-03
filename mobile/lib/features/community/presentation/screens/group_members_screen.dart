import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_network_image.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

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

class _GroupMembersScreenState extends ConsumerState<GroupMembersScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _searchController.dispose();
    _tabController.dispose();
    super.dispose();
  }

  bool get _canManage =>
      widget.myRole == GroupRole.owner || widget.myRole == GroupRole.admin;

  @override
  Widget build(BuildContext context) {
    final membersState = ref.watch(groupMembersProvider(widget.groupId));

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(context.l10n.gmMembersTitle(widget.groupName)),
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: context.l10n.gmTabMembers),
            Tab(text: context.l10n.gmTabLeaderboard),
          ],
        ),
        actions: [
          if (_canManage)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.person_add),
              onPressed: () {
                AppFeedback.info(context, 'Invite feature coming soon');
              },
            ),
        ],
      ),
      child: ContentConstraint(
        child: TabBarView(
          controller: _tabController,
          children: [
            // ── Tab 1: Members list ──────────────────────────────────────
            Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(DS.spacing16),
                  child: TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: 'Search members...',
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _searchQuery.isNotEmpty
                          ? SparkleIconButton(
                              variant: ButtonVariant.ghost,
                              size: 32,
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
                      fillColor: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
                    ),
                    onChanged: (value) =>
                        setState(() => _searchQuery = value.toLowerCase()),
                  ),
                ),
                Expanded(
                  child: membersState.when(
                    data: (members) {
                      final filteredMembers = _searchQuery.isEmpty
                          ? members
                          : members
                              .where(
                                (m) =>
                                    m.user.username
                                        .toLowerCase()
                                        .contains(_searchQuery) ||
                                    (m.user.nickname
                                            ?.toLowerCase()
                                            .contains(_searchQuery) ??
                                        false),
                              )
                              .toList();

                      if (filteredMembers.isEmpty) {
                        return Center(
                          child: Text(
                            _searchQuery.isEmpty
                                ? 'No members yet'
                                : 'No members found',
                            style:
                                TextStyle(color: DS.neutral500, fontSize: 16),
                          ),
                        );
                      }

                      // Group by role
                      final owners = filteredMembers
                          .where((m) => m.role == GroupRole.owner)
                          .toList();
                      final admins = filteredMembers
                          .where((m) => m.role == GroupRole.admin)
                          .toList();
                      final regularMembers = filteredMembers
                          .where((m) => m.role == GroupRole.member)
                          .toList();

                      return ListView(
                        children: [
                          if (owners.isNotEmpty) ...[
                            _buildSectionHeader('Owner (${owners.length})'),
                            ...owners.asMap().entries.map(
                                  (entry) => SparkleStaggerItem(
                                    index: entry.key,
                                    child: _buildMemberTile(entry.value),
                                  ),
                                ),
                          ],
                          if (admins.isNotEmpty) ...[
                            _buildSectionHeader('Admins (${admins.length})'),
                            ...admins.asMap().entries.map(
                                  (entry) => SparkleStaggerItem(
                                    index: owners.length + entry.key,
                                    child: _buildMemberTile(entry.value),
                                  ),
                                ),
                          ],
                          if (regularMembers.isNotEmpty) ...[
                            _buildSectionHeader(
                              'Members (${regularMembers.length})',
                            ),
                            ...regularMembers.asMap().entries.map(
                                  (entry) => SparkleStaggerItem(
                                    index: owners.length +
                                        admins.length +
                                        entry.key,
                                    child: _buildMemberTile(entry.value),
                                  ),
                                ),
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
                            context.l10n.gmLoadFailed,
                            style: TextStyle(color: DS.error, fontSize: 16),
                          ),
                          const SizedBox(height: DS.md),
                          SparkleButton(
                            label: 'Retry',
                            onPressed: () => ref
                                .read(
                                  groupMembersProvider(widget.groupId).notifier,
                                )
                                .refresh(),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),

            // ── Tab 2: Leaderboard ───────────────────────────────────────
            membersState.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Text(
                  context.l10n.gmLoadMembersFailed,
                  style: TextStyle(color: DS.textSecondary),
                ),
              ),
              data: _buildLeaderboard,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLeaderboard(List<GroupMemberInfo> members) {
    final byFlame = [...members]
      ..sort((a, b) => b.flameContribution.compareTo(a.flameContribution));
    final byStreak = [...members]
      ..sort((a, b) => b.checkinStreak.compareTo(a.checkinStreak));
    final byTasks = [...members]
      ..sort((a, b) => b.tasksCompleted.compareTo(a.tasksCompleted));

    return DefaultTabController(
      length: 3,
      child: Column(
        children: [
          TabBar(
            tabs: [
              Tab(text: context.l10n.gmTabFlame),
              Tab(text: context.l10n.gmTabCheckin),
              Tab(text: context.l10n.gmTabTasks),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                _buildRankList(
                  byFlame,
                  value: (m) => context.l10n.gmFlameValue(m.flameContribution),
                ),
                _buildRankList(
                  byStreak,
                  value: (m) => context.l10n.gmDayValue(m.checkinStreak),
                ),
                _buildRankList(
                  byTasks,
                  value: (m) => context.l10n.gmTaskValue(m.tasksCompleted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRankList(
    List<GroupMemberInfo> members, {
    required String Function(GroupMemberInfo) value,
  }) =>
      ListView.builder(
        padding: const EdgeInsets.all(DS.spacing16),
        itemCount: members.length,
        itemBuilder: (ctx, i) {
          final m = members[i];
          final rankIcons = ['🥇', '🥈', '🥉'];
          return SparkleStaggerItem(
            index: i,
            child: ListTile(
              leading: Text(
                i < 3 ? rankIcons[i] : '${i + 1}',
                style: const TextStyle(fontSize: 20),
              ),
              title: Text(m.user.displayName),
              trailing: Text(
                value(m),
                style: TextStyle(
                  fontWeight: DS.fontWeightBold,
                  color: DS.brandPrimary,
                ),
              ),
            ),
          );
        },
      );

  Widget _buildSectionHeader(String title) => Padding(
        padding:
            const EdgeInsets.fromLTRB(DS.spacing16, DS.lg, DS.spacing16, DS.sm),
        child: Text(
          title,
          style: TextStyle(
            fontSize: 14,
            fontWeight: DS.fontWeightBold,
            color: DS.neutral600,
          ),
        ),
      );

  Widget _buildMemberTile(GroupMemberInfo member) {
    final isOwner = member.role == GroupRole.owner;
    final isAdmin = member.role == GroupRole.admin;

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      margin:
          const EdgeInsets.symmetric(horizontal: DS.spacing16, vertical: DS.xs),
      padding: EdgeInsets.zero,
      child: ListTile(
        leading: Stack(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: _getFlameColor(member.flameContribution),
              child: member.user.avatarUrl != null
                  ? ClipOval(
                      child: SparkleNetworkImage(
                        imageUrl: member.user.avatarUrl!,
                        width: 48,
                        height: 48,
                        errorWidget: _buildDefaultAvatar(member.user),
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
                    border: Border.all(
                      color: DS.surfaceRoleColor(SparkleSurfaceRole.card),
                      width: 2,
                    ),
                  ),
                ),
              ),
          ],
        ),
        title: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Flexible(
              child: Text(
                member.user.displayName,
                style: TextStyle(
                  fontWeight:
                      isOwner || isAdmin ? DS.fontWeightBold : FontWeight.normal,
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
                  style: TextStyle(
                    fontSize: 10,
                    color: DS.neutral900,
                    fontWeight: DS.fontWeightBold,
                  ),
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
                  style: TextStyle(
                    fontSize: 10,
                    color: DS.brandPrimaryConst,
                    fontWeight: DS.fontWeightBold,
                  ),
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
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12, color: DS.neutral500),
            ),
            const SizedBox(height: DS.xs),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Icon(Icons.local_fire_department, size: 14, color: DS.warning),
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
                      items.add(
                        PopupMenuItem(
                          value: 'demote',
                          child: Row(
                            children: [
                              Icon(Icons.arrow_downward, size: 18),
                              SizedBox(width: DS.sm),
                              Text(I18nService.instance.isChinese ? '降为普通成员' : 'Demote to Member'),
                            ],
                          ),
                        ),
                      );
                    } else {
                      items.add(
                        PopupMenuItem(
                          value: 'promote',
                          child: Row(
                            children: [
                              Icon(Icons.arrow_upward, size: 18),
                              SizedBox(width: DS.sm),
                              Text(I18nService.instance.isChinese ? '晋升为管理员' : 'Promote to Admin'),
                            ],
                          ),
                        ),
                      );
                    }
                    items.add(
                      PopupMenuItem(
                        value: 'transfer',
                        child: Row(
                          children: [
                            Icon(
                              Icons.supervisor_account,
                              size: 18,
                              color: DS.warning,
                            ),
                            const SizedBox(width: DS.sm),
                            Text(
                              I18nService.instance.isChinese ? '转让群主' : 'Transfer Ownership',
                              style: TextStyle(color: DS.warning),
                            ),
                          ],
                        ),
                      ),
                    );
                  }

                  items
                    ..add(const PopupMenuDivider())
                    // Mute / Warn actions for admin
                    ..add(
                      PopupMenuItem(
                        value: 'mute',
                        child: Row(
                          children: [
                            Icon(Icons.mic_off, size: 18, color: DS.warning),
                            const SizedBox(width: DS.sm),
                            Text(
                              context.l10n.gmMute,
                              style: TextStyle(color: DS.warning),
                            ),
                          ],
                        ),
                      ),
                    )
                    ..add(
                      PopupMenuItem(
                        value: 'warn',
                        child: Row(
                          children: [
                            Icon(Icons.warning_amber_outlined, size: 18),
                            SizedBox(width: DS.sm),
                            Text(context.l10n.gmSendWarning),
                          ],
                        ),
                      ),
                    )
                    ..add(const PopupMenuDivider())
                    ..add(
                      PopupMenuItem(
                        value: 'kick',
                        child: Row(
                          children: [
                            Icon(Icons.person_remove,
                                size: 18, color: DS.error),
                            const SizedBox(width: DS.sm),
                            Text(
                              context.l10n.gmKick,
                              style: TextStyle(color: DS.error),
                            ),
                          ],
                        ),
                      ),
                    );

                  return items;
                },
              )
            : null,
        onTap: () {
          unawaited(
            context.pushNamed(
              'userProfile',
              pathParameters: {'id': member.user.id},
              queryParameters: {'name': member.user.displayName},
            ),
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
            fontWeight: DS.fontWeightBold,
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

  Future<void> _handleMemberAction(
    GroupMemberInfo member,
    String action,
  ) async {
    switch (action) {
      case 'promote':
        final zh = I18nService.instance.isChinese;
        final confirmed = await _showConfirmDialog(
          zh ? '晋升 ${member.user.displayName}？' : 'Promote ${member.user.displayName}?',
          zh ? '此成员将成为管理员，可以管理群组。' : 'This member will become an admin and can manage the group.',
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref
                .read(groupMembersProvider(widget.groupId).notifier)
                .promoteMember(member.user.id);
            if (mounted) {
              AppFeedback.success(
                context,
                zh ? '${member.user.displayName} 已晋升为管理员' : '${member.user.displayName} promoted to admin',
              );
            }
          } catch (e) {
            if (mounted) {
              AppFeedback.error(context, zh ? '晋升失败：$e' : 'Failed to promote: $e');
            }
          }
        }

      case 'demote':
        final zh = I18nService.instance.isChinese;
        final confirmed = await _showConfirmDialog(
          zh ? '降权 ${member.user.displayName}？' : 'Demote ${member.user.displayName}?',
          zh ? '此管理员将成为普通成员。' : 'This admin will become a regular member.',
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref
                .read(groupMembersProvider(widget.groupId).notifier)
                .demoteMember(member.user.id);
            if (mounted) {
              AppFeedback.success(
                context,
                zh ? '${member.user.displayName} 已降为普通成员' : '${member.user.displayName} demoted to member',
              );
            }
          } catch (e) {
            if (mounted) {
              AppFeedback.error(context, zh ? '降权失败：$e' : 'Failed to demote: $e');
            }
          }
        }

      case 'transfer':
        final zh = I18nService.instance.isChinese;
        final confirmed = await _showConfirmDialog(
          zh ? '将群主转让给 ${member.user.displayName}？' : 'Transfer ownership to ${member.user.displayName}?',
          zh ? '你将成为普通成员。此操作无法撤销。' : 'You will become a regular member. This action cannot be undone.',
          isDestructive: true,
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref
                .read(groupMembersProvider(widget.groupId).notifier)
                .transferOwnership(member.user.id);
            if (mounted) {
              AppFeedback.success(
                context,
                zh ? '群主已转让给 ${member.user.displayName}' : 'Ownership transferred to ${member.user.displayName}',
              );
              context.pop(); // Go back to group detail
            }
          } catch (e) {
            if (mounted) {
              AppFeedback.error(context, zh ? '转让失败：$e' : 'Failed to transfer: $e');
            }
          }
        }

      case 'mute':
        await _showMuteDialog(member);

      case 'warn':
        await _showWarnDialog(member);

      case 'kick':
        final confirmed = await _showConfirmDialog(
          context.l10n.gmKickConfirm(member.user.displayName),
          context.l10n.gmKickConfirmMsg,
          isDestructive: true,
        );
        if ((confirmed ?? false) && mounted) {
          try {
            await ref
                .read(groupMembersProvider(widget.groupId).notifier)
                .kickMember(member.user.id);
            if (mounted) {
              AppFeedback.success(
                context,
                context.l10n.gmKicked(member.user.displayName),
              );
            }
          } catch (e) {
            if (mounted) {
              AppFeedback.error(
                  context, context.l10n.gmActionFailed(e.toString()));
            }
          }
        }
    }
  }

  Future<bool?> _showConfirmDialog(
    String title,
    String message, {
    bool isDestructive = false,
  }) =>
      showSensoryDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: [
            SparkleButton.ghost(
              label: context.l10n.gmCancel,
              onPressed: () => Navigator.pop(context, false),
            ),
            SparkleButton(
              label: context.l10n.gmConfirm,
              onPressed: () => Navigator.pop(context, true),
              variant: isDestructive
                  ? ButtonVariant.destructive
                  : ButtonVariant.primary,
            ),
          ],
        ),
      );

  Future<void> _showMuteDialog(GroupMemberInfo member) async {
    var durationMinutes = 60;
    final reasonController = TextEditingController();

    await showSensoryDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: Text(context.l10n.gmMuteTitle(member.user.displayName)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(context.l10n.gmMuteDuration),
              Wrap(
                spacing: DS.sm,
                children: [
                  for (final m in [15, 30, 60, 1440])
                    ChoiceChip(
                      label: Text(m >= 1440
                          ? context.l10n.gm24Hours
                          : context.l10n.gmMinutes(m)),
                      selected: durationMinutes == m,
                      onSelected: (_) => setState(() => durationMinutes = m),
                    ),
                ],
              ),
              const SizedBox(height: DS.md),
              TextField(
                controller: reasonController,
                decoration: InputDecoration(
                  labelText: context.l10n.gmMuteReason,
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
          actions: [
            SparkleButton.ghost(
              label: context.l10n.gmCancel,
              onPressed: () => Navigator.pop(ctx),
            ),
            SparkleButton.primary(
              label: context.l10n.gmConfirmMute,
              onPressed: () async {
                Navigator.pop(ctx);
                try {
                  await ref.read(communityRepositoryProvider).muteMember(
                        widget.groupId,
                        member.user.id,
                        durationMinutes,
                        reason: reasonController.text.trim().isEmpty
                            ? null
                            : reasonController.text.trim(),
                      );
                  if (!mounted) return;
                  AppFeedback.success(
                    context,
                    context.l10n.gmMuted(member.user.displayName),
                  );
                } catch (e) {
                  if (!mounted) return;
                  AppFeedback.error(
                      context, context.l10n.gmActionFailed(e.toString()));
                }
              },
            ),
          ],
        ),
      ),
    );
    reasonController.dispose();
  }

  Future<void> _showWarnDialog(GroupMemberInfo member) async {
    final reasonController = TextEditingController();

    await showSensoryDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(context.l10n.gmWarnTitle(member.user.displayName)),
        content: TextField(
          controller: reasonController,
          decoration: InputDecoration(
            labelText: context.l10n.gmWarnReason,
            border: OutlineInputBorder(),
          ),
          autofocus: true,
          maxLines: 3,
        ),
        actions: [
          SparkleButton.ghost(
            label: context.l10n.gmCancel,
            onPressed: () => Navigator.pop(ctx),
          ),
          SparkleButton.primary(
            label: context.l10n.gmSendWarningBtn,
            onPressed: () async {
              final reason = reasonController.text.trim();
              if (reason.isEmpty) {
                AppFeedback.info(ctx, context.l10n.gmWarnReasonRequired);
                return;
              }
              Navigator.pop(ctx);
              try {
                await ref
                    .read(communityRepositoryProvider)
                    .warnMember(widget.groupId, member.user.id, reason);
                if (!mounted) return;
                AppFeedback.success(
                  context,
                  context.l10n.gmWarned(member.user.displayName),
                );
              } catch (e) {
                if (!mounted) return;
                AppFeedback.error(
                    context, context.l10n.gmActionFailed(e.toString()));
              }
            },
          ),
        ],
      ),
    );
    reasonController.dispose();
  }
}
