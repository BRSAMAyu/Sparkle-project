import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/accountability_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

Future<void> showShareResourceSheet(
  BuildContext context, {
  required String resourceType,
  required String resourceId,
  required String title,
  String? subtitle,
}) async {
  final feedbackContext = context;
  await showSensoryModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
    builder: (context) => ShareResourceSheet(
      resourceType: resourceType,
      resourceId: resourceId,
      title: title,
      subtitle: subtitle,
      feedbackContext: feedbackContext,
    ),
  );
}

class ShareResourceSheet extends ConsumerStatefulWidget {
  const ShareResourceSheet({
    required this.resourceType,
    required this.resourceId,
    required this.title,
    this.subtitle,
    this.feedbackContext,
    super.key,
  });

  final String resourceType;
  final String resourceId;
  final String title;
  final String? subtitle;
  final BuildContext? feedbackContext;

  @override
  ConsumerState<ShareResourceSheet> createState() => _ShareResourceSheetState();
}

class _ShareResourceSheetState extends ConsumerState<ShareResourceSheet>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final TextEditingController _commentController = TextEditingController();

  String? _selectedUserId;
  String? _selectedGroupId;
  String? _autoSelectedPartnerId;
  bool _isSharing = false;

  String _shareErrorMessage(Object error) {
    final raw = error.toString().replaceFirst('Exception: ', '').trim();
    if (raw.isEmpty || raw.toLowerCase() == 'null') {
      return '分享失败，请稍后再试';
    }
    return raw;
  }

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
    final overviewAsync = ref.watch(accountabilityOverviewProvider);
    final l10n = context.l10n;
    final activePartnershipId = overviewAsync.valueOrNull?.activePartnership?.id;
    final selectorHeight = MediaQuery.sizeOf(context).height < 760 ? 196.0 : 220.0;

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
                  l10n.shareResourceTitle,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              const SizedBox(height: DS.sm),
              _buildResourcePreview(),
              const SizedBox(height: DS.md),
              TabBar(
                controller: _tabController,
                labelColor: DS.brandPrimary,
                labelPadding:
                    const EdgeInsets.symmetric(horizontal: DS.spacing12),
                tabs: [
                  Tab(text: l10n.shareResourceTabFriends),
                  Tab(text: l10n.shareResourceTabGroups),
                ],
              ),
              SizedBox(
                height: selectorHeight,
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildFriendsList(
                      friendsState,
                      activePartnershipId: activePartnershipId,
                    ),
                    _buildGroupsList(groupsState),
                  ],
                ),
              ),
              const SizedBox(height: DS.sm),
              TextField(
                controller: _commentController,
                maxLines: 2,
                decoration: InputDecoration(
                  hintText: l10n.shareResourceCommentHint,
                  isDense: true,
                  border: const OutlineInputBorder(
                    borderRadius: DS.borderRadius12,
                  ),
                ),
              ),
              const SizedBox(height: DS.md),
              SizedBox(
                width: double.infinity,
                child: SparkleButton(
                  label: l10n.shareResourceNow,
                  onPressed: _isSharing ? null : _share,
                  loading: _isSharing,
                  expand: true,
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
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            if (widget.subtitle != null && widget.subtitle!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(
                widget.subtitle!,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: DS.textSecondary, fontSize: 12),
              ),
            ],
          ],
        ),
      );

  Widget _buildFriendsList(
    AsyncValue<List<FriendshipInfo>> state, {
    required String? activePartnershipId,
  }) =>
      state.when(
        data: (friends) {
          final sortedFriends = _sortFriends(
            friends,
            activePartnershipId: activePartnershipId,
          );
          _maybePreselectCorePartner(
            sortedFriends,
            activePartnershipId: activePartnershipId,
          );

          return sortedFriends.isEmpty
            ? _buildEmpty(context.l10n.shareResourceNoFriends)
            : ListView.separated(
                itemCount: sortedFriends.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final friendship = sortedFriends[index];
                  final friend = friendship.friend;
                  final isCorePartner =
                      friendship.accountability?.status == 'active' &&
                      friendship.accountability?.partnershipId ==
                          activePartnershipId;
                  final isSelected = _selectedUserId == friend.id;
                  return ListTile(
                    leading: SparkleAvatar(
                      radius: 16,
                      url: friend.avatarUrl,
                      fallbackText: friend.displayName,
                    ),
                    title: Text(friend.displayName),
                    subtitle: isCorePartner
                        ? Text(
                            '核心责任伙伴',
                            style: TextStyle(
                              color: DS.brandPrimary,
                              fontSize: 12,
                              fontWeight: DS.fontWeightSemibold,
                            ),
                          )
                        : friendship.accountability?.isPending == true
                            ? Text(
                                '责任伙伴邀请待确认',
                                style: TextStyle(
                                  color: DS.warning,
                                  fontSize: 12,
                                ),
                              )
                            : null,
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
              );
        },
        loading: () => const Center(child: LoadingIndicator()),
        error: (e, _) => _buildEmpty(context.l10n.loadingFailedWithError(e)),
      );

  List<FriendshipInfo> _sortFriends(
    List<FriendshipInfo> friends, {
    required String? activePartnershipId,
  }) {
    final sorted = [...friends];
    int priority(FriendshipInfo friendship) {
      final accountability = friendship.accountability;
      if (accountability == null) return 3;
      if (accountability.status == 'active' &&
          accountability.partnershipId == activePartnershipId) {
        return 0;
      }
      if (accountability.status == 'active') return 1;
      if (accountability.status == 'pending') return 2;
      return 3;
    }

    sorted.sort((a, b) {
      final priorityCompare = priority(a).compareTo(priority(b));
      if (priorityCompare != 0) return priorityCompare;
      return a.friend.displayName.compareTo(b.friend.displayName);
    });
    return sorted;
  }

  void _maybePreselectCorePartner(
    List<FriendshipInfo> friends, {
    required String? activePartnershipId,
  }) {
    if (_selectedUserId != null || activePartnershipId == null) return;

    FriendshipInfo? corePartner;
    for (final friendship in friends) {
      if (friendship.accountability?.status == 'active' &&
          friendship.accountability?.partnershipId == activePartnershipId) {
        corePartner = friendship;
        break;
      }
    }
    if (corePartner == null || _autoSelectedPartnerId == corePartner.friend.id) {
      return;
    }

    _autoSelectedPartnerId = corePartner.friend.id;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _selectedUserId != null) return;
      setState(() {
        _selectedUserId = corePartner?.friend.id;
        _selectedGroupId = null;
      });
    });
  }

  Widget _buildGroupsList(AsyncValue<List<GroupListItem>> state) => state.when(
        data: (groups) => groups.isEmpty
            ? _buildEmpty(context.l10n.shareResourceNoGroups)
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
                    subtitle: Text(
                      context.l10n.shareResourceGroupMembers(group.memberCount),
                    ),
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
        error: (e, _) => _buildEmpty(context.l10n.loadingFailedWithError(e)),
      );

  Widget _buildEmpty(String message) => Center(
        child: Text(
          message,
          style: TextStyle(color: DS.textSecondary),
        ),
      );

  Future<void> _share() async {
    if (_selectedGroupId == null && _selectedUserId == null) {
      AppFeedback.info(context, context.l10n.shareResourceSelectTarget);
      return;
    }

    setState(() => _isSharing = true);
    try {
      final comment = _commentController.text.trim().isEmpty
          ? null
          : _commentController.text.trim();
      if (widget.resourceType == 'achievement') {
        if (_selectedGroupId != null) {
          await ref.read(communityRepositoryProvider).sendMessage(
                _selectedGroupId!,
                type: MessageType.achievement,
                content: comment ?? widget.title,
                contentData: {
                  'achievement_id': widget.resourceId,
                  'name': widget.title,
                  'description': widget.subtitle,
                },
              );
        } else if (_selectedUserId != null) {
          await ref.read(communityRepositoryProvider).sendPrivateMessage(
                PrivateMessageSend(
                  targetUserId: _selectedUserId!,
                  messageType: MessageType.achievement,
                  content: comment ?? widget.title,
                  contentData: {
                    'achievement_id': widget.resourceId,
                    'name': widget.title,
                    'description': widget.subtitle,
                  },
                ),
              );
        }
      } else {
        await ref.read(communityShareRepositoryProvider).shareResource(
              resourceType: widget.resourceType,
              resourceId: widget.resourceId,
              targetGroupId: _selectedGroupId,
              targetUserId: _selectedUserId,
              comment: comment,
            );
      }

      if (!mounted) return;
      final messengerContext = widget.feedbackContext ?? context;
      if (Navigator.of(context).canPop()) {
        Navigator.of(context).pop();
      }
      if (messengerContext.mounted) {
        AppFeedback.success(
          messengerContext,
          messengerContext.l10n.shareResourceSuccess,
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(
        widget.feedbackContext ?? context,
        context.l10n.shareResourceFailed(_shareErrorMessage(e)),
      );
    } finally {
      if (mounted) {
        setState(() => _isSharing = false);
      }
    }
  }
}
