import 'package:flutter/material.dart';

/// 复习性能评价按钮组
///
/// 用于复习页面，让用户评价自己对错题的掌握情况
/// 三个选项：记住了(remembered)、有点模糊(fuzzy)、忘记了(forgotten)
class ReviewPerformanceButtons extends StatelessWidget {

  const ReviewPerformanceButtons({
    super.key,
    required this.onPerformanceSelected,
    this.isLoading = false,
  });
  final Function(String performance) onPerformanceSelected;
  final bool isLoading;

  @override
  Widget build(BuildContext context) => Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          '你对这道题的掌握情况？',
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: _PerformanceButton(
                performance: 'forgotten',
                label: '忘记了',
                icon: Icons.close,
                color: Colors.red,
                description: '下次会提前复习',
                isLoading: isLoading,
                onTap: () => onPerformanceSelected('forgotten'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _PerformanceButton(
                performance: 'fuzzy',
                label: '有点模糊',
                icon: Icons.remove,
                color: Colors.orange,
                description: '保持复习间隔',
                isLoading: isLoading,
                onTap: () => onPerformanceSelected('fuzzy'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _PerformanceButton(
                performance: 'remembered',
                label: '记住了',
                icon: Icons.check,
                color: Colors.green,
                description: '延长复习间隔',
                isLoading: isLoading,
                onTap: () => onPerformanceSelected('remembered'),
              ),
            ),
          ],
        ),
      ],
    );
}

class _PerformanceButton extends StatelessWidget {

  const _PerformanceButton({
    required this.performance,
    required this.label,
    required this.icon,
    required this.color,
    required this.description,
    required this.isLoading,
    required this.onTap,
  });
  final String performance;
  final String label;
  final IconData icon;
  final Color color;
  final String description;
  final bool isLoading;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: color.withOpacity(0.1),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: isLoading ? null : onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
          decoration: BoxDecoration(
            border: Border.all(color: color.withOpacity(0.3)),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Icon(
                icon,
                color: color,
                size: 32,
              ),
              const SizedBox(height: 8),
              Text(
                label,
                style: theme.textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: color,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: color.withOpacity(0.8),
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 复习性能选择对话框（备选方案）
///
/// 可以作为底部弹窗使用，提供更详细的说明
class ReviewPerformanceBottomSheet extends StatelessWidget {

  const ReviewPerformanceBottomSheet({
    super.key,
    required this.onPerformanceSelected,
  });
  final Function(String performance) onPerformanceSelected;

  static Future<String?> show(BuildContext context) => showModalBottomSheet<String>(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => ReviewPerformanceBottomSheet(
        onPerformanceSelected: (performance) {
          Navigator.of(context).pop(performance);
        },
      ),
    );

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '评价你的掌握情况',
              style: theme.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              '根据你的评价，系统会智能调整下次复习时间',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),
            _PerformanceOption(
              performance: 'remembered',
              label: '完全记住了 ✓',
              description: '能准确回忆并理解解题思路',
              color: Colors.green,
              onTap: () => onPerformanceSelected('remembered'),
            ),
            const SizedBox(height: 12),
            _PerformanceOption(
              performance: 'fuzzy',
              label: '有点模糊 ≈',
              description: '大致记得，但细节不够清晰',
              color: Colors.orange,
              onTap: () => onPerformanceSelected('fuzzy'),
            ),
            const SizedBox(height: 12),
            _PerformanceOption(
              performance: 'forgotten',
              label: '完全忘记了 ✗',
              description: '想不起来或记错了',
              color: Colors.red,
              onTap: () => onPerformanceSelected('forgotten'),
            ),
            const SizedBox(height: 16),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('取消'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PerformanceOption extends StatelessWidget {

  const _PerformanceOption({
    required this.performance,
    required this.label,
    required this.description,
    required this.color,
    required this.onTap,
  });
  final String performance;
  final String label;
  final String description;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Material(
      color: color.withOpacity(0.1),
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border.all(color: color.withOpacity(0.3), width: 2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _getIcon(performance),
                  color: color,
                  size: 28,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: color,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      description,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: color,
              ),
            ],
          ),
        ),
      ),
    );
  }

  IconData _getIcon(String performance) {
    switch (performance) {
      case 'remembered':
        return Icons.check_circle;
      case 'fuzzy':
        return Icons.help;
      case 'forgotten':
        return Icons.cancel;
      default:
        return Icons.help;
    }
  }
}
