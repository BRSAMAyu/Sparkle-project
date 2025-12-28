import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/design/motion.dart';

/// 计划卡片组件
/// 用于在聊天中显示 AI 生成的计划
class PlanCard extends StatefulWidget {

  const PlanCard({
    required this.data, super.key,
  });
  final Map<String, dynamic> data;

  @override
  State<PlanCard> createState() => _PlanCardState();
}

class _PlanCardState extends State<PlanCard> with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: SparkleMotion.fast,
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _handleTap() {
    HapticFeedback.selectionClick();
    final planType = widget.data['type'] as String;
    if (planType == 'sprint') {
      context.push('/sprint');
    } else if (planType == 'growth') {
      context.push('/growth');
    }
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.data['title'] as String;
    final planType = widget.data['type'] as String;
    final description = widget.data['description'] as String?;
    final targetDate = widget.data['target_date'] as String?;
    final mastery = (widget.data['target_mastery'] as num?)?.toDouble();

    return SparkleMotion.pressScale(
      animation: _controller,
      child: GestureDetector(
        onTapDown: (_) => _controller.forward(),
        onTapUp: (_) => _controller.reverse(),
        onTapCancel: () => _controller.reverse(),
        onTap: _handleTap,
        child: Card(
          margin: const EdgeInsets.symmetric(vertical: 8),
          elevation: 2,
          // Remove InkWell as we handle taps on GestureDetector
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    _buildTypeIcon(planType),
                    const SizedBox(width: DS.sm),
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    _buildPlanTypeChip(context, planType),
                  ],
                ),
                
                if (description != null && description.isNotEmpty) ...[
                  const SizedBox(height: DS.sm),
                  Text(
                    description,
                    style: Theme.of(context).textTheme.bodyMedium,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],

                const SizedBox(height: DS.md),
                Row(
                  children: [
                    if (targetDate != null) ...[
                      Icon(Icons.calendar_today,
                        size: AppDesignTokens.iconSizeSm,
                        color: Theme.of(context).hintColor,),
                      const SizedBox(width: AppDesignTokens.spacing4),
                      Text('目标日期: $targetDate'),
                      const SizedBox(width: AppDesignTokens.spacing16),
                    ],
                    if (mastery != null) ...[
                      Icon(Icons.grade,
                        size: AppDesignTokens.iconSizeSm,
                        color: Theme.of(context).hintColor,),
                      const SizedBox(width: AppDesignTokens.spacing4),
                      Text('目标掌握度: ${(mastery * 100).toInt()}%'),
                    ],
                    const Spacer(),
                    // Just a visual indicator now - not interactive so smaller is acceptable
                    const Icon(Icons.arrow_forward_ios,
                      size: AppDesignTokens.iconSizeXs,
                      color: AppDesignTokens.neutral400,),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTypeIcon(String type) {
    IconData icon;
    Color color;

    switch (type) {
      case 'sprint':
        icon = Icons.directions_run;
        color = AppDesignTokens.warning;
      case 'growth':
        icon = Icons.trending_up;
        color = AppDesignTokens.success;
      default:
        icon = Icons.assignment;
        color = AppDesignTokens.neutral500;
    }

    // Ensure minimum 48x48 touch target
    return Container(
      width: AppDesignTokens.touchTargetMinSize,
      height: AppDesignTokens.touchTargetMinSize,
      padding: const EdgeInsets.all(AppDesignTokens.spacing8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: AppDesignTokens.borderRadius8,
      ),
      child: Icon(icon, size: AppDesignTokens.iconSizeBase, color: color),
    );
  }

  Widget _buildPlanTypeChip(BuildContext context, String type) {
    final color = context.colors.getPlanColor(type);
    final label = type == 'sprint' ? '冲刺计划' : type == 'growth' ? '成长计划' : type;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppDesignTokens.spacing8,
        vertical: AppDesignTokens.spacing4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: AppDesignTokens.borderRadius12,
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: AppDesignTokens.fontSizeXs,
        ),
      ),
    );
  }
}