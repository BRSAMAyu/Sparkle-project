import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';

class CreateGroupScreen extends ConsumerStatefulWidget {
  const CreateGroupScreen({super.key});

  @override
  ConsumerState<CreateGroupScreen> createState() => _CreateGroupScreenState();
}

class _CreateGroupScreenState extends ConsumerState<CreateGroupScreen> {
  final _formKey = GlobalKey<FormState>();

  // Controllers to track changes
  late TextEditingController _nameController;
  late TextEditingController _descController;
  late TextEditingController _tagsController;
  late TextEditingController _goalController;

  GroupType _type = GroupType.squad;
  DateTime? _deadline;

  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _descController = TextEditingController();
    _tagsController = TextEditingController();
    _goalController = TextEditingController();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    _tagsController.dispose();
    _goalController.dispose();
    super.dispose();
  }

  bool get _isDirty =>
      _nameController.text.isNotEmpty ||
      _descController.text.isNotEmpty ||
      _tagsController.text.isNotEmpty ||
      _goalController.text.isNotEmpty;

  Future<bool> _onWillPop() async {
    if (!_isDirty || _isSubmitting) return true;

    final shouldPop = await showSensoryDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: DS.surfacePrimary,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: DS.border.withValues(alpha: 0.5)),
        ),
        title: Text('Discard group creation?'),
        content: Text('You have unsaved changes. Discard?'),
        actions: [
          SparkleButton.ghost(
            label: 'Keep Editing',
            onPressed: () => Navigator.of(context).pop(false),
          ),
          SparkleButton.destructive(
            label: 'Discard',
            onPressed: () => Navigator.of(context).pop(true),
          ),
        ],
      ),
    );
    return shouldPop ?? false;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    // No need to save(), controllers have values
    var focusTags = <String>[];
    if (_tagsController.text.isNotEmpty) {
      focusTags = _tagsController.text
          .split(',')
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
    }

    if (_type == GroupType.sprint && _deadline == null) {
      AppFeedback.info(
        context,
        '请选择冲刺社群的截止时间',
      );
      return;
    }

    setState(() {
      _isSubmitting = true;
    });

    try {
      await SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm);
      final groupData = GroupCreate(
        name: _nameController.text.trim(),
        description: _descController.text.trim().isEmpty
            ? null
            : _descController.text.trim(),
        type: _type,
        focusTags: focusTags,
        deadline: _deadline,
        sprintGoal: _goalController.text.trim().isEmpty
            ? null
            : _goalController.text.trim(),
      );

      final group =
          await ref.read(myGroupsProvider.notifier).createGroup(groupData);

      if (mounted) {
        await SensoryFeedbackService.emit(SensoryFeedbackEvent.success);
        context.go('/community/groups/${group.id}');
      }
    } catch (e) {
      if (mounted) {
        await SensoryFeedbackService.emit(SensoryFeedbackEvent.error);
        AppFeedback.error(context, '创建社群失败: $e');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
        onPopInvokedWithResult: (didPop, result) async {
          if (didPop) return;
          final shouldPop = await _onWillPop();
          if (shouldPop && mounted) {
            if (context.mounted) {
              Navigator.of(context).pop();
            }
          }
        },
        child: Scaffold(
          appBar: AppBar(
            backgroundColor: DS.surfaceOverlay.withValues(alpha: 0.94),
            surfaceTintColor: Colors.transparent,
            scrolledUnderElevation: 0,
            leading: SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.arrow_back),
              onPressed: () =>
                  context.canPop() ? context.pop() : context.go('/community'),
            ),
            title: Text('Create Group'),
          ),
          body: ContentConstraint(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextFormField(
                      controller: _nameController,
                      decoration: const InputDecoration(
                        labelText: '社群名称',
                        hintText: 'e.g. Daily Algorithm Sprint',
                        border: OutlineInputBorder(),
                      ),
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return '请输入社群名称';
                        }
                        if (value.length < 2) return '名称至少 2 个字符';
                        return null;
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    DropdownButtonFormField<GroupType>(
                      initialValue: _type,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: '小组类型',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: GroupType.squad,
                          child: Text(
                            '学习小组',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        DropdownMenuItem(
                          value: GroupType.sprint,
                          child: Text(
                            '冲刺小组',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                      selectedItemBuilder: (context) => const [
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            '学习小组',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Text(
                            '冲刺小组',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.selection,
                          );
                          setState(() {
                            _type = value;
                          });
                        }
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextFormField(
                      controller: _descController,
                      decoration: const InputDecoration(
                        labelText: '社群介绍',
                        border: OutlineInputBorder(),
                        alignLabelWithHint: true,
                      ),
                      maxLines: 3,
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextFormField(
                      controller: _tagsController,
                      decoration: const InputDecoration(
                        labelText: '主题标签',
                        hintText: '用逗号分隔，例如：数学, 算法, 考研',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    if (_type == GroupType.sprint) ...[
                      const SizedBox(height: DS.spacing16),
                      const Divider(),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        '冲刺设置',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: DS.spacing16),
                      ListTile(
                        title: const Text('截止日期'),
                        subtitle: Text(
                          _deadline == null
                              ? '选择日期'
                              : _deadline.toString().split(' ')[0],
                        ),
                        trailing: const Icon(Icons.calendar_today),
                        tileColor: DS.brandPrimary.shade100,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        onTap: () async {
                          await SensoryFeedbackService.emit(
                            SensoryFeedbackEvent.dialogOpen,
                          );
                          final date = await showDatePicker(
                            context: context,
                            initialDate:
                                DateTime.now().add(const Duration(days: 7)),
                            firstDate: DateTime.now(),
                            lastDate:
                                DateTime.now().add(const Duration(days: 365)),
                          );
                          if (date != null) {
                            await SensoryFeedbackService.emit(
                              SensoryFeedbackEvent.selection,
                            );
                            setState(() {
                              _deadline = date;
                            });
                          }
                        },
                      ),
                      const SizedBox(height: DS.spacing16),
                      TextFormField(
                        controller: _goalController,
                        decoration: InputDecoration(
                          labelText: '冲刺目标',
                          hintText: context.l10n.communityCreateGroupGoalHint,
                          border: OutlineInputBorder(),
                        ),
                        validator: (value) {
                          if (_type == GroupType.sprint &&
                              (value == null || value.trim().isEmpty)) {
                            return '请输入冲刺目标';
                          }
                          return null;
                        },
                      ),
                    ],
                    const SizedBox(height: DS.spacing32),
                    SparkleButton(
                      label: _isSubmitting ? '创建中...' : '创建社群',
                      onPressed: _isSubmitting ? null : _submit,
                      loading: _isSubmitting,
                      expand: true,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}
