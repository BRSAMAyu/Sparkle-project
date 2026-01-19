import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/presentation/screens/memory_detail_screen.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';

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
  MemoryEntryType? _filterType;
  MemoryEvidenceStatus? _filterEvidence;
  DateTimeRange? _dateRange;
  MemorySort _sort = MemorySort.newest;
  MemoryViewMode _viewMode = MemoryViewMode.compact;
  final Set<String> _pinnedIds = {};

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
        service.getGoals(limit: 20),
        service.getEpisodic(limit: 20),
      ]);
      if (!mounted) {
        return;
      }
      setState(() {
        _preferences = results[0] as List<MemoryPreferenceItem>;
        _goals = results[1] as List<MemoryGoalItem>;
        _episodic = results[2] as List<EpisodicMemoryItem>;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = '记忆面板加载失败: $e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: DS.deepSpaceStart,
        appBar: AppBar(
          title: Text('记忆面板', style: TextStyle(color: DS.brandPrimary)),
          iconTheme: IconThemeData(color: DS.brandPrimary),
          backgroundColor: Colors.transparent,
          elevation: 0,
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: _loadAll,
            ),
          ],
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _buildError(context)
                : AppFeatureFlags.enableMemoryPanelV2
                    ? _buildV2Panel(context)
                    : _buildV1Panel(context),
      );

  Widget _buildError(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _error ?? '记忆面板不可用',
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.md),
              SparkleButton.primary(
                label: '重试',
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
            _SectionHeader(title: '偏好'),
            const SizedBox(height: DS.sm),
            ..._preferences.map(_buildPreferenceCard),
            const SizedBox(height: DS.xl),
            _SectionHeader(title: '目标'),
            const SizedBox(height: DS.sm),
            ..._goals.map(_buildGoalCard),
            const SizedBox(height: DS.xl),
            _SectionHeader(title: '经历'),
            const SizedBox(height: DS.sm),
            ..._episodic.map(_buildEpisodicCard),
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
          _buildFilterBar(context),
          const SizedBox(height: DS.md),
          if (entries.isEmpty)
            _buildEmptyState()
          else
            ...entries.map((entry) => _buildEntryCard(entry)),
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
                label: '全部',
                selected: _filterType == null,
                onSelected: (_) => _setTypeFilter(null),
              ),
              _buildFilterChip(
                label: '偏好',
                selected: _filterType == MemoryEntryType.preference,
                onSelected: (_) => _setTypeFilter(MemoryEntryType.preference),
              ),
              _buildFilterChip(
                label: '目标',
                selected: _filterType == MemoryEntryType.goal,
                onSelected: (_) => _setTypeFilter(MemoryEntryType.goal),
              ),
              _buildFilterChip(
                label: '经历',
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
                label: '证据全部',
                selected: _filterEvidence == null,
                onSelected: (_) => _setEvidenceFilter(null),
              ),
              _buildFilterChip(
                label: 'OK',
                selected: _filterEvidence == MemoryEvidenceStatus.ok,
                onSelected: (_) => _setEvidenceFilter(MemoryEvidenceStatus.ok),
              ),
              _buildFilterChip(
                label: '缺失',
                selected: _filterEvidence == MemoryEvidenceStatus.missing,
                onSelected: (_) =>
                    _setEvidenceFilter(MemoryEvidenceStatus.missing),
              ),
              _buildFilterChip(
                label: '已隐藏',
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
                items: const [
                  DropdownMenuItem(
                    value: MemorySort.newest,
                    child: Text('最新'),
                  ),
                  DropdownMenuItem(
                    value: MemorySort.oldest,
                    child: Text('最旧'),
                  ),
                  DropdownMenuItem(
                    value: MemorySort.importance,
                    child: Text('重要度'),
                  ),
                  DropdownMenuItem(
                    value: MemorySort.confidence,
                    child: Text('置信度'),
                  ),
                ],
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: _pickDateRange,
                icon: const Icon(Icons.date_range),
                label: Text(
                  _dateRange == null
                      ? '日期'
                      : '${_dateRange!.start.month}/${_dateRange!.start.day}'
                          ' - ${_dateRange!.end.month}/${_dateRange!.end.day}',
                ),
              ),
              const SizedBox(width: DS.sm),
              IconButton(
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
              ),
            ],
          ),
        ],
      );

  Widget _buildEmptyState() => Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.xl),
        child: Center(
          child: Text(
            '暂无符合条件的记忆',
            style: TextStyle(color: DS.textSecondary),
          ),
        ),
      );

  Widget _buildPreferenceCard(MemoryPreferenceItem item) => _MemoryCard(
        title: item.prefKey,
        subtitle: _formatUpdated(item.updatedAt),
        badge: MemoryEvidenceBadge(status: _statusFor(item.evidenceMissing, item.evidenceRefs)),
        correctionCount: item.correctionCount,
        onTap: () => _openDetail(
          context,
          MemoryDetailArgs.preference(item),
        ),
      );

  Widget _buildGoalCard(MemoryGoalItem item) => _MemoryCard(
        title: item.title,
        subtitle: item.status,
        badge: MemoryEvidenceBadge(status: _statusFor(item.evidenceMissing, item.evidenceRefs)),
        correctionCount: item.correctionCount,
        onTap: () => _openDetail(
          context,
          MemoryDetailArgs.goal(item),
        ),
      );

  Widget _buildEpisodicCard(EpisodicMemoryItem item) => _MemoryCard(
        title: item.summary,
        subtitle: _formatUpdated(item.occurredAt),
        badge: MemoryEvidenceBadge(status: _statusFor(item.evidenceMissing, item.evidenceRefs)),
        correctionCount: item.correctionCount,
        onTap: () => _openDetail(
          context,
          MemoryDetailArgs.episodic(item),
        ),
      );

  Widget _buildEntryCard(MemoryEntry entry) {
    final isPinned = _pinnedIds.contains(entry.id);
    final subtitle = [
      _entryTypeLabel(entry.type),
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
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            MemoryEvidenceBadge(status: entry.evidenceStatus),
            if (entry.correctionCount > 0) ...[
              const SizedBox(height: 6),
              _CorrectionBadge(count: entry.correctionCount),
            ],
            const SizedBox(height: 6),
            IconButton(
              icon: Icon(isPinned ? Icons.push_pin : Icons.push_pin_outlined),
              onPressed: () => setState(() {
                if (isPinned) {
                  _pinnedIds.remove(entry.id);
                } else {
                  _pinnedIds.add(entry.id);
                }
              }),
            ),
          ],
        ),
        onTap: () => _openDetail(context, entry.detailArgs),
      ),
    );
  }

  void _openDetail(BuildContext context, MemoryDetailArgs args) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => MemoryDetailScreen(args: args),
      ),
    );
  }

  String _formatUpdated(DateTime? value) {
    if (value == null) {
      return '未更新';
    }
    return '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
  }

  String _entryTypeLabel(MemoryEntryType type) => switch (type) {
        MemoryEntryType.preference => '偏好',
        MemoryEntryType.goal => '目标',
        MemoryEntryType.episodic => '经历',
      };

  String _formatMetrics(MemoryEntry entry) {
    final importance = entry.importance;
    final confidence = entry.confidence;
    final parts = <String>[];
    if (importance != null) {
      parts.add('重要度 ${importance.toStringAsFixed(2)}');
    }
    if (confidence != null) {
      parts.add('置信度 ${confidence.toStringAsFixed(2)}');
    }
    return parts.isEmpty ? '指标: -' : parts.join(' · ');
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

  List<MemoryEntry> _applyFilters(List<MemoryEntry> entries) {
    return entries.where((entry) {
      if (_filterType != null && entry.type != _filterType) {
        return false;
      }
      if (_filterEvidence != null && entry.evidenceStatus != _filterEvidence) {
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
  }

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
        default:
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
  });

  final String title;
  final String subtitle;
  final Widget badge;
  final int correctionCount;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
        margin: const EdgeInsets.only(bottom: DS.md),
        child: ListTile(
          title: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(subtitle),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              badge,
              if (correctionCount > 0) ...[
                const SizedBox(height: 6),
                _CorrectionBadge(count: correctionCount),
              ],
            ],
          ),
          onTap: onTap,
        ),
      );
}

class _CorrectionBadge extends StatelessWidget {
  const _CorrectionBadge({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) => Chip(
        label: Text('纠错 $count', style: TextStyle(color: DS.semanticWarning)),
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
        onSelected: onSelected,
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
