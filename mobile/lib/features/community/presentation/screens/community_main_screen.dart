import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/experience/experience_profile.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
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

  void _toggleFocusMode() {
    final focusMode = ref.read(focusModeProvider);
    ref.read(focusModeProvider.notifier).toggle();
    ScaffoldMessenger.of(context).showSnackBar(
      SparkleSnackBar.info(
        focusMode
            ? context.l10n.communityFocusModeDisabled
            : context.l10n.communityFocusModeEnabled,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _showMoreOptions() {
    showMenu<String>(
      context: context,
      position: const RelativeRect.fromLTRB(1000, 88, 16, 0),
      items: [
        PopupMenuItem(
          value: 'focus',
          child: Row(
            children: [
              Icon(
                ref.read(focusModeProvider)
                    ? Icons.do_not_disturb_on
                    : Icons.do_not_disturb_off_outlined,
                size: 18,
                color: ref.read(focusModeProvider)
                    ? DS.warning
                    : DS.textSecondary,
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Text(
                  ref.read(focusModeProvider)
                      ? context.l10n.communityFocusModeOff
                      : context.l10n.communityFocusModeOn,
                ),
              ),
            ],
          ),
        ),
        PopupMenuItem(
          value: 'favorites',
          child: Row(
            children: [
              Icon(Icons.bookmark_outline, size: 18),
              SizedBox(width: DS.spacing10),
              Expanded(child: Text(I18nService.instance.isChinese ? '收藏' : 'Favorites')),
            ],
          ),
        ),
        PopupMenuItem(
          value: 'add',
          child: Row(
            children: [
              const Icon(Icons.person_add_outlined, size: 18),
              const SizedBox(width: DS.spacing10),
              Expanded(child: Text(context.l10n.commonAdd)),
            ],
          ),
        ),
      ],
    ).then((value) {
      if (value == null || !mounted) return;
      switch (value) {
        case 'focus':
          _toggleFocusMode();
          break;
        case 'favorites':
          context.pushNamed('favorites');
          break;
        case 'add':
          _showAddOptions();
          break;
      }
    });
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
            fontWeight: DS.fontWeightBold,
          ),
        ),
        centerTitle: false,
        actions: [
          Tooltip(
            message: context.l10n.communitySearch,
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.search),
              onPressed: _showSearchOptions,
            ),
          ),
          Tooltip(
            message: I18nService.instance.isChinese ? '更多' : 'More',
            child: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: Icon(
                Icons.more_horiz_rounded,
                color: focusMode ? DS.warning : DS.textSecondary,
              ),
              onPressed: _showMoreOptions,
            ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabAlignment: TabAlignment.fill,
          labelPadding: const EdgeInsets.symmetric(vertical: DS.spacing4),
          tabs: [
            Tab(text: context.l10n.communityTabFriends),
            Tab(text: context.l10n.communityTabGroups),
          ],
          indicatorColor: DS.brandPrimary,
          indicatorWeight: 2.5,
          dividerColor: Colors.transparent,
          labelColor: DS.textPrimary,
          unselectedLabelColor: DS.textSecondary,
          labelStyle: const TextStyle(fontWeight: DS.fontWeightBold),
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
  Widget build(BuildContext context, WidgetRef ref) => const FriendsHubView(
      padding: EdgeInsets.fromLTRB(16, 10, 16, 24),
    );
}

class _GroupsListTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) => const GroupsHubView(
      padding: EdgeInsets.fromLTRB(16, 10, 16, 24),
    );
}
