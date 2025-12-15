import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/presentation/widgets/custom_button.dart';

class ActionCard extends StatefulWidget {
  final ChatAction action;
  final VoidCallback? onConfirm;
  final VoidCallback? onDismiss;

  const ActionCard({
    required this.action, 
    super.key,
    this.onConfirm,
    this.onDismiss,
  });

  @override
  State<ActionCard> createState() => _ActionCardState();
}

class _ActionCardState extends State<ActionCard> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    
    _scaleAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: AppDesignTokens.borderRadius12,
        boxShadow: AppDesignTokens.shadowMd,
        border: const Border(
          left: BorderSide(
            width: 4,
            color: Colors.transparent, // Handled by gradient container behind or clipper? 
            // Simpler: Use a Stack or Row for the colored stripe.
          ),
        ),
      ),
      child: ClipRRect(
        borderRadius: AppDesignTokens.borderRadius12,
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
            
            Padding(
              padding: const EdgeInsets.all(AppDesignTokens.spacing16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      AnimatedBuilder(
                        animation: _scaleAnimation,
                        builder: (context, child) {
                          return Transform.scale(
                            scale: _scaleAnimation.value,
                            child: Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                gradient: _getActionGradient(widget.action.type),
                                shape: BoxShape.circle,
                                boxShadow: AppDesignTokens.shadowSm,
                              ),
                              child: Icon(
                                _getActionIcon(widget.action.type),
                                color: Colors.white,
                                size: 16,
                              ),
                            ),
                          );
                        },
                      ),
                      const SizedBox(width: AppDesignTokens.spacing12),
                      Text(
                        _getTitleForAction(widget.action.type),
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: AppDesignTokens.fontWeightBold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppDesignTokens.spacing16),
                  _buildContentForAction(context, widget.action),
                  const SizedBox(height: AppDesignTokens.spacing16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (widget.onDismiss != null)
                        TextButton(
                          onPressed: widget.onDismiss,
                          child: Text(
                            'Dismiss',
                            style: TextStyle(color: AppDesignTokens.neutral600),
                          ),
                        ),
                      const SizedBox(width: 8),
                      if (widget.onConfirm != null)
                        CustomButton(
                          text: 'Confirm',
                          icon: Icons.check,
                          variant: CustomButtonVariant.primary,
                          onPressed: widget.onConfirm,
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
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
      default:
        return AppDesignTokens.primaryGradient;
    }
  }

  IconData _getActionIcon(String type) {
    switch (type) {
      case 'create_task':
        return Icons.add_task;
      case 'create_plan':
        return Icons.map;
      default:
        return Icons.touch_app;
    }
  }

  String _getTitleForAction(String type) {
    switch (type) {
      case 'create_task':
        return 'New Task Suggestion';
      case 'create_plan':
        return 'New Plan Suggestion';
      default:
        return 'Suggested Action';
    }
  }

  Widget _buildContentForAction(BuildContext context, ChatAction action) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (action.params['title'] != null)
          Text(
            action.params['title'],
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.bold),
          ),
        const SizedBox(height: AppDesignTokens.spacing8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: action.params.entries.where((e) => e.key != 'title').map((entry) {
            return Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: AppDesignTokens.neutral50,
                borderRadius: AppDesignTokens.borderRadius8,
                border: Border.all(color: AppDesignTokens.neutral200),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '${entry.key}: ',
                    style: TextStyle(color: AppDesignTokens.neutral600, fontSize: 12),
                  ),
                  Text(
                    entry.value.toString(),
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}