import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_feedback.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';

class ThoughtCapsuleDialog extends ConsumerStatefulWidget {
  const ThoughtCapsuleDialog({super.key});

  @override
  ConsumerState<ThoughtCapsuleDialog> createState() =>
      _ThoughtCapsuleDialogState();
}

class _ThoughtCapsuleDialogState extends ConsumerState<ThoughtCapsuleDialog> {
  final TextEditingController _controller = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

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
        AppFeedback.success(context, context.l10n.thoughtCapsuleCaptured);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.thoughtCapsuleCaptureFailed(e));
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final media = MediaQuery.of(context);
    final stackActions = media.size.width < 360;

    return Dialog(
      shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius20),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: 460,
          maxHeight: media.size.height * 0.85,
        ),
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(DS.sm),
                      decoration: BoxDecoration(
                        color: DS.primaryBase.withValues(alpha: 0.1),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(Icons.psychology, color: DS.primaryBase),
                    ),
                    const SizedBox(width: DS.spacing12),
                    Expanded(
                      child: Text(
                        l10n.thoughtCapsuleTitle,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                              fontWeight: DS.fontWeightBold,
                            ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: DS.spacing16),
                Text(
                  l10n.thoughtCapsulePrompt,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: DS.neutral600,
                      ),
                ),
                const SizedBox(height: DS.spacing16),
                TextField(
                  controller: _controller,
                  maxLines: 4,
                  decoration: InputDecoration(
                    hintText: l10n.thoughtCapsuleHint,
                    border: const OutlineInputBorder(
                      borderRadius: DS.borderRadius12,
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: DS.borderRadius12,
                      borderSide: BorderSide(color: DS.primaryBase, width: 2),
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing24),
                if (stackActions) ...[
                  SizedBox(
                    width: double.infinity,
                    child: CustomButton.primary(
                      text: l10n.send,
                      icon: Icons.send_rounded,
                      onPressed: _isSubmitting ? null : _submit,
                      isLoading: _isSubmitting,
                      size: CustomButtonSize.small,
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  SizedBox(
                    width: double.infinity,
                    child: SparkleButton.ghost(
                      label: l10n.cancel,
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  ),
                ] else
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      SparkleButton.ghost(
                        label: l10n.cancel,
                        onPressed: () => Navigator.of(context).pop(),
                      ),
                      const SizedBox(width: DS.spacing12),
                      CustomButton.primary(
                        text: l10n.send,
                        icon: Icons.send_rounded,
                        onPressed: _isSubmitting ? null : _submit,
                        isLoading: _isSubmitting,
                        size: CustomButtonSize.small,
                      ),
                    ],
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
