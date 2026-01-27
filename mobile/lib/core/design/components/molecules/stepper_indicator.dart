import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';

/// 步骤指示器组件（垂直时间线 + 动画）
class StepperIndicator extends StatefulWidget {
  const StepperIndicator({
    required this.steps,
    required this.currentStepIndex,
    super.key,
  });

  final List<TransparencyStep> steps;
  final int currentStepIndex;

  @override
  State<StepperIndicator> createState() => _StepperIndicatorState();
}

class _StepperIndicatorState extends State<StepperIndicator>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
  }

  @override
  void didUpdateWidget(StepperIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.currentStepIndex != widget.currentStepIndex) {
      _pulseController.reset();
      _pulseController.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < widget.steps.length; i++) ...[
          _buildStepItem(widget.steps[i], i),
          if (i < widget.steps.length - 1) _buildConnector(i),
        ],
      ],
    );

  Widget _buildStepItem(TransparencyStep step, int index) {
    final isCurrent = index == widget.currentStepIndex;
    final isCompleted = index < widget.currentStepIndex;

    Color iconColor;
    IconData iconData;
    if (step.status == 'failed') {
      iconColor = DS.error;
      iconData = Icons.error_rounded;
    } else if (isCompleted) {
      iconColor = DS.success;
      iconData = Icons.check_circle_rounded;
    } else if (isCurrent) {
      iconColor = DS.primaryBase;
      iconData = Icons.adjust_rounded;
    } else {
      iconColor = DS.neutral300;
      iconData = Icons.circle_outlined;
    }

    Widget iconWidget = Icon(iconData, color: iconColor, size: 18);

    // 当前步骤添加脉冲动画
    if (isCurrent && step.status != 'failed') {
      iconWidget = AnimatedBuilder(
        animation: _pulseController,
        builder: (context, child) => Transform.scale(
            scale: 1.0 + (_pulseController.value * 0.15),
            child: DecoratedBox(
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: DS.primaryBase.withValues(alpha: 0.4 * _pulseController.value),
                    blurRadius: 8 * _pulseController.value,
                    spreadRadius: 2 * _pulseController.value,
                  ),
                ],
              ),
              child: child,
            ),
          ),
        child: iconWidget,
      );
    }

    // 渐入滑动动画
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
      builder: (context, value, child) => Opacity(
          opacity: value,
          child: Transform.translate(
            offset: const Offset(0, 10) * (1 - value),
            child: child,
          ),
        ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 左侧图标和时间线
          SizedBox(
            width: 32,
            child: Column(
              children: [
                iconWidget,
                if (index < widget.steps.length - 1)
                  Container(
                    width: 2,
                    height: 24,
                    margin: const EdgeInsets.only(top: 4),
                    color: isCompleted
                        ? DS.primaryBase.withValues(alpha: 0.3)
                        : DS.neutral200,
                  ),
              ],
            ),
          ),
          const SizedBox(width: DS.spacing12),
          // 右侧步骤详情
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  step.name,
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    fontWeight: isCurrent ? DS.fontWeightSemibold : DS.fontWeightRegular,
                    color: step.status == 'failed' ? DS.error : DS.textPrimary,
                  ),
                ),
                if (step.formattedDuration != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    step.formattedDuration!,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.neutral500,
                    ),
                  ),
                ],
                if (isCurrent && step.status == 'in_progress') ...[
                  const SizedBox(height: 4),
                  _buildPulsingBar(),
                ],
                if (step.status == 'failed' && step.error != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    step.error!,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.error,
                    ),
                  ),
                ],
                // 步骤结果详情（如果有）
                if (step.result != null && step.result!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  _buildStepResultDetails(step.result!),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  /// 当前步骤的进度条动画
  Widget _buildPulsingBar() => AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) => Container(
          height: 3,
          decoration: BoxDecoration(
            borderRadius: DS.borderRadius20,
            color: DS.neutral200,
          ),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: 0.3 + (_pulseController.value * 0.7),
            child: Container(
              decoration: BoxDecoration(
                borderRadius: DS.borderRadius20,
                color: DS.primaryBase,
              ),
            ),
          ),
        ),
    );

  /// 步骤结果详情（可展示如检索到的知识数量、生成的token数等）
  Widget _buildStepResultDetails(Map<String, dynamic> result) => Container(
      padding: const EdgeInsets.all(DS.spacing8),
      decoration: BoxDecoration(
        color: DS.neutral100,
        borderRadius: DS.borderRadius8,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: result.entries.map((e) => Padding(
            padding: const EdgeInsets.only(bottom: 2),
            child: Row(
              children: [
                Text(
                  '${e.key}: ',
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.neutral600,
                  ),
                ),
                Expanded(
                  child: Text(
                    e.value.toString(),
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
          )).toList(),
      ),
    );

  Widget _buildConnector(int index) {
    final isCompleted = index < widget.currentStepIndex;
    return Container(
      width: 2,
      height: 24,
      margin: const EdgeInsets.only(left: 15),
      color: isCompleted
          ? DS.primaryBase.withValues(alpha: 0.3)
          : DS.neutral200,
    );
  }
}
