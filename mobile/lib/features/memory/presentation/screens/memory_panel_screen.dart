import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/memory/memory_routes.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_detail_screen.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_drawer.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';
import 'package:sparkle/features/memory/presentation/widgets/pending_commitments_section.dart';
import 'package:sparkle/features/memory/presentation/widgets/unresolved_conflicts_section.dart';
import 'package:sparkle/features/user/user_routes.dart';

enum MemoryEntryType { preference, goal, episodic }

enum MemorySort { newest, oldest, importance, confidence }

enum MemoryViewMode { compact, expanded }

class MemoryEntry {
  MemoryEntry({
    required this.id,
    required this.type,
    required this.title,
    required this.evidenceStatus,
    required this.detailArgs,
    required this.updatedAt,
    required this.correctionCount,
    this.importance,
    this.confidence,
  });

  final String id;
  final MemoryEntryType type;
  final String title;
  final MemoryEvidenceStatus evidenceStatus;
  final MemoryDetailArgs detailArgs;
  final DateTime? updatedAt;
  final int correctionCount;
  final double? importance;
  final double? confidence;
}

class MemoryPanelScreen extends ConsumerStatefulWidget {
  const MemoryPanelScreen({super.key});

  @override
  ConsumerState<MemoryPanelScreen> createState() => _MemoryPanelScreenState();
}

class _MemoryPanelScreenState extends ConsumerState<MemoryPanelScreen> {
  bool _loading = true;
  String? _error;
  List<MemoryPreferenceItem> _preferences = [];
  List<MemoryGoalItem> _goals = [];
  List<EpisodicMemoryItem> _episodic = [];
  List<RecentSceneSummaryItem> _recentScenes = [];
  ForesightHintSummaryItem? _foresightHint;
  List<PendingCommitmentItem> _pendingCommitments = [];
  List<UnresolvedConflictItem> _unresolvedConflicts = [];
  MemoryEntryType? _filterType;
  MemoryEvidenceStatus? _filterEvidence;
  DateTimeRange? _dateRange;
  MemorySort _sort = MemorySort.newest;
  MemoryViewMode _viewMode = MemoryViewMode.compact;
  final Set<String> _pinnedIds = {};
  final Set<String> _revokingIds = {};
  final Set<String> _processingCommitmentIds = {};
  final Set<String> _processingConflictIds = {};

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final service = ref.read(memoryApiServiceProvider);
      final results = await Future.wait([
        service.getPreferences(),
        service.getGoals(),
        service.getEpisodic(),
        service.getRecentScenes(),
        service.getForesightHintSummary(),
        service.getPendingCommitments(),
        service.getUnresolvedConflicts(),
      ]);
      if (!mounted) {
        return;
      }
      setState(() {
        _preferences = results[0] as List<MemoryPreferenceItem>;
        _goals = results[1] as List<MemoryGoalItem>;
        _episodic = results[2] as List<EpisodicMemoryItem>;
        _recentScenes = results[3] as List<RecentSceneSummaryItem>;
        _foresightHint = results[4] as ForesightHintSummaryItem?;
        _pendingCommitments = results[5] as List<PendingCommitmentItem>;
        _unresolvedConflicts = results[6] as List<UnresolvedConflictItem>;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = context.l10n.memoryPanelLoadFailed('$e');
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => GraphiteScaffold(
        safeArea: false,
        appBar: AppBar(
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
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
              onPressed: _loadAll,
              variant: ButtonVariant.ghost,
            ),
          ],
        ),
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ContentConstraint(
                child: _error != null
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
                _error ?? context.l10n.memoryPanelUnavailable,
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

  Widget _buildV1Panel(BuildContext context) => RefreshIndicator(
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
                ..._autoMemoryEntries.map((item) => _buildEpisodicCard(item)),
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
            ],
          ],
        ),
      );

  Widget _buildV2Panel(BuildContext context) {
    final entries = _applySort(_applyFilters(_buildEntries()));
    return RefreshIndicator(
      onRefresh: _loadAll,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(DS.lg),
        children: [
          SparkleStaggerItem(index: 0, child: _buildFilterBar(context)),
          const SizedBox(height: DS.md),
          if (!_hasAnyMemoryContent) ...[
            _buildGuidedEmptyState(context),
          ] else ...[
            if (_foresightHint?.hintText?.isNotEmpty ?? false) ...[
              SparkleStaggerItem(index: 1, child: _buildForesightHintSection()),
              const SizedBox(height: DS.md),
            ],
            if (_recentScenes.isNotEmpty) ...[
              SparkleStaggerItem(
                index: _foresightHint?.hintText?.isNotEmpty ?? false ? 2 : 1,
                child: _buildRecentScenesSection(),
              ),
              const SizedBox(height: DS.md),
            ],
            if (_unresolvedConflicts.isNotEmpty)
              UnresolvedConflictsSection(
                items: _unresolvedConflicts,
                processingIds: _processingConflictIds,
                onSelectLeft: _selectConflictLeft,
                onSelectRight: _selectConflictRight,
                onSelectNone: _selectConflictNone,
              ),
            if (_unresolvedConflicts.isNotEmpty) const SizedBox(height: DS.md),
            if (_pendingCommitments.isNotEmpty)
              PendingCommitmentsSection(
                items: _pendingCommitments,
                processingIds: _processingCommitmentIds,
                onResolve: _resolvePendingCommitment,
                onDismiss: _dismissPendingCommitment,
              ),
            if (_pendingCommitments.isNotEmpty) const SizedBox(height: DS.md),
            if (entries.isEmpty)
              _buildEmptyState(context)
            else
              ...entries.indexed.map(
                (entry) => SparkleStaggerItem(
                  index: entry.$1 +
                      (_recentScenes.isNotEmpty ? 2 : 1) +
                      ((_foresightHint?.hintText?.isNotEmpty ?? false) ? 1 : 0),
                  child: _buildEntryCard(entry.$2),
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _buildFilterBar(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: DS.sm,
            runSpacing: DS.sm,
            children: [
              _buildFilterChip(
                label: context.l10n.taskFilterAll,
                selected: _filterType == null,
                onSelected: (_) => _setTypeFilter(null),
              ),
              _buildFilterChip(
                label: context.l10n.memoryTypePreference,
                selected: _filterType == MemoryEntryType.preference,
                onSelected: (_) => _setTypeFilter(MemoryEntryType.preference),
              ),
              _buildFilterChip(
                label: context.l10n.memoryTypeGoal,
                selected: _filterType == MemoryEntryType.goal,
                onSelected: (_) => _setTypeFilter(MemoryEntryType.goal),
              ),
              _buildFilterChip(
                label: context.l10n.memoryTypeEpisodic,
                selected: _filterType == MemoryEntryType.episodic,
                onSelected: (_) => _setTypeFilter(MemoryEntryType.episodic),
              ),
            ],
          ),
          const SizedBox(height: DS.sm),
          Wrap(
            spacing: DS.sm,
            runSpacing: DS.sm,
            children: [
              _buildFilterChip(
                label: context.l10n.memoryPanelEvidenceAll,
                selected: _filterEvidence == null,
                onSelected: (_) => _setEvidenceFilter(null),
              ),
              _buildFilterChip(
                label: context.l10n.memoryPanelEvidenceOk,
                selected: _filterEvidence == MemoryEvidenceStatus.ok,
                onSelected: (_) => _setEvidenceFilter(MemoryEvidenceStatus.ok),
              ),
              _buildFilterChip(
                label: context.l10n.memoryPanelEvidenceMissing,
                selected: _filterEvidence == MemoryEvidenceStatus.missing,
                onSelected: (_) =>
                    _setEvidenceFilter(MemoryEvidenceStatus.missing),
              ),
              _buildFilterChip(
                label: context.l10n.memoryPanelEvidenceRedacted,
                selected: _filterEvidence == MemoryEvidenceStatus.redacted,
                onSelected: (_) =>
                    _setEvidenceFilter(MemoryEvidenceStatus.redacted),
              ),
            ],
          ),
          const SizedBox(height: DS.sm),
          Row(
            children: [
              DropdownButton<MemorySort>(
                value: _sort,
                onChanged: (value) {
                  if (value == null) {
                    return;
                  }
                  setState(() => _sort = value);
                },
                items: [
                  DropdownMenuItem(
                    value: MemorySort.newest,
                    child: Text(context.l10n.memorySortNewest),
                  ),
                  DropdownMenuItem(
                    value: MemorySort.oldest,
                    child: Text(context.l10n.memorySortOldest),
                  ),
                  DropdownMenuItem(
                    value: MemorySort.importance,
                    child: Text(context.l10n.memorySortImportance),
                  ),
                  DropdownMenuItem(
                    value: MemorySort.confidence,
                    child: Text(context.l10n.memoryConfidence),
                  ),
                ],
              ),
              const Spacer(),
              SparkleButton.ghost(
                label: _dateRange == null
                    ? context.l10n.memoryPanelDate
                    : '${_dateRange!.start.month}/${_dateRange!.start.day}'
                        ' - ${_dateRange!.end.month}/${_dateRange!.end.day}',
                onPressed: _pickDateRange,
                icon: const Icon(Icons.date_range),
              ),
              const SizedBox(width: DS.sm),
              SparkleIconButton(
                icon: Icon(
                  _viewMode == MemoryViewMode.compact
                      ? Icons.view_agenda
                      : Icons.view_stream,
                ),
                onPressed: () => setState(() {
                  _viewMode = _viewMode == MemoryViewMode.compact
                      ? MemoryViewMode.expanded
                      : MemoryViewMode.compact;
                }),
                variant: ButtonVariant.ghost,
              ),
            ],
          ),
        ],
      );

  void _clearFilters() {
    setState(() {
      _filterType = null;
      _filterEvidence = null;
      _dateRange = null;
    });
  }

  Widget _buildEmptyState(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.xl),
        child: EmptyState(
          type: EmptyStateType.noResults,
          title: context.l10n.memoryPanelEmptyFilterTitle,
          description: context.l10n.memoryPanelEmptyFilterDescription,
          actionText: context.l10n.memoryPanelClearFilter,
          onAction: _clearFilters,
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
      if (item.deviationCount > 0) context.l10n.memoryPanelDeviationsDetected(item.deviationCount),
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
                      (confidence) => Chip(
                        label: Text(
                          '${_labelForForesightDim(confidence.dim)} ${confidence.confidence.toStringAsFixed(2)}',
                        ),
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
                        context.l10n.memoryPanelSceneMemories(_formatSceneTime(item.timeStart, item.timeEnd), item.memberCount),
                        style: TextStyle(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.sm),
                Chip(
                  label: Text('Q ${item.qualityScore.toStringAsFixed(2)}'),
                  backgroundColor: DS.semanticSuccess.withValues(alpha: 0.12),
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
        subtitle: item.status,
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
        title: item.summary,
        subtitle: _formatEpisodicSubtitle(item),
        badge: MemoryEvidenceBadge(
          status: _statusFor(item.evidenceMissing, item.evidenceRefs),
        ),
        correctionCount: item.correctionCount,
        footer: _buildEpisodicFooter(item),
        onTap: () => _openDetail(
          context,
          MemoryDetailArgs.episodic(item),
        ),
      );

  Widget _buildEntryCard(MemoryEntry entry) {
    final isPinned = _pinnedIds.contains(entry.id);
    final preference = entry.detailArgs.preference;
    final episodic = entry.detailArgs.episodic;
    final showAdjust = preference?.sourceType == 'ai_inferred' &&
        (preference?.adjustable ?? false);
    final showUndo = episodic != null && _isInferredAutoMemory(episodic);
    final subtitle = [
      _entryTypeLabel(entry.type),
      if (episodic != null && _isInferredAutoMemory(episodic)) context.l10n.memoryPanelAiAutoMemories,
      _formatUpdated(entry.updatedAt),
    ].where((value) => value.isNotEmpty).join(' · ');
    return Card(
      margin: const EdgeInsets.only(bottom: DS.md),
      child: ListTile(
        title: Text(entry.title, maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: _viewMode == MemoryViewMode.compact
            ? Text(subtitle)
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(subtitle),
                  const SizedBox(height: 4),
                  Text(_formatMetrics(entry)),
                ],
              ),
        trailing: SizedBox(
          width: showAdjust || showUndo ? 260 : 176,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              MemoryEvidenceBadge(status: entry.evidenceStatus),
              if (entry.correctionCount > 0) ...[
                const SizedBox(width: 6),
                _CorrectionBadge(label: context.l10n.memoryPanelCorrectionCount(entry.correctionCount)),
              ],
              if (showAdjust) ...[
                const SizedBox(width: 6),
                SparkleButton.ghost(
                  onPressed: () => _openPersonaAdjust(preference!),
                  label: context.l10n.memoryPanelAdjust,
                ),
              ],
              if (showUndo) ...[
                const SizedBox(width: 6),
                SparkleButton(
                  label: _revokingIds.contains(entry.id) ? context.l10n.memoryPanelRevoking : context.l10n.memoryPanelRevoke,
                  onPressed: _revokingIds.contains(entry.id)
                      ? () {}
                      : () => _revokeAutoMemory(episodic!),
                  disabled: _revokingIds.contains(entry.id),
                  variant: ButtonVariant.ghost,
                ),
              ],
              const SizedBox(width: 4),
              SparkleIconButton(
                icon: Icon(
                  isPinned ? Icons.push_pin : Icons.push_pin_outlined,
                ),
                onPressed: () => setState(() {
                  if (isPinned) {
                    _pinnedIds.remove(entry.id);
                  } else {
                    _pinnedIds.add(entry.id);
                  }
                }),
                variant: ButtonVariant.ghost,
                size: 32,
              ),
            ],
          ),
        ),
        onTap: () => _openDetail(context, entry.detailArgs),
      ),
    );
  }

  void _openDetail(BuildContext context, MemoryDetailArgs args) {
    final router = GoRouter.maybeOf(context);
    if (router != null) {
      context.push(MemoryRoutes.detail, extra: args);
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => MemoryDetailScreen(args: args),
      ),
    );
  }

  String _formatUpdated(DateTime? value) {
    if (value == null) {
      return context.l10n.memoryPanelNotUpdated;
    }
    return '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
  }

  String _formatSceneTime(DateTime start, DateTime end) {
    final startLabel =
        '${start.month.toString().padLeft(2, '0')}/${start.day.toString().padLeft(2, '0')} ${start.hour.toString().padLeft(2, '0')}:${start.minute.toString().padLeft(2, '0')}';
    final endLabel =
        '${end.month.toString().padLeft(2, '0')}/${end.day.toString().padLeft(2, '0')} ${end.hour.toString().padLeft(2, '0')}:${end.minute.toString().padLeft(2, '0')}';
    return '$startLabel - $endLabel';
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

  String _entryTypeLabel(MemoryEntryType type) => switch (type) {
        MemoryEntryType.preference => context.l10n.memoryTypePreference,
        MemoryEntryType.goal => context.l10n.memoryTypeGoal,
        MemoryEntryType.episodic => context.l10n.memoryTypeEpisodic,
      };

  List<EpisodicMemoryItem> get _autoMemoryEntries => _episodic
      .where((item) => _isInferredAutoMemory(item))
      .toList(growable: false);

  String _formatMetrics(MemoryEntry entry) {
    final importance = entry.importance;
    final confidence = entry.confidence;
    final parts = <String>[];
    if (importance != null) {
      parts.add(context.l10n.memoryPanelImportanceValue(importance.toStringAsFixed(2)));
    }
    if (confidence != null) {
      parts.add(context.l10n.memoryPanelConfidenceValue(confidence.toStringAsFixed(2)));
    }
    return parts.isEmpty ? context.l10n.memoryPanelMetricsNone : parts.join(' · ');
  }

  void _setTypeFilter(MemoryEntryType? type) {
    setState(() {
      _filterType = type;
    });
  }

  void _setEvidenceFilter(MemoryEvidenceStatus? status) {
    setState(() {
      _filterEvidence = status;
    });
  }

  Future<void> _pickDateRange() async {
    final selected = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      initialDateRange: _dateRange,
    );
    if (selected != null) {
      setState(() => _dateRange = selected);
    }
  }

  List<MemoryEntry> _buildEntries() {
    final entries = <MemoryEntry>[];
    for (final item in _preferences) {
      entries.add(
        MemoryEntry(
          id: item.id,
          type: MemoryEntryType.preference,
          title: item.prefKey,
          updatedAt: item.updatedAt,
          confidence: item.confidence,
          evidenceStatus: _statusFor(item.evidenceMissing, item.evidenceRefs),
          correctionCount: item.correctionCount,
          detailArgs: MemoryDetailArgs.preference(item),
        ),
      );
    }
    for (final item in _goals) {
      entries.add(
        MemoryEntry(
          id: item.id,
          type: MemoryEntryType.goal,
          title: item.title,
          updatedAt: item.updatedAt,
          evidenceStatus: _statusFor(item.evidenceMissing, item.evidenceRefs),
          correctionCount: item.correctionCount,
          detailArgs: MemoryDetailArgs.goal(item),
        ),
      );
    }
    for (final item in _episodic) {
      entries.add(
        MemoryEntry(
          id: item.id,
          type: MemoryEntryType.episodic,
          title: item.summary,
          updatedAt: item.occurredAt,
          importance: item.importanceScore,
          evidenceStatus: _statusFor(item.evidenceMissing, item.evidenceRefs),
          correctionCount: item.correctionCount,
          detailArgs: MemoryDetailArgs.episodic(item),
        ),
      );
    }
    return entries;
  }

  List<MemoryEntry> _applyFilters(List<MemoryEntry> entries) =>
      entries.where((entry) {
        if (_filterType != null && entry.type != _filterType) {
          return false;
        }
        if (_filterEvidence != null &&
            entry.evidenceStatus != _filterEvidence) {
          return false;
        }
        if (_dateRange != null && entry.updatedAt != null) {
          if (entry.updatedAt!.isBefore(_dateRange!.start) ||
              entry.updatedAt!.isAfter(_dateRange!.end)) {
            return false;
          }
        }
        return true;
      }).toList();

  List<MemoryEntry> _applySort(List<MemoryEntry> entries) {
    entries.sort((a, b) {
      if (_pinnedIds.contains(a.id) && !_pinnedIds.contains(b.id)) {
        return -1;
      }
      if (_pinnedIds.contains(b.id) && !_pinnedIds.contains(a.id)) {
        return 1;
      }
      switch (_sort) {
        case MemorySort.oldest:
          return _compareDates(a.updatedAt, b.updatedAt);
        case MemorySort.importance:
          return _compareNumber(b.importance, a.importance);
        case MemorySort.confidence:
          return _compareNumber(b.confidence, a.confidence);
        case MemorySort.newest:
          return _compareDates(b.updatedAt, a.updatedAt);
      }
    });
    return entries;
  }

  int _compareDates(DateTime? a, DateTime? b) {
    if (a == null && b == null) {
      return 0;
    }
    if (a == null) {
      return 1;
    }
    if (b == null) {
      return -1;
    }
    return a.compareTo(b);
  }

  int _compareNumber(double? a, double? b) {
    if (a == null && b == null) {
      return 0;
    }
    if (a == null) {
      return 1;
    }
    if (b == null) {
      return -1;
    }
    return a.compareTo(b);
  }

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
      if (_isInferredAutoMemory(item)) item.declarationLabel ?? context.l10n.memoryPanelAiAutoMemories,
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

  Widget? _buildEpisodicFooter(EpisodicMemoryItem item) {
    if (!_isInferredAutoMemory(item)) {
      return null;
    }
    final parts = <Widget>[
      Text(
        context.l10n.memoryPanelAiInferredDescription,
        style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
      ),
    ];
    if ((item.decayPolicy ?? '').isNotEmpty) {
      parts.add(
        Padding(
          padding: const EdgeInsets.only(top: DS.xs),
          child: Text(
            context.l10n.memoryPanelValidUntil(item.decayPolicy!),
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ),
      );
    }
    parts.add(
      Padding(
        padding: const EdgeInsets.only(top: DS.sm),
        child: Wrap(
          spacing: DS.sm,
          runSpacing: DS.sm,
          children: [
            SparkleButton(
              label: _revokingIds.contains(item.id) ? context.l10n.memoryPanelRevoking : context.l10n.memoryPanelRevokeThis,
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

  bool _isInferredAutoMemory(EpisodicMemoryItem item) =>
      item.sourceLane == 'inferred_extraction';

  Future<void> _revokeAutoMemory(EpisodicMemoryItem item) async {
    setState(() {
      _revokingIds.add(item.id);
    });
    try {
      final service = ref.read(memoryApiServiceProvider);
      await service.retractMemory(
        type: 'episodic',
        id: item.id,
        reason: 'user_revoked_ai_auto_memory',
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _episodic = _episodic.where((entry) => entry.id != item.id).toList();
        _revokingIds.remove(item.id);
      });
      AppFeedback.success(context, context.l10n.memoryPanelRevokedAutoMemory);
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _revokingIds.remove(item.id);
      });
      AppFeedback.error(context, context.l10n.memoryPanelRevokeFailed('$e'));
    }
  }

  Future<void> _resolvePendingCommitment(PendingCommitmentItem item) async {
    setState(() => _processingCommitmentIds.add(item.id));
    try {
      final service = ref.read(memoryApiServiceProvider);
      await service.resolvePendingCommitment(item.id);
      if (!mounted) {
        return;
      }
      setState(() {
        _pendingCommitments =
            _pendingCommitments.where((entry) => entry.id != item.id).toList();
        _processingCommitmentIds.remove(item.id);
      });
      AppFeedback.success(context, context.l10n.memoryPanelMarkedComplete);
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _processingCommitmentIds.remove(item.id));
      AppFeedback.error(context, context.l10n.memoryPanelMarkFailed('$e'));
    }
  }

  Future<void> _dismissPendingCommitment(PendingCommitmentItem item) async {
    setState(() => _processingCommitmentIds.add(item.id));
    try {
      final service = ref.read(memoryApiServiceProvider);
      await service.retractMemory(
        type: 'episodic',
        id: item.id,
        reason: 'stage17_dismiss_pending_commitment',
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _pendingCommitments =
            _pendingCommitments.where((entry) => entry.id != item.id).toList();
        _processingCommitmentIds.remove(item.id);
      });
      AppFeedback.success(context, context.l10n.memoryPanelCommitmentDismissed);
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _processingCommitmentIds.remove(item.id));
      AppFeedback.error(context, context.l10n.memoryPanelDismissFailed('$e'));
    }
  }

  Future<void> _selectConflictLeft(UnresolvedConflictItem item) async {
    await _arbitrateConflict(item,
        selection: 'left', successMessage: context.l10n.memoryPanelConflictResolvedA);
  }

  Future<void> _selectConflictRight(UnresolvedConflictItem item) async {
    await _arbitrateConflict(item,
        selection: 'right', successMessage: context.l10n.memoryPanelConflictResolvedB);
  }

  Future<void> _selectConflictNone(UnresolvedConflictItem item) async {
    await _arbitrateConflict(item,
        selection: 'none', successMessage: context.l10n.memoryPanelConflictResolvedNone);
  }

  Future<void> _arbitrateConflict(
    UnresolvedConflictItem item, {
    required String selection,
    required String successMessage,
  }) async {
    setState(() => _processingConflictIds.add(item.id));
    try {
      final service = ref.read(memoryApiServiceProvider);
      await service.arbitrateUnresolvedConflict(
        item.id,
        selection: selection,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _unresolvedConflicts =
            _unresolvedConflicts.where((entry) => entry.id != item.id).toList();
        _processingConflictIds.remove(item.id);
      });
      AppFeedback.success(context, successMessage);
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _processingConflictIds.remove(item.id));
      AppFeedback.error(context, context.l10n.memoryPanelConflictFailed('$e'));
    }
  }

  void _openPersonaAdjust(MemoryPreferenceItem item) {
    final uri = Uri(
      path: UserRoutes.persona,
      queryParameters: {'override': item.prefKey},
    );
    context.push(uri.toString());
  }
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
                          _CorrectionBadge(label: context.l10n.memoryPanelCorrectionCount(correctionCount)),
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
  Widget build(BuildContext context) => Chip(
        label: Text(label, style: TextStyle(color: DS.textPrimary)),
        backgroundColor: DS.semanticWarning.withValues(alpha: 0.12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: BorderSide(color: DS.semanticWarning.withValues(alpha: 0.4)),
        ),
      );
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.selected,
    required this.onSelected,
  });

  final String label;
  final bool selected;
  final ValueChanged<bool> onSelected;

  @override
  Widget build(BuildContext context) => FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: (value) {
          unawaited(
            SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
          );
          onSelected(value);
        },
      );
}

extension on _MemoryPanelScreenState {
  Widget _buildFilterChip({
    required String label,
    required bool selected,
    required ValueChanged<bool> onSelected,
  }) =>
      _FilterChip(label: label, selected: selected, onSelected: onSelected);
}
