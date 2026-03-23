import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/presentation/providers/focus_mode_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/friends_hub_view.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_hub_view.dart';

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
                  context.pushNamed('userSearch');
                },
              ),
              ListTile(
                leading: Icon(Icons.search, color: DS.primaryBase),
                title: Text(context.l10n.communitySearchGroups),
                onTap: () {
                  Navigator.pop(context);
                  context.pushNamed('groupDiscover');
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
                  context.pushNamed('friendsDiscover');
                },
              ),
              ListTile(
                leading: Icon(Icons.group_add, color: DS.primaryBase),
                title: Text(context.l10n.communityCreateGroup),
                subtitle: Text(context.l10n.communityCreateGroupHint),
                onTap: () {
                  Navigator.pop(context);
                  context.pushNamed('createGroup');
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
      context.pushNamed('createGroup');
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
      unawaited(
        SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
      );
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
    final experience = ExperienceProfiles.socialWarm;
    final focusMode = ref.watch(focusModeProvider);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GraphiteScaffold(
      role: experience.pageRole,
      motionToken: experience.motionToken,
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
              onPressed: () => context.pushNamed('favorites'),
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
            SparkleStaggerItem(
              index: 0,
              motionToken: SparkleMotionToken.scene,
              child: _FriendsListTab(),
            ),
            SparkleStaggerItem(
              index: 1,
              motionToken: SparkleMotionToken.scene,
              child: _GroupsListTab(),
            ),
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
    return const GroupsHubView(
      padding: EdgeInsets.fromLTRB(12, 12, 12, 28),
    );
  }
}
