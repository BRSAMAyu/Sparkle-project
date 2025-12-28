import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/repositories/error_repository.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

/// 错误类型选项
const List<String> _errorTypes = [
  '概念混淆',
  '计算错误',
  '审题不清',
  '知识遗忘',
  '方法不当',
  '其他',
];

/// 闪念胶囊 - 快速错题记录
class FlashCapsuleTool extends ConsumerStatefulWidget {

  const FlashCapsuleTool({
    super.key,
    this.taskId,
    this.initialSubject,
  });
  final String? taskId;
  final String? initialSubject;

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
    setState(() => _isLoading = true);
    try {
      final subjects = await ref.read(errorRepositoryProvider).getSubjects();
      setState(() {
        _subjects = subjects;
        if (subjects.isNotEmpty) {
          // 尝试匹配初始科目
          if (widget.initialSubject != null) {
            final match = subjects.firstWhere(
              (s) => s['name'] == widget.initialSubject,
              orElse: () => subjects.first,
            );
            _selectedSubjectId = match['id'];
          } else {
            _selectedSubjectId = subjects.first['id'];
          }
        }
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _submit() async {
    if (_selectedSubjectId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: const Text('请选择科目'), backgroundColor: DS.warning),
      );
      return;
    }

    final topic = _topicController.text.trim();
    if (topic.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: const Text('请输入知识点'), backgroundColor: DS.warning),
      );
      return;
    }

    final description = _descriptionController.text.trim();
    if (description.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: const Text('请输入错误描述'), backgroundColor: DS.warning),
      );
      return;
    }

    setState(() => _isSubmitting = true);

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
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('已记录错题'),
            backgroundColor: DS.success,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } catch (e) {
      setState(() => _isSubmitting = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('记录失败: $e'),
            backgroundColor: DS.error,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 600,
      decoration: BoxDecoration(
        color: DS.brandPrimaryConst,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Drag Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.neutral300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: Colors.amber.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.lightbulb_outlined, color: Colors.amber, size: 24),
              ),
              const SizedBox(width: DS.md),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '闪念胶囊',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: DS.fontWeightBold,
                    ),
                  ),
                  Text(
                    '快速记录学习中遇到的问题',
                    style: TextStyle(
                      color: DS.neutral500,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: DS.xl),

          // Scrollable Content
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Subject Dropdown
                  Text(
                    '科目',
                    style: TextStyle(
                      fontWeight: DS.fontWeightMedium,
                      color: DS.neutral700,
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  if (_isLoading) const Center(child: CircularProgressIndicator(strokeWidth: 2)) else Container(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          decoration: BoxDecoration(
                            color: DS.neutral50,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: DS.neutral200),
                          ),
                          child: DropdownButtonHideUnderline(
                            child: DropdownButton<int>(
                              value: _selectedSubjectId,
                              isExpanded: true,
                              hint: const Text('选择科目'),
                              items: _subjects.map((subject) => DropdownMenuItem<int>(
                                  value: subject['id'],
                                  child: Text(subject['name'] ?? ''),
                                ),).toList(),
                              onChanged: (value) {
                                setState(() => _selectedSubjectId = value);
                              },
                            ),
                          ),
                        ),
                  const SizedBox(height: 20),

                  // Topic Input
                  Text(
                    '知识点',
                    style: TextStyle(
                      fontWeight: DS.fontWeightMedium,
                      color: DS.neutral700,
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  TextField(
                    controller: _topicController,
                    decoration: InputDecoration(
                      hintText: '例如：三角函数求导、牛顿第二定律...',
                      filled: true,
                      fillColor: DS.neutral50,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: BorderSide.none,
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Colors.amber, width: 2),
                      ),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Error Type Chips
                  Text(
                    '错误类型',
                    style: TextStyle(
                      fontWeight: DS.fontWeightMedium,
                      color: DS.neutral700,
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _errorTypes.map((type) {
                      final isSelected = type == _selectedErrorType;
                      return ChoiceChip(
                        label: Text(type),
                        selected: isSelected,
                        onSelected: (selected) {
                          if (selected) {
                            setState(() => _selectedErrorType = type);
                          }
                        },
                        selectedColor: Colors.amber.withValues(alpha: 0.2),
                        backgroundColor: DS.neutral100,
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.amber.shade800 : DS.neutral600,
                          fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                          side: BorderSide(
                            color: isSelected ? Colors.amber : Colors.transparent,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 20),

                  // Description
                  Text(
                    '描述',
                    style: TextStyle(
                      fontWeight: DS.fontWeightMedium,
                      color: DS.neutral700,
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  Container(
                    height: 120,
                    padding: const EdgeInsets.all(DS.xs),
                    decoration: BoxDecoration(
                      color: Colors.amber.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
                    ),
                    child: TextField(
                      controller: _descriptionController,
                      maxLines: null,
                      expands: true,
                      decoration: const InputDecoration(
                        hintText: '简单描述错误情况和原因分析...',
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.all(DS.md),
                      ),
                      style: const TextStyle(fontSize: 14, height: 1.5),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: DS.lg),

          // Submit Button
          CustomButton.primary(
            text: '快速保存',
            icon: Icons.flash_on_rounded,
            onPressed: _isSubmitting ? null : _submit,
            customGradient: LinearGradient(
              colors: [DS.warning, const Color(0xFFFFB74D)],
            ),
          ),
        ],
      ),
    );
}
