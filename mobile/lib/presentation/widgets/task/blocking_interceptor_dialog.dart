import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class BlockingInterceptorDialog extends ConsumerStatefulWidget {

  const BlockingInterceptorDialog({
    required this.taskId, required this.onAbandonConfirmed, super.key,
  });
  final String taskId;
  final VoidCallback onAbandonConfirmed;

  @override
  ConsumerState<BlockingInterceptorDialog> createState() => _BlockingInterceptorDialogState();
}

class _BlockingInterceptorDialogState extends ConsumerState<BlockingInterceptorDialog> {
  final TextEditingController _controller = TextEditingController();
  String? _selectedReason;
  bool _isSubmitting = false;

  final List<String> _reasons = [
    '高估了自己的效率',
    '中途被消息打断',
    '追求完美导致卡壳',
    '任务太难不知道怎么做',
    '心情不好不想做',
  ];

  Future<void> _submit() async {
    final content = _selectedReason ?? _controller.text.trim();
    if (content.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请选择原因或输入想法')),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      // 1. Record Cognitive Fragment
      await ref.read(cognitiveProvider.notifier).createFragment(
        content: content,
        sourceType: 'interceptor',
        taskId: widget.taskId,
      );

      // 2. Abandon Task (Handled by callback or here? Callback usually just closes UI or triggers repo)
      // The parent usually calls abandonTask API.
      // But we want to record fragment BEFORE abandoning? Or in parallel?
      // Let's assume onAbandonConfirmed handles the actual task abandonment.
      
      widget.onAbandonConfirmed();
      
      if (mounted) {
        Navigator.of(context).pop(); // Close dialog
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('提交失败: $e'), backgroundColor: AppDesignTokens.error),
        );
        setState(() => _isSubmitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) => Dialog(
      shape: RoundedRectangleBorder(borderRadius: AppDesignTokens.borderRadius20),
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
                    decoration: BoxDecoration(
                      color: AppDesignTokens.warning.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.block, color: AppDesignTokens.warning),
                  ),
                  const SizedBox(width: AppDesignTokens.spacing12),
                  Expanded(
                    child: Text(
                      '遇到阻碍了吗？',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: AppDesignTokens.fontWeightBold,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppDesignTokens.spacing16),
              Text(
                '记录下原因，AI 会帮你分析行为定式，下次做得更好。',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppDesignTokens.neutral600,
                ),
              ),
              const SizedBox(height: AppDesignTokens.spacing20),
              
              // Preset Options
              ..._reasons.map((reason) => RadioListTile<String>(
                title: Text(reason),
                value: reason,
                groupValue: _selectedReason,
                onChanged: (value) => setState(() => _selectedReason = value),
                contentPadding: EdgeInsets.zero,
                activeColor: AppDesignTokens.primaryBase,
              ),),

              // Other/Custom Input
              RadioListTile<String>(
                title: const Text('其他原因...'),
                value: 'other',
                groupValue: _selectedReason == null || !_reasons.contains(_selectedReason) ? 'other' : null,
                onChanged: (value) => setState(() => _selectedReason = 'other'), // Hacky handling
                contentPadding: EdgeInsets.zero,
                activeColor: AppDesignTokens.primaryBase,
              ),
              
              if (_selectedReason == 'other')
                TextField(
                  controller: _controller,
                  decoration: const InputDecoration(
                    hintText: '请输入具体原因',
                    isDense: true,
                  ),
                ),

              const SizedBox(height: AppDesignTokens.spacing24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  SparkleButton.ghost(label: '取消', onPressed: () => Navigator.of(context).pop()),
                  const SizedBox(width: AppDesignTokens.spacing12),
                  CustomButton.primary(
                    text: '确认放弃',
                    icon: Icons.check,
                    onPressed: _isSubmitting ? () {} : _submit,
                    isLoading: _isSubmitting,
                    size: CustomButtonSize.small,
                    customGradient: AppDesignTokens.warningGradient, // Orange/Red warning
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
}
