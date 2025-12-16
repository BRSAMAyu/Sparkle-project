import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

enum TimerMode { countUp, countDown }

class TimerWidget extends StatefulWidget {
  final int initialSeconds;
  final int? maxSeconds; // For progress visualization
  final TimerMode mode;
  final Function(int seconds)? onTick;
  final VoidCallback? onComplete;
  final Function(bool isRunning)? onStateChange;

  const TimerWidget({
    required this.mode, 
    super.key,
    this.initialSeconds = 0,
    this.maxSeconds,
    this.onTick,
    this.onComplete,
    this.onStateChange,
  });

  @override
  State<TimerWidget> createState() => _TimerWidgetState();
}

class _TimerWidgetState extends State<TimerWidget> with TickerProviderStateMixin {
  Timer? _timer;
  late int _currentSeconds;
  bool _isRunning = false;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _currentSeconds = widget.initialSeconds;
    
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.05).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  void _startTimer() {
    if (_isRunning) return;
    setState(() => _isRunning = true);
    widget.onStateChange?.call(true);
    _pulseController.repeat(reverse: true);

    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (widget.mode == TimerMode.countUp) {
        setState(() => _currentSeconds++);
        widget.onTick?.call(_currentSeconds);
      } else {
        if (_currentSeconds > 0) {
          setState(() => _currentSeconds--);
          widget.onTick?.call(_currentSeconds);
        } else {
          _stopTimer(notify: false);
          widget.onComplete?.call();
        }
      }
    });
  }

  void _stopTimer({bool notify = true}) {
    if (!_isRunning) return;
    _timer?.cancel();
    setState(() => _isRunning = false);
    _pulseController.stop();
    _pulseController.value = 1.0; // Reset scale
    if(notify) widget.onStateChange?.call(false);
  }

  void _toggleTimer() {
    if (_isRunning) {
      _stopTimer();
    } else {
      _startTimer();
    }
  }

  String _formatTime(int totalSeconds) {
    final duration = Duration(seconds: totalSeconds);
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    final hours = twoDigits(duration.inHours);
    final minutes = twoDigits(duration.inMinutes.remainder(60));
    final seconds = twoDigits(duration.inSeconds.remainder(60));
    return '$hours:$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final int maxSecs = widget.maxSeconds ?? (widget.mode == TimerMode.countDown ? widget.initialSeconds : 3600); // Default 1hr base for countup
    double progress;
    if (widget.mode == TimerMode.countDown) {
      progress = maxSecs > 0 ? _currentSeconds / maxSecs : 0.0;
    } else {
      progress = maxSecs > 0 ? (_currentSeconds % maxSecs) / maxSecs : 0.0; // Loop or fill? Let's just fill for now.
      if (_currentSeconds > maxSecs) progress = 1.0; 
    }

    return Column(
      children: [
        AnimatedBuilder(
          animation: _pulseAnimation,
          builder: (context, child) {
            return Transform.scale(
              scale: _isRunning ? _pulseAnimation.value : 1.0,
              child: child,
            );
          },
          child: CustomPaint(
            size: const Size(220, 220),
            painter: _CircularTimerPainter(
              progress: progress,
              gradient: AppDesignTokens.primaryGradient,
              backgroundColor: AppDesignTokens.neutral200,
            ),
            child: SizedBox(
              width: 220,
              height: 220,
              child: Center(
                child: Text(
                  _formatTime(_currentSeconds),
                  style: Theme.of(context).textTheme.displayMedium?.copyWith(
                    fontWeight: AppDesignTokens.fontWeightBold,
                    fontFamily: 'monospace',
                    color: AppDesignTokens.neutral900,
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppDesignTokens.spacing32),
        AnimatedSwitcher(
          duration: AppDesignTokens.durationFast,
          transitionBuilder: (child, animation) {
            return ScaleTransition(
              scale: animation,
              child: FadeTransition(opacity: animation, child: child),
            );
          },
          child: IconButton(
            key: ValueKey(_isRunning),
            icon: Icon(_isRunning ? Icons.pause_circle_filled : Icons.play_circle_filled),
            iconSize: 80, // Slightly larger
            color: AppDesignTokens.primaryBase,
            onPressed: _toggleTimer,
            padding: EdgeInsets.zero,
          ),
        ),
      ],
    );
  }
}

class _CircularTimerPainter extends CustomPainter {
  final double progress;
  final Gradient gradient;
  final Color backgroundColor;

  _CircularTimerPainter({
    required this.progress,
    required this.gradient,
    required this.backgroundColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = size.width / 2 - 10; // Padding
    const strokeWidth = 12.0;

    // Background Circle
    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, bgPaint);

    // Progress Arc
    final rect = Rect.fromCircle(center: center, radius: radius);
    final progressPaint = Paint()
      ..shader = gradient.createShader(rect)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      rect,
      -pi / 2, // Start at top
      2 * pi * progress,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _CircularTimerPainter oldDelegate) {
    return oldDelegate.progress != progress ||
           oldDelegate.gradient != gradient ||
           oldDelegate.backgroundColor != backgroundColor;
  }
}