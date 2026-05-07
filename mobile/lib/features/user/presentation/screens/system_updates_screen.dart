import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/user/presentation/providers/persona_view_provider.dart';

class SystemUpdatesScreen extends ConsumerStatefulWidget {
  const SystemUpdatesScreen({super.key});

  @override
  ConsumerState<SystemUpdatesScreen> createState() =>
      _SystemUpdatesScreenState();
}

class _SystemUpdatesScreenState extends ConsumerState<SystemUpdatesScreen> {
  static const _allFilter = '__all__';
  final TextEditingController _searchController = TextEditingController();
  String _categoryFilter = _allFilter;
  String _priorityFilter = _allFilter;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final updatesAsync = ref.watch(systemUpdatesProvider);
    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: Text(context.l10n.systemUpdates),
      ),
      child: updatesAsync.when(
        data: (items) => ContentConstraint(child: _buildList(context, items)),
        loading: () => const SparkleListSkeleton(),
        error: (err, stack) => Center(
          child: Text(context.l10n.systemUpdatesLoadFailed('$err')),
        ),
      ),
    );
  }

  Widget _buildList(
    BuildContext context,
    List<Map<String, dynamic>> items,
  ) {
    final categories = _collectOptions(items, 'category');
    final priorities = _collectOptions(items, 'priority');
    final filtered = _applyFilters(items);

    return SparkleRefreshIndicator(
      onRefresh: () async {
        ref.invalidate(systemUpdatesProvider);
        await ref.read(systemUpdatesProvider.future);
      },
      child: ListView(
        padding: const EdgeInsets.all(DS.spacing16),
        children: [
          GraphiteCardSurface(
            surfaceRole: SparkleSurfaceRole.card,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildSearchField(context),
                const SizedBox(height: DS.spacing12),
                _buildFilterRow(
                  title: context.l10n.systemUpdatesTypeFilter,
                  options: categories,
                  selected: _categoryFilter,
                  onSelected: (value) =>
                      setState(() => _categoryFilter = value),
                ),
                const SizedBox(height: DS.spacing12),
                _buildFilterRow(
                  title: context.l10n.systemUpdatesPriorityFilter,
                  options: priorities,
                  selected: _priorityFilter,
                  onSelected: (value) =>
                      setState(() => _priorityFilter = value),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            context.l10n.systemUpdatesCount(filtered.length),
            style: TextStyle(color: DS.neutral600, fontSize: DS.fontSizeSm),
          ),
          const SizedBox(height: DS.spacing12),
          if (filtered.isEmpty)
            Center(
              child: Padding(
                padding: const EdgeInsets.only(top: DS.spacing32),
                child: Text(
                  context.l10n.systemUpdatesNoItems,
                  style: TextStyle(color: DS.neutral500),
                ),
              ),
            )
          else
            ...filtered.asMap().entries.map(
                  (entry) => SparkleStaggerItem(
                    index: entry.key,
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing12),
                      child: _buildUpdateCard(entry.value),
                    ),
                  ),
                ),
        ],
      ),
    );
  }

  Widget _buildSearchField(BuildContext context) => TextField(
        controller: _searchController,
        onChanged: (_) => setState(() {}),
        decoration: InputDecoration(
          prefixIcon: const Icon(Icons.search_rounded),
          hintText: context.l10n.systemUpdatesSearchHint,
          filled: true,
          fillColor: DS.surfaceRoleColor(SparkleSurfaceRole.panel),
          border: OutlineInputBorder(
            borderRadius: DS.borderRadius12,
            borderSide: BorderSide(color: DS.neutral200),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: DS.borderRadius12,
            borderSide: BorderSide(color: DS.neutral200),
          ),
          contentPadding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: 12,
          ),
        ),
      );

  Widget _buildFilterRow({
    required String title,
    required List<String> options,
    required String selected,
    required ValueChanged<String> onSelected,
  }) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              fontWeight: DS.fontWeightSemibold,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: options
                .map(
                  (item) => ChoiceChip(
                    label: Text(
                      item == _allFilter ? context.l10n.systemUpdatesAll : item,
                    ),
                    selected: selected == item,
                    selectedColor: DS.primaryBase.withValues(alpha: 0.15),
                    labelStyle: TextStyle(
                      color: selected == item ? DS.primaryBase : DS.neutral600,
                    ),
                    onSelected: (_) {
                      unawaited(
                        SensoryFeedbackService.emit(
                          SensoryFeedbackEvent.selection,
                        ),
                      );
                      onSelected(item);
                    },
                  ),
                )
                .toList(),
          ),
        ],
      );

  Widget _buildUpdateCard(Map<String, dynamic> item) {
    final title = item['title']?.toString() ?? context.l10n.systemUpdates;
    final description = item['description']?.toString() ?? '';
    final category = item['category']?.toString() ?? '';
    final priority = item['priority']?.toString() ?? '';
    final createdAt = _formatTime(item['created_at']);
    final metadata = (item['metadata'] as Map<dynamic, dynamic>? ??
            const <dynamic, dynamic>{})
        .map<String, dynamic>((key, value) => MapEntry('$key', value));
    final evolutionKind = metadata['evolution_kind']?.toString() ?? '';

    final priorityStyle = _priorityStyle(priority);

    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      padding: const EdgeInsets.all(DS.spacing12),
      borderColor: priorityStyle.border,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontWeight: DS.fontWeightSemibold,
                    color: DS.textPrimary,
                  ),
                ),
              ),
              if (priority.isNotEmpty)
                _pill(priority, priorityStyle.bg, priorityStyle.fg),
            ],
          ),
          if (createdAt.isNotEmpty)
            Text(
              createdAt,
              style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
            ),
          if (description.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              description,
              style: TextStyle(color: DS.textSecondary),
            ),
          ],
          ..._buildStructuredDetails(metadata, evolutionKind),
          if (category.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            _pill(category, DS.neutral100, DS.neutral600),
          ],
        ],
      ),
    );
  }

  List<Widget> _buildStructuredDetails(
    Map<String, dynamic> metadata,
    String evolutionKind,
  ) {
    if (evolutionKind == 'proactive_insight') {
      final insightText = metadata['insight_text']?.toString() ?? '';
      final evidenceSummary = metadata['evidence_summary']?.toString() ?? '';
      final confidence = metadata['confidence'];
      return [
        if (insightText.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            insightText,
            style: TextStyle(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ],
        if (evidenceSummary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            evidenceSummary,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ],
        if (confidence != null) ...[
          const SizedBox(height: DS.spacing8),
          _pill(
            context.l10n.systemUpdatesConfidence(
              ((confidence as num).toDouble() * 100).toInt(),
            ),
            DS.info.withValues(alpha: 0.12),
            DS.info,
          ),
        ],
      ];
    }
    if (evolutionKind == 'weekly_learning_report') {
      final learnings = (metadata['top_learnings'] as List<dynamic>? ?? [])
          .map((e) => '$e')
          .where((e) => e.isNotEmpty)
          .toList();
      final oneKeyAdjustment = metadata['one_key_adjustment']?.toString() ?? '';
      final comparisonHighlight =
          metadata['comparison_highlight']?.toString() ?? '';
      final periodRange = metadata['period_range']?.toString() ?? '';
      final evidenceSummary = metadata['evidence_summary']?.toString() ?? '';
      return [
        if (learnings.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          ...learnings.map(
            (item) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 5,
                    height: 5,
                    margin: const EdgeInsets.only(top: 8, right: 8),
                    decoration: BoxDecoration(
                      color: DS.textPrimary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  Expanded(
                    child: Text(item, style: TextStyle(color: DS.textPrimary)),
                  ),
                ],
              ),
            ),
          ),
        ],
        if (oneKeyAdjustment.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            context.l10n.systemUpdatesNextWeekAdjust(oneKeyAdjustment),
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ],
        if (evidenceSummary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            evidenceSummary,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ],
        if (comparisonHighlight.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            comparisonHighlight,
            style: TextStyle(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ],
        if (periodRange.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            periodRange,
            style: TextStyle(color: DS.neutral500, fontSize: DS.fontSizeSm),
          ),
        ],
      ];
    }
    if (evolutionKind == 'progress_comparison') {
      final comparison = (metadata['comparison'] as Map<dynamic, dynamic>? ??
              const <dynamic, dynamic>{})
          .map<String, dynamic>((key, value) => MapEntry('$key', value));
      final evidenceSummary = metadata['evidence_summary']?.toString() ?? '';
      if (comparison.isEmpty) {
        return const <Widget>[];
      }
      return [
        const SizedBox(height: DS.spacing8),
        Text(
          comparison['delta_text']?.toString() ?? '',
          style: TextStyle(
            color: DS.textPrimary,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
        const SizedBox(height: DS.spacing8),
        Text(
          '${comparison['before_label'] ?? context.l10n.systemUpdatesBeforeLabel}：${comparison['before_value'] ?? '-'}',
          style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
        ),
        const SizedBox(height: DS.spacing4),
        Text(
          '${comparison['after_label'] ?? context.l10n.systemUpdatesAfterLabel}：${comparison['after_value'] ?? '-'}',
          style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
        ),
        if ((comparison['why_it_matters']?.toString() ?? '').isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            comparison['why_it_matters'].toString(),
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ],
        if (evidenceSummary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            evidenceSummary,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ],
      ];
    }
    if (evolutionKind == 'plan_reasoning') {
      final reasoningSummary = metadata['reasoning_summary']?.toString() ?? '';
      final alignmentSummary = metadata['alignment_summary']?.toString() ?? '';
      final alignmentScore = (metadata['alignment_score'] as num?)?.toDouble();
      final reasoningDetails =
          (metadata['reasoning_details'] as List<dynamic>? ?? [])
              .whereType<Map<dynamic, dynamic>>()
              .map(Map<String, dynamic>.from)
              .toList();
      final evidenceSummary = metadata['evidence_summary']?.toString() ?? '';
      return [
        if (reasoningSummary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            reasoningSummary,
            style: TextStyle(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ],
        if (alignmentSummary.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            alignmentSummary,
            style: TextStyle(color: DS.info, fontSize: DS.fontSizeSm),
          ),
        ],
        if (alignmentScore != null) ...[
          const SizedBox(height: DS.spacing4),
          Text(
            context.l10n.systemUpdatesAlignmentScore(
              (alignmentScore * 100).toStringAsFixed(0),
            ),
            style: TextStyle(
              color: DS.info,
              fontSize: DS.fontSizeXs,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
        ],
        if (reasoningDetails.isNotEmpty) ...[
          const SizedBox(height: DS.spacing8),
          ...reasoningDetails.map(
            (detail) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 5,
                    height: 5,
                    margin: const EdgeInsets.only(top: 7, right: 8),
                    decoration: BoxDecoration(
                      color: DS.textSecondary,
                      shape: BoxShape.circle,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      '${detail['label'] ?? ''}：${detail['evidence'] ?? ''}',
                      style: TextStyle(
                        color: DS.textSecondary,
                        fontSize: DS.fontSizeSm,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
        if (evidenceSummary.isNotEmpty && reasoningDetails.isEmpty) ...[
          const SizedBox(height: DS.spacing8),
          Text(
            evidenceSummary,
            style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeSm),
          ),
        ],
      ];
    }
    return const <Widget>[];
  }

  List<String> _collectOptions(List<Map<String, dynamic>> items, String key) {
    final values = <String>{_allFilter};
    for (final item in items) {
      final value = item[key]?.toString();
      if (value != null && value.isNotEmpty) {
        values.add(value);
      }
    }
    final sorted = values.toList()..sort();
    if (sorted.first != _allFilter && sorted.contains(_allFilter)) {
      sorted
        ..remove(_allFilter)
        ..insert(0, _allFilter);
    }
    return sorted;
  }

  List<Map<String, dynamic>> _applyFilters(List<Map<String, dynamic>> items) {
    final keyword = _searchController.text.trim().toLowerCase();
    return items.where((item) {
      final title = item['title']?.toString().toLowerCase() ?? '';
      final description = item['description']?.toString().toLowerCase() ?? '';
      final category = item['category']?.toString() ?? '';
      final priority = item['priority']?.toString() ?? '';

      if (_categoryFilter != _allFilter && category != _categoryFilter) {
        return false;
      }
      if (_priorityFilter != _allFilter && priority != _priorityFilter) {
        return false;
      }
      if (keyword.isNotEmpty &&
          !title.contains(keyword) &&
          !description.contains(keyword) &&
          !category.toLowerCase().contains(keyword)) {
        return false;
      }
      return true;
    }).toList();
  }

  _PriorityStyle _priorityStyle(String value) {
    switch (value.toLowerCase()) {
      case 'high':
        return _PriorityStyle(
          bg: DS.warning.withValues(alpha: 0.12),
          fg: DS.warning,
          border: DS.warning.withValues(alpha: 0.3),
        );
      case 'medium':
        return _PriorityStyle(
          bg: DS.info.withValues(alpha: 0.12),
          fg: DS.info,
          border: DS.info.withValues(alpha: 0.3),
        );
      case 'low':
      default:
        return _PriorityStyle(
          bg: DS.neutral100,
          fg: DS.neutral600,
          border: DS.neutral200,
        );
    }
  }

  Widget _pill(String text, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: DS.borderRadius20,
          border: Border.all(color: DS.neutral200),
        ),
        child: Text(
          text,
          style: TextStyle(color: fg, fontSize: DS.fontSizeSm),
        ),
      );

  String _formatTime(dynamic raw) {
    if (raw is int && raw > 0) {
      final dt = DateTime.fromMillisecondsSinceEpoch(raw * 1000);
      return Formatters.formatDateTime(dt);
    }
    return '';
  }
}

class _PriorityStyle {
  const _PriorityStyle({
    required this.bg,
    required this.fg,
    required this.border,
  });
  final Color bg;
  final Color fg;
  final Color border;
}
