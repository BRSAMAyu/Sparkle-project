import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../widgets/subject_chips.dart';
import '../../data/providers/error_book_provider.dart';

/// 添加错题页面
///
/// 设计原则：
/// 1. 表单验证严格：防止无效数据
/// 2. 用户体验优先：自动聚焦、智能键盘、清晰提示
/// 3. 状态反馈及时：加载状态、成功/失败提示
class AddErrorScreen extends ConsumerStatefulWidget {
  const AddErrorScreen({super.key});

  @override
  ConsumerState<AddErrorScreen> createState() => _AddErrorScreenState();
}

class _AddErrorScreenState extends ConsumerState<AddErrorScreen> {
  final _formKey = GlobalKey<FormState>();
  final _questionController = TextEditingController();
  final _userAnswerController = TextEditingController();
  final _correctAnswerController = TextEditingController();
  final _chapterController = TextEditingController();

  String _selectedSubject = 'math';
  bool _isSubmitting = false;

  @override
  void dispose() {
    _questionController.dispose();
    _userAnswerController.dispose();
    _correctAnswerController.dispose();
    _chapterController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_isSubmitting) return;

    setState(() => _isSubmitting = true);

    try {
      await ref.read(errorOperationsProvider.notifier).createError(
            questionText: _questionController.text.trim(),
            userAnswer: _userAnswerController.text.trim(),
            correctAnswer: _correctAnswerController.text.trim(),
            subject: _selectedSubject,
            chapter: _chapterController.text.trim().isEmpty
                ? null
                : _chapterController.text.trim(),
          );

      if (mounted) {
        // 显示成功提示
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Row(
              children: [
                Icon(Icons.check_circle, color: Colors.white),
                SizedBox(width: 12),
                Expanded(
                  child: Text('错题已添加，AI 正在分析中...'              ),
                ),
              ],
            ),
            backgroundColor: Colors.green,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 3),
          ),
        );

        // 返回上一页
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.error, color: Colors.white),
                const SizedBox(width: 12),
                Expanded(
                  child: Text('添加失败: ${e.toString()}'),
                ),
              ],
            ),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('添加错题'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: TextButton.icon(
              onPressed: _isSubmitting ? null : _submit,
              icon: _isSubmitting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.check),
              label: Text(_isSubmitting ? '保存中...' : '保存'),
              style: TextButton.styleFrom(
                foregroundColor: theme.colorScheme.onPrimary,
              ),
            ),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // 提示卡片
            _buildInfoCard(context),
            const SizedBox(height: 20),

            // 科目选择
            Text(
              '选择科目 *',
              style: theme.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            SubjectFilterChips(
              selectedSubject: _selectedSubject,
              onSelected: (subject) {
                setState(() {
                  _selectedSubject = subject ?? 'math';
                });
              },
            ),
            const SizedBox(height: 24),

            // 章节（可选）
            TextFormField(
              controller: _chapterController,
              decoration: InputDecoration(
                labelText: '章节（可选）',
                hintText: '例如：第三章 牛顿运动定律',
                border: const OutlineInputBorder(),
                prefixIcon: const Icon(Icons.folder_outlined),
                helperText: '填写后便于按章节筛选复习',
              ),
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 20),

            // 题目内容
            TextFormField(
              controller: _questionController,
              decoration: const InputDecoration(
                labelText: '题目内容 *',
                hintText: '请输入完整的题目内容...',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.quiz_outlined),
                alignLabelWithHint: true,
              ),
              maxLines: 6,
              textInputAction: TextInputAction.newline,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return '请输入题目内容';
                }
                if (value.trim().length < 5) {
                  return '题目内容至少需要 5 个字符';
                }
                if (value.trim().length > 5000) {
                  return '题目内容过长（最多 5000 字符）';
                }
                return null;
              },
            ),
            const SizedBox(height: 20),

            // 你的答案
            TextFormField(
              controller: _userAnswerController,
              decoration: const InputDecoration(
                labelText: '你的答案 *',
                hintText: '你当时写的错误答案...',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.edit_outlined),
                alignLabelWithHint: true,
              ),
              maxLines: 4,
              textInputAction: TextInputAction.newline,
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return '请输入你的答案';
                }
                if (value.trim().length > 2000) {
                  return '答案内容过长（最多 2000 字符）';
                }
                return null;
              },
            ),
            const SizedBox(height: 20),

            // 正确答案
            TextFormField(
              controller: _correctAnswerController,
              decoration: const InputDecoration(
                labelText: '正确答案 *',
                hintText: '标准答案或正确的解题过程...',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.check_circle_outline),
                alignLabelWithHint: true,
              ),
              maxLines: 4,
              textInputAction: TextInputAction.done,
              onFieldSubmitted: (_) => _submit(),
              validator: (value) {
                if (value == null || value.trim().isEmpty) {
                  return '请输入正确答案';
                }
                if (value.trim().length > 2000) {
                  return '答案内容过长（最多 2000 字符）';
                }
                return null;
              },
            ),
            const SizedBox(height: 32),

            // 底部提交按钮（大按钮）
            FilledButton.icon(
              onPressed: _isSubmitting ? null : _submit,
              icon: _isSubmitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Icon(Icons.save),
              label: Text(_isSubmitting ? '保存中，请稍候...' : '保存错题'),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                textStyle: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.primaryContainer.withOpacity(0.3),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.primary.withOpacity(0.3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.lightbulb_outline,
            color: theme.colorScheme.primary,
            size: 28,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AI 智能分析',
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: theme.colorScheme.primary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  '保存后，AI 将自动分析错题原因、生成学习建议，并关联到知识星图的相关节点',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
