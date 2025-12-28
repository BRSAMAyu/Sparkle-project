import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/design/motion.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class ActionCard extends StatefulWidget {

  const ActionCard({
    required this.action, 
    super.key,
    this.onConfirm,
    this.onDismiss,
  });
  final WidgetPayload action;
  final VoidCallback? onConfirm;
  final VoidCallback? onDismiss;

  @override
  State<ActionCard> createState() => _ActionCardState();
}

class _ActionCardState extends State<ActionCard> with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _iconScaleAnimation;
  late AnimationController _pressController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    
    _iconScaleAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _pressController = AnimationController(
      vsync: this,
      duration: SparkleMotion.fast,
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _pressController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final hasAction = widget.onConfirm != null || widget.onDismiss != null;

    return GestureDetector(
      onTapDown: hasAction ? (_) => _pressController.forward() : null,
      onTapUp: hasAction ? (_) => _pressController.reverse() : null,
      onTapCancel: hasAction ? () => _pressController.reverse() : null,
      onTap: hasAction ? HapticFeedback.selectionClick : null,
      child: SparkleMotion.pressScale(
        animation: _pressController,
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: context.colors.surfaceCard,
            borderRadius: AppDesignTokens.borderRadius16,
            boxShadow: AppDesignTokens.shadowMd,
          ),
          child: ClipRRect(
            borderRadius: AppDesignTokens.borderRadius16,
            child: Stack(
              children: [
                // Gradient Stripe
                Positioned(
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: 4,
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: _getActionGradient(widget.action.type),
                    ),
                  ),
                ),

                // Shimmer overlay for unconfirmed actions
                if (hasAction)
                  Positioned.fill(
                    child: TweenAnimationBuilder<double>(
                      tween: Tween(begin: -2.0, end: 2.0),
                      duration: const Duration(seconds: 3),
                      builder: (context, value, child) => Container(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Colors.transparent,
                                DS.brandPrimary.withValues(alpha: 0.1),
                                Colors.transparent,
                              ],
                              stops: [
                                (value - 0.3).clamp(0.0, 1.0),
                                value.clamp(0.0, 1.0),
                                (value + 0.3).clamp(0.0, 1.0),
                              ],
                            ),
                          ),
                        ),
                      onEnd: () {
                        // Restart animation
                        if (mounted) setState(() {});
                      },
                    ),
                  ),

                Padding(
                  padding: const EdgeInsets.all(AppDesignTokens.spacing16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          AnimatedBuilder(
                            animation: _iconScaleAnimation,
                            builder: (context, child) => Transform.scale(
                                scale: hasAction ? _iconScaleAnimation.value : 1.0,
                                child: Container(
                                  padding: const EdgeInsets.all(AppDesignTokens.spacing8),
                                  decoration: BoxDecoration(
                                    gradient: _getActionGradient(widget.action.type),
                                    shape: BoxShape.circle,
                                    boxShadow: [
                                      BoxShadow(
                                        color: _getActionColor(widget.action.type).withValues(alpha: 0.3),
                                        blurRadius: 8,
                                        offset: const Offset(0, 2),
                                      ),
                                    ],
                                  ),
                                  child: Icon(
                                    _getActionIcon(widget.action.type),
                                    color: DS.brandPrimary,
                                    size: AppDesignTokens.iconSizeSm,
                                  ),
                                ),
                              ),
                          ),
                          const SizedBox(width: AppDesignTokens.spacing12),
                          Expanded(
                            child: Text(
                              _getTitleForAction(widget.action.type),
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                fontWeight: AppDesignTokens.fontWeightBold,
                                color: AppDesignTokens.neutral900,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppDesignTokens.spacing16),
                      _buildContentForAction(context, widget.action),
                      if (hasAction) ...[
                        const SizedBox(height: AppDesignTokens.spacing16),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            if (widget.onDismiss != null)
                              CustomButton.text(
                                text: '忽略',
                                onPressed: widget.onDismiss,
                                size: ButtonSize.small,
                              ),
                            const SizedBox(width: AppDesignTokens.spacing8),
                            if (widget.onConfirm != null)
                              CustomButton.primary(
                                text: '确认',
                                icon: Icons.check_rounded,
                                onPressed: widget.onConfirm,
                                size: ButtonSize.small,
                                customGradient: _getActionGradient(widget.action.type),
                              ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  LinearGradient _getActionGradient(String type) {
    switch (type) {
      case 'create_task':
        return AppDesignTokens.primaryGradient;
      case 'create_plan':
        return AppDesignTokens.secondaryGradient;
      case 'update_preference':
        return AppDesignTokens.infoGradient;
      case 'add_error':
        return AppDesignTokens.warningGradient;
      default:
        return AppDesignTokens.primaryGradient;
    }
  }

  Color _getActionColor(String type) {
    switch (type) {
      case 'create_task':
        return AppDesignTokens.primaryBase;
      case 'create_plan':
        return AppDesignTokens.secondaryBase;
      case 'update_preference':
        return AppDesignTokens.info;
      case 'add_error':
        return AppDesignTokens.warning;
      default:
        return AppDesignTokens.primaryBase;
    }
  }

  IconData _getActionIcon(String type) {
    switch (type) {
      case 'create_task':
        return Icons.add_task_rounded;
      case 'create_plan':
        return Icons.map_rounded;
      case 'update_preference':
        return Icons.settings_rounded;
      case 'add_error':
        return Icons.error_outline_rounded;
      default:
        return Icons.touch_app_rounded;
    }
  }

  String _getTitleForAction(String type) {
    switch (type) {
      case 'create_task':
        return 'AI建议：创建任务';
      case 'create_plan':
        return 'AI建议：创建计划';
      case 'update_preference':
        return 'AI建议：更新偏好';
      case 'add_error':
        return 'AI建议：记录错题';
      default:
        return 'AI建议操作';
    }
  }

  Widget _buildContentForAction(BuildContext context, WidgetPayload action) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (action.data['title'] != null) ...[
          Container(
            padding: const EdgeInsets.all(AppDesignTokens.spacing12),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  _getActionColor(action.type).withValues(alpha: 0.1),
                  _getActionColor(action.type).withValues(alpha: 0.05),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: AppDesignTokens.borderRadius12,
              border: Border.all(
                color: _getActionColor(action.type).withValues(alpha: 0.2),
              ),
            ),
            child: Text(
              action.data['title'],
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                fontWeight: AppDesignTokens.fontWeightSemibold,
                color: AppDesignTokens.neutral900,
              ),
            ),
          ),
          const SizedBox(height: AppDesignTokens.spacing12),
        ],
        if (action.data.entries.where((e) => e.key != 'title').isNotEmpty)
          Wrap(
            spacing: AppDesignTokens.spacing8,
            runSpacing: AppDesignTokens.spacing8,
            children: action.data.entries
                .where((e) => e.key != 'title')
                .map((entry) => Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppDesignTokens.spacing12,
                  vertical: AppDesignTokens.spacing8,
                ),
                decoration: BoxDecoration(
                  color: AppDesignTokens.neutral100,
                  borderRadius: AppDesignTokens.borderRadius8,
                  border: Border.all(color: AppDesignTokens.neutral200),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _getParamIcon(entry.key),
                      size: AppDesignTokens.iconSizeXs,
                      color: AppDesignTokens.neutral600,
                    ),
                    const SizedBox(width: AppDesignTokens.spacing4),
                    Text(
                      '${_formatParamKey(entry.key)}: ',
                      style: const TextStyle(
                        color: AppDesignTokens.neutral600,
                        fontSize: AppDesignTokens.fontSizeSm,
                      ),
                    ),
                    Text(
                      entry.value.toString(),
                      style: const TextStyle(
                        fontWeight: AppDesignTokens.fontWeightSemibold,
                        fontSize: AppDesignTokens.fontSizeSm,
                        color: AppDesignTokens.neutral900,
                      ),
                    ),
                  ],
                ),
              ),).toList(),
          ),
      ],
    );

  IconData _getParamIcon(String key) {
    switch (key.toLowerCase()) {
      case 'type':
      case 'task_type':
        return Icons.category_rounded;
      case 'difficulty':
        return Icons.stars_rounded;
      case 'estimated_minutes':
      case 'duration':
        return Icons.timer_rounded;
      case 'subject':
        return Icons.book_rounded;
      case 'due_date':
      case 'target_date':
        return Icons.calendar_today_rounded;
      default:
        return Icons.label_rounded;
    }
  }

  String _formatParamKey(String key) {
    // Convert snake_case to readable format
    return key
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }
}