import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_drawer.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';

enum MemoryDetailType { preference, goal, episodic }

class MemoryDetailArgs {
  factory MemoryDetailArgs.preference(MemoryPreferenceItem item) =>
      MemoryDetailArgs._(
        MemoryDetailType.preference,
        item.prefKey,
        item.evidenceMissing,
        item.evidenceRefs,
        prefKey: item.prefKey,
        preference: item,
      );

  factory MemoryDetailArgs.preferenceKey(String prefKey) => MemoryDetailArgs._(
        MemoryDetailType.preference,
        prefKey,
        false,
        const <EvidenceRefModel>[],
        prefKey: prefKey,
      );

  factory MemoryDetailArgs.goal(MemoryGoalItem item) => MemoryDetailArgs._(
        MemoryDetailType.goal,
        item.title,
        item.evidenceMissing,
        item.evidenceRefs,
        goal: item,
      );

  factory MemoryDetailArgs.episodic(EpisodicMemoryItem item) =>
      MemoryDetailArgs._(
        MemoryDetailType.episodic,
        item.summary,
        item.evidenceMissing,
        item.evidenceRefs,
        episodic: item,
      );
  MemoryDetailArgs._(
    this.type,
    this.title,
    this.evidenceMissing,
    this.refs, {
    this.prefKey,
    this.preference,
    this.goal,
    this.episodic,
  });

  final MemoryDetailType type;
  final String title;
  final bool evidenceMissing;
  final List<EvidenceRefModel> refs;
  final String? prefKey;
  final MemoryPreferenceItem? preference;
  final MemoryGoalItem? goal;
  final EpisodicMemoryItem? episodic;
}

class MemoryDetailScreen extends ConsumerStatefulWidget {
  const MemoryDetailScreen({required this.args, super.key});

  final MemoryDetailArgs args;

  @override
  ConsumerState<MemoryDetailScreen> createState() => _MemoryDetailScreenState();
}

class _MemoryDetailScreenState extends ConsumerState<MemoryDetailScreen> {
  bool _loadingHistory = false;
  List<MemoryPreferenceHistoryItem> _history = [];
  String? _historyError;
  late List<EvidenceRefModel> _refs;
  late bool _evidenceMissing;
  MemoryPreferenceItem? _preference;
  MemoryGoalItem? _goal;
  EpisodicMemoryItem? _episodic;
  double? _confidence;
  int _correctionCount = 0;
  double? _evidenceScore;
  DateTime? _retractedAt;
  MemorySettingsModel? _memorySettings;
  String? _settingsError;

  @override
  void initState() {
    super.initState();
    _refs = List<EvidenceRefModel>.from(widget.args.refs);
    _evidenceMissing = widget.args.evidenceMissing;
    _preference = widget.args.preference;
    _goal = widget.args.goal;
    _episodic = widget.args.episodic;
    _confidence = widget.args.preference?.confidence;
    _correctionCount = widget.args.preference?.correctionCount ??
        widget.args.goal?.correctionCount ??
        widget.args.episodic?.correctionCount ??
        0;
    _evidenceScore = widget.args.preference?.evidenceScore ??
        widget.args.goal?.evidenceScore ??
        widget.args.episodic?.evidenceScore;
    _retractedAt = widget.args.preference?.retractedAt ??
        widget.args.goal?.retractedAt ??
        widget.args.episodic?.retractedAt;
    if (widget.args.type == MemoryDetailType.preference) {
      _loadHistory();
    }
    if (AppFeatureFlags.enableMemoryExplain &&
        AppFeatureFlags.enableUserMemoryControls) {
      _loadSettings();
    }
  }

  Future<void> _loadHistory() async {
    final prefKey = widget.args.prefKey;
    if (prefKey == null) {
      return;
    }
    setState(() {
      _loadingHistory = true;
      _historyError = null;
    });
    try {
      final service = ref.read(memoryApiServiceProvider);
      final items = await service.getPreferenceHistory(prefKey);
      if (!mounted) {
        return;
      }
      setState(() {
        _history = items;
        if (_preference == null && items.isNotEmpty) {
          _preference = _preferenceFromHistory(items.first);
          _confidence = _preference?.confidence;
          _correctionCount = _preference?.correctionCount ?? _correctionCount;
          _evidenceScore = _preference?.evidenceScore ?? _evidenceScore;
          _retractedAt = _preference?.retractedAt ?? _retractedAt;
          _refs = List<EvidenceRefModel>.from(items.first.evidenceRefs);
          _evidenceMissing = items.first.evidenceMissing;
        }
        _loadingHistory = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _historyError = '${context.l10n.memoryHistoryLoadFailed}: $e';
        _loadingHistory = false;
      });
    }
  }

  Future<void> _loadSettings() async {
    setState(() {
      _settingsError = null;
    });
    try {
      final service = ref.read(memoryApiServiceProvider);
      final settings = await service.getMemorySettings();
      if (!mounted) {
        return;
      }
      setState(() {
        _memorySettings = settings;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _settingsError = '${context.l10n.memorySettingsLoadFailed}: $e';
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
            widget.args.title,
            style: DS.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          iconTheme: IconThemeData(color: DS.textPrimary),
          backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
          elevation: 0,
          actions: [
            if (AppFeatureFlags.enableMemoryPanelV2)
              SparkleIconButton(
                icon: const Icon(Icons.copy),
                onPressed: _copyDetail,
                variant: ButtonVariant.ghost,
              ),
            if (AppFeatureFlags.enableMemoryPanelV2)
              SparkleIconButton(
                icon: const Icon(Icons.file_download),
                onPressed: _showExportDialog,
                variant: ButtonVariant.ghost,
              ),
            if (AppFeatureFlags.enableEvidenceViewer)
              SparkleIconButton(
                icon: const Icon(Icons.link),
                onPressed: () => _showEvidence(context),
                variant: ButtonVariant.ghost,
              ),
          ],
        ),
        child: ContentConstraint(
          child: Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: _buildBody(context),
          ),
        ),
      );

  Widget _buildBody(BuildContext context) {
    switch (widget.args.type) {
      case MemoryDetailType.preference:
        return _buildPreferenceDetail(context);
      case MemoryDetailType.goal:
        return _buildGoalDetail(context);
      case MemoryDetailType.episodic:
        return _buildEpisodicDetail(context);
    }
  }

  Widget _buildPreferenceDetail(BuildContext context) => SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                MemoryEvidenceBadge(status: _evidenceStatus),
                const SizedBox(width: DS.sm),
                Text(context.l10n.memoryCurrentVersion, style: Theme.of(context).textTheme.bodyMedium),
              ],
            ),
            const SizedBox(height: DS.md),
            _buildKeyValue('Key', widget.args.prefKey ?? '-'),
            _buildKeyValue(
              'Value',
              _preference?.prefValue.toString() ?? '-',
            ),
            _buildKeyValue(
              'Confidence',
              _confidence?.toStringAsFixed(2) ?? '-',
            ),
            _buildKeyValue(
              'Evidence',
              _evidenceScore?.toStringAsFixed(2) ?? '-',
            ),
            _buildKeyValue('Corrections', _correctionCount.toString()),
            _buildKeyValue(
              'Updated',
              _formatDate(_preference?.updatedAt),
            ),
            _buildKeyValue(
              'Retracted',
              _formatDate(_retractedAt),
            ),
            if (AppFeatureFlags.enableMemoryCorrection) ...[
              const SizedBox(height: DS.md),
              _buildCorrectionActions(context),
            ],
            if (AppFeatureFlags.enableMemoryExplain) ...[
              const SizedBox(height: DS.lg),
              _buildWhyMemorySection(),
            ],
            const SizedBox(height: DS.lg),
            Text(context.l10n.memoryVersionHistory, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: DS.sm),
            if (_loadingHistory)
              const Center(child: CircularProgressIndicator())
            else if (_historyError != null)
              Text(_historyError!,
                  style: Theme.of(context).textTheme.bodyMedium,)
            else if (AppFeatureFlags.enableMemoryPanelV2)
              ...List.generate(_history.length, (index) => _buildTimelineCard(context, index))
            else
              ...List.generate(_history.length, (index) => _buildHistoryTile(context, _history[index])),
          ],
        ),
      );

  Widget _buildGoalDetail(BuildContext context) {
    final goal = _goal;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MemoryEvidenceBadge(status: _evidenceStatus),
        const SizedBox(height: DS.md),
        _buildKeyValue('状态', goal?.status ?? '-'),
        _buildKeyValue('目标日期', _formatDate(goal?.targetDate)),
        _buildKeyValue('截止时间', _formatDate(goal?.expiresAt)),
        _buildKeyValue('最后更新', _formatDate(goal?.updatedAt)),
        _buildKeyValue('Evidence', _evidenceScore?.toStringAsFixed(2) ?? '-'),
        _buildKeyValue('Corrections', _correctionCount.toString()),
        _buildKeyValue('撤回时间', _formatDate(_retractedAt)),
        if (AppFeatureFlags.enableMemoryCorrection) ...[
          const SizedBox(height: DS.md),
          _buildCorrectionActions(context),
        ],
        if (AppFeatureFlags.enableMemoryExplain &&
            widget.args.type != MemoryDetailType.goal) ...[
          const SizedBox(height: DS.lg),
          _buildWhyMemorySection(),
        ],
      ],
    );
  }

  Widget _buildEpisodicDetail(BuildContext context) {
    final episodic = _episodic;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        MemoryEvidenceBadge(status: _evidenceStatus),
        const SizedBox(height: DS.md),
        _buildKeyValue('来源', episodic?.sourceType ?? '-'),
        if ((episodic?.declarationLabel ?? '').isNotEmpty)
          _buildKeyValue('声明', episodic?.declarationLabel ?? '-'),
        _buildKeyValue('发生时间', _formatDate(episodic?.occurredAt)),
        _buildKeyValue(
            '重要度', episodic?.importanceScore?.toStringAsFixed(2) ?? '-',),
        _buildKeyValue('置信度', episodic?.confidence?.toStringAsFixed(2) ?? '-'),
        _buildKeyValue('证据 Token', episodic?.evidenceToken ?? '-'),
        _buildKeyValue('衰减策略', episodic?.decayPolicy ?? '-'),
        _buildKeyValue('Evidence', _evidenceScore?.toStringAsFixed(2) ?? '-'),
        _buildKeyValue('Corrections', _correctionCount.toString()),
        _buildKeyValue('最后更新', _formatDate(episodic?.updatedAt)),
        _buildKeyValue('撤回时间', _formatDate(_retractedAt)),
        if (AppFeatureFlags.enableMemoryCorrection) ...[
          const SizedBox(height: DS.md),
          _buildCorrectionActions(context),
        ],
        if (AppFeatureFlags.enableMemoryExplain &&
            widget.args.type != MemoryDetailType.goal) ...[
          const SizedBox(height: DS.lg),
          _buildWhyMemorySection(),
        ],
      ],
    );
  }

  Widget _buildKeyValue(String label, String value) => Padding(
        padding: const EdgeInsets.only(bottom: DS.sm),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 90,
              child: Text(label, style: Theme.of(context).textTheme.bodySmall),
            ),
            Expanded(child: Text(value)),
          ],
        ),
      );

  Widget _buildHistoryTile(
    BuildContext context,
    MemoryPreferenceHistoryItem item,
  ) =>
      Card(
        margin: const EdgeInsets.only(bottom: DS.sm),
        child: ListTile(
          title: Text('v${item.version}'),
          subtitle: Text(_formatDate(item.updatedAt)),
          trailing: MemoryEvidenceBadge(
            status: _statusFor(item.evidenceMissing, item.evidenceRefs),
          ),
          onTap: () => EvidenceDrawer.show(
            context,
            refs: item.evidenceRefs,
            evidenceMissing: item.evidenceMissing,
          ),
        ),
      );

  void _showEvidence(BuildContext context) {
    unawaited(
      SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen),
    );
    EvidenceDrawer.show(
      context,
      refs: _refs,
      evidenceMissing: _evidenceMissing,
    );
  }

  String _formatDate(DateTime? value) {
    if (value == null) {
      return '-';
    }
    return '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
  }

  MemoryEvidenceStatus get _evidenceStatus =>
      _statusFor(_evidenceMissing, _refs);

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

  Widget _buildTimelineCard(BuildContext context, int index) {
    final item = _history[index];
    final previous = index + 1 < _history.length ? _history[index + 1] : null;
    final diff = _diffPreference(item.prefValue, previous?.prefValue);
    return Card(
      margin: const EdgeInsets.only(bottom: DS.md),
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  'v${item.version}',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const Spacer(),
                MemoryEvidenceBadge(
                  status: _statusFor(item.evidenceMissing, item.evidenceRefs),
                ),
              ],
            ),
            const SizedBox(height: DS.sm),
            Text('更新: ${_formatDate(item.updatedAt)}'),
            Text('置信度: ${item.confidence?.toStringAsFixed(2) ?? '-'}'),
            if (diff.isNotEmpty) ...[
              const SizedBox(height: DS.sm),
              Text('Diff', style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 4),
              Text(diff, style: Theme.of(context).textTheme.bodySmall),
            ],
            const SizedBox(height: DS.sm),
            Row(
              children: [
                Tooltip(
                  message: AppFeatureFlags.enableMemoryRetraction
                      ? '撤回到此版本'
                      : '需要开启 ENABLE_MEMORY_RETRACTION',
                  child: SparkleButton(
                    label: 'Revert',
                    onPressed: () => _showRevertInfo(context),
                    variant: ButtonVariant.outline,
                    disabled: !AppFeatureFlags.enableMemoryRetraction,
                  ),
                ),
                const Spacer(),
                SparkleIconButton(
                  icon: const Icon(Icons.link),
                  onPressed: AppFeatureFlags.enableEvidenceViewer
                      ? () => EvidenceDrawer.show(
                            context,
                            refs: item.evidenceRefs,
                            evidenceMissing: item.evidenceMissing,
                          )
                      : null,
                  variant: ButtonVariant.ghost,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _diffPreference(dynamic current, dynamic previous) {
    if (previous == null) {
      return '初始版本';
    }
    final currentMap = _normalizeMap(current);
    final previousMap = _normalizeMap(previous);
    if (currentMap == null || previousMap == null) {
      return current.toString();
    }
    final changes = <String>[];
    for (final entry in currentMap.entries) {
      final oldValue = previousMap[entry.key];
      if (oldValue != entry.value) {
        changes.add('${entry.key}: $oldValue -> ${entry.value}');
      }
    }
    if (changes.isEmpty) {
      return '无变化';
    }
    return changes.join('\n');
  }

  Map<String, dynamic>? _normalizeMap(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return value.map((key, value) => MapEntry('$key', value));
    }
    return null;
  }

  void _showRevertInfo(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Revert 功能尚未启用')),
    );
  }

  MemoryPreferenceItem _preferenceFromHistory(
    MemoryPreferenceHistoryItem item,
  ) =>
      MemoryPreferenceItem(
        id: item.id,
        prefKey: item.prefKey,
        prefValue: item.prefValue,
        version: item.version,
        confidence: item.confidence,
        updatedAt: item.updatedAt,
        evidenceMissing: item.evidenceMissing,
        evidenceRefs: item.evidenceRefs,
        evidenceScore: item.evidenceScore,
        correctionCount: item.correctionCount,
        retractedAt: item.retractedAt,
      );

  Widget _buildWhyMemorySection() {
    final budget = _preference?.prefValue is Map
        ? (_preference?.prefValue as Map)['context_pack']
        : null;
    final evidenceCount = _refs.length;
    final versions = _history.length;
    final settingsSummary = _buildSettingsSummary();
    final settingsHint = _buildSettingsHint();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(DS.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Why this memory?',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: DS.sm),
            Text(_explanationText()),
            if (settingsSummary != null) ...[
              const SizedBox(height: DS.sm),
              Text(settingsSummary),
            ],
            if (_settingsError != null) ...[
              const SizedBox(height: DS.sm),
              Text(
                _settingsError!,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            if (settingsHint != null) ...[
              const SizedBox(height: DS.sm),
              Text(
                settingsHint,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: DS.sm),
            Text('Evidence: $evidenceCount'),
            if (widget.args.type == MemoryDetailType.preference)
              Text('Versions: $versions'),
            Text('Budget: ${budget ?? 'N/A'}'),
            if (AppFeatureFlags.enableEvidenceViewer)
              Align(
                alignment: Alignment.centerLeft,
                child: SparkleButton.ghost(
                  label: '查看证据',
                  onPressed: () => _showEvidence(context),
                ),
              ),
          ],
        ),
      ),
    );
  }

  String? _buildSettingsSummary() {
    if (_memorySettings == null ||
        !AppFeatureFlags.enableUserMemoryControls ||
        !AppFeatureFlags.enableMemoryExplain) {
      return null;
    }
    final allowed = <String>[];
    if (_memorySettings!.allowPreferences) {
      allowed.add('偏好');
    }
    if (_memorySettings!.allowGoals) {
      allowed.add('目标');
    }
    if (_memorySettings!.allowEpisodic) {
      allowed.add('经历');
    }
    final typesLabel = allowed.isEmpty ? '无' : allowed.join(' / ');
    return '已允许捕获：$typesLabel\n捕获级别：${_memorySettings!.captureLevel}';
  }

  String? _buildSettingsHint() {
    if (_memorySettings == null ||
        !AppFeatureFlags.enableUserMemoryControls ||
        !AppFeatureFlags.enableMemoryExplain) {
      return null;
    }
    final settings = _memorySettings!;
    if (!settings.enabled) {
      return '当前已关闭长期记忆，后续不会记录此类记忆。';
    }
    if (widget.args.type == MemoryDetailType.preference) {
      if (!settings.allowPreferences) {
        return '当前设置已关闭偏好捕获，后续不会记录此类记忆。';
      }
      final prefKey = widget.args.prefKey;
      if (prefKey != null && settings.blockedPrefKeys.contains(prefKey)) {
        return '该偏好已被屏蔽，后续不会记录此类记忆。';
      }
    }
    if (widget.args.type == MemoryDetailType.goal) {
      if (!settings.allowGoals) {
        return '当前设置已关闭目标捕获，后续不会记录此类记忆。';
      }
    }
    if (widget.args.type == MemoryDetailType.episodic) {
      if (!settings.allowEpisodic) {
        return '当前设置已关闭经历捕获，后续不会记录此类记忆。';
      }
      if (!_memorySettings!.allowInferredEpisodic &&
          (_episodic?.sourceLane == 'inferred_extraction')) {
        return '当前已关闭 AI 自动记忆，后续不会继续写入此类推断。';
      }
      final sourceType = _episodic?.sourceType;
      if (sourceType != null && settings.blockedSources.contains(sourceType)) {
        return '该来源已被屏蔽，后续不会记录此类记忆。';
      }
    }
    return null;
  }

  String _explanationText() {
    switch (widget.args.type) {
      case MemoryDetailType.preference:
        return 'Captured because your preference updated recently.';
      case MemoryDetailType.episodic:
        if ((_episodic?.sourceLane ?? '') == 'inferred_extraction') {
          return '这条经历由 AI 从聊天中推断，并保留了证据 token、置信度与撤销路径。';
        }
        return 'Captured because this experience was marked important.';
      case MemoryDetailType.goal:
        return 'Captured to keep your active goals visible.';
    }
  }

  Future<void> _copyDetail() async {
    final payload = switch (widget.args.type) {
      MemoryDetailType.preference => _preference?.prefValue,
      MemoryDetailType.goal => _goal,
      MemoryDetailType.episodic => _episodic,
    };
    if (payload == null) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: payload.toString()));
    if (!mounted) {
      return;
    }
    AppFeedback.info(context, '已复制记忆内容');
  }

  void _showExportDialog() {
    final payload = switch (widget.args.type) {
      MemoryDetailType.preference => _preference,
      MemoryDetailType.goal => _goal,
      MemoryDetailType.episodic => _episodic,
    };
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('导出视图'),
        content: SingleChildScrollView(
          child: SelectableText(payload.toString()),
        ),
        actions: [
          SparkleButton.ghost(
            label: '关闭',
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }

  Widget _buildCorrectionActions(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('纠错操作', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: DS.sm),
          Wrap(
            spacing: DS.sm,
            runSpacing: DS.sm,
            children: [
              _buildCorrectionButton('Not true', 'reject'),
              _buildCorrectionButton(
                  'No longer applies', 'no_longer_applicable',),
              _buildCorrectionButton('Lower confidence', 'lower_confidence'),
              _buildCorrectionButton('Merge', 'merge'),
            ],
          ),
        ],
      );

  Widget _buildCorrectionButton(String label, String action) => SparkleButton(
        label: label,
        onPressed: () => _submitCorrection(action),
        variant: ButtonVariant.outline,
      );

  Future<void> _submitCorrection(String action) async {
    try {
      if (action == 'merge') {
        if (!mounted) {
          return;
        }
        AppFeedback.info(context, '合并功能即将上线');
        return;
      }
      final service = ref.read(memoryApiServiceProvider);
      final id = switch (widget.args.type) {
        MemoryDetailType.preference => _preference?.id,
        MemoryDetailType.goal => _goal?.id,
        MemoryDetailType.episodic => _episodic?.id,
      };
      if (id == null) {
        return;
      }
      final type = switch (widget.args.type) {
        MemoryDetailType.preference => 'preference',
        MemoryDetailType.goal => 'goal',
        MemoryDetailType.episodic => 'episodic',
      };
      final result = await service.correctMemory(
        type: type,
        id: id,
        action: action,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _refs = result.evidenceRefs;
        _evidenceMissing = result.evidenceMissing;
        _evidenceScore = result.evidenceScore;
        _correctionCount = result.correctionCount;
        _confidence = result.confidence ?? _confidence;
        _retractedAt = result.retractedAt ?? _retractedAt;
      });
      AppFeedback.success(context, '已提交纠错: $action');
    } catch (e) {
      if (!mounted) {
        return;
      }
      AppFeedback.error(context, '纠错失败: $e');
    }
  }
}
