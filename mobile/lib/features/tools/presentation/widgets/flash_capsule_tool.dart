// ignore_for_file: discarded_futures, unawaited_futures

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/error_book/error_book.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/shared/entities/cognitive_analysis.dart';

const List<String> _errorTypes = [
  '概念混淆',
  '计算错误',
  '审题不清',
  '知识遗忘',
  '方法不当',
  '其他',
];

class _SubjectOption {
  const _SubjectOption(this.code, this.label);

  final String code;
  final String label;
}

const List<_SubjectOption> _subjectOptions = [
  _SubjectOption('math', '数学'),
  _SubjectOption('physics', '物理'),
  _SubjectOption('chemistry', '化学'),
  _SubjectOption('biology', '生物'),
  _SubjectOption('english', '英语'),
  _SubjectOption('chinese', '语文'),
  _SubjectOption('computer', '计算机'),
  _SubjectOption('other', '其他'),
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

  late String _selectedSubjectCode;
  String _selectedErrorType = _errorTypes[0];
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _selectedSubjectCode = _resolveInitialSubject(widget.initialSubject);
  }

  @override
  void dispose() {
    _topicController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  String _resolveInitialSubject(String? initialSubject) {
    if (initialSubject == null || initialSubject.trim().isEmpty) {
      return _subjectOptions.first.code;
    }
    final normalized = initialSubject.trim().toLowerCase();
    final match = _subjectOptions.cast<_SubjectOption?>().firstWhere(
          (subject) =>
              subject!.code == normalized ||
              subject.label == initialSubject ||
              subject.label.toLowerCase() == normalized,
          orElse: () => null,
        );
    return match?.code ?? _subjectOptions.first.code;
  }

  CognitiveDimension _inferCognitiveDimension() {
    switch (_selectedErrorType) {
      case '概念混淆':
      case '知识遗忘':
        return CognitiveDimension.memory;
      case '计算错误':
      case '方法不当':
        return CognitiveDimension.application;
      case '审题不清':
        return CognitiveDimension.analysis;
      default:
        return CognitiveDimension.analysis;
    }
  }

  Future<void> _submit() async {
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
      final selectedSubject = _subjectOptions.firstWhere(
        (item) => item.code == _selectedSubjectCode,
        orElse: () => _subjectOptions.first,
      );
      await ref.read(errorOperationsProvider.notifier).createError(
            questionText: topic,
            userAnswer: description,
            subject: selectedSubject.code,
            chapter: selectedSubject.label,
          );
      await ref.read(cognitiveProvider.notifier).createFragment(
            content: '[$_selectedErrorType] $topic\n$description',
            sourceType: 'flash_capsule',
            taskId: widget.taskId,
          );

      HapticFeedback.mediumImpact();
      if (mounted) {
        Navigator.pop(context);
        AppFeedback.success(context, '已记录到错题本，并写入认知棱镜');
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
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: '${_subjectOptions.length} 个科目',
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
          ToolSectionCard(
            accentColor: accent,
            title: '记录内容',
            subtitle: '选择科目、错误类型，再补充知识点和描述。',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _SubjectDropdown(
                  value: _selectedSubjectCode,
                  subjects: _subjectOptions,
                  onChanged: (value) {
                    if (value == null) {
                      return;
                    }
                    setState(() => _selectedSubjectCode = value);
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
          const SizedBox(height: DS.spacing16),
          ToolMetricRow(
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
              ToolMetricCard(
                label: '认知维度',
                value: _inferCognitiveDimension().label,
                accentColor: accent,
                icon: Icons.psychology_alt_rounded,
              ),
            ],
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

  final String value;
  final List<_SubjectOption> subjects;
  final ValueChanged<String?> onChanged;

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
            child: DropdownButton<String>(
              value: value,
              isExpanded: true,
              hint: const Text('选择科目'),
              items: subjects
                  .map(
                    (subject) => DropdownMenuItem<String>(
                      value: subject.code,
                      child: Text(subject.label),
                    ),
                  )
                  .toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      );
}
