import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/skill_models.dart';
import 'package:sparkle/core/services/skill_api_service.dart';

class SkillManagementScreen extends ConsumerStatefulWidget {
  const SkillManagementScreen({super.key});

  @override
  ConsumerState<SkillManagementScreen> createState() =>
      _SkillManagementScreenState();
}

class _SkillManagementScreenState extends ConsumerState<SkillManagementScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController =
      TabController(length: 2, vsync: this);
  bool _loading = true;
  String? _error;
  List<SkillItemModel> _skills = [];
  List<SharedSkillItemModel> _sharedSkills = [];
  final Set<String> _busyIds = <String>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(skillApiServiceProvider);
      final results = await Future.wait<dynamic>([
        api.getSkills(),
        api.getSharedSkills(),
      ]);
      if (!mounted) return;
      setState(() {
        _skills = results[0] as List<SkillItemModel>;
        _sharedSkills = results[1] as List<SharedSkillItemModel>;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '我的方式加载失败: $e';
        _loading = false;
      });
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => GraphiteScaffold(
        appBar: AppBar(
          title: const Text('我的方式'),
          actions: [
            IconButton(
              icon: const Icon(Icons.auto_awesome_outlined),
              tooltip: '从草稿生成',
              onPressed: _openDraftExtractor,
            ),
            IconButton(
              icon: const Icon(Icons.add_rounded),
              tooltip: '新建方式',
              onPressed: () => _openEditor(),
            ),
            IconButton(
              icon: const Icon(Icons.refresh_rounded),
              onPressed: _load,
            ),
          ],
          bottom: TabBar(
            controller: _tabController,
            tabs: const [
              Tab(text: '我的方式'),
              Tab(text: '共享目录'),
            ],
          ),
        ),
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Text(_error!))
                : ContentConstraint(
                    child: TabBarView(
                      controller: _tabController,
                      children: [
                        RefreshIndicator(
                          onRefresh: _load,
                          child: ListView(
                            padding: const EdgeInsets.symmetric(
                              vertical: DS.spacing16,
                            ),
                            children: [
                            _buildIntroCard(),
                            const SizedBox(height: DS.spacing12),
                            ..._skills.map(_buildSkillCard),
                            if (_skills.isEmpty)
                              const Padding(
                                padding: EdgeInsets.only(top: DS.spacing24),
                                child: Center(child: Text('还没有沉淀任何 Skill')),
                              ),
                          ],
                        ),
                      ),
                      RefreshIndicator(
                        onRefresh: _load,
                        child: ListView(
                          padding: const EdgeInsets.symmetric(
                            vertical: DS.spacing16,
                          ),
                          children: [
                            ..._sharedSkills.map(_buildSharedSkillCard),
                            if (_sharedSkills.isEmpty)
                              const Padding(
                                padding: EdgeInsets.only(top: DS.spacing24),
                                child: Center(child: Text('共享目录暂时为空')),
                              ),
                          ],
                        ),
                      ),
                    ],
                    ),
                  ),
      );

  Widget _buildIntroCard() => GraphiteCardSurface(
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '把你认可的处理方式沉淀下来',
                style: DS.titleMedium.copyWith(fontWeight: DS.fontWeightBold),
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                '你可以手动新建、从对话草稿导入、启用/停用、编辑、删除、共享或从匿名目录 fork。',
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
            ],
          ),
        ),
      );

  Widget _buildSkillCard(SkillItemModel item) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing12),
        child: GraphiteCardSurface(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        item.name,
                        style: DS.titleMedium.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                    Switch(
                      value: item.active,
                      onChanged: _busyIds.contains(item.id)
                          ? null
                          : (value) => _toggleSkill(item, value),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  item.patternTemplate,
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: DS.spacing8),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    _SkillTag(label: 'usage ${item.usageCount}'),
                    _SkillTag(label: item.isForked ? 'forked' : 'self'),
                    _SkillTag(label: item.isShared ? 'shared' : 'private'),
                    if (item.forkedAt != null)
                      _SkillTag(
                        label:
                            'forked ${item.forkedAt!.toIso8601String().split('T').first}',
                      ),
                  ],
                ),
                const SizedBox(height: DS.spacing12),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    SparkleButton.ghost(
                      label: '编辑',
                      onPressed: () => _openEditor(existing: item),
                    ),
                    SparkleButton.ghost(
                      label: '删除',
                      onPressed: () => _deleteSkill(item),
                    ),
                    if (!item.isForked && !item.isShared)
                      SparkleButton.ghost(
                        label: '共享',
                        onPressed: () => _shareSkill(item),
                      ),
                    if (item.isShared)
                      SparkleButton.ghost(
                        label: '撤回共享',
                        onPressed: () => _unshareSkill(item),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildSharedSkillCard(SharedSkillItemModel item) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing12),
        child: GraphiteCardSurface(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        item.name,
                        style: DS.titleMedium.copyWith(
                          fontWeight: DS.fontWeightBold,
                        ),
                      ),
                    ),
                    _SkillTag(label: item.authorLabel),
                  ],
                ),
                const SizedBox(height: DS.spacing8),
                Text(
                  item.patternTemplate,
                  style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                ),
                const SizedBox(height: DS.spacing12),
                SparkleButton(
                  label: 'Fork 到我的方式',
                  disabled: _busyIds.contains(item.id),
                  onPressed: () => _forkSkill(item),
                ),
              ],
            ),
          ),
        ),
      );

  Future<void> _toggleSkill(SkillItemModel item, bool active) async {
    await _runBusy(item.id, () async {
      final updated = await ref.read(skillApiServiceProvider).toggleSkill(
            item.id,
            active,
          );
      _replaceSkill(updated);
    });
  }

  Future<void> _deleteSkill(SkillItemModel item) async {
    await _runBusy(item.id, () async {
      await ref.read(skillApiServiceProvider).deleteSkill(item.id);
      if (!mounted) return;
      setState(() {
        _skills = _skills.where((element) => element.id != item.id).toList();
      });
    });
  }

  Future<void> _shareSkill(SkillItemModel item) async {
    await _runBusy(item.id, () async {
      await ref.read(skillApiServiceProvider).shareSkill(item.id);
      await _load();
    });
  }

  Future<void> _unshareSkill(SkillItemModel item) async {
    await _runBusy(item.id, () async {
      final updated = await ref.read(skillApiServiceProvider).unshareSkill(
            item.id,
          );
      _replaceSkill(updated);
    });
  }

  Future<void> _forkSkill(SharedSkillItemModel item) async {
    await _runBusy(item.id, () async {
      await ref.read(skillApiServiceProvider).forkSharedSkill(item.id);
      await _load();
    });
  }

  Future<void> _openDraftExtractor() async {
    final draft = await showDialog<SkillDraftModel>(
      context: context,
      builder: (context) => const _SkillDraftRequestDialog(),
    );
    if (draft == null || !mounted) return;
    await _openEditor(draft: draft);
  }

  Future<void> _openEditor({
    SkillItemModel? existing,
    SkillDraftModel? draft,
  }) async {
    final payload = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) =>
          _SkillEditorDialog(existing: existing, draft: draft),
    );
    if (payload == null) {
      if (draft != null) {
        await ref.read(skillApiServiceProvider).recordDraftOutcome(false);
      }
      return;
    }

    try {
      SkillItemModel saved;
      if (existing == null) {
        saved = await ref.read(skillApiServiceProvider).createSkill(payload);
        if (draft != null) {
          await ref.read(skillApiServiceProvider).recordDraftOutcome(true);
        }
        if (!mounted) return;
        setState(() {
          _skills = [saved, ..._skills];
        });
      } else {
        saved = await ref
            .read(skillApiServiceProvider)
            .updateSkill(existing.id, payload);
        _replaceSkill(saved);
      }
      if (!mounted) return;
      AppFeedback.success(context, '已保存我的方式');
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, '保存失败: $e');
    }
  }

  void _replaceSkill(SkillItemModel item) {
    if (!mounted) return;
    setState(() {
      _skills = _skills
          .map((element) => element.id == item.id ? item : element)
          .toList();
    });
  }

  Future<void> _runBusy(String id, Future<void> Function() action) async {
    setState(() => _busyIds.add(id));
    try {
      await action();
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '操作失败: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _busyIds.remove(id));
      }
    }
  }
}

class _SkillTag extends StatelessWidget {
  const _SkillTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(label, style: DS.labelSmall),
      );
}

class _SkillEditorDialog extends StatefulWidget {
  const _SkillEditorDialog({this.existing, this.draft});

  final SkillItemModel? existing;
  final SkillDraftModel? draft;

  @override
  State<_SkillEditorDialog> createState() => _SkillEditorDialogState();
}

class _SkillEditorDialogState extends State<_SkillEditorDialog> {
  late final TextEditingController _nameController = TextEditingController(
    text: widget.existing?.name ?? widget.draft?.name ?? '',
  );
  late final TextEditingController _patternController = TextEditingController(
    text:
        widget.existing?.patternTemplate ?? widget.draft?.patternTemplate ?? '',
  );
  late final TextEditingController _intentController = TextEditingController(
    text: _csvForKind('intent_keywords'),
  );
  late final TextEditingController _toolController = TextEditingController(
    text: _csvForKind('tool_category'),
  );
  late final TextEditingController _timeController = TextEditingController(
    text: _csvForKind('time_of_day'),
  );
  late final TextEditingController _weekdayController = TextEditingController(
    text: _csvForKind('weekday_set'),
  );
  late final TextEditingController _examplesController = TextEditingController(
    text: (widget.existing?.examples ?? widget.draft?.examples ?? const [])
        .join('\n'),
  );

  List<SkillActivationConditionModel> get _conditions =>
      widget.existing?.activationConditions ??
      widget.draft?.activationConditions ??
      const [];

  String _csvForKind(String kind) {
    return _conditions
        .where((item) => item.kind == kind)
        .expand((item) => item.value)
        .join(', ');
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(widget.existing == null ? '新建方式' : '编辑方式'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _nameController,
                decoration: const InputDecoration(labelText: '名称'),
              ),
              TextField(
                controller: _patternController,
                decoration: const InputDecoration(labelText: '处理模板'),
                minLines: 3,
                maxLines: 5,
              ),
              TextField(
                controller: _intentController,
                decoration: const InputDecoration(labelText: 'intent keywords'),
              ),
              TextField(
                controller: _toolController,
                decoration: const InputDecoration(labelText: 'tool category'),
              ),
              TextField(
                controller: _timeController,
                decoration: const InputDecoration(labelText: 'time of day'),
              ),
              TextField(
                controller: _weekdayController,
                decoration: const InputDecoration(labelText: 'weekday set'),
              ),
              TextField(
                controller: _examplesController,
                decoration: const InputDecoration(labelText: '示例（每行一条）'),
                minLines: 2,
                maxLines: 4,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(_buildPayload()),
            child: const Text('保存'),
          ),
        ],
      );

  Map<String, dynamic> _buildPayload() => {
        'name': _nameController.text.trim(),
        'pattern_template': _patternController.text.trim(),
        'activation_conditions': [
          if (_intentController.text.trim().isNotEmpty)
            {
              'kind': 'intent_keywords',
              'value': _splitCsv(_intentController.text),
            },
          if (_toolController.text.trim().isNotEmpty)
            {
              'kind': 'tool_category',
              'value': _splitCsv(_toolController.text),
            },
          if (_timeController.text.trim().isNotEmpty)
            {
              'kind': 'time_of_day',
              'value': _splitCsv(_timeController.text),
            },
          if (_weekdayController.text.trim().isNotEmpty)
            {
              'kind': 'weekday_set',
              'value': _splitCsv(_weekdayController.text),
            },
        ],
        'examples': _examplesController.text
            .split('\n')
            .map((item) => item.trim())
            .where((item) => item.isNotEmpty)
            .toList(),
        'active': widget.existing?.active ?? true,
      };

  List<String> _splitCsv(String raw) => raw
      .split(',')
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList();
}

class _SkillDraftRequestDialog extends ConsumerStatefulWidget {
  const _SkillDraftRequestDialog();

  @override
  ConsumerState<_SkillDraftRequestDialog> createState() =>
      _SkillDraftRequestDialogState();
}

class _SkillDraftRequestDialogState
    extends ConsumerState<_SkillDraftRequestDialog> {
  final TextEditingController _consentController = TextEditingController(
    text: '以后这样做，记住这种方式',
  );
  final TextEditingController _userController = TextEditingController();
  final TextEditingController _assistantController = TextEditingController();
  bool _submitting = false;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('从草稿生成'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: _consentController,
                decoration: const InputDecoration(labelText: '显式同意文本'),
              ),
              TextField(
                controller: _userController,
                decoration: const InputDecoration(labelText: '用户原话'),
                minLines: 2,
                maxLines: 4,
              ),
              TextField(
                controller: _assistantController,
                decoration: const InputDecoration(labelText: 'AI 回复'),
                minLines: 2,
                maxLines: 4,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: _submitting ? null : () => Navigator.of(context).pop(),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: _submitting ? null : _submit,
            child: Text(_submitting ? '生成中...' : '生成草稿'),
          ),
        ],
      );

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      final draft = await ref.read(skillApiServiceProvider).extractDraft({
        'trigger_type': 'explicit_phrase',
        'consent_text': _consentController.text.trim(),
        'user_message': _userController.text.trim(),
        'assistant_message': _assistantController.text.trim(),
        'seconds_since_response': 20,
      });
      if (!mounted) return;
      Navigator.of(context).pop(draft);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, '草稿生成失败: $e');
      setState(() => _submitting = false);
    }
  }
}
