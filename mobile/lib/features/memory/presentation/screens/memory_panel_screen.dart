import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/display/lexicon/date_formatting.dart';
import 'package:sparkle/core/display/lexicon/goal_status_lexicon.dart';
import 'package:sparkle/core/display/lexicon/lexicon.dart';
import 'package:sparkle/core/display/lexicon/memory_event_lexicon.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/memory_routes.dart';
import 'package:sparkle/features/memory/presentation/providers/understanding_overview_provider.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_detail_screen.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_drawer.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';
import 'package:sparkle/features/memory/presentation/widgets/pending_commitments_section.dart';
import 'package:sparkle/features/memory/presentation/widgets/understanding_overview_view.dart';
import 'package:sparkle/features/memory/presentation/widgets/unresolved_conflicts_section.dart';
import 'package:sparkle/features/user/user_routes.dart';

class _MemoryPanelDataState {
  const _MemoryPanelDataState({
    this.isLoading = true,
    this.error,
    this.partialError,
    this.preferences = const [],
    this.goals = const [],
    this.episodic = const [],
    this.recentScenes = const [],
    this.foresightHint,
    this.pendingCommitments = const [],
    this.unresolvedConflicts = const [],
    this.revokingIds = const {},
    this.correctingIds = const {},
    this.processingCommitmentIds = const {},
    this.processingConflictIds = const {},
    this.episodicHasMore = false,
    this.episodicTotal = 0,
    this.episodicLoadingMore = false,
  });

  final bool isLoading;

  /// 全量失败：所有分区都不可用时置位，UI 渲染整页错误态。
  final String? error;

  /// F7-05: 部分分区失败但仍渲染成功分区时置位，以非阻塞反馈提示。
  final String? partialError;
  final List<MemoryPreferenceItem> preferences;
  final List<MemoryGoalItem> goals;
  final List<EpisodicMemoryItem> episodic;
  final List<RecentSceneSummaryItem> recentScenes;
  final ForesightHintSummaryItem? foresightHint;
  final List<PendingCommitmentItem> pendingCommitments;
  final List<UnresolvedConflictItem> unresolvedConflicts;
  final Set<String> revokingIds;

  /// memory-governance-mvp: 纠正/删除/确认动作进行中的条目。
  final Set<String> correctingIds;
  final Set<String> processingCommitmentIds;
  final Set<String> processingConflictIds;

  /// memory-governance-mvp: episodic 分页游标状态。
  final bool episodicHasMore;
  final int episodicTotal;
  final bool episodicLoadingMore;

  _MemoryPanelDataState copyWith({
    bool? isLoading,
    String? error,
    String? partialError,
    List<MemoryPreferenceItem>? preferences,
    List<MemoryGoalItem>? goals,
    List<EpisodicMemoryItem>? episodic,
    List<RecentSceneSummaryItem>? recentScenes,
    Object? foresightHint = _foresightHintSentinel,
    List<PendingCommitmentItem>? pendingCommitments,
    List<UnresolvedConflictItem>? unresolvedConflicts,
    Set<String>? revokingIds,
    Set<String>? correctingIds,
    Set<String>? processingCommitmentIds,
    Set<String>? processingConflictIds,
    bool? episodicHasMore,
    int? episodicTotal,
    bool? episodicLoadingMore,
    bool clearError = false,
  }) =>
      _MemoryPanelDataState(
        isLoading: isLoading ?? this.isLoading,
        error: clearError ? null : error ?? this.error,
        partialError: clearError ? null : partialError ?? this.partialError,
        preferences: preferences ?? this.preferences,
        goals: goals ?? this.goals,
        episodic: episodic ?? this.episodic,
        recentScenes: recentScenes ?? this.recentScenes,
        foresightHint: identical(foresightHint, _foresightHintSentinel)
            ? this.foresightHint
            : foresightHint as ForesightHintSummaryItem?,
        pendingCommitments: pendingCommitments ?? this.pendingCommitments,
        unresolvedConflicts: unresolvedConflicts ?? this.unresolvedConflicts,
        revokingIds: revokingIds ?? this.revokingIds,
        correctingIds: correctingIds ?? this.correctingIds,
        processingCommitmentIds:
            processingCommitmentIds ?? this.processingCommitmentIds,
        processingConflictIds: processingConflictIds ?? this.processingConflictIds,
        episodicHasMore: episodicHasMore ?? this.episodicHasMore,
        episodicTotal: episodicTotal ?? this.episodicTotal,
        episodicLoadingMore: episodicLoadingMore ?? this.episodicLoadingMore,
      );
}

const Object _foresightHintSentinel = Object();

class _MemoryPanelDataNotifier extends StateNotifier<_MemoryPanelDataState> {
  _MemoryPanelDataNotifier(this._service)
      : super(const _MemoryPanelDataState());

  final MemoryApiService _service;

  /// U-03：V2 主呈现换成四组理解视图，面板自身只加载问责分区
  /// （场景/前瞻/承诺/冲突）；偏好/目标/经历改由 provenance API 提供，
  /// 不再重复请求旧列表端点。V1（legacy）仍走全量加载。
  Future<void> loadAll({bool includeMemories = true}) async {
    state = state.copyWith(isLoading: true, clearError: true);

    // F7-05: 逐分区 settle，单个分区失败不再让整个面板进入全量错误态；
    // 成功分区照常渲染，失败分区保留旧数据。
    Future<(Object?, Object?)> settled(Future<Object?> future) async {
      try {
        return (await future, null);
      } catch (e) {
        return (null, e);
      }
    }

    final results = await Future.wait<(Object?, Object?)>([
      if (includeMemories) settled(_service.getPreferences()),
      if (includeMemories) settled(_service.getGoals()),
      if (includeMemories) settled(_service.getEpisodicPage()),
      settled(_service.getRecentScenes()),
      settled(_service.getForesightHintSummary()),
      settled(_service.getPendingCommitments()),
      settled(_service.getUnresolvedConflicts()),
    ]);
    if (!mounted) {
      return;
    }
    var index = 0;
    final preferences = includeMemories
        ? results[index++].$1 as List<MemoryPreferenceItem>?
        : null;
    final goals =
        includeMemories ? results[index++].$1 as List<MemoryGoalItem>? : null;
    final episodicPage = includeMemories
        ? results[index++] as (EpisodicMemoryPage?, Object?)
        : null;
    state = state.copyWith(
      preferences: preferences,
      goals: goals,
      episodic: episodicPage?.$1?.items,
      recentScenes: results[index++].$1 as List<RecentSceneSummaryItem>?,
      foresightHint: results[index++].$1 as ForesightHintSummaryItem?,
      pendingCommitments:
          results[index++].$1 as List<PendingCommitmentItem>?,
      unresolvedConflicts: results[index].$1 as List<UnresolvedConflictItem>?,
      episodicHasMore: episodicPage?.$1?.hasMore,
      episodicTotal: episodicPage?.$1?.total,
      isLoading: false,
    );
    Object? firstFailure;
    var failureCount = 0;
    for (final (_, failure) in results) {
      if (failure != null) {
        firstFailure ??= failure;
        failureCount++;
      }
    }
    final allFailed = failureCount == results.length;
    final failureMessage = firstFailure == null ? null : '$firstFailure';
    state = state.copyWith(
      error: allFailed ? failureMessage : null,
      partialError: allFailed ? null : failureMessage,
    );
  }

  /// memory-governance-mvp: 追加下一页 episodic（offset 分页）。
  Future<void> loadMoreEpisodic() async {
    if (state.episodicLoadingMore || !state.episodicHasMore) {
      return;
    }
    state = state.copyWith(episodicLoadingMore: true);
    try {
      final page = await _service.getEpisodicPage(
        offset: state.episodic.length,
      );
      if (!mounted) {
        return;
      }
      final known = state.episodic.map((e) => e.id).toSet();
      final fresh =
          page.items.where((e) => !known.contains(e.id)).toList();
      state = state.copyWith(
        episodic: [...state.episodic, ...fresh],
        episodicHasMore: page.hasMore,
        episodicTotal: page.total,
        episodicLoadingMore: false,
      );
    } catch (_) {
      if (mounted) {
        state = state.copyWith(episodicLoadingMore: false);
      }
      rethrow;
    }
  }

  /// memory-governance-mvp: 对单条 episodic 记忆执行用户治理动作。
  ///
  /// action ∈ wrong（记错）/ outdated（不再是）/ delete（删除）→ 从列表移除；
  /// confirm（这就是对的）→ 原位替换为服务端返回的最新条目。
  Future<void> correctEpisodic(
    EpisodicMemoryItem item, {
    required String action,
    String? reason,
  }) async {
    state = state.copyWith(correctingIds: {...state.correctingIds, item.id});
    try {
      final updated = await _service.correctEpisodicMemory(
        item.id,
        action: action,
        reason: reason,
      );
      if (!mounted) {
        return;
      }
      final List<EpisodicMemoryItem> nextEpisodic;
      if (action == 'confirm') {
        nextEpisodic = [
          for (final entry in state.episodic)
            if (entry.id == item.id) updated else entry,
        ];
      } else {
        nextEpisodic =
            state.episodic.where((entry) => entry.id != item.id).toList();
      }
      state = state.copyWith(
        episodic: nextEpisodic,
        episodicTotal:
            action == 'confirm' ? state.episodicTotal : state.episodicTotal - 1,
        correctingIds:
            state.correctingIds.where((id) => id != item.id).toSet(),
      );
    } catch (_) {
      if (mounted) {
        state = state.copyWith(
          correctingIds: state.correctingIds.where((id) => id != item.id).toSet(),
        );
      }
      rethrow;
    }
  }

  Future<void> revokeAutoMemory(EpisodicMemoryItem item) async {
    state = state.copyWith(revokingIds: {...state.revokingIds, item.id});
    try {
      await _service.retractMemory(
        type: 'episodic',
        id: item.id,
        reason: 'user_revoked_ai_auto_memory',
      );
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        episodic: state.episodic.where((entry) => entry.id != item.id).toList(),
        revokingIds: state.revokingIds.where((id) => id != item.id).toSet(),
      );
    } catch (_) {
      if (mounted) {
        state = state.copyWith(
          revokingIds: state.revokingIds.where((id) => id != item.id).toSet(),
        );
      }
      rethrow;
    }
  }

  Future<void> resolvePendingCommitment(PendingCommitmentItem item) async {
    state = state.copyWith(
      processingCommitmentIds: {...state.processingCommitmentIds, item.id},
    );
    try {
      await _service.resolvePendingCommitment(item.id);
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        pendingCommitments: state.pendingCommitments
            .where((entry) => entry.id != item.id)
            .toList(),
        processingCommitmentIds:
            state.processingCommitmentIds.where((id) => id != item.id).toSet(),
      );
    } catch (_) {
      if (mounted) {
        state = state.copyWith(
          processingCommitmentIds: state.processingCommitmentIds
              .where((id) => id != item.id)
              .toSet(),
        );
      }
      rethrow;
    }
  }

  Future<void> dismissPendingCommitment(PendingCommitmentItem item) async {
    state = state.copyWith(
      processingCommitmentIds: {...state.processingCommitmentIds, item.id},
    );
    try {
      await _service.retractMemory(
        type: 'episodic',
        id: item.id,
        reason: 'stage17_dismiss_pending_commitment',
      );
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        pendingCommitments: state.pendingCommitments
            .where((entry) => entry.id != item.id)
            .toList(),
        processingCommitmentIds:
            state.processingCommitmentIds.where((id) => id != item.id).toSet(),
      );
    } catch (_) {
      if (mounted) {
        state = state.copyWith(
          processingCommitmentIds: state.processingCommitmentIds
              .where((id) => id != item.id)
              .toSet(),
        );
      }
      rethrow;
    }
  }

  Future<void> arbitrateConflict(
    UnresolvedConflictItem item, {
    required String selection,
  }) async {
    state = state.copyWith(
      processingConflictIds: {...state.processingConflictIds, item.id},
    );
    try {
      await _service.arbitrateUnresolvedConflict(item.id, selection: selection);
      if (!mounted) {
        return;
      }
      state = state.copyWith(
        unresolvedConflicts: state.unresolvedConflicts
            .where((entry) => entry.id != item.id)
            .toList(),
        processingConflictIds:
            state.processingConflictIds.where((id) => id != item.id).toSet(),
      );
    } catch (_) {
      if (mounted) {
        state = state.copyWith(
          processingConflictIds:
              state.processingConflictIds.where((id) => id != item.id).toSet(),
        );
      }
      rethrow;
    }
  }
}

final _memoryPanelDataProvider = StateNotifierProvider.autoDispose<
    _MemoryPanelDataNotifier, _MemoryPanelDataState>((ref) {
  final notifier =
      _MemoryPanelDataNotifier(ref.watch(memoryApiServiceProvider));
  // U-03：V2 呈现四组理解视图（provenance API），面板数据只取问责分区。
  unawaited(notifier.loadAll(includeMemories: !AppFeatureFlags.enableMemoryPanelV2));
  return notifier;
});

class MemoryPanelScreen extends ConsumerStatefulWidget {
  const MemoryPanelScreen({super.key});

  @override
  ConsumerState<MemoryPanelScreen> createState() => _MemoryPanelScreenState();
}

class _MemoryPanelScreenState extends ConsumerState<MemoryPanelScreen> {
  _MemoryPanelDataState get _data => ref.watch(_memoryPanelDataProvider);

  List<MemoryPreferenceItem> get _preferences => _data.preferences;

  List<MemoryGoalItem> get _goals => _data.goals;

  List<EpisodicMemoryItem> get _episodic => _data.episodic;

  List<RecentSceneSummaryItem> get _recentScenes => _data.recentScenes;

  ForesightHintSummaryItem? get _foresightHint => _data.foresightHint;

  List<PendingCommitmentItem> get _pendingCommitments =>
      _data.pendingCommitments;

  List<UnresolvedConflictItem> get _unresolvedConflicts =>
      _data.unresolvedConflicts;

  Set<String> get _revokingIds => _data.revokingIds;

  Set<String> get _processingCommitmentIds => _data.processingCommitmentIds;

  Set<String> get _processingConflictIds => _data.processingConflictIds;

  Future<void> _loadAll() async {
    await ref.read(_memoryPanelDataProvider.notifier).loadAll();
    if (!mounted) {
      return;
    }
    // F7-05: 部分分区失败时面板数据照常渲染，仅以非阻塞反馈告知。
    final partialError = ref.read(_memoryPanelDataProvider).partialError;
    if (partialError != null) {
      AppFeedback.error(
        context,
        context.l10n.memoryPanelLoadFailed(partialError),
      );
    }
  }

  @override
  Widget build(BuildContext context) => GraphiteScaffold(
        safeArea: false,
        appBar: AppBar(
          // 甲式（A11Y-BATCH5）：semanticLabel 承载按钮名。
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
            semanticLabel: context.l10n.back,
            onPressed: () => context.pop(),
            variant: ButtonVariant.ghost,
          ),
          title: Text(
            context.l10n.memoryPanel,
            style: DS.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          iconTheme: IconThemeData(color: DS.textPrimary),
          backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
          elevation: 0,
          actions: [
            SparkleIconButton(
              icon: const Icon(Icons.refresh),
              semanticLabel: context.l10n.commonRefresh,
              onPressed: _loadAll,
              variant: ButtonVariant.ghost,
            ),
          ],
        ),
        child: _data.isLoading
            ? const ContentConstraint(child: _MemoryPanelLoadingSkeleton())
            : ContentConstraint(
                child: _data.error != null
                    ? _buildError(context)
                    : AppFeatureFlags.enableMemoryPanelV2
                        ? _buildV2Panel(context)
                        : _buildV1Panel(context),
              ),
      );

  bool get _hasAnyMemoryContent =>
      _preferences.isNotEmpty ||
      _goals.isNotEmpty ||
      _episodic.isNotEmpty ||
      _recentScenes.isNotEmpty ||
      (_foresightHint?.hintText?.isNotEmpty ?? false) ||
      _pendingCommitments.isNotEmpty ||
      _unresolvedConflicts.isNotEmpty;

  Widget _buildError(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _data.error == null
                    ? context.l10n.memoryPanelUnavailable
                    : context.l10n.memoryPanelLoadFailed(_data.error!),
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.md),
              SparkleButton.primary(
                label: context.l10n.retry,
                onPressed: _loadAll,
              ),
            ],
          ),
        ),
      );

  Widget _buildV1Panel(BuildContext context) => SparkleRefreshIndicator(
        onRefresh: _loadAll,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(DS.lg),
          children: [
            if (!_hasAnyMemoryContent)
              _buildGuidedEmptyState(context)
            else ...[
              if (_foresightHint?.hintText?.isNotEmpty ?? false) ...[
                _SectionHeader(title: context.l10n.memoryPanelForesightHint),
                const SizedBox(height: DS.sm),
                _buildForesightHintSection(),
                const SizedBox(height: DS.xl),
              ],
              if (_recentScenes.isNotEmpty) ...[
                _SectionHeader(title: context.l10n.memoryPanelRecentScenes),
                const SizedBox(height: DS.sm),
                _buildRecentScenesSection(),
                const SizedBox(height: DS.xl),
              ],
              _SectionHeader(title: context.l10n.memoryTypePreference),
              const SizedBox(height: DS.sm),
              ..._preferences.map(_buildPreferenceCard),
              const SizedBox(height: DS.xl),
              _SectionHeader(title: context.l10n.memoryTypeGoal),
              const SizedBox(height: DS.sm),
              ..._goals.map(_buildGoalCard),
              if (_autoMemoryEntries.isNotEmpty) ...[
                const SizedBox(height: DS.xl),
                _SectionHeader(title: context.l10n.memoryPanelAiAutoMemories),
                const SizedBox(height: DS.sm),
                ..._autoMemoryEntries.map(_buildEpisodicCard),
              ],
              if (_unresolvedConflicts.isNotEmpty) ...[
                const SizedBox(height: DS.xl),
                UnresolvedConflictsSection(
                  items: _unresolvedConflicts,
                  processingIds: _processingConflictIds,
                  onSelectLeft: _selectConflictLeft,
                  onSelectRight: _selectConflictRight,
                  onSelectNone: _selectConflictNone,
                ),
              ],
              if (_pendingCommitments.isNotEmpty) ...[
                const SizedBox(height: DS.xl),
                PendingCommitmentsSection(
                  items: _pendingCommitments,
                  processingIds: _processingCommitmentIds,
                  onResolve: _resolvePendingCommitment,
                  onDismiss: _dismissPendingCommitment,
                ),
              ],
              const SizedBox(height: DS.xl),
              _SectionHeader(title: context.l10n.memoryTypeEpisodic),
              const SizedBox(height: DS.sm),
              ..._episodic
                  .where((item) => !_isInferredAutoMemory(item))
                  .map(_buildEpisodicCard),
              if (_episodicHasMore) ...[
                const SizedBox(height: DS.sm),
                _buildLoadMoreButton(context),
              ],
            ],
          ],
        ),
      );

  /// U-03 V2 主呈现：四组理解视图（不是数据库管理器）。
  ///
  /// 移除了旧 V2 的类型/证据筛选 chips、"N 条"计数与重要性/置信度排序等
  /// 黑话式主呈现（COPY_TONE：无来源精确数字不上主位）；理解条目的
  /// 来源/范围/置信层级在每张卡片内以用户语言呈现。
  Widget _buildV2Panel(BuildContext context) {
    final understanding = ref.watch(understandingOverviewProvider);
    final hasScenes = _recentScenes.isNotEmpty;
    final hasHint = _foresightHint?.hintText?.isNotEmpty ?? false;
    final hasConflicts = _unresolvedConflicts.isNotEmpty;
    final hasCommitments = _pendingCommitments.isNotEmpty;
    final hasUnderstanding = !understanding.isEmpty;
    return SparkleRefreshIndicator(
      onRefresh: () async {
        await Future.wait([
          ref.read(understandingOverviewProvider.notifier).refresh(),
          ref.read(_memoryPanelDataProvider.notifier).loadAll(includeMemories: false),
        ]);
        if (!mounted) {
          return;
        }
        final partialError =
            ref.read(_memoryPanelDataProvider).partialError;
        if (partialError != null) {
          AppFeedback.error(
            context,
            context.l10n.memoryPanelLoadFailed(partialError),
          );
        }
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(DS.lg),
        children: [
          if (!hasUnderstanding &&
              !hasScenes &&
              !hasHint &&
              !hasConflicts &&
              !hasCommitments &&
              understanding.error == null)
            _buildGuidedEmptyState(context)
          else ...[
            Text(
              context.l10n.understandingViewTitle,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            const SizedBox(height: DS.sm),
            if (understanding.error != null && !hasUnderstanding)
              CustomErrorWidget(
                message: understanding.error ?? '',
                onRetry: () => ref
                    .read(understandingOverviewProvider.notifier)
                    .refresh(),
              )
            else
              UnderstandingOverviewView(
                embedded: true,
                onNeedFullView: () =>
                    context.push(MemoryRoutes.understanding),
              ),
            // 场景/前瞻卡片自带标题，不再额外加 _SectionHeader（避免重复）。
            if (hasHint) ...[
              const SizedBox(height: DS.md),
              _buildForesightHintSection(),
            ],
            if (hasScenes) ...[
              const SizedBox(height: DS.md),
              _buildRecentScenesSection(),
            ],
            if (hasConflicts) ...[
              const SizedBox(height: DS.xl),
              UnresolvedConflictsSection(
                items: _unresolvedConflicts,
                processingIds: _processingConflictIds,
                onSelectLeft: _selectConflictLeft,
                onSelectRight: _selectConflictRight,
                onSelectNone: _selectConflictNone,
              ),
            ],
            if (hasCommitments) ...[
              const SizedBox(height: DS.xl),
              PendingCommitmentsSection(
                items: _pendingCommitments,
                processingIds: _processingCommitmentIds,
                onResolve: _resolvePendingCommitment,
                onDismiss: _dismissPendingCommitment,
              ),
            ],
          ],
        ],
      ),
    );
  }

  /// memory-governance-mvp: episodic 分页"加载更多"。
  Widget _buildLoadMoreButton(BuildContext context) => Center(
        child: SparkleButton(
          label: _episodicLoadingMore
              ? context.l10n.memoryGovWorking
              : context.l10n.memoryGovLoadMore(_episodicTotal),
          onPressed: _episodicLoadingMore ? () {} : _loadMoreEpisodic,
          disabled: _episodicLoadingMore,
          variant: ButtonVariant.ghost,
        ),
      );

  Widget _buildGuidedEmptyState(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.xl),
        child: EmptyState(
          icon: Icons.psychology_alt_outlined,
          title: context.l10n.memoryPanelEmptyTitle,
          description: context.l10n.memoryPanelEmptyDescription,
          actionText: context.l10n.emptyStateStartChatAction,
          onAction: () => context.go('/chat'),
        ),
      );

  Widget _buildForesightHintSection() {
    final item = _foresightHint;
    if (item == null || (item.hintText?.isEmpty ?? true)) {
      return const SizedBox.shrink();
    }
    final subtitleParts = [
      if (item.deviationCount > 0)
        context.l10n.memoryPanelDeviationsDetected(item.deviationCount),
      if (item.generatedAt != null) _formatUpdated(item.generatedAt),
    ];
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.visibility_outlined),
                const SizedBox(width: DS.sm),
                Text(
                  context.l10n.memoryPanelForesightHint,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: DS.fontWeightBold),
                ),
              ],
            ),
            const SizedBox(height: DS.sm),
            Text(
              item.hintText ?? '',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (subtitleParts.isNotEmpty) ...[
              const SizedBox(height: DS.xs),
              Text(
                subtitleParts.join(' · '),
                style: TextStyle(color: DS.textSecondary),
              ),
            ],
            if (item.attractorConfidences.isNotEmpty) ...[
              const SizedBox(height: DS.sm),
              Wrap(
                spacing: DS.xs,
                runSpacing: DS.xs,
                children: item.attractorConfidences
                    .take(3)
                    .map(
                      (confidence) => SemanticPill(
                        // S2/§6.3：机器置信度禁出两位小数裸数值，走三档人话。
                        label:
                            '${_labelForForesightDim(confidence.dim)} · ${bandLabel(confidence.confidence, context.l10n, high: (l10n) => l10n.displayForesightConfident, mid: (l10n) => l10n.displayForesightVerifying, low: (l10n) => l10n.displayForesightUnsure)}',
                        tone: PillTone.neutral,
                        dense: true,
                      ),
                    )
                    .toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRecentScenesSection() => Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(DS.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    context.l10n.memoryPanelRecentScenes,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: DS.fontWeightBold),
                  ),
                  const Spacer(),
                  Text(
                    context.l10n.memoryPanelItemCount(_recentScenes.length),
                    style: TextStyle(color: DS.textSecondary),
                  ),
                ],
              ),
              const SizedBox(height: DS.sm),
              ..._recentScenes.map(_buildRecentSceneTile),
            ],
          ),
        ),
      );

  Widget _buildRecentSceneTile(RecentSceneSummaryItem item) => Padding(
        padding: const EdgeInsets.only(bottom: DS.sm),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        context.l10n.memoryPanelSceneMemories(
                            _formatSceneTime(item.timeStart, item.timeEnd),
                            item.memberCount,),
                        style: TextStyle(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.sm),
                SemanticPill(
                  // S2 例4：Q 值是机器指标，释义化为三档人话（§6.3 禁裸数值）。
                  label: bandLabel(
                    item.qualityScore,
                    context.l10n,
                    high: (l10n) => l10n.displaySceneQualityHigh,
                    mid: (l10n) => l10n.displaySceneQualityMid,
                    low: (l10n) => l10n.displaySceneQualityLow,
                  ),
                  tone: PillTone.success,
                  dense: true,
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildPreferenceCard(MemoryPreferenceItem item) => _MemoryCard(
        title: item.prefKey,
        subtitle: _formatPreferenceSubtitle(item),
        badge: MemoryEvidenceBadge(
          status: _statusFor(item.evidenceMissing, item.evidenceRefs),
        ),
        correctionCount: item.correctionCount,
        footer: _buildPreferenceFooter(item),
        onTap: () => _openDetail(
          context,
          MemoryDetailArgs.preference(item),
        ),
      );

  Widget _buildGoalCard(MemoryGoalItem item) => _MemoryCard(
        title: item.title,
        // S2 例4：记录状态经词典人话化，禁「completed」等原始枚举直出。
        subtitle: memoryRecordStatusLabel(context.l10n, item.status) ??
            item.status,
        badge: MemoryEvidenceBadge(
          status: _statusFor(item.evidenceMissing, item.evidenceRefs),
        ),
        correctionCount: item.correctionCount,
        onTap: () => _openDetail(
          context,
          MemoryDetailArgs.goal(item),
        ),
      );

  Widget _buildEpisodicCard(EpisodicMemoryItem item) => _MemoryCard(
        // S2 例4：英文事件名（「completed …」类）经动词词典人话化。
        title: humanizeMemoryEvent(item.summary, context.l10n),
        subtitle: _formatEpisodicSubtitle(item),
        badge: MemoryEvidenceBadge(
          status: _statusFor(item.evidenceMissing, item.evidenceRefs),
        ),
        correctionCount: item.correctionCount,
        footer: _buildEpisodicGovernanceFooter(item),
        onTap: () => _openDetail(
          context,
          MemoryDetailArgs.episodic(item),
        ),
      );

  /// memory-governance-mvp: 每条情景记忆的来源标注 + 标签 + 纠正/删除/确认操作。
  Widget? _buildEpisodicGovernanceFooter(EpisodicMemoryItem item) {
    final parts = <Widget>[];
    final sourceLine = _formatEpisodicSourceLine(item);
    if (sourceLine.isNotEmpty) {
      parts.add(
        Text(
          sourceLine,
          style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
        ),
      );
    }
    if (item.tags.isNotEmpty) {
      parts.add(
        Padding(
          padding: const EdgeInsets.only(top: DS.xs),
          child: Wrap(
            spacing: DS.xs,
            runSpacing: DS.xs,
            children: item.tags
                .take(4)
                .map(
                  (tag) => SemanticPill(
                    label: tag,
                    tone: PillTone.neutral,
                    dense: true,
                  ),
                )
                .toList(),
          ),
        ),
      );
    }
    if (_isInferredAutoMemory(item)) {
      parts.add(
        Padding(
          padding: const EdgeInsets.only(top: DS.xs),
          child: Text(
            context.l10n.memoryPanelAiInferredDescription,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ),
      );
      if ((item.decayPolicy ?? '').isNotEmpty) {
        parts.add(
          Padding(
            padding: const EdgeInsets.only(top: DS.xs),
            child: Text(
              context.l10n.memoryPanelValidUntil(item.decayPolicy!),
              style:
                  TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
            ),
          ),
        );
      }
    }
    parts.add(
      Padding(
        padding: const EdgeInsets.only(top: DS.sm),
        child: Wrap(
          spacing: DS.sm,
          runSpacing: DS.sm,
          children: [
            SparkleButton(
              label: _correctingIds.contains(item.id)
                  ? context.l10n.memoryGovWorking
                  : context.l10n.memoryGovConfirm,
              onPressed: _correctingIds.contains(item.id)
                  ? () {}
                  : () => _correctEpisodic(item, 'confirm'),
              disabled: _correctingIds.contains(item.id),
              variant: ButtonVariant.ghost,
            ),
            SparkleButton(
              label: context.l10n.memoryGovCorrect,
              onPressed: _correctingIds.contains(item.id)
                  ? () {}
                  : () => _showCorrectionSheet(item),
              disabled: _correctingIds.contains(item.id),
              variant: ButtonVariant.ghost,
            ),
            SparkleButton(
              label: context.l10n.memoryGovDelete,
              onPressed: _correctingIds.contains(item.id)
                  ? () {}
                  : () => _correctEpisodic(item, 'delete'),
              disabled: _correctingIds.contains(item.id),
              variant: ButtonVariant.ghost,
            ),
            if (_isInferredAutoMemory(item))
              SparkleButton(
                label: _revokingIds.contains(item.id)
                    ? context.l10n.memoryPanelRevoking
                    : context.l10n.memoryPanelRevokeThis,
                onPressed: _revokingIds.contains(item.id)
                    ? () {}
                    : () => _revokeAutoMemory(item),
                disabled: _revokingIds.contains(item.id),
                variant: ButtonVariant.ghost,
              ),
            if (AppFeatureFlags.enableEvidenceViewer)
              SparkleButton.ghost(
                onPressed: () => EvidenceDrawer.show(
                  context,
                  refs: item.evidenceRefs,
                  evidenceMissing: item.evidenceMissing,
                ),
                label: context.l10n.memoryViewEvidence,
              ),
          ],
        ),
      ),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: parts,
    );
  }

  /// memory-governance-mvp: "这条记忆从哪来"的一行标注（模块 + 对话轮次 + 写入时间）。
  String _formatEpisodicSourceLine(EpisodicMemoryItem item) {
    final parts = <String>[
      context.l10n.memoryGovSource(_episodicSourceLabel(item)),
      if (item.sourceTurnId != null)
        context.l10n.memoryGovTurn(
          item.sourceTurnId!.length > 8
              ? item.sourceTurnId!.substring(0, 8)
              : item.sourceTurnId!,
        ),
      if (item.writtenAt != null)
        context.l10n.memoryGovWrittenAt(_formatUpdated(item.writtenAt)),
    ];
    return parts.join(' · ');
  }

  String _episodicSourceLabel(EpisodicMemoryItem item) => switch (item.sourceType) {
        'chat' || 'text' => context.l10n.memSrcChat,
        'analysis' => context.l10n.memSrcAnalysis,
        'user_state' => context.l10n.memSrcUserState,
        'user_created' => context.l10n.memSrcUserCreated,
        'behavior' || 'behavior_auto' => context.l10n.memSrcBehavior,
        'document' || 'document_import' => context.l10n.memSrcDocument,
        'error_book' => context.l10n.memSrcErrorBook,
        'plan' => context.l10n.memSrcPlan,
        'system' => context.l10n.memSrcSystem,
        _ => item.sourceLabel ?? item.sourceType,
      };

  Set<String> get _correctingIds => _data.correctingIds;

  bool get _episodicHasMore => _data.episodicHasMore;

  int get _episodicTotal => _data.episodicTotal;

  bool get _episodicLoadingMore => _data.episodicLoadingMore;

  Future<void> _correctEpisodic(
    EpisodicMemoryItem item,
    String action, {
    String? reason,
  }) async {
    try {
      await ref
          .read(_memoryPanelDataProvider.notifier)
          .correctEpisodic(item, action: action, reason: reason);
      if (!mounted) {
        return;
      }
      AppFeedback.success(
        context,
        switch (action) {
          'confirm' => context.l10n.memoryGovConfirmed,
          'delete' => context.l10n.memoryGovDeleted,
          _ => context.l10n.memoryGovCorrected,
        },
      );
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, context.l10n.memoryGovFailed('$e'));
    }
  }

  Future<void> _showCorrectionSheet(EpisodicMemoryItem item) async {
    final result = await showModalBottomSheet<(String, String?)>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (sheetContext) => _CorrectionActionSheet(item: item),
    );
    if (!mounted || result == null) {
      return;
    }
    await _correctEpisodic(item, result.$1, reason: result.$2);
  }

  Future<void> _loadMoreEpisodic() async {
    try {
      await ref.read(_memoryPanelDataProvider.notifier).loadMoreEpisodic();
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, context.l10n.memoryGovFailed('$e'));
    }
  }

  void _openDetail(BuildContext context, MemoryDetailArgs args) {
    unawaited(context.push(MemoryRoutes.detail, extra: args));
  }

  String _formatUpdated(DateTime? value) {
    if (value == null) {
      return context.l10n.memoryPanelNotUpdated;
    }
    return '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
  }

  String _formatSceneTime(DateTime start, DateTime end) {
    // S2 例2/X8：时间 Range 走唯一格式化入口；起止相同折叠为单点，禁毫秒。
    return formatSparkleSceneRange(start, end, context.l10n);
  }

  String _labelForForesightDim(String dim) {
    switch (dim) {
      case 'study_pace':
        return context.l10n.memoryPanelDimPace;
      case 'completion_rate':
        return context.l10n.memoryPanelDimCompletionRate;
      case 'engagement_level':
        return context.l10n.memoryPanelDimEngagement;
      case 'mood_valence':
        return context.l10n.memoryPanelDimMood;
      case 'plan_adherence':
        return context.l10n.memoryPanelDimPlanAdherence;
      default:
        return dim;
    }
  }

  List<EpisodicMemoryItem> get _autoMemoryEntries => _episodic
      .where(_isInferredAutoMemory)
      .toList(growable: false);

  MemoryEvidenceStatus _statusFor(
    bool evidenceMissing,
    List<EvidenceRefModel> refs,
  ) {
    if (evidenceMissing) {
      return MemoryEvidenceStatus.missing;
    }
    if (refs.any((ref) => ref.userDeleted)) {
      return MemoryEvidenceStatus.redacted;
    }
    return MemoryEvidenceStatus.ok;
  }

  String _formatPreferenceSubtitle(MemoryPreferenceItem item) {
    final parts = <String>[
      if ((item.sourceLabel ?? '').isNotEmpty) item.sourceLabel!,
      _formatUpdated(item.updatedAt),
    ];
    return parts.join(' · ');
  }

  String _formatEpisodicSubtitle(EpisodicMemoryItem item) {
    final parts = <String>[
      if (_isInferredAutoMemory(item))
        item.declarationLabel ?? context.l10n.memoryPanelAiAutoMemories,
      if ((item.subjectType ?? '').isNotEmpty) item.subjectType!,
      _formatUpdated(item.occurredAt),
    ];
    return parts.join(' · ');
  }

  Widget? _buildPreferenceFooter(MemoryPreferenceItem item) {
    final parts = <Widget>[];
    if ((item.explanation ?? '').isNotEmpty) {
      parts.add(
        Text(
          item.explanation!,
          style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
        ),
      );
    }
    if (item.sourceType == 'ai_inferred' && item.adjustable) {
      if (parts.isNotEmpty) {
        parts.add(const SizedBox(height: DS.sm));
      }
      parts.add(
        Align(
          alignment: Alignment.centerLeft,
          child: SparkleButton.ghost(
            onPressed: () => _openPersonaAdjust(item),
            label: context.l10n.memoryPanelAdjust,
          ),
        ),
      );
    }
    if (parts.isEmpty) {
      return null;
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: parts,
    );
  }

  bool _isInferredAutoMemory(EpisodicMemoryItem item) =>
      item.sourceLane == 'inferred_extraction';

  Future<void> _revokeAutoMemory(EpisodicMemoryItem item) async {
    try {
      await ref.read(_memoryPanelDataProvider.notifier).revokeAutoMemory(item);
      if (!mounted) {
        return;
      }
      AppFeedback.success(context, context.l10n.memoryPanelRevokedAutoMemory);
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, context.l10n.memoryPanelRevokeFailed('$e'));
    }
  }

  Future<void> _resolvePendingCommitment(PendingCommitmentItem item) async {
    try {
      await ref
          .read(_memoryPanelDataProvider.notifier)
          .resolvePendingCommitment(item);
      if (!mounted) {
        return;
      }
      AppFeedback.success(context, context.l10n.memoryPanelMarkedComplete);
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, context.l10n.memoryPanelMarkFailed('$e'));
    }
  }

  Future<void> _dismissPendingCommitment(PendingCommitmentItem item) async {
    try {
      await ref
          .read(_memoryPanelDataProvider.notifier)
          .dismissPendingCommitment(item);
      if (!mounted) {
        return;
      }
      AppFeedback.success(context, context.l10n.memoryPanelCommitmentDismissed);
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, context.l10n.memoryPanelDismissFailed('$e'));
    }
  }

  Future<void> _selectConflictLeft(UnresolvedConflictItem item) async {
    await _arbitrateConflict(item,
        selection: 'left',
        successMessage: context.l10n.memoryPanelConflictResolvedA,);
  }

  Future<void> _selectConflictRight(UnresolvedConflictItem item) async {
    await _arbitrateConflict(item,
        selection: 'right',
        successMessage: context.l10n.memoryPanelConflictResolvedB,);
  }

  Future<void> _selectConflictNone(UnresolvedConflictItem item) async {
    await _arbitrateConflict(item,
        selection: 'none',
        successMessage: context.l10n.memoryPanelConflictResolvedNone,);
  }

  Future<void> _arbitrateConflict(
    UnresolvedConflictItem item, {
    required String selection,
    required String successMessage,
  }) async {
    try {
      await ref.read(_memoryPanelDataProvider.notifier).arbitrateConflict(
            item,
            selection: selection,
          );
      if (!mounted) {
        return;
      }
      AppFeedback.success(context, successMessage);
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, context.l10n.memoryPanelConflictFailed('$e'));
    }
  }

  void _openPersonaAdjust(MemoryPreferenceItem item) {
    final uri = Uri(
      path: UserRoutes.persona,
      queryParameters: {'override': item.prefKey},
    );
    unawaited(context.push(uri.toString()));
  }
}

/// memory-governance-mvp: 纠正动作选择面板。
/// 返回 (action, reason)：wrong=记错 / outdated=不再是；取消返回 null。
class _CorrectionActionSheet extends StatefulWidget {
  const _CorrectionActionSheet({required this.item});

  final EpisodicMemoryItem item;

  @override
  State<_CorrectionActionSheet> createState() => _CorrectionActionSheetState();
}

class _CorrectionActionSheetState extends State<_CorrectionActionSheet> {
  final _reasonController = TextEditingController();

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  void _submit(String action) {
    final reason = _reasonController.text.trim();
    Navigator.of(context).pop((action, reason.isEmpty ? null : reason));
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return Padding(
      padding: EdgeInsets.only(
        left: DS.lg,
        right: DS.lg,
        top: DS.sm,
        bottom: DS.lg + MediaQuery.viewPaddingOf(context).bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.memoryGovSheetTitle,
            // sheet 主标题：依赖 19px 视觉重量，显式升 titleLarge（N41 同名
            // 同值收敛后 DS.titleMedium=16/w500——TYPE-RHYTHM 卡）。
            style: DS.titleLarge.copyWith(fontWeight: DS.fontWeightBold),
          ),
          const SizedBox(height: DS.md),
          SparkleButton(
            label: l10n.memoryGovWrong,
            variant: ButtonVariant.secondary,
            onPressed: () => _submit('wrong'),
          ),
          const SizedBox(height: DS.sm),
          SparkleButton(
            label: l10n.memoryGovOutdated,
            variant: ButtonVariant.secondary,
            onPressed: () => _submit('outdated'),
          ),
          const SizedBox(height: DS.md),
          TextField(
            controller: _reasonController,
            maxLines: 2,
            maxLength: 200,
            decoration: InputDecoration(
              hintText: l10n.memoryGovReasonHint,
              border: const OutlineInputBorder(),
              isDense: true,
            ),
          ),
        ],
      ),
    );
  }
}

class _MemoryPanelLoadingSkeleton extends StatelessWidget {
  const _MemoryPanelLoadingSkeleton();


  @override
  Widget build(BuildContext context) => ListView.separated(
        padding: const EdgeInsets.all(DS.lg),
        itemBuilder: (context, index) => Card(
          margin: EdgeInsets.zero,
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _SkeletonBar(widthFactor: index == 0 ? 0.42 : 0.62),
                const SizedBox(height: DS.sm),
                const _SkeletonBar(widthFactor: 0.88, height: 12),
                const SizedBox(height: DS.xs),
                const _SkeletonBar(widthFactor: 0.58, height: 12),
              ],
            ),
          ),
        ),
        separatorBuilder: (context, index) => const SizedBox(height: DS.md),
        itemCount: 5,
      );
}

class _SkeletonBar extends StatelessWidget {
  const _SkeletonBar({
    required this.widthFactor,
    this.height = 16,
  });

  final double widthFactor;
  final double height;

  @override
  Widget build(BuildContext context) => FractionallySizedBox(
        widthFactor: widthFactor,
        alignment: Alignment.centerLeft,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.surfaceTertiary,
            borderRadius: BorderRadius.circular(999),
          ),
          child: SizedBox(height: height),
        ),
      );
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => Text(
        title,
        style: Theme.of(context)
            .textTheme
            .titleLarge
            ?.copyWith(color: DS.textPrimary),
      );
}

class _MemoryCard extends StatelessWidget {
  const _MemoryCard({
    required this.title,
    required this.subtitle,
    required this.badge,
    required this.correctionCount,
    required this.onTap,
    this.footer,
  });

  final String title;
  final String subtitle;
  final Widget badge;
  final int correctionCount;
  final VoidCallback onTap;
  final Widget? footer;

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: DS.md),
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(DS.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 4),
                          Text(subtitle),
                        ],
                      ),
                    ),
                    const SizedBox(width: DS.sm),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        badge,
                        if (correctionCount > 0) ...[
                          const SizedBox(width: 6),
                          _CorrectionBadge(
                              label: context.l10n
                                  .memoryPanelCorrectionCount(correctionCount),),
                        ],
                      ],
                    ),
                  ],
                ),
                if (footer != null) ...[
                  const SizedBox(height: DS.sm),
                  footer!,
                ],
              ],
            ),
          ),
        ),
      );
}

class _CorrectionBadge extends StatelessWidget {
  const _CorrectionBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) =>
      SemanticPill(label: label, tone: PillTone.warning, dense: true);
}

