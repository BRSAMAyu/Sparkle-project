import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shimmer/shimmer.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/compact_error_card.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/community/community_routes.dart';
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

    return SparkleRefreshIndicator(
      onRefresh: () async {
        ref.invalidate(myGroupsProvider);
        ref.invalidate(groupRecommendationsProvider);
        ref.invalidate(groupDiscoverProvider);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: padding,
        children: [
          // NAV-IA P-4：小队入口补位——Community（同伴关系的家）内零小队
          // 入口是结构性失衡（`/community/squads` 此前仅 sprint 屏与错题
          // 分享弹窗两个入边）。首行一行式入口直达小队列表，把「找到小队」
          // 从 3 跳收敛到 1 跳；sprint 屏既有入口保留不动。
          const _SquadsEntryTile(),
          const SizedBox(height: DS.spacing20),
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

/// NAV-IA P-4：冲刺小队一行式入口（样式照 `_JoinedGroupTile` 既有家族：
/// GraphiteCardSurface + ListTile，sprint 语义 = timer 图标 + warning 底）。
class _SquadsEntryTile extends StatelessWidget {
  const _SquadsEntryTile();

  @override
  Widget build(BuildContext context) => GraphiteCardSurface(
        key: const ValueKey('community-squads-entry'),
        surfaceRole: SparkleSurfaceRole.card,
        padding: EdgeInsets.zero,
        onTap: () => context.push(CommunityRoutes.squads),
        child: ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          leading: Container(
            width: 46,
            height: 46,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              color: DS.warning.withValues(alpha: 0.16),
            ),
            child: Icon(
              Icons.timer_outlined,
              color: DS.textPrimary,
            ),
          ),
          title: Text(context.l10n.squadEntryLabel),
          subtitle: Text(context.l10n.communitySquadsEntryHint),
          trailing: const Icon(Icons.chevron_right),
        ),
      );
}

class _CommunityHero extends StatefulWidget {
  const _CommunityHero({required this.directoryAsync});

  final AsyncValue<GroupDirectoryInfo> directoryAsync;

  @override
  State<_CommunityHero> createState() => _CommunityHeroState();
}

class _CommunityHeroState extends State<_CommunityHero> {
  static const _collapsedPrefsKey = 'community_group_entry_collapsed_v1';
  bool _collapsed = false;

  @override
  void initState() {
    super.initState();
    unawaited(_loadCollapsed());
  }

  Future<void> _loadCollapsed() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _collapsed = prefs.getBool(_collapsedPrefsKey) ?? false;
    });
  }

  Future<void> _toggleCollapsed() async {
    final prefs = await SharedPreferences.getInstance();
    final next = !_collapsed;
    await prefs.setBool(_collapsedPrefsKey, next);
    if (!mounted) return;
    setState(() {
      _collapsed = next;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).textTheme;
    final directory = widget.directoryAsync.valueOrNull;
    final tags = directory?.availableTags.take(6).toList() ?? const <String>[];

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.accent,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  gradient: LinearGradient(
                    colors: [
                      DS.brandPrimary,
                      DS.warning.withValues(alpha: 0.88),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Icon(Icons.hub_outlined, color: DS.neutral0),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      context.l10n.communityGroupEntry,
                      style: theme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      directory == null
                          ? context.l10n.communityBrowseOrCreate
                          : context.l10n
                              .communityPublicGroupsCount(directory.totalCount),
                      style: theme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              SparkleButton(
                label: _collapsed
                    ? context.l10n.communityExpand
                    : context.l10n.communityCollapse,
                variant: ButtonVariant.ghost,
                size: ButtonSize.small,
                onPressed: _toggleCollapsed,
              ),
            ],
          ),
          if (!_collapsed) ...[
            const SizedBox(height: 12),
            Text(
              context.l10n.communityDiscoverCampusGroups,
              style: theme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            Text(
              directory == null
                  ? context.l10n.communityDiscoverBrowseHint
                  : context.l10n.communityDiscoverFilterHint,
              style: theme.bodyMedium?.copyWith(color: DS.textSecondary),
            ),
            if (tags.isNotEmpty) ...[
              const SizedBox(height: 12),
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
            const SizedBox(height: 12),
          ] else
            const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: SparkleButton.primary(
                  label: context.l10n.communityBrowseGroups,
                  icon: const Icon(Icons.travel_explore_outlined),
                  onPressed: () => context.push('/community/groups/discover'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: SparkleButton(
                  label: context.l10n.communityCreateGroup,
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
  Widget build(BuildContext context, WidgetRef ref) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(context.l10n.communityRecommendedForYou,
                  style: Theme.of(context).textTheme.titleMedium,),
              const Spacer(),
              SparkleButton(
                label: context.l10n.communityViewAll,
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
                height: 200,
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
                          unawaited(
  ref
                                .read(groupRecommendationsProvider.notifier)
                                .join(item.group.id),
                          );
                          ref.invalidate(myGroupsProvider);
                        },
                        onDismiss: () {
                          unawaited(
  ref
                                .read(groupRecommendationsProvider.notifier)
                                .dismiss(item.group.id),
                          );
                        },
                      ),
                    );
                  },
                ),
              );
            },
            loading: () => SizedBox(
              height: 200,
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
              context.l10n.communityRecommendLoadError,
              style: TextStyle(color: DS.textSecondary),
            ),
          ),
        ],
      );
}

class _MyGroupsSection extends ConsumerWidget {
  const _MyGroupsSection({required this.state});

  final AsyncValue<List<GroupListItem>> state;

  @override
  Widget build(BuildContext context, WidgetRef ref) => state.when(
        data: (groups) {
          if (groups.isEmpty) {
            return CompactEmptyState(
              message: context.l10n.communityNoGroupsYet,
              icon: Icons.groups_outlined,
              actionText: context.l10n.communityDiscoverGroups,
              onAction: () => context.push('/community/groups/discover'),
            );
          }
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(context.l10n.communityMyGroups,
                      style: Theme.of(context).textTheme.titleMedium,),
                  const Spacer(),
                  SparkleButton(
                    label: context.l10n.communityViewAllGroups,
                    variant: ButtonVariant.ghost,
                    size: ButtonSize.small,
                    onPressed: () => context.push('/community/groups'),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              ...List.generate(groups.length > 4 ? 4 : groups.length, (index) {
                final group = groups[index];
                return Padding(
                  padding: EdgeInsets.only(
                    bottom: index == (groups.length > 4 ? 3 : groups.length - 1)
                        ? 0
                        : 12,
                  ),
                  child: _JoinedGroupTile(group: group),
                );
              }),
              if (groups.length > 4) ...[
                const SizedBox(height: 12),
                Text(
                  context.l10n.communityMoreGroupsFolded(groups.length - 4),
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: DS.fontSizeSm,
                  ),
                ),
              ],
            ],
          );
        },
        loading: () => const SparkleListSkeleton(),
        // COMMUNITY-401: the raw DioException text (401 textbook dump with a
        // mozilla link) used to be interpolated verbatim here. Humanize via
        // UserFacingError (SPEC-C precedent) and give the section a visible
        // tap-to-retry so a transient auth/network failure can recover.
        error: (error, _) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.l10n.communityMyGroupsLoadError(
                UserFacingError.from(error),
              ),
              style: TextStyle(color: DS.textSecondary),
            ),
            const SizedBox(height: DS.spacing8),
            CompactErrorCard(
              onRetry: () => ref.invalidate(myGroupsProvider),
            ),
          ],
        ),
      );
}

class _JoinedGroupTile extends StatelessWidget {
  const _JoinedGroupTile({required this.group});

  final GroupListItem group;

  @override
  Widget build(BuildContext context) {
    final roleLabel = switch (group.myRole) {
      GroupRole.owner => context.l10n.communityRoleOwner,
      GroupRole.admin => context.l10n.communityRoleAdmin,
      GroupRole.member => context.l10n.communityRoleMember,
      null => context.l10n.communityRolePublic,
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
              context.l10n.communityGroupSubtitle(
                  roleLabel, group.memberCount, group.todayCheckinCount,),
              style: TextStyle(color: DS.textSecondary, fontSize: 12),
            ),
          ],
        ),
        trailing: const Icon(Icons.chevron_right),
      ),
    );
  }
}
