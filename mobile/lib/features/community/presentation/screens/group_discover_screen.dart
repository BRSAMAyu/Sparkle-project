import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/group_recommendation_card.dart';
import 'package:sparkle/features/community/presentation/widgets/recommendation_feedback_widgets.dart';

class GroupDiscoverScreen extends ConsumerStatefulWidget {
  const GroupDiscoverScreen({super.key});

  @override
  ConsumerState<GroupDiscoverScreen> createState() =>
      _GroupDiscoverScreenState();
}

class _GroupDiscoverScreenState extends ConsumerState<GroupDiscoverScreen> {
  late final TextEditingController _searchController;

  @override
  void initState() {
    super.initState();
    final notifier = ref.read(groupDiscoverProvider.notifier);
    _searchController = TextEditingController(text: notifier.keyword);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _submitSearch() async {
    await ref.read(groupDiscoverProvider.notifier).setKeyword(
          _searchController.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    final directoryState = ref.watch(groupDiscoverProvider);
    final notifier = ref.read(groupDiscoverProvider.notifier);
    final promptsState = ref.watch(recommendationFeedbackPromptsProvider);
    final insightsState = ref.watch(recommendationFeedbackInsightsProvider);
    final groupPrompts = (promptsState.valueOrNull ?? const [])
        .where((prompt) => prompt.itemType == RecommendationItemType.group)
        .toList();
    final groupInsight = (insightsState.valueOrNull ?? const [])
        .where((insight) => insight.itemType == RecommendationItemType.group)
        .cast<RecommendationFeedbackInsight?>()
        .firstWhere((insight) => insight != null, orElse: () => null);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('社群广场'),
        centerTitle: true,
        actions: [
          SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.add_circle_outline),
            onPressed: () => context.push('/community/groups/create'),
          ),
        ],
      ),
      child: directoryState.when(
        data: (directory) => ContentConstraint(
          child: RefreshIndicator(
            onRefresh: notifier.refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _SearchBar(
                  controller: _searchController,
                  onSubmitted: _submitSearch,
                  onClear: () async {
                    _searchController.clear();
                    await notifier.setKeyword('');
                  },
                ),
                const SizedBox(height: 16),
                _SortSelector(
                  current: notifier.sortBy,
                  onChanged: notifier.setSortBy,
                ),
                const SizedBox(height: 12),
                _TypeSelector(
                  current: notifier.type,
                  onChanged: notifier.setType,
                ),
                if (directory.availableTags.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _TagSelector(
                    availableTags: directory.availableTags,
                    selectedTags: notifier.selectedTags,
                    onToggle: notifier.toggleTag,
                  ),
                ],
                if (groupPrompts.isNotEmpty) ...[
                  const SizedBox(height: 18),
                  Text(
                    '待你校准',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '告诉我们这些推荐社群是否真的对口，系统会继续优化发现结果。',
                    style: TextStyle(color: DS.textSecondary),
                  ),
                  const SizedBox(height: 12),
                  ...groupPrompts.take(2).map(
                        (prompt) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: RecommendationFeedbackPromptCard(
                            prompt: prompt,
                            onRespond: () =>
                                _handlePromptFeedback(context, prompt),
                          ),
                        ),
                      ),
                ],
                if (groupInsight != null && groupInsight.recentFeedbackCount > 0)
                  Padding(
                    padding: const EdgeInsets.only(top: 18),
                    child: RecommendationFeedbackInsightCard(
                      insight: groupInsight,
                    ),
                  ),
                const SizedBox(height: 18),
                if (directory.recommendations.isNotEmpty &&
                    notifier.keyword.isEmpty &&
                    notifier.selectedTags.isEmpty &&
                    notifier.type == null) ...[
                  _RecommendationsPanel(
                    items: directory.recommendations,
                    onJoin: notifier.join,
                    onFeedback: (item) => _handleRecommendationFeedback(
                      context,
                      item,
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
                Row(
                  children: [
                    Text(
                      '公开社群目录',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const Spacer(),
                    Text(
                      '${directory.totalCount} 个结果',
                      style: TextStyle(color: DS.textSecondary),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                if (directory.groups.isEmpty)
                  CompactEmptyState(
                    message: '暂时没有符合条件的社群，换个标签、排序或直接创建一个吧。',
                    icon: Icons.travel_explore_outlined,
                    actionText: '清空筛选',
                    onAction: () async {
                      _searchController.clear();
                      await notifier.clearFilters();
                    },
                  )
                else
                  ...List.generate(directory.groups.length, (index) {
                    final group = directory.groups[index];
                    return Padding(
                      padding: EdgeInsets.only(
                        bottom: index == directory.groups.length - 1 ? 0 : 12,
                      ),
                      child: _DirectoryGroupCard(
                        group: group,
                        onTap: () =>
                            context.push('/community/groups/${group.id}'),
                        onJoin: group.isJoined
                            ? null
                            : () {
                                notifier.join(group.id);
                              },
                      ),
                    );
                  }),
              ],
            ),
          ),
        ),
        loading: () => const Center(child: LoadingIndicator()),
        error: (error, stackTrace) => Center(
          child: CustomErrorWidget.page(
            context: context,
            message: error.toString(),
            onRetry: notifier.refresh,
          ),
        ),
      ),
    );
  }

  Future<void> _handlePromptFeedback(
    BuildContext context,
    RecommendationFeedbackPrompt prompt,
  ) async {
    final draft = await showRecommendationFeedbackSheet(
      context: context,
      itemType: RecommendationItemType.group,
      prompt: prompt,
      group: prompt.group,
    );
    if (draft == null || !context.mounted) return;

    await _submitGroupFeedback(
      context,
      groupId: prompt.group?.id ?? prompt.itemId,
      action: _groupActionFromTrigger(prompt.triggerAction),
      source: 'groups_prompt',
      promptId: draft.promptId,
      stage: draft.stage,
      overallScore: draft.overallScore,
      relevanceScore: draft.relevanceScore,
      explanationScore: draft.explanationScore,
      actionabilityScore: draft.actionabilityScore,
      interestMatchScore: draft.interestMatchScore,
      activityScore: draft.activityScore,
      atmosphereScore: draft.atmosphereScore,
      selectedIssues: draft.selectedIssues,
      selectedStrengths: draft.selectedStrengths,
      freeText: draft.freeText,
    );
  }

  Future<void> _handleRecommendationFeedback(
    BuildContext context,
    GroupRecommendationItem item,
  ) async {
    final draft = await showRecommendationFeedbackSheet(
      context: context,
      itemType: RecommendationItemType.group,
      group: item.group,
    );
    if (draft == null || !context.mounted) return;

    await _submitGroupFeedback(
      context,
      groupId: item.group.id,
      action: 'view',
      source: 'groups_card_feedback',
      reasonTypes: item.reasons.map((reason) => reason.type).toList(),
      promptId: draft.promptId,
      stage: draft.stage,
      overallScore: draft.overallScore,
      relevanceScore: draft.relevanceScore,
      explanationScore: draft.explanationScore,
      actionabilityScore: draft.actionabilityScore,
      interestMatchScore: draft.interestMatchScore,
      activityScore: draft.activityScore,
      atmosphereScore: draft.atmosphereScore,
      selectedIssues: draft.selectedIssues,
      selectedStrengths: draft.selectedStrengths,
      freeText: draft.freeText,
    );
  }

  Future<void> _submitGroupFeedback(
    BuildContext context, {
    required String groupId,
    required String action,
    required String source,
    List<String>? reasonTypes,
    String? promptId,
    RecommendationFeedbackStage? stage,
    int? overallScore,
    int? relevanceScore,
    int? explanationScore,
    int? actionabilityScore,
    int? interestMatchScore,
    int? activityScore,
    int? atmosphereScore,
    List<String>? selectedIssues,
    List<String>? selectedStrengths,
    String? freeText,
  }) async {
    try {
      await ref.read(communityRepositoryProvider).sendGroupRecommendationFeedback(
            groupId: groupId,
            action: action,
            source: source,
            reasonTypes: reasonTypes,
            promptId: promptId,
            stage: stage,
            questionnaireVersion: 1,
            overallScore: overallScore,
            relevanceScore: relevanceScore,
            explanationScore: explanationScore,
            actionabilityScore: actionabilityScore,
            interestMatchScore: interestMatchScore,
            activityScore: activityScore,
            atmosphereScore: atmosphereScore,
            selectedIssues: selectedIssues,
            selectedStrengths: selectedStrengths,
            freeText: freeText,
          );
      ref.invalidate(recommendationFeedbackPromptsProvider);
      ref.invalidate(recommendationFeedbackInsightsProvider);
      ref.invalidate(groupDiscoverProvider);
      ref.invalidate(groupRecommendationsProvider);
      if (context.mounted) {
        AppFeedback.success(context, '反馈已提交，社群推荐会继续变聪明');
      }
    } catch (e) {
      if (context.mounted) {
        AppFeedback.error(context, '提交失败: $e');
      }
    }
  }

  String _groupActionFromTrigger(String trigger) {
    if (trigger.contains('join')) {
      return 'join';
    }
    if (trigger.contains('dismiss')) {
      return 'dismiss';
    }
    return 'view';
  }
}

class _SearchBar extends StatelessWidget {
  const _SearchBar({
    required this.controller,
    required this.onSubmitted,
    required this.onClear,
  });

  final TextEditingController controller;
  final Future<void> Function() onSubmitted;
  final Future<void> Function() onClear;

  @override
  Widget build(BuildContext context) {
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(12),
      child: Row(
        children: [
          const Icon(Icons.search),
          const SizedBox(width: 10),
          Expanded(
            child: TextField(
              controller: controller,
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                hintText: '搜索感兴趣的社群、课程或主题',
                border: InputBorder.none,
                isDense: true,
              ),
              onSubmitted: (_) {
                onSubmitted();
              },
            ),
          ),
          if (controller.text.isNotEmpty)
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.close),
              onPressed: () {
                onClear();
              },
            ),
        ],
      ),
    );
  }
}

class _SortSelector extends StatelessWidget {
  const _SortSelector({
    required this.current,
    required this.onChanged,
  });

  final GroupDirectorySort current;
  final Future<void> Function(GroupDirectorySort) onChanged;

  @override
  Widget build(BuildContext context) {
    const options = <(GroupDirectorySort, String)>[
      (GroupDirectorySort.hot, '热度优先'),
      (GroupDirectorySort.latest, '最新创建'),
      (GroupDirectorySort.random, '随机发现'),
    ];

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: options.map((option) {
        final selected = current == option.$1;
        return ChoiceChip(
          label: Text(option.$2),
          selected: selected,
          onSelected: (_) {
            onChanged(option.$1);
          },
        );
      }).toList(),
    );
  }
}

class _TypeSelector extends StatelessWidget {
  const _TypeSelector({
    required this.current,
    required this.onChanged,
  });

  final GroupType? current;
  final Future<void> Function(GroupType?) onChanged;

  @override
  Widget build(BuildContext context) {
    const options = <(GroupType?, String)>[
      (null, '全部'),
      (GroupType.squad, '学习小组'),
      (GroupType.sprint, '冲刺小组'),
    ];

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: options.map((option) {
        final selected = current == option.$1;
        return ChoiceChip(
          label: Text(option.$2),
          selected: selected,
          onSelected: (_) {
            onChanged(option.$1);
          },
        );
      }).toList(),
    );
  }
}

class _TagSelector extends StatelessWidget {
  const _TagSelector({
    required this.availableTags,
    required this.selectedTags,
    required this.onToggle,
  });

  final List<String> availableTags;
  final Set<String> selectedTags;
  final Future<void> Function(String tag) onToggle;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: availableTags.take(12).map((tag) {
        return FilterChip(
          label: Text(tag),
          selected: selectedTags.contains(tag),
          onSelected: (_) {
            onToggle(tag);
          },
        );
      }).toList(),
    );
  }
}

class _RecommendationsPanel extends StatelessWidget {
  const _RecommendationsPanel({
    required this.items,
    required this.onJoin,
    required this.onFeedback,
  });

  final List<GroupRecommendationItem> items;
  final Future<void> Function(String groupId) onJoin;
  final Future<void> Function(GroupRecommendationItem item) onFeedback;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('为你推荐', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        SizedBox(
          height: 218,
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
                    onJoin(item.group.id);
                  },
                  onFeedback: () {
                    onFeedback(item);
                  },
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _DirectoryGroupCard extends StatelessWidget {
  const _DirectoryGroupCard({
    required this.group,
    required this.onTap,
    this.onJoin,
  });

  final GroupListItem group;
  final VoidCallback onTap;
  final VoidCallback? onJoin;

  @override
  Widget build(BuildContext context) {
    final accent = group.isSprint ? DS.warning : DS.brandPrimary;
    final actionLabel = group.isJoined
        ? '已加入'
        : group.joinRequiresApproval
            ? '申请加入'
            : '加入';

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(16),
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: accent.withValues(alpha: 0.14),
                ),
                child: Icon(
                  group.isSprint
                      ? Icons.timer_outlined
                      : Icons.groups_2_outlined,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      group.name,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${group.memberCount} 人 · 今日 ${group.todayCheckinCount} 打卡 · 火苗 ${group.totalFlamePower.toStringAsFixed(0)}',
                      style: TextStyle(color: DS.textSecondary, fontSize: 12),
                    ),
                  ],
                ),
              ),
              SemanticPill(
                label: group.isSprint ? '冲刺' : '学习',
                dense: true,
                tone: group.isSprint ? PillTone.warning : PillTone.brand,
              ),
            ],
          ),
          if (group.description != null && group.description!.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              group.description!,
              style: TextStyle(color: DS.textSecondary, height: 1.4),
            ),
          ],
          if (group.focusTags.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: group.focusTags
                  .take(4)
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
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: Text(
                  group.activityScore == null
                      ? '公开社群'
                      : '热度分 ${group.activityScore!.toStringAsFixed(1)}',
                  style: TextStyle(color: DS.textSecondary, fontSize: 12),
                ),
              ),
              SparkleButton(
                label: actionLabel,
                size: ButtonSize.small,
                variant: group.isJoined
                    ? ButtonVariant.secondary
                    : ButtonVariant.primary,
                onPressed: group.isJoined ? onTap : onJoin,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
