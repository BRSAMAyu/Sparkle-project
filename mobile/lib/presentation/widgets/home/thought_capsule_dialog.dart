import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
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
          const SnackBar(content: Text('闪念已捕捉 ✨')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('捕捉失败: $e'), backgroundColor: AppDesignTokens.error),
        );
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius20),
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: AppDesignTokens.primaryBase.withValues(alpha: 0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.psychology, color: AppDesignTokens.primaryBase),
                ),
                const SizedBox(width: AppDesignTokens.spacing12),
                Text(
                  '闪念胶囊',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: AppDesignTokens.fontWeightBold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            Text(
              '此刻是什么拦住了你？或者有什么想吐槽的？',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppDesignTokens.neutral600,
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing16),
            TextField(
              controller: _controller,
              maxLines: 4,
              decoration: InputDecoration(
                hintText: '输入你的想法...',
                border: OutlineInputBorder(
                  borderRadius: AppDesignTokens.borderRadius12,
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: AppDesignTokens.borderRadius12,
                  borderSide: const BorderSide(color: AppDesignTokens.primaryBase, width: 2),
                ),
              ),
            ),
            const SizedBox(height: AppDesignTokens.spacing24),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('取消'),
                ),
                const SizedBox(width: AppDesignTokens.spacing12),
                CustomButton.primary(
                  text: '发送',
                  icon: Icons.send_rounded,
                  onPressed: _isSubmitting ? () {} : _submit,
                  isLoading: _isSubmitting,
                  size: ButtonSize.small,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
