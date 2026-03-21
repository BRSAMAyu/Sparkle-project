import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/group_recommendation_card.dart';

class GroupsHubView extends ConsumerWidget {
  const GroupsHubView({
    super.key,
    this.padding = const EdgeInsets.fromLTRB(16, 16, 16, 32),
  });

  final EdgeInsets padding;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final groupsAsync = ref.watch(myGroupsProvider);
    final recommendationsAsync = ref.watch(groupRecommendationsProvider);
    final directoryAsync = ref.watch(groupDiscoverProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(myGroupsProvider);
        ref.invalidate(groupRecommendationsProvider);
        ref.invalidate(groupDiscoverProvider);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: padding,
        children: [
          // My groups first — the primary action
          _MyGroupsSection(state: groupsAsync),
          const SizedBox(height: DS.spacing20),
          // Discovery & recommendations below
          _CommunityHero(directoryAsync: directoryAsync),
          const SizedBox(height: DS.spacing20),
          _RecommendationsSection(state: recommendationsAsync),
        ],
      ),
    );
  }
}

class _CommunityHero extends StatelessWidget {
  const _CommunityHero({required this.directoryAsync});

  final AsyncValue<GroupDirectoryInfo> directoryAsync;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    final directory = directoryAsync.valueOrNull;
    final tags = directory?.availableTags.take(6).toList() ?? const <String>[];

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.accent,
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(18),
              gradient: LinearGradient(
                colors: [
                  DS.brandPrimary,
                  DS.warning.withValues(alpha: 0.88),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: const Icon(Icons.hub_outlined, color: Colors.white),
          ),
          const SizedBox(height: 16),
          Text(
            '像逛校园社团一样发现社群',
            style: theme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          Text(
            directory == null
                ? '浏览公开社群、按兴趣筛选、看看当前最火的小组，也能随时创建属于自己的学习社区。'
                : '当前可浏览 ${directory.totalCount} 个公开社群，支持热度、最新、随机发现，还能按兴趣标签快速筛选。',
            style: theme.bodyMedium?.copyWith(color: DS.textSecondary),
          ),
          if (tags.isNotEmpty) ...[
            const SizedBox(height: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: tags
                  .map(
                    (tag) => SemanticPill(
                      label: tag,
                      tone: PillTone.brand,
                      dense: true,
                    ),
                  )
                  .toList(),
            ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: SparkleButton.primary(
                  label: '浏览社群',
                  icon: const Icon(Icons.travel_explore_outlined),
                  onPressed: () => context.push('/community/groups/discover'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: SparkleButton(
                  label: '创建社群',
                  variant: ButtonVariant.secondary,
                  icon: const Icon(Icons.add_circle_outline),
                  onPressed: () => context.push('/community/groups/create'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RecommendationsSection extends ConsumerWidget {
  const _RecommendationsSection({required this.state});

  final AsyncValue<List<GroupRecommendationItem>> state;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('为你推荐', style: Theme.of(context).textTheme.titleMedium),
            const Spacer(),
            SparkleButton(
              label: '看全部',
              variant: ButtonVariant.ghost,
              size: ButtonSize.small,
              onPressed: () => context.push('/community/groups/discover'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        state.when(
          data: (items) {
            if (items.isEmpty) {
              return const SizedBox.shrink();
            }
            return SizedBox(
              height: 220,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: items.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, index) {
                  final item = items[index];
                  return SizedBox(
                    width: 292,
                    child: GroupRecommendationCard(
                      recommendation: item,
                      onTap: () =>
                          context.push('/community/groups/${item.group.id}'),
                      onJoin: () {
                        ref
                            .read(groupRecommendationsProvider.notifier)
                            .join(item.group.id);
                        ref.invalidate(myGroupsProvider);
                      },
                      onDismiss: () {
                        ref
                            .read(groupRecommendationsProvider.notifier)
                            .dismiss(item.group.id);
                      },
                    ),
                  );
                },
              ),
            );
          },
          loading: () => SizedBox(
            height: 220,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: 2,
              separatorBuilder: (_, __) => const SizedBox(width: 12),
              itemBuilder: (_, __) => Shimmer.fromColors(
                baseColor: DS.surfaceOverlay,
                highlightColor: DS.surfacePrimary,
                child: Container(
                  width: 292,
                  decoration: BoxDecoration(
                    color: DS.surfaceOverlay,
                    borderRadius: BorderRadius.circular(24),
                  ),
                ),
              ),
            ),
          ),
          error: (_, __) => Text(
            '推荐暂时加载失败，稍后下拉刷新即可。',
            style: TextStyle(color: DS.textSecondary),
          ),
        ),
      ],
    );
  }
}

class _MyGroupsSection extends StatelessWidget {
  const _MyGroupsSection({required this.state});

  final AsyncValue<List<GroupListItem>> state;

  @override
  Widget build(BuildContext context) {
    return state.when(
      data: (groups) {
        if (groups.isEmpty) {
          return CompactEmptyState(
            message: '你还没有加入社群，先去逛一逛公开社群广场吧。',
            icon: Icons.groups_outlined,
            actionText: '去发现社群',
            onAction: () => context.push('/community/groups/discover'),
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('我的社群', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            ...List.generate(groups.length, (index) {
              final group = groups[index];
              return Padding(
                padding: EdgeInsets.only(
                  bottom: index == groups.length - 1 ? 0 : 12,
                ),
                child: _JoinedGroupTile(group: group),
              );
            }),
          ],
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => Text(
        '我的社群加载失败: $error',
        style: TextStyle(color: DS.textSecondary),
      ),
    );
  }
}

class _JoinedGroupTile extends StatelessWidget {
  const _JoinedGroupTile({required this.group});

  final GroupListItem group;

  @override
  Widget build(BuildContext context) {
    final roleLabel = switch (group.myRole) {
      GroupRole.owner => '群主',
      GroupRole.admin => '管理员',
      GroupRole.member => '成员',
      null => '公开社群',
    };

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: EdgeInsets.zero,
      // Tap goes directly to chat — the primary action for joined groups
      onTap: () => context.push('/chat/group/${group.id}'),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        leading: Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: group.isSprint
                ? DS.warning.withValues(alpha: 0.16)
                : DS.brandPrimary.withValues(alpha: 0.12),
          ),
          child: Icon(
            group.isSprint ? Icons.timer_outlined : Icons.groups_2_outlined,
            color: DS.textPrimary,
          ),
        ),
        title: Text(group.name),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (group.description != null && group.description!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  group.description!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            const SizedBox(height: 6),
            Text(
              '$roleLabel · ${group.memberCount} 人 · 今日 ${group.todayCheckinCount} 次打卡',
              style: TextStyle(color: DS.textSecondary, fontSize: 12),
            ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}
