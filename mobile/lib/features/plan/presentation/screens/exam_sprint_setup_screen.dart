import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/file/data/models/file_models.dart';
import 'package:sparkle/features/file/presentation/widgets/file_picker_with_presigned.dart';
import 'package:sparkle/features/plan/data/models/exam_sprint_models.dart';
import 'package:sparkle/features/plan/data/repositories/exam_sprint_repository.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';

class ExamSprintSetupScreen extends ConsumerStatefulWidget {
  const ExamSprintSetupScreen({super.key});

  @override
  ConsumerState<ExamSprintSetupScreen> createState() =>
      _ExamSprintSetupScreenState();
}

class _ExamSprintSetupScreenState extends ConsumerState<ExamSprintSetupScreen> {
  static const List<String> _subjectSuggestions = <String>[
    '计算机网络',
    '操作系统',
    '数据库',
    '高数',
    '线代',
    '英语',
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _subjectController = TextEditingController();
  final TextEditingController _scopeController = TextEditingController();

  DateTime? _examDate = DateTime.now().add(const Duration(days: 7));
  String _targetMode = 'pass';
  double _currentLevel = 35;
  double _dailyMinutes = 90;
  bool _isSubmitting = false;
  final List<StoredFile> _uploadedFiles = <StoredFile>[];
  final Set<String> _selectedWeakChapters = <String>{};

  List<String> get _chapterSuggestions =>
      _chapterSuggestionsFor(_subjectController.text.trim());

  @override
  void dispose() {
    _subjectController.dispose();
    _scopeController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final probabilityLabel = '${_dailyMinutes.round()} 分钟/天';

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('考试冲刺设置'),
      ),
      child: ContentConstraint(
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.all(DS.spacing16),
            children: [
              _buildHeroCard(context),
              const SizedBox(height: DS.spacing16),
              _buildSection(
                context,
                title: '1. 哪门课？',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextFormField(
                      controller: _subjectController,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        hintText: '例如：计算机网络 / 高数 / 英语四级',
                        prefixIcon: Icon(Icons.menu_book_outlined),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return '先告诉我你要冲刺哪门课';
                        }
                        return null;
                      },
                      onChanged: (_) => setState(() {}),
                    ),
                    const SizedBox(height: DS.spacing12),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: _subjectSuggestions.map((String subject) {
                        final selected =
                            _subjectController.text.trim() == subject;
                        return ChoiceChip(
                          label: Text(subject),
                          selected: selected,
                          onSelected: (_) {
                            setState(() {
                              _subjectController.text = subject;
                              _selectedWeakChapters.clear();
                            });
                          },
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildSection(
                context,
                title: '2. 考试哪天？',
                child: InkWell(
                  borderRadius: BorderRadius.circular(18),
                  onTap: _pickExamDate,
                  child: Container(
                    padding: const EdgeInsets.all(DS.spacing16),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: DS.surfaceTertiary),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.event_outlined),
                        const SizedBox(width: DS.spacing12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _examDate == null
                                    ? '选择考试日期'
                                    : MaterialLocalizations.of(context)
                                        .formatMediumDate(_examDate!),
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: DS.spacing4),
                              Text(
                                _examDate == null
                                    ? '日期会决定冲刺天数和节奏'
                                    : '离考试还有 ${_daysLeftLabel(_examDate!)}',
                                style: Theme.of(context)
                                    .textTheme
                                    .bodySmall
                                    ?.copyWith(color: DS.textSecondary),
                              ),
                            ],
                          ),
                        ),
                        const Icon(Icons.chevron_right_rounded),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildSection(
                context,
                title: '3. 目标是通过、保分还是冲高分？',
                child: Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: _targetOptions
                      .map(
                        (option) => ChoiceChip(
                          label: Text(option.label),
                          selected: _targetMode == option.value,
                          onSelected: (_) {
                            setState(() => _targetMode = option.value);
                          },
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildSection(
                context,
                title: '4. 考试范围 / 老师重点有吗？',
                subtitle: '可以直接粘贴重点，也可以上传 PDF / DOCX / PPT / TXT。',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    TextFormField(
                      controller: _scopeController,
                      maxLines: 5,
                      minLines: 4,
                      decoration: const InputDecoration(
                        hintText: '例如：重点看传输层、网络层；老师说会考简答和计算题。',
                        alignLabelWithHint: true,
                      ),
                    ),
                    const SizedBox(height: DS.spacing12),
                    Row(
                      children: [
                        SparkleButton.outline(
                          label: '上传资料',
                          icon: const Icon(Icons.upload_file_outlined),
                          onPressed: _openUploadSheet,
                        ),
                        const SizedBox(width: DS.spacing8),
                        Text(
                          _uploadedFiles.isEmpty
                              ? '还没上传资料'
                              : '已上传 ${_uploadedFiles.length} 份资料',
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: DS.textSecondary),
                        ),
                      ],
                    ),
                    if (_uploadedFiles.isNotEmpty) ...[
                      const SizedBox(height: DS.spacing12),
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: _uploadedFiles
                            .map(
                              (StoredFile file) => InputChip(
                                label: Text(file.fileName),
                                avatar: const Icon(
                                  Icons.description_outlined,
                                  size: 18,
                                ),
                                onDeleted: () {
                                  setState(() {
                                    _uploadedFiles.removeWhere(
                                      (StoredFile item) => item.id == file.id,
                                    );
                                  });
                                },
                              ),
                            )
                            .toList(),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildSection(
                context,
                title: '5. 你现在大概会多少？最怕哪几章？',
                subtitle: _baselineLabel(_currentLevel.round()),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          '${_currentLevel.round()} / 100',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const Spacer(),
                        Text(
                          _baselineLabel(_currentLevel.round()),
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: DS.textSecondary),
                        ),
                      ],
                    ),
                    Slider(
                      value: _currentLevel,
                      max: 100,
                      divisions: 20,
                      label: _currentLevel.round().toString(),
                      onChanged: (double value) {
                        setState(() => _currentLevel = value);
                      },
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      '最怕哪几章？',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: DS.spacing8),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: _chapterSuggestions.map((String chapter) {
                        final selected =
                            _selectedWeakChapters.contains(chapter);
                        return FilterChip(
                          label: Text(chapter),
                          selected: selected,
                          onSelected: (bool value) {
                            setState(() {
                              if (value) {
                                _selectedWeakChapters.add(chapter);
                              } else {
                                _selectedWeakChapters.remove(chapter);
                              }
                            });
                          },
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing12),
              _buildSection(
                context,
                title: '6. 每天真实能学多久？',
                subtitle: probabilityLabel,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${_dailyMinutes.round()} 分钟 / 天',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    Slider(
                      value: _dailyMinutes,
                      min: 30,
                      max: 360,
                      divisions: 11,
                      label: '${_dailyMinutes.round()} 分钟',
                      onChanged: (double value) {
                        setState(() => _dailyMinutes = value);
                      },
                    ),
                    Text(
                      '用“你大概率能坚持”的时间，不用理想状态。',
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing20),
              SparkleButton(
                label: '生成我的第一天任务',
                icon: const Icon(Icons.rocket_launch_outlined),
                loading: _isSubmitting,
                expand: true,
                onPressed: _isSubmitting ? null : _submit,
              ),
              const SizedBox(height: DS.spacing12),
              Text(
                '提交后会在 3 秒内给出初评，并直接带你进入计划或第一天任务。',
                textAlign: TextAlign.center,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.spacing20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeroCard(BuildContext context) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(Icons.flash_on_rounded),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '不是填问卷，是一起确定起点',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        '填完这 6 个问题，我会直接给你初始评估、推荐策略和第一天任务。',
                        style: Theme.of(context)
                            .textTheme
                            .bodyMedium
                            ?.copyWith(color: DS.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      );

  Widget _buildSection(
    BuildContext context, {
    required String title,
    required Widget child,
    String? subtitle,
  }) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            if (subtitle != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                subtitle,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: DS.textSecondary),
              ),
            ],
            const SizedBox(height: DS.spacing12),
            child,
          ],
        ),
      );

  Future<void> _pickExamDate() async {
    final now = DateTime.now();
    final initialDate = _examDate == null || _examDate!.isBefore(now)
        ? now.add(const Duration(days: 7))
        : _examDate!;
    final picked = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: DateUtils.dateOnly(now),
      lastDate: now.add(const Duration(days: 365)),
    );
    if (picked == null || !mounted) {
      return;
    }
    setState(() => _examDate = DateUtils.dateOnly(picked));
  }

  Future<void> _openUploadSheet() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext sheetContext) => FilePickerWithPresignedUpload(
        onUploaded: (StoredFile file) {
          if (!mounted) {
            return;
          }
          setState(() {
            if (_uploadedFiles.every((StoredFile item) => item.id != file.id)) {
              _uploadedFiles.add(file);
            }
          });
          Navigator.of(sheetContext).pop();
          AppFeedback.success(context, '资料已上传');
        },
        onError: (String message) {
          if (mounted) {
            AppFeedback.error(context, message);
          }
        },
      ),
    );
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) {
      return;
    }
    if (_examDate == null) {
      AppFeedback.error(context, '先选择考试日期');
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      final request = ExamSprintIntakeRequest(
        subject: _subjectController.text.trim(),
        examDate: _examDate!,
        targetMode: _targetMode,
        scopeContext: ExamSprintScopeContext(
          text: _scopeController.text.trim().isEmpty
              ? null
              : _scopeController.text.trim(),
          fileIds: _uploadedFiles.map((StoredFile file) => file.id).toList(),
          fileNames:
              _uploadedFiles.map((StoredFile file) => file.fileName).toList(),
        ),
        baseline: ExamSprintBaselineInput(
          currentLevel: _currentLevel.round(),
          weakChapters: _selectedWeakChapters.toList(),
        ),
        dailyStudyMinutes: _dailyMinutes.round(),
      );

      final result =
          await ref.read(examSprintRepositoryProvider).submitIntake(request);

      await ref.read(planListProvider.notifier).refresh();
      await ref.read(taskListProvider.notifier).refreshTasks();
      ref.invalidate(planDetailProvider(result.launch.planId));

      if (!mounted) {
        return;
      }
      await _showAssessmentSheet(result);
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, e.toString());
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  Future<void> _showAssessmentSheet(ExamSprintIntakeResult result) async {
    final primaryRoute =
        result.launch.recommendedTaskRoute ?? result.launch.planRoute;
    final canOpenTask = result.launch.recommendedTaskRoute != null;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing12,
            DS.spacing16,
            DS.spacing20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: DS.surfaceTertiary,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              Text(
                '初步评估已完成',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: DS.spacing8),
              Text(
                result.initialAssessment.summary,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: DS.spacing16),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  _buildResultChip(
                    context,
                    Icons.flag_outlined,
                    '通过概率 ${(result.initialAssessment.passProbability * 100).round()}%',
                  ),
                  _buildResultChip(
                    context,
                    Icons.tune_rounded,
                    '建议模式 ${result.initialAssessment.recommendedModeLabel}',
                  ),
                  _buildResultChip(
                    context,
                    Icons.layers_outlined,
                    result.selectedPack.packName,
                  ),
                ],
              ),
              const SizedBox(height: DS.spacing16),
              GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.card,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '第一天先做什么',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: DS.spacing8),
                    Text(result.strategyPreview.firstDayFocus),
                    const SizedBox(height: DS.spacing8),
                    Text(
                      result.strategyPreview.firstDayOutput,
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(color: DS.textSecondary),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: DS.spacing16),
              SparkleButton(
                label: canOpenTask ? '开始第一天任务' : '查看计划',
                icon: Icon(
                  canOpenTask
                      ? Icons.play_circle_outline_rounded
                      : Icons.map_outlined,
                ),
                expand: true,
                onPressed: () {
                  Navigator.of(sheetContext).pop();
                  context.go(primaryRoute);
                },
              ),
              if (canOpenTask) ...[
                const SizedBox(height: DS.spacing8),
                SparkleButton.outline(
                  label: '查看整个计划',
                  expand: true,
                  onPressed: () {
                    Navigator.of(sheetContext).pop();
                    context.go(result.launch.planRoute);
                  },
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildResultChip(BuildContext context, IconData icon, String label) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(999),
          color: DS.surfaceSecondary,
          border: Border.all(color: DS.surfaceTertiary),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium,
            ),
          ],
        ),
      );

  String _baselineLabel(int score) {
    if (score <= 25) {
      return '几乎要从零开始';
    }
    if (score <= 50) {
      return '上过课，但基础还不稳';
    }
    if (score <= 75) {
      return '有一部分基础，可以边补边冲';
    }
    return '基础不错，重点是提分校准';
  }

  String _daysLeftLabel(DateTime examDate) {
    final days = DateUtils.dateOnly(examDate)
        .difference(DateUtils.dateOnly(DateTime.now()))
        .inDays;
    return '${days <= 0 ? 1 : days} 天';
  }

  List<String> _chapterSuggestionsFor(String subject) {
    final normalized = subject.toLowerCase();
    if (normalized.contains('计算机网络') || normalized.contains('计网')) {
      return const <String>['物理层', '数据链路层', '网络层', '传输层', '应用层'];
    }
    if (normalized.contains('操作系统')) {
      return const <String>['进程线程', '同步互斥', '内存管理', '文件系统', '死锁'];
    }
    if (normalized.contains('数据库')) {
      return const <String>['ER 模型', 'SQL', '范式', '事务', '索引'];
    }
    if (normalized.contains('高数')) {
      return const <String>['极限连续', '导数微分', '积分', '级数', '微分方程'];
    }
    if (normalized.contains('线代')) {
      return const <String>['矩阵', '行列式', '向量组', '特征值', '二次型'];
    }
    if (normalized.contains('英语')) {
      return const <String>['词汇', '长难句', '阅读', '翻译', '写作'];
    }
    return const <String>['第一章', '第二章', '第三章', '第四章', '第五章'];
  }
}

class _TargetModeOption {
  const _TargetModeOption({
    required this.value,
    required this.label,
  });

  final String value;
  final String label;
}

const List<_TargetModeOption> _targetOptions = <_TargetModeOption>[
  _TargetModeOption(value: 'pass', label: '通过'),
  _TargetModeOption(value: 'hold', label: '保分'),
  _TargetModeOption(value: 'high_score', label: '冲高分'),
];
