import 'package:flutter/material.dart';
import 'dart:math' as math;

/// 多智能体头像堆叠组件
///
/// 显示多个协作智能体的头像，带有动画转换效果
class AgentAvatarStack extends StatefulWidget {
  /// 当前活跃的智能体
  final List<AgentInfo> activeAgents;

  /// 头像大小
  final double size;

  /// 是否显示动画
  final bool animate;

  const AgentAvatarStack({
    super.key,
    required this.activeAgents,
    this.size = 40,
    this.animate = true,
  });

  @override
  State<AgentAvatarStack> createState() => _AgentAvatarStackState();
}

class _AgentAvatarStackState extends State<AgentAvatarStack>
    with TickerProviderStateMixin {
  late AnimationController _transitionController;

  @override
  void initState() {
    super.initState();

    _transitionController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );

    if (widget.animate) {
      _transitionController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(AgentAvatarStack oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (widget.activeAgents != oldWidget.activeAgents && widget.animate) {
      _transitionController.forward(from: 0);
    }
  }

  @override
  void dispose() {
    _transitionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.activeAgents.isEmpty) {
      return const SizedBox.shrink();
    }

    return SizedBox(
      height: widget.size,
      width: _calculateWidth(),
      child: Stack(
        children: _buildAvatarStack(),
      ),
    );
  }

  double _calculateWidth() {
    // 每个头像重叠 1/3
    final overlap = widget.size * 0.33;
    return widget.size + (widget.activeAgents.length - 1) * overlap;
  }

  List<Widget> _buildAvatarStack() {
    final widgets = <Widget>[];
    final overlap = widget.size * 0.33;

    for (int i = 0; i < widget.activeAgents.length; i++) {
      final agent = widget.activeAgents[i];
      final left = i * overlap;

      widgets.add(
        Positioned(
          left: left,
          child: AnimatedBuilder(
            animation: _transitionController,
            builder: (context, child) {
              // 最后一个头像有脉冲效果（表示当前活跃）
              final isActive = i == widget.activeAgents.length - 1;
              final scale = isActive
                  ? 1.0 + _transitionController.value * 0.1
                  : 1.0;

              return Transform.scale(
                scale: scale,
                child: child,
              );
            },
            child: _buildAvatar(agent),
          ),
        ),
      );
    }

    return widgets;
  }

  Widget _buildAvatar(AgentInfo agent) {
    return Container(
      width: widget.size,
      height: widget.size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: agent.color,
        border: Border.all(
          color: Colors.white,
          width: 2,
        ),
        boxShadow: [
          BoxShadow(
            color: agent.color.withOpacity(0.5),
            blurRadius: 8,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Center(
        child: Icon(
          agent.icon,
          color: Colors.white,
          size: widget.size * 0.5,
        ),
      ),
    );
  }
}

/// 智能体信息
class AgentInfo {
  final String type;
  final String name;
  final IconData icon;
  final Color color;

  AgentInfo({
    required this.type,
    required this.name,
    required this.icon,
    required this.color,
  });

  factory AgentInfo.fromType(String type) {
    switch (type.toLowerCase()) {
      case 'math':
        return AgentInfo(
          type: 'math',
          name: 'Math Expert',
          icon: Icons.functions,
          color: Colors.blue.shade600,
        );
      case 'code':
        return AgentInfo(
          type: 'code',
          name: 'Code Expert',
          icon: Icons.code,
          color: Colors.green.shade600,
        );
      case 'writing':
        return AgentInfo(
          type: 'writing',
          name: 'Writing Expert',
          icon: Icons.edit,
          color: Colors.orange.shade600,
        );
      case 'science':
        return AgentInfo(
          type: 'science',
          name: 'Science Expert',
          icon: Icons.science,
          color: Colors.purple.shade600,
        );
      case 'orchestrator':
      default:
        return AgentInfo(
          type: 'orchestrator',
          name: 'Orchestrator',
          icon: Icons.hub,
          color: Colors.grey.shade700,
        );
    }
  }
}

/// 智能体转换动画组件
///
/// 显示智能体之间的"接力"动画
class AgentHandoffAnimation extends StatefulWidget {
  /// 发起智能体
  final AgentInfo fromAgent;

  /// 目标智能体
  final AgentInfo toAgent;

  /// 动画完成回调
  final VoidCallback? onComplete;

  const AgentHandoffAnimation({
    super.key,
    required this.fromAgent,
    required this.toAgent,
    this.onComplete,
  });

  @override
  State<AgentHandoffAnimation> createState() => _AgentHandoffAnimationState();
}

class _AgentHandoffAnimationState extends State<AgentHandoffAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _curveAnimation;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    _curveAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeInOut,
    );

    _controller.forward().then((_) {
      widget.onComplete?.call();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _curveAnimation,
      builder: (context, child) {
        return CustomPaint(
          size: Size(200, 100),
          painter: _HandoffPainter(
            progress: _curveAnimation.value,
            fromColor: widget.fromAgent.color,
            toColor: widget.toAgent.color,
          ),
        );
      },
    );
  }
}

/// 接力动画绘制器
class _HandoffPainter extends CustomPainter {
  final double progress;
  final Color fromColor;
  final Color toColor;

  _HandoffPainter({
    required this.progress,
    required this.fromColor,
    required this.toColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final startX = size.width * 0.2;
    final endX = size.width * 0.8;
    final centerY = size.height / 2;

    // 绘制连接线
    final linePaint = Paint()
      ..color = Color.lerp(fromColor, toColor, progress)!.withOpacity(0.5)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    final path = Path()
      ..moveTo(startX, centerY)
      ..quadraticBezierTo(
        size.width / 2,
        centerY - 30,
        endX,
        centerY,
      );

    canvas.drawPath(path, linePaint);

    // 绘制移动的点（表示信息传递）
    final currentX = startX + (endX - startX) * progress;
    final currentY = centerY -
        30 * math.sin(progress * math.pi); // 曲线运动

    final dotPaint = Paint()
      ..color = Color.lerp(fromColor, toColor, progress)!
      ..style = PaintingStyle.fill;

    canvas.drawCircle(Offset(currentX, currentY), 6, dotPaint);
  }

  @override
  bool shouldRepaint(_HandoffPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
