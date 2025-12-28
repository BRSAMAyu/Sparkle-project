import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class ThoughtCapsuleDialog extends ConsumerStatefulWidget {
  const ThoughtCapsuleDialog({super.key});

  @override
  ConsumerState<ThoughtCapsuleDialog> createState() => _ThoughtCapsuleDialogState();
}

class _ThoughtCapsuleDialogState extends ConsumerState<ThoughtCapsuleDialog> {
  final TextEditingController _controller = TextEditingController();
  bool _isSubmitting = false;

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() => _isSubmitting = true);

    try {
      await ref.read(cognitiveProvider.notifier).createFragment(
        content: text,
        sourceType: 'capsule',
      );
      if (mounted) {
        Navigator.of(context).pop();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('闪念已捕捉 ✨')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('捕捉失败: $e'), backgroundColor: DS.error),
        );
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Dialog(
      shape: RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      child: Padding(
        padding: EdgeInsets.all(DS.spacing20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: DS.primaryBase.withValues(alpha: 0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.psychology, color: DS.primaryBase),
                ),
                SizedBox(width: DS.spacing12),
                Text(
                  '闪念胶囊',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ],
            ),
            SizedBox(height: DS.spacing16),
            Text(
              '此刻是什么拦住了你？或者有什么想吐槽的？',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: DS.neutral600,
              ),
            ),
            SizedBox(height: DS.spacing16),
            TextField(
              controller: _controller,
              maxLines: 4,
              decoration: InputDecoration(
                hintText: '输入你的想法...',
                border: OutlineInputBorder(
                  borderRadius: DS.borderRadius12,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: DS.borderRadius12,
                  borderSide: BorderSide(color: DS.primaryBase, width: 2),
                ),
              ),
            ),
            SizedBox(height: DS.spacing24),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                SparkleButton.ghost(label: '取消', onPressed: () => Navigator.of(context).pop()),
                SizedBox(width: DS.spacing12),
                CustomButton.primary(
                  text: '发送',
                  icon: Icons.send_rounded,
                  onPressed: _isSubmitting ? () {} : _submit,
                  isLoading: _isSubmitting,
                  size: CustomButtonSize.small,
                ),
              ],
            ),
          ],
        ),
      ),
    );
}
