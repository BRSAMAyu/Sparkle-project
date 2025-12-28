import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/design/sparkle_theme.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';
import 'package:sparkle/presentation/widgets/community/community_widgets.dart';

// Provider for last selected tab
final communityTabIndexProvider = StateProvider<int>((ref) => 0);

// Provider for focus mode
final focusModeProvider = StateNotifierProvider<FocusModeNotifier, bool>((ref) => FocusModeNotifier());

class FocusModeNotifier extends StateNotifier<bool> {
  FocusModeNotifier() : super(false) {
    _loadFromPrefs();
  }

  Future<void> _loadFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    state = prefs.getBool('focus_mode') ?? false;
  }

  Future<void> toggle() async {
    state = !state;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('focus_mode', state);
    // TODO: Update user status to backend when focus mode changes
    // This would require accessing CommunityRepository here
  }
}

class CommunityMainScreen extends ConsumerStatefulWidget {
  const CommunityMainScreen({super.key});

  @override
  ConsumerState<CommunityMainScreen> createState() => _CommunityMainScreenState();
}

class _CommunityMainScreenState extends ConsumerState<CommunityMainScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    final savedIndex = ref.read(communityTabIndexProvider);
    _tabController = TabController(length: 2, vsync: this, initialIndex: savedIndex);
    _tabController.addListener(_onTabChanged);
    _loadSavedTab();
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

    return Scaffold(
      appBar: AppBar(
        title: const Text('星火社群', style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: false,
        actions: [
          // Focus mode indicator and toggle
          IconButton(
            icon: Icon(
              focusMode ? Icons.do_not_disturb_on : Icons.do_not_disturb_off_outlined,
              color: focusMode ? AppDesignTokens.warning : null,
            ),
            tooltip: focusMode ? '专注模式开启中' : '开启专注模式',
            onPressed: () {
              ref.read(focusModeProvider.notifier).toggle();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text(focusMode ? '已关闭专注模式' : '已开启专注模式，消息将不会打扰您'),
                  duration: const Duration(seconds: 2),
                ),
              );
            },
          ),
          IconButton(icon: const Icon(Icons.search), onPressed: () {}),
          IconButton(icon: const Icon(Icons.person_add_outlined), onPressed: () {}),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: const [Tab(text: '好友'), Tab(text: '群组')],
          indicatorColor: SparkleTheme.primary,
          labelStyle: const TextStyle(fontWeight: FontWeight.bold),
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _FriendsListTab(),
          _GroupsListTab(),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        child: const Icon(Icons.add),
      ),
    );
  }
}

class _FriendsListTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final friendsAsync = ref.watch(friendsProvider);

    return friendsAsync.when(
      data: (friends) {
        if (friends.isEmpty) {
          return const Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.people_outline, size: 64, color: AppDesignTokens.neutral300),
                SizedBox(height: DS.lg),
                Text('还没有好友', style: TextStyle(color: AppDesignTokens.neutral500)),
              ],
            ),
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.symmetric(vertical: 8),
          itemCount: friends.length,
          itemBuilder: (context, index) {
            final f = friends[index];
            return InkWell(
              onTap: () => context.push('/community/chat/private/${f.friend.id}?name=${Uri.encodeComponent(f.friend.displayName)}'),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                child: Row(
                  children: [
                    StatusAvatar(status: f.friend.status, url: f.friend.avatarUrl),
                    const SizedBox(width: DS.md),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            f.friend.displayName,
                            style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 16),
                          ),
                          const SizedBox(height: 2),
                          Row(
                            children: [
                              Container(
                                width: 8,
                                height: 8,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: f.friend.status == UserStatus.online
                                      ? AppDesignTokens.success
                                      : AppDesignTokens.neutral300,
                                ),
                              ),
                              const SizedBox(width: DS.xs),
                              Text(
                                f.friend.status == UserStatus.online ? '在线' : '离线',
                                style: TextStyle(
                                  color: f.friend.status == UserStatus.online
                                      ? AppDesignTokens.success
                                      : AppDesignTokens.neutral500,
                                  fontSize: 12,
                                ),
                              ),
                              const SizedBox(width: DS.sm),
                              Text(
                                'Lv.${f.friend.flameLevel}',
                                style: const TextStyle(color: AppDesignTokens.neutral500, fontSize: 12),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right, size: 20, color: AppDesignTokens.neutral400),
                  ],
                ),
              ),
            );
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
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
          return const Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.group_outlined, size: 64, color: AppDesignTokens.neutral300),
                SizedBox(height: DS.lg),
                Text('还没有加入群组', style: TextStyle(color: AppDesignTokens.neutral500)),
              ],
            ),
          );
        }
        return ListView.builder(
          padding: const EdgeInsets.all(DS.lg),
          itemCount: groups.length,
          itemBuilder: (context, index) {
            final g = groups[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: InkWell(
                onTap: () => context.push('/community/chat/group/${g.id}'),
                borderRadius: BorderRadius.circular(12),
                child: Padding(
                  padding: const EdgeInsets.all(DS.lg),
                  child: Row(
                    children: [
                      SparkleAvatar(
                        radius: 24,
                        backgroundColor: SparkleTheme.primary.withValues(alpha: 0.1),
                        fallbackText: g.name,
                      ),
                      const SizedBox(width: DS.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(g.name, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                            const SizedBox(height: DS.xs),
                            Row(
                              children: [
                                const Icon(Icons.people, size: 14, color: AppDesignTokens.neutral500),
                                const SizedBox(width: DS.xs),
                                Text('${g.memberCount} 成员', style: const TextStyle(color: AppDesignTokens.neutral500, fontSize: 12)),
                                const SizedBox(width: DS.md),
                                Icon(Icons.local_fire_department, size: 14, color: DS.brandPrimary),
                                const SizedBox(width: DS.xs),
                                Text('${g.totalFlamePower}', style: const TextStyle(color: AppDesignTokens.neutral500, fontSize: 12)),
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
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }
}
