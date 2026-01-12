import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';

class ReflectionDialog extends ConsumerStatefulWidget {
  const ReflectionDialog({super.key});

  @override
  ConsumerState<ReflectionDialog> createState() => _ReflectionDialogState();
}

class _ReflectionDialogState extends ConsumerState<ReflectionDialog> {
  String? _feeling;
  final TextEditingController _noteController = TextEditingController();
  bool _isSubmitting = false;

  Future<void> _submit() async {
    if (_feeling == null) return;

    setState(() => _isSubmitting = true);

    try {
      final content =
          'Focus Session Reflection: I felt $_feeling.\n${_noteController.text}';

      // Create Fragment
      await ref.read(cognitiveProvider.notifier).createFragment(
            content: content,
            sourceType: 'reflection',
            // taskId: we could pass task id if available
          );

      if (mounted) {
        context.pop(true);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Reflection saved to Cognitive Prism')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to save: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        backgroundColor: DS.deepSpaceEnd,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          '专注结束',
          style: TextStyle(
              color: DS.brandPrimaryConst, fontWeight: FontWeight.bold,),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('这次专注的感觉如何？', style: TextStyle(color: DS.brandPrimaryConst)),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: ['🔥 心流', '🙂 专注', '😐 一般', '😖 分心', '😫 疲惫']
                  .map(
                    (f) => ChoiceChip(
                      label: Text(f),
                      selected: _feeling == f,
                      onSelected: (b) =>
                          setState(() => _feeling = b ? f : null),
                      backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
                      selectedColor: DS.brandPrimary,
                      labelStyle: TextStyle(
                        color:
                            _feeling == f ? Colors.black : DS.brandPrimaryConst,
                      ),
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _noteController,
              decoration: InputDecoration(
                hintText: '有什么值得记录的吗？(可选)',
                hintStyle: TextStyle(color: DS.brandPrimary.withValues(alpha: 0.5)),
                enabledBorder: OutlineInputBorder(
                  borderSide:
                      BorderSide(color: DS.brandPrimary.withValues(alpha: 0.3)),
                  borderRadius: BorderRadius.circular(12),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: DS.brandPrimary),
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              style: TextStyle(color: DS.brandPrimaryConst),
              maxLines: 2,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => context.pop(false),
            child: Text('跳过',
                style: TextStyle(color: DS.brandPrimary.withValues(alpha: 0.6)),),
          ),
          ElevatedButton(
            onPressed: _feeling != null && !_isSubmitting ? _submit : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: DS.brandPrimary,
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),),
            ),
            child: _isSubmitting
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),)
                : const Text('保存'),
          ),
        ],
      );
}
