import 'dart:async';

import 'package:flutter/material.dart';

/// Agent 状态枚举
///
/// 对应后端 orchestrator 的状态
enum AgentStatus {
  idle('idle', '空闲', Icons.check_circle_outline),
  thinking('thinking', '思考中', Icons.psychology),
  searching('searching', '搜索中', Icons.search),
  executingTool('executing_tool', '执行操作中', Icons.build_circle),
  generating('generating', '正在输入', Icons.edit_note),
  error('error', '出错了', Icons.error_outline);

  const AgentStatus(this.code, this.label, this.icon);

  final String code;
  final String label;
  final IconData icon;

  static AgentStatus fromCode(String code) => AgentStatus.values.firstWhere(
        (status) => status.code == code,
        orElse: () => AgentStatus.idle,
      );
}

/// Agent 状态指示器
///
/// 设计原则：
/// 1. 简洁明了：小巧的标签，不干扰对话
/// 2. 动画流畅：旋转动画表示正在处理
/// 3. 颜色区分：不同状态用不同颜色
class AgentStatusIndicator extends StatelessWidget {
  const AgentStatusIndicator({
    required this.status,
    super.key,
    this.compact = false,
  });
  final AgentStatus status;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    // 空闲状态不显示
    if (status == AgentStatus.idle) {
      return const SizedBox.shrink();
    }

    final theme = Theme.of(context);
    final color = _getStatusColor(status, theme);

    if (compact) {
      return _buildCompactIndicator(theme, color);
    }

    return _buildFullIndicator(theme, color);
  }

  Widget _buildFullIndicator(ThemeData theme, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: color.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            _AnimatedIcon(
              icon: status.icon,
              color: color,
              size: 16,
            ),
            const SizedBox(width: 6),
            Text(
              status.label,
              style: theme.textTheme.labelMedium?.copyWith(
                color: color,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );

  Widget _buildCompactIndicator(ThemeData theme, Color color) => Tooltip(
        message: status.label,
        child: Container(
          width: 24,
          height: 24,
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            shape: BoxShape.circle,
            border: Border.all(
              color: color.withValues(alpha: 0.3),
              width: 1.5,
            ),
          ),
          child: _AnimatedIcon(
            icon: status.icon,
            color: color,
            size: 14,
          ),
        ),
      );

  Color _getStatusColor(AgentStatus status, ThemeData theme) {
    switch (status) {
      case AgentStatus.thinking:
        return theme.colorScheme.primary;
      case AgentStatus.searching:
        return Colors.blue;
      case AgentStatus.executingTool:
        return Colors.orange;
      case AgentStatus.generating:
        return Colors.green;
      case AgentStatus.error:
        return theme.colorScheme.error;
      case AgentStatus.idle:
        return theme.colorScheme.onSurfaceVariant;
    }
  }
}

/// 带动画的图标
///
/// 根据状态决定是否显示旋转动画
class _AnimatedIcon extends StatefulWidget {
  const _AnimatedIcon({
    required this.icon,
    required this.color,
    required this.size,
  });
  final IconData icon;
  final Color color;
  final double size;

  @override
  State<_AnimatedIcon> createState() => _AnimatedIconState();
}

class _AnimatedIconState extends State<_AnimatedIcon>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    unawaited(_controller.repeat());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => RotationTransition(
        turns: _controller,
        child: Icon(
          widget.icon,
          size: widget.size,
          color: widget.color,
        ),
      );
}

/// Agent 状态流式指示器（用于聊天气泡）
///
/// 在 AI 回复前显示，表示 AI 正在处理
class AgentTypingIndicator extends StatefulWidget {
  const AgentTypingIndicator({
    super.key,
    this.statusText,
  });
  final String? statusText;

  @override
  State<AgentTypingIndicator> createState() => _AgentTypingIndicatorState();
}

class _AgentTypingIndicatorState extends State<AgentTypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1400),
      vsync: this,
    );
    unawaited(_controller.repeat());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildDot(0),
          const SizedBox(width: 4),
          _buildDot(1),
          const SizedBox(width: 4),
          _buildDot(2),
          if (widget.statusText != null) ...[
            const SizedBox(width: 12),
            Text(
              widget.statusText!,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDot(int index) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) {
          final value = (_controller.value + index * 0.33) % 1.0;
          final opacity = (1 - (value - 0.5).abs() * 2).clamp(0.3, 1.0);
          final scale =
              0.6 + (1 - (value - 0.5).abs() * 2).clamp(0.0, 1.0) * 0.4;

          return Transform.scale(
            scale: scale,
            child: Opacity(
              opacity: opacity,
              child: Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.primary,
                  shape: BoxShape.circle,
                ),
              ),
            ),
          );
        },
      );
}

/// Agent 状态变化监听器
///
/// 包装在聊天界面外层，监听状态变化并显示指示器
class AgentStatusListener extends StatelessWidget {
  const AgentStatusListener({
    required this.status,
    required this.child,
    super.key,
    this.showIndicator = true,
  });
  final AgentStatus status;
  final Widget child;
  final bool showIndicator;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          if (showIndicator && status != AgentStatus.idle)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: AgentStatusIndicator(status: status),
            ),
          Expanded(child: child),
        ],
      );
}
