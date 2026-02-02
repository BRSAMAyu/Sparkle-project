import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/leaderboard/presentation/providers/leaderboard_provider.dart';

/// Leaderboard Screen
///
/// Displays various leaderboards with tab navigation
class LeaderboardScreen extends ConsumerStatefulWidget {
  const LeaderboardScreen({super.key});

  @override
  ConsumerState<LeaderboardScreen> createState() => _LeaderboardScreenState();
}

class _LeaderboardScreenState extends ConsumerState<LeaderboardScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  final List<LeaderboardType> _tabs = [
    LeaderboardType.global,
    LeaderboardType.friends,
    LeaderboardType.weekly,
    LeaderboardType.streak,
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
    // Load initial data
    Future.microtask(() {
      ref.read(leaderboardProvider.notifier).loadAllLeaderboards();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(leaderboardProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('排行榜'),
        bottom: TabBar(
          controller: _tabController,
          tabs: _tabs.map((type) => Tab(text: _getTabLabel(type))).toList(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refreshCurrentTab,
          ),
        ],
      ),
      body: state.isLoading
          ? const Center(child: CircularProgressIndicator())
          : state.error != null
              ? _buildErrorView()
              : TabBarView(
                  controller: _tabController,
                  children: _tabs.map(_buildLeaderboardTab).toList(),
                ),
    );
  }

  Widget _buildLeaderboardTab(LeaderboardType type) {
    final state = ref.watch(leaderboardProvider);
    final leaderboard = state.getLeaderboard(type);

    if (leaderboard == null) {
      return _buildEmptyView(type);
    }

    return RefreshIndicator(
      onRefresh: () => _refreshLeaderboard(type),
      child: ContentConstraint(
        child: CustomScrollView(
          slivers: [
            // Podium for top 3
            if (leaderboard.entries.isNotEmpty)
              SliverToBoxAdapter(
                child: _buildPodium(leaderboard.entries.take(3).toList()),
              ),

            // My rank banner
            SliverToBoxAdapter(
              child: _buildMyRankBanner(leaderboard),
            ),

            // Full leaderboard
            SliverList(
              delegate: SliverChildBuilderDelegate(
                (context, index) {
                  if (index >= leaderboard.entries.length) return null;
                  return _buildLeaderboardEntry(leaderboard.entries[index]);
                },
                childCount: leaderboard.entries.length,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPodium(List<LeaderboardEntry> topThree) => Container(
      height: 180,
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          // Second place
          if (topThree.length > 1)
            Expanded(
              child: _buildPodiumItem(
                topThree[1],
                120,
                Colors.grey[400]!,
                '🥈',
              ),
            ),
          const SizedBox(width: 8),

          // First place
          if (topThree.isNotEmpty)
            Expanded(
              child: _buildPodiumItem(
                topThree[0],
                160,
              Colors.amber[400]!,
                '🥇',
              ),
            ),
          const SizedBox(width: 8),

          // Third place
          if (topThree.length > 2)
            Expanded(
              child: _buildPodiumItem(
                topThree[2],
                100,
              Colors.brown[400]!,
                '🥉',
              ),
            ),
        ],
      ),
    );

  Widget _buildPodiumItem(
    LeaderboardEntry entry,
    double height,
    Color color,
    String emoji,
  ) => Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            image: entry.avatarUrl != null
                ? DecorationImage(
                    image: NetworkImage(entry.avatarUrl!),
                    fit: BoxFit.cover,
                  )
                : null,
            ),
          child: entry.avatarUrl == null
              ? CircleAvatar(
                  backgroundColor: color.withValues(alpha: 0.3),
                  child: Text(
                    entry.username.isNotEmpty ? entry.username[0].toUpperCase() : '?',
                    style: TextStyle(
                      color: color,
                      fontWeight: FontWeight.bold,
                      fontSize: 24,
                    ),
                  ),
                )
              : null,
        ),
        const SizedBox(height: 8),
        Text(
          emoji,
          style: const TextStyle(fontSize: 32),
        ),
        const SizedBox(height: 4),
        Container(
          width: double.infinity,
          height: height,
          decoration: BoxDecoration(
            color: color,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                entry.username,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 12,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 4),
              Text(
                entry.scoreLabel,
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ),
        ),
      ],
    );

  Widget _buildMyRankBanner(LeaderboardData leaderboard) {
    if (leaderboard.myRank == null) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).primaryColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Text(
            '我的排名: ${leaderboard.myRank}',
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
          const Spacer(),
          Text(
            leaderboard.myScore != null
                ? '${leaderboard.myScore!.toInt()}分'
                : '-',
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLeaderboardEntry(LeaderboardEntry entry) => ListTile(
      leading: CircleAvatar(
        backgroundColor: _getRankColor(entry.rank),
        backgroundImage: entry.avatarUrl != null
            ? NetworkImage(entry.avatarUrl!)
            : null,
        child: entry.avatarUrl == null
            ? Text(
                entry.rank.toString(),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              )
            : null,
      ),
      title: Text(
        entry.username,
        style: TextStyle(
          fontWeight: entry.isMe ? FontWeight.bold : FontWeight.normal,
        ),
      ),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (entry.badge != null)
            Text(
              entry.badge!,
              style: const TextStyle(fontSize: 20),
            ),
          const SizedBox(width: 8),
          Text(
            entry.scoreLabel,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );

  Widget _buildEmptyView(LeaderboardType type) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.leaderboard_outlined, size: 64, color: Colors.grey),
          const SizedBox(height: 16),
          Text(
            '暂无${_getTabLabel(type)}数据',
            style: const TextStyle(fontSize: 16, color: Colors.grey),
          ),
        ],
      ),
    );

  Widget _buildErrorView() => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          const Text(
            '加载失败，请重试',
            style: TextStyle(fontSize: 16),
          ),
          const SizedBox(height: 8),
          ElevatedButton(
            onPressed: () {
              ref.read(leaderboardProvider.notifier).loadAllLeaderboards();
            },
            child: const Text('重试'),
          ),
        ],
      ),
    );

  Color _getRankColor(int rank) {
    if (rank == 1) return Colors.amber;
    if (rank == 2) return Colors.grey[400]!;
    if (rank == 3) return Colors.brown[400]!;
    return Colors.blue;
  }

  String _getTabLabel(LeaderboardType type) {
    switch (type) {
      case LeaderboardType.global:
        return '全局榜';
      case LeaderboardType.friends:
        return '好友榜';
      case LeaderboardType.group:
        return '群组榜';
      case LeaderboardType.subject:
        return '学科榜';
      case LeaderboardType.weekly:
        return '本周榜';
      case LeaderboardType.streak:
        return '连胜榜';
    }
  }

  Future<void> _refreshCurrentTab() async {
    final type = _tabs[_tabController.index];
    await ref.read(leaderboardProvider.notifier).refresh(type);
  }

  Future<void> _refreshLeaderboard(LeaderboardType type) async {
    await ref.read(leaderboardProvider.notifier).refresh(type);
  }
}
