import 'package:flutter/material.dart';
import 'dart:math' as math;
import 'package:sparkle/core/design/design_tokens.dart';

/// 架构可视化动画 - 必杀技 C
///
/// 展示 Sparkle 系统架构的动画说明
/// - Flutter 移动端
/// - Go Gateway (WebSocket)
/// - Python Agent Engine (gRPC)
/// - PostgreSQL + Redis
///
/// 用于 Onboarding 流程，帮助用户理解系统工作原理
class ArchitectureAnimation extends StatefulWidget {
  final VoidCallback? onComplete;
  final bool autoPlay;

  const ArchitectureAnimation({
    this.onComplete,
    this.autoPlay = true,
    super.key,
  });

  @override
  State<ArchitectureAnimation> createState() => _ArchitectureAnimationState();
}

class _ArchitectureAnimationState extends State<ArchitectureAnimation>
    with TickerProviderStateMixin {
  late AnimationController _mainController;
  late AnimationController _pulseController;
  late Animation<double> _fadeAnimation;
  late Animation<double> _slideAnimation;

  int _currentStep = 0;
  final int _totalSteps = 5;

  @override
  void initState() {
    super.initState();

    // Main animation controller for step transitions
    _mainController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    // Pulse animation for data flow
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();

    _fadeAnimation = CurvedAnimation(
      parent: _mainController,
      curve: Curves.easeInOut,
    );

    _slideAnimation = CurvedAnimation(
      parent: _mainController,
      curve: Curves.easeOutCubic,
    );

    if (widget.autoPlay) {
      _startAnimation();
    }
  }

  void _startAnimation() async {
    for (int i = 0; i < _totalSteps; i++) {
      setState(() => _currentStep = i);
      _mainController.forward(from: 0);
      await Future.delayed(const Duration(seconds: 3));
    }

    widget.onComplete?.call();
  }

  @override
  void dispose() {
    _mainController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 500,
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            AppDesignTokens.deepSpaceStart,
            AppDesignTokens.deepSpaceEnd,
          ],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Stack(
        children: [
          // Background stars
          _buildStarField(),

          // Architecture diagram
          Positioned.fill(
            child: CustomPaint(
              painter: _ArchitecturePainter(
                currentStep: _currentStep,
                fadeValue: _fadeAnimation.value,
                pulseValue: _pulseController.value,
              ),
            ),
          ),

          // Step indicator
          Positioned(
            bottom: 20,
            left: 0,
            right: 0,
            child: _buildStepIndicator(),
          ),

          // Description overlay
          if (_currentStep < _totalSteps)
            Positioned(
              top: 20,
              left: 20,
              right: 20,
              child: FadeTransition(
                opacity: _fadeAnimation,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0, -0.5),
                    end: Offset.zero,
                  ).animate(_slideAnimation),
                  child: _buildStepDescription(),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildStarField() {
    return CustomPaint(
      painter: _StarFieldPainter(),
    );
  }

  Widget _buildStepIndicator() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(_totalSteps, (index) {
        return Container(
          width: index == _currentStep ? 24 : 8,
          height: 8,
          margin: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(
            color: index <= _currentStep
                ? Colors.white
                : Colors.white.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(4),
          ),
        );
      }),
    );
  }

  Widget _buildStepDescription() {
    final steps = [
      {
        'title': '移动端',
        'description': 'Flutter 跨平台应用\n提供流畅的用户体验',
        'icon': Icons.phone_android,
      },
      {
        'title': 'WebSocket 连接',
        'description': 'Go Gateway 提供实时双向通信\n高性能、低延迟',
        'icon': Icons.swap_horiz,
      },
      {
        'title': 'AI 引擎',
        'description': 'Python Agent Engine\n强大的推理和工具调用能力',
        'icon': Icons.psychology,
      },
      {
        'title': '数据存储',
        'description': 'PostgreSQL + pgvector\n向量检索 + 图谱存储',
        'icon': Icons.storage,
      },
      {
        'title': '完整链路',
        'description': '从提问到回答\n毫秒级响应体验',
        'icon': Icons.rocket_launch,
      },
    ];

    final step = steps[_currentStep];

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.blue.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              step['icon'] as IconData,
              color: Colors.white,
              size: 32,
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  step['title'] as String,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  step['description'] as String,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.8),
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ArchitecturePainter extends CustomPainter {
  final int currentStep;
  final double fadeValue;
  final double pulseValue;

  _ArchitecturePainter({
    required this.currentStep,
    required this.fadeValue,
    required this.pulseValue,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);

    // Layer positions
    final mobilePos = Offset(center.dx, size.height * 0.15);
    final gatewayPos = Offset(center.dx, size.height * 0.35);
    final agentPos = Offset(center.dx, size.height * 0.55);
    final dbPos = Offset(center.dx, size.height * 0.75);

    // Draw connections
    if (currentStep >= 1) {
      _drawConnection(canvas, mobilePos, gatewayPos, currentStep >= 1 ? fadeValue : 0);
    }
    if (currentStep >= 2) {
      _drawConnection(canvas, gatewayPos, agentPos, currentStep >= 2 ? fadeValue : 0);
    }
    if (currentStep >= 3) {
      _drawConnection(canvas, agentPos, dbPos, currentStep >= 3 ? fadeValue : 0);
    }

    // Draw data flow particles
    if (currentStep == 4) {
      _drawDataFlow(canvas, mobilePos, gatewayPos, pulseValue);
      _drawDataFlow(canvas, gatewayPos, agentPos, (pulseValue + 0.3) % 1.0);
      _drawDataFlow(canvas, agentPos, dbPos, (pulseValue + 0.6) % 1.0);
    }

    // Draw layers
    if (currentStep >= 0) {
      _drawLayer(canvas, mobilePos, 'Flutter\nMobile', Icons.phone_android.codePoint,
          currentStep >= 0 ? fadeValue : 0, Colors.blue.shade400,);
    }
    if (currentStep >= 1) {
      _drawLayer(canvas, gatewayPos, 'Go\nGateway', Icons.swap_horiz.codePoint,
          currentStep >= 1 ? fadeValue : 0, Colors.green.shade400,);
    }
    if (currentStep >= 2) {
      _drawLayer(canvas, agentPos, 'Python\nAgent', Icons.psychology.codePoint,
          currentStep >= 2 ? fadeValue : 0, Colors.purple.shade400,);
    }
    if (currentStep >= 3) {
      _drawLayer(canvas, dbPos, 'PostgreSQL\n+ Redis', Icons.storage.codePoint,
          currentStep >= 3 ? fadeValue : 0, Colors.orange.shade400,);
    }
  }

  void _drawLayer(Canvas canvas, Offset position, String label, int iconCode,
      double opacity, Color color,) {
    final paint = Paint()
      ..color = color.withValues(alpha: opacity * 0.3)
      ..style = PaintingStyle.fill;

    final borderPaint = Paint()
      ..color = color.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    // Draw rectangle
    final rect = Rect.fromCenter(center: position, width: 200, height: 80);
    final rrect = RRect.fromRectAndRadius(rect, const Radius.circular(12));

    canvas.drawRRect(rrect, paint);
    canvas.drawRRect(rrect, borderPaint);

    // Draw label
    final textPainter = TextPainter(
      text: TextSpan(
        text: label,
        style: TextStyle(
          color: Colors.white.withValues(alpha: opacity),
          fontSize: 16,
          fontWeight: FontWeight.bold,
        ),
      ),
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
    );

    textPainter.layout();
    textPainter.paint(
      canvas,
      Offset(
        position.dx - textPainter.width / 2,
        position.dy - textPainter.height / 2,
      ),
    );
  }

  void _drawConnection(Canvas canvas, Offset start, Offset end, double opacity) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: opacity * 0.5)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    // Draw arrow
    canvas.drawLine(start, end, paint);

    // Draw arrowhead
    final arrowPaint = Paint()
      ..color = Colors.white.withValues(alpha: opacity * 0.5)
      ..style = PaintingStyle.fill;

    final angle = math.atan2(end.dy - start.dy, end.dx - start.dx);
    const arrowSize = 10.0;

    final path = Path()
      ..moveTo(end.dx, end.dy)
      ..lineTo(
        end.dx - arrowSize * math.cos(angle - math.pi / 6),
        end.dy - arrowSize * math.sin(angle - math.pi / 6),
      )
      ..lineTo(
        end.dx - arrowSize * math.cos(angle + math.pi / 6),
        end.dy - arrowSize * math.sin(angle + math.pi / 6),
      )
      ..close();

    canvas.drawPath(path, arrowPaint);
  }

  void _drawDataFlow(Canvas canvas, Offset start, Offset end, double progress) {
    final position = Offset.lerp(start, end, progress)!;

    final paint = Paint()
      ..color = Colors.cyan.withValues(alpha: 0.8)
      ..style = PaintingStyle.fill;

    canvas.drawCircle(position, 6, paint);

    // Glow effect
    final glowPaint = Paint()
      ..color = Colors.cyan.withValues(alpha: 0.3)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 10);

    canvas.drawCircle(position, 12, glowPaint);
  }

  @override
  bool shouldRepaint(covariant _ArchitecturePainter oldDelegate) =>
      oldDelegate.currentStep != currentStep ||
      oldDelegate.fadeValue != fadeValue ||
      oldDelegate.pulseValue != pulseValue;
}

class _StarFieldPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = Colors.white.withValues(alpha: 0.3);

    final random = math.Random(42); // Fixed seed for consistent stars

    for (int i = 0; i < 50; i++) {
      final x = random.nextDouble() * size.width;
      final y = random.nextDouble() * size.height;
      final radius = random.nextDouble() * 2;

      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
