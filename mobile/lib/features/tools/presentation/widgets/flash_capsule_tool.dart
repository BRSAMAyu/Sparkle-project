// ignore_for_file: discarded_futures, unawaited_futures

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

const List<String> _errorTypes = [
  '概念混淆',
  '计算错误',
  '审题不清',
  '知识遗忘',
  '方法不当',
  '其他',
];

class FlashCapsuleTool extends ConsumerStatefulWidget {
  const FlashCapsuleTool({
    super.key,
    this.taskId,
    this.initialSubject,
    this.surface = ToolSurface.page,
  });

  final String? taskId;
  final String? initialSubject;
  final ToolSurface surface;

  @override
  ConsumerState<FlashCapsuleTool> createState() => _FlashCapsuleToolState();
}

class _FlashCapsuleToolState extends ConsumerState<FlashCapsuleTool> {
  final _topicController = TextEditingController();
  final _descriptionController = TextEditingController();

  List<Map<String, dynamic>> _subjects = [];
  int? _selectedSubjectId;
  String _selectedErrorType = _errorTypes[0];
  bool _isLoading = false;
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _loadSubjects();
  }

  @override
  void dispose() {
    _topicController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _loadSubjects() async {
    if (!mounted) {
      return;
    }
    setState(() => _isLoading = true);
    try {
      final subjects = await ref.read(errorRepositoryProvider).getSubjects();
      if (!mounted) {
        return;
      }
      setState(() {
        _subjects = subjects;
        if (subjects.isNotEmpty) {
          if (widget.initialSubject != null) {
            final match = subjects.firstWhere(
              (subject) => subject['name'] == widget.initialSubject,
              orElse: () => subjects.first,
            );
            _selectedSubjectId = match['id'] as int?;
          } else {
            _selectedSubjectId = subjects.first['id'] as int?;
          }
        }
        _isLoading = false;
      });
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _submit() async {
    if (_selectedSubjectId == null) {
      AppFeedback.info(context, '请选择科目');
      return;
    }

    final topic = _topicController.text.trim();
    final description = _descriptionController.text.trim();
    if (topic.isEmpty || description.isEmpty) {
      AppFeedback.info(context, '请补全知识点和错误描述');
      return;
    }

    if (mounted) {
      setState(() => _isSubmitting = true);
    }

    try {
      await ref.read(errorRepositoryProvider).createError(
            subjectId: _selectedSubjectId!,
            topic: topic,
            errorType: _selectedErrorType,
            description: description,
          );

      HapticFeedback.mediumImpact();
      if (mounted) {
        Navigator.pop(context);
        AppFeedback.success(context, '已记录错题');
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isSubmitting = false);
        AppFeedback.error(context, '记录失败: $e');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.warning;
    return ToolShell(
      surface: widget.surface,
      icon: Icons.lightbulb_outline_rounded,
      title: '闪念胶囊',
      subtitle: '把一闪而过的疑点及时落地成错题线索，减少“知道有问题但没记住”的损耗。',
      accentColor: accent,
      fillHeight: true,
      heroChips: [
        ToolHeroChip(
          label: _subjects.isEmpty ? '等待科目加载' : '${_subjects.length} 个科目',
          accentColor: accent,
          icon: Icons.category_rounded,
        ),
        ToolHeroChip(
          label: _selectedErrorType,
          accentColor: accent,
          icon: Icons.label_rounded,
        ),
      ],
      body: Column(
        children: [
          Wrap(
            spacing: DS.spacing12,
            runSpacing: DS.spacing12,
            children: [
              ToolMetricCard(
                label: '知识点长度',
                value: '${_topicController.text.trim().length}',
                accentColor: accent,
                icon: Icons.topic_rounded,
              ),
              ToolMetricCard(
                label: '描述长度',
                value: '${_descriptionController.text.trim().length}',
                accentColor: accent,
                icon: Icons.notes_rounded,
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          Expanded(
            child: ToolSectionCard(
              accentColor: accent,
              fillHeight: true,
              title: '记录内容',
              subtitle: '选择科目、错误类型，再补充知识点和描述。',
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (_isLoading)
                      Center(
                        child: Padding(
                          padding: const EdgeInsets.all(DS.spacing24),
                          child: CircularProgressIndicator(color: accent),
                        ),
                      )
                    else
                      _SubjectDropdown(
                        value: _selectedSubjectId,
                        subjects: _subjects,
                        onChanged: (value) {
                          setState(() => _selectedSubjectId = value);
                        },
                      ),
                    const SizedBox(height: DS.spacing16),
                    TextField(
                      controller: _topicController,
                      decoration: const InputDecoration(
                        labelText: '知识点',
                        hintText: '例如：三角函数求导、牛顿第二定律...',
                      ),
                      onChanged: (_) => setState(() {}),
                    ),
                    const SizedBox(height: DS.spacing16),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: Wrap(
                        spacing: DS.spacing10,
                        runSpacing: DS.spacing10,
                        children: _errorTypes
                            .map(
                              (type) => ToolChoiceChip(
                                label: type,
                                selected: _selectedErrorType == type,
                                onTap: () => setState(() {
                                  _selectedErrorType = type;
                                }),
                                accentColor: accent,
                              ),
                            )
                            .toList(),
                      ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextField(
                      controller: _descriptionController,
                      maxLines: 8,
                      decoration: const InputDecoration(
                        labelText: '错误描述',
                        hintText: '记录你是怎么错的、卡在什么地方、下次要如何避免。',
                        alignLabelWithHint: true,
                      ),
                      onChanged: (_) => setState(() {}),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      footer: SparkleButton(
        label: _isSubmitting ? '记录中...' : '保存胶囊',
        onPressed: _isSubmitting ? null : _submit,
        icon: const Icon(Icons.check_rounded),
        loading: _isSubmitting,
        expand: true,
      ),
    );
  }
}

class _SubjectDropdown extends StatelessWidget {
  const _SubjectDropdown({
    required this.value,
    required this.subjects,
    required this.onChanged,
  });

  final int? value;
  final List<Map<String, dynamic>> subjects;
  final ValueChanged<int?> onChanged;

  @override
  Widget build(BuildContext context) => DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<int>(
              value: value,
              isExpanded: true,
              hint: const Text('选择科目'),
              items: subjects
                  .map(
                    (subject) => DropdownMenuItem<int>(
                      value: subject['id'] as int,
                      child: Text(subject['name'] as String? ?? ''),
                    ),
                  )
                  .toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      );
}
