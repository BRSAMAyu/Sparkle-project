import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/providers/focus_mode_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/community_widgets.dart';
import 'package:sparkle/features/community/presentation/widgets/friends_hub_view.dart';

// Provider for last selected tab
final communityTabIndexProvider = StateProvider<int>((ref) => 0);

class CommunityMainScreen extends ConsumerStatefulWidget {
  const CommunityMainScreen({super.key});

  @override
  ConsumerState<CommunityMainScreen> createState() =>
      _CommunityMainScreenState();
}

class _CommunityMainScreenState extends ConsumerState<CommunityMainScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    final savedIndex = ref.read(communityTabIndexProvider);
    _tabController =
        TabController(length: 2, vsync: this, initialIndex: savedIndex);
    _tabController.addListener(_onTabChanged);
    _loadSavedTab();
  }

  void _showSearchOptions() {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: Colors.transparent,
        builder: (context) => GraphiteModalSurface(
          title: context.l10n.communitySearch,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: Icon(Icons.person_search, color: DS.primaryBase),
                title: Text(context.l10n.communitySearchUsers),
                onTap: () {
                  Navigator.pop(context);
                  context.push('/community/users/search');
                },
              ),
              ListTile(
                leading: Icon(Icons.search, color: DS.primaryBase),
                title: Text(context.l10n.communitySearchGroups),
                onTap: () {
                  Navigator.pop(context);
                  context.push('/community/groups/search');
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showAddOptions() {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: Colors.transparent,
        builder: (context) => GraphiteModalSurface(
          title: context.l10n.communityActions,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: Icon(Icons.person_add, color: DS.primaryBase),
                title: Text(context.l10n.communityDiscoverFriends),
                subtitle: Text(context.l10n.communityDiscoverFriendsHint),
                onTap: () {
                  Navigator.pop(context);
                  context.push('/community/friends/discover');
                },
              ),
              ListTile(
                leading: Icon(Icons.group_add, color: DS.primaryBase),
                title: Text(context.l10n.communityCreateGroup),
                subtitle: Text(context.l10n.communityCreateGroupHint),
                onTap: () {
                  Navigator.pop(context);
                  context.push('/community/groups/create');
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _handleFabPressed() {
    final currentTabIndex = _tabController.index;

    if (currentTabIndex == 0) {
      // Friends tab - show friend discovery
      _showAddOptions();
    } else {
      // Groups tab - navigate to group creation
      context.push('/community/groups/create');
    }
  }

  Future<void> _loadSavedTab() async {
    final prefs = await SharedPreferences.getInstance();
    final savedIndex = prefs.getInt('community_tab_index') ?? 0;
    if (mounted && savedIndex != _tabController.index) {
      _tabController.animateTo(savedIndex);
      ref.read(communityTabIndexProvider.notifier).state = savedIndex;
    }
  }

  void _onTabChanged() {
    if (!_tabController.indexIsChanging) {
      ref.read(communityTabIndexProvider.notifier).state = _tabController.index;
      _saveTabIndex(_tabController.index);
    }
  }

  Future<void> _saveTabIndex(int index) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('community_tab_index', index);
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final focusMode = ref.watch(focusModeProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GraphiteScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        backgroundColor:
            DS.surfaceOverlay.withValues(alpha: isDark ? 0.88 : 0.94),
        surfaceTintColor: Colors.transparent,
        scrolledUnderElevation: 0,
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        title: Text(
          context.l10n.communityTitle,
          style: DS.titleLarge.copyWith(
            color: DS.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        centerTitle: false,
        actions: [
          // Focus mode indicator and toggle
          Tooltip(
            message: focusMode
                ? context.l10n.communityFocusModeOn
                : context.l10n.communityFocusModeOff,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: Icon(
                focusMode
                    ? Icons.do_not_disturb_on
                    : Icons.do_not_disturb_off_outlined,
                color: focusMode ? DS.warning : null,
              ),
              onPressed: () {
                ref.read(focusModeProvider.notifier).toggle();
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(focusMode
                        ? context.l10n.communityFocusModeDisabled
                        : context.l10n.communityFocusModeEnabled),
                    duration: const Duration(seconds: 2),
                  ),
                );
              },
            ),
          ),
          Tooltip(
            message: '我的收藏',
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.bookmark_outline),
              onPressed: () => context.push('/community/favorites'),
            ),
          ),
          Tooltip(
            message: context.l10n.communitySearch,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.search),
              onPressed: _showSearchOptions,
            ),
          ),
          Tooltip(
            message: context.l10n.commonAdd,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.person_add_outlined),
              onPressed: _showAddOptions,
            ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: context.l10n.communityTabFriends),
            Tab(text: context.l10n.communityTabGroups),
          ],
          indicatorColor: DS.brandPrimary,
          indicatorWeight: 2.5,
          dividerColor: Colors.transparent,
          labelColor: DS.textPrimary,
          unselectedLabelColor: DS.textSecondary,
          labelStyle: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      floatingActionButton: Tooltip(
        message: _tabController.index == 0
            ? context.l10n.communityAddFriend
            : context.l10n.communityCreateGroup,
        child: SparkleIconButton(
          size: 56,
          icon: const Icon(Icons.add),
          onPressed: _handleFabPressed,
        ),
      ),
      child: ContentConstraint(
        child: TabBarView(
          controller: _tabController,
          children: [
            _FriendsListTab(),
            _GroupsListTab(),
          ],
        ),
      ),
    );
  }
}

class _FriendsListTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const FriendsHubView(
      padding: EdgeInsets.fromLTRB(12, 12, 12, 28),
    );
  }
}

class _GroupsListTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsAsync = ref.watch(myGroupsProvider);

    return groupsAsync.when(
      data: (groups) {
        if (groups.isEmpty) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.group_outlined, size: 64, color: DS.neutral300),
                const SizedBox(height: DS.lg),
                Text(
                  context.l10n.communityNoGroups,
                  style: TextStyle(color: DS.neutral500),
                ),
              ],
            ),
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.all(DS.lg),
          itemCount: groups.length,
          itemBuilder: (context, index) {
            final g = groups[index];
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GraphiteCardSurface(
                onTap: () => context.push('/chat/group/${g.id}'),
                child: Row(
                  children: [
                    SparkleAvatar(
                      radius: 24,
                      backgroundColor: DS.surfacePanel,
                      fallbackText: g.name,
                    ),
                    const SizedBox(width: DS.md),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            g.name,
                            style: DS.bodyLarge.copyWith(
                              color: DS.textPrimary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: DS.xs),
                          Row(
                            children: [
                              Icon(
                                Icons.people,
                                size: 14,
                                color: DS.textSecondary,
                              ),
                              const SizedBox(width: DS.xs),
                              Text(
                                context.l10n.communityMembers(g.memberCount),
                                style: TextStyle(
                                  color: DS.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(width: DS.md),
                              Icon(
                                Icons.local_fire_department,
                                size: 14,
                                color: DS.brandPrimaryConst,
                              ),
                              const SizedBox(width: DS.xs),
                              Text(
                                '${g.totalFlamePower}',
                                style: TextStyle(
                                  color: DS.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    Icon(Icons.chevron_right, color: DS.neutral400),
                  ],
                ),
              ),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Text('${context.l10n.loadingFailed}: $e'),
      ),
    );
  }
}
