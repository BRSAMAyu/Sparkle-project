import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
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
    unawaited(
      Future.microtask(() {
        unawaited(ref.read(leaderboardProvider.notifier).loadAllLeaderboards());
      }),
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(leaderboardProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.leaderboardTitle),
        bottom: TabBar(
          controller: _tabController,
          isScrollable: true,
          onTap: (_) {
            unawaited(
              SensoryFeedbackService.emit(
                SensoryFeedbackEvent.selection,
              ),
            );
          },
          tabs: _tabs.map((type) => Tab(text: _getTabLabel(type))).toList(),
        ),
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.refresh),
            onPressed: () {
              unawaited(_refreshCurrentTab());
            },
          ),
        ],
      ),
      child: state.isLoading
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
                  return SparkleStaggerItem(
                    index: index,
                    child: _buildLeaderboardEntry(leaderboard.entries[index]),
                  );
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
        padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
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
                  DS.rarityCommon,
                  '🥈',
                ),
              ),
            const SizedBox(width: DS.spacing8),

            // First place
            if (topThree.isNotEmpty)
              Expanded(
                child: _buildPodiumItem(
                  topThree[0],
                  160,
                  DS.rarityRare,
                  '🥇',
                ),
              ),
            const SizedBox(width: DS.spacing8),

            // Third place
            if (topThree.length > 2)
              Expanded(
                child: _buildPodiumItem(
                  topThree[2],
                  100,
                  DS.warning,
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
  ) =>
      Column(
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
                      entry.username.isNotEmpty
                          ? entry.username[0].toUpperCase()
                          : '?',
                      style: TextStyle(
                        color: color,
                        fontWeight: DS.fontWeightBold,
                        fontSize: 24,
                      ),
                    ),
                  )
                : null,
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            emoji,
            style: const TextStyle(fontSize: 32),
          ),
          const SizedBox(height: DS.spacing4),
          Container(
            width: double.infinity,
            height: height,
            decoration: BoxDecoration(
              color: color,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(DS.spacing8),
              ),
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  entry.username,
                  style: const TextStyle(
                    fontWeight: DS.fontWeightBold,
                    fontSize: 12,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: DS.spacing4),
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

    return SparkleAttentionPulse(
      glowColor: Theme.of(context).colorScheme.primary,
      child: Container(
        margin: const EdgeInsets.all(DS.spacing16),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        decoration: BoxDecoration(
          color: Theme.of(context).primaryColor.withValues(alpha: 0.1),
          borderRadius: DS.borderRadius12,
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                context.l10n.leaderboardMyRank(leaderboard.myRank!),
                style: const TextStyle(
                  fontWeight: DS.fontWeightBold,
                  fontSize: 16,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const Spacer(),
            Text(
              leaderboard.myScore != null
                  ? context.l10n.leaderboardPoints(
                      leaderboard.myScore!.toInt(),
                    )
                  : '-',
              style: const TextStyle(
                fontSize: 16,
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLeaderboardEntry(LeaderboardEntry entry) => ListTile(
        leading: CircleAvatar(
          backgroundColor: _getRankColor(entry.rank),
          backgroundImage:
              entry.avatarUrl != null ? NetworkImage(entry.avatarUrl!) : null,
          child: entry.avatarUrl == null
              ? Text(
                  entry.rank.toString(),
                  style: TextStyle(
                    color: DS.textOnPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
                )
              : null,
        ),
        title: Text(
          entry.username,
          style: TextStyle(
            fontWeight: entry.isMe ? DS.fontWeightBold : FontWeight.normal,
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
            const SizedBox(width: DS.spacing8),
            Text(
              entry.scoreLabel,
              style: const TextStyle(
                fontWeight: DS.fontWeightBold,
              ),
            ),
          ],
        ),
      );

  Widget _buildEmptyView(LeaderboardType type) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.leaderboard_outlined,
              size: 64,
              color: DS.textSecondary,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.leaderboardNoData(_getTabLabel(type)),
              style: TextStyle(
                fontSize: 16,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
      );

  Widget _buildErrorView() => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: DS.error),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.leaderboardLoadFailed,
              style: const TextStyle(fontSize: 16),
            ),
            const SizedBox(height: DS.spacing8),
            SparkleButton.primary(
              onPressed: () {
                unawaited(
                  ref.read(leaderboardProvider.notifier).loadAllLeaderboards(),
                );
              },
              label: context.l10n.retry,
            ),
          ],
        ),
      );

  Color _getRankColor(int rank) {
    if (rank == 1) return DS.rarityRare;
    if (rank == 2) return DS.rarityCommon;
    if (rank == 3) return DS.warning;
    return DS.info;
  }

  String _getTabLabel(LeaderboardType type) {
    switch (type) {
      case LeaderboardType.global:
        return context.l10n.leaderboardGlobal;
      case LeaderboardType.friends:
        return context.l10n.leaderboardFriends;
      case LeaderboardType.group:
        return context.l10n.leaderboardGroup;
      case LeaderboardType.subject:
        return context.l10n.leaderboardSubject;
      case LeaderboardType.weekly:
        return context.l10n.leaderboardWeekly;
      case LeaderboardType.streak:
        return context.l10n.leaderboardStreak;
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
