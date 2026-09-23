import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/utils/text_rendering.dart';

enum TimerMode { countUp, countDown }

class TimerWidget extends StatefulWidget {
  const TimerWidget({
    required this.mode,
    super.key,
    this.initialSeconds = 0,
    this.maxSeconds,
    this.autoStart = false,
    this.onTick,
    this.onComplete,
    this.onStateChange,
  });
  final int initialSeconds;
  final int? maxSeconds; // For progress visualization
  final TimerMode mode;
  final bool autoStart;
  final void Function(int seconds)? onTick;
  final VoidCallback? onComplete;
  final void Function(bool isRunning)? onStateChange;

  @override
  State<TimerWidget> createState() => _TimerWidgetState();
}

class _TimerWidgetState extends State<TimerWidget>
    with TickerProviderStateMixin, WidgetsBindingObserver {
  Timer? _timer;
  late int _currentSeconds;
  int _elapsedSeconds = 0;
  bool _isRunning = false;
  DateTime? _runStartedAt;
  bool _didComplete = false;
  // N33 reduce-motion 守护口径（didChangeDependencies 内经 MediaQuery 读取，
  // 系统 ∨ in-app 叠加；禁 platformDispatcher 直读——A-SPEC6 N32 统一令）。
  bool _reduceMotion = false;
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _resetToInitialState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.05).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      widget.onTick?.call(_currentSeconds);
      if (widget.autoStart) {
        _startTimer();
      }
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // N33 reduce-motion 守护：`context.reduceMotion` 为 MediaQuery 口径
    // （maybeOf 内部 dependOn，系统/应用内减弱动效开关变化时自动重入）。
    // 装饰性脉动（表盘呼吸缩放）随开关启停；秒级计时本体是功能
    // （Timer.periodic），不受减弱动效影响。
    _reduceMotion = context.reduceMotion;
    if (!_isRunning) {
      return;
    }
    if (_reduceMotion) {
      _pulseController
        ..stop()
        ..value = 0; // 静止终态：pulse Tween begin=1.0 → 表盘 scale 1.0
    } else {
      _ensurePulse();
    }
  }

  @override
  void didUpdateWidget(TimerWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialSeconds != widget.initialSeconds && !_isRunning) {
      setState(_resetToInitialState);
      widget.onTick?.call(_currentSeconds);
    }

    if (!_isRunning && !oldWidget.autoStart && widget.autoStart) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && !_isRunning) {
          _startTimer();
        }
      });
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (!_isRunning) {
      return;
    }

    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.paused) {
      _syncFromClock(notifyTick: false);
      _stopPeriodicTicker();
      return;
    }

    if (state == AppLifecycleState.resumed) {
      _syncFromClock();
      if (_isRunning && !_didComplete) {
        _startPeriodicTicker();
      }
    }
  }

  void _resetToInitialState() {
    _elapsedSeconds = 0;
    _currentSeconds = widget.initialSeconds;
    _runStartedAt = null;
    _didComplete =
        widget.mode == TimerMode.countDown && widget.initialSeconds == 0;
  }

  /// 装饰性脉动的唯一启动点（persistentRepeatLoop 守卫口径：单调用点）。
  /// 启动与开关恢复两路生命周期都经此，幂等（已在播不重启）。
  void _ensurePulse() {
    if (!_pulseController.isAnimating) {
      unawaited(_pulseController.repeat(reverse: true));
    }
  }

  void _startTimer() {
    if (_isRunning) return;
    _didComplete = false;
    _runStartedAt = DateTime.now();
    setState(() => _isRunning = true);
    widget.onStateChange?.call(true);
    if (!_reduceMotion) {
      // N33：减弱动效下不启动装饰性脉动，表盘静止（计时功能照常）。
      _ensurePulse();
    }
    _syncFromClock();
    _startPeriodicTicker();
  }

  void _startPeriodicTicker() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!_isRunning) {
        timer.cancel();
        return;
      }
      _syncFromClock();
    });
  }

  void _stopPeriodicTicker() {
    _timer?.cancel();
    _timer = null;
  }

  int _displayedSecondsForElapsed(int elapsedSeconds) {
    if (widget.mode == TimerMode.countUp) {
      return elapsedSeconds;
    }
    return max(widget.initialSeconds - elapsedSeconds, 0);
  }

  void _syncFromClock({bool notifyTick = true}) {
    if (!_isRunning || _runStartedAt == null) {
      return;
    }

    final now = DateTime.now();
    final elapsedSinceStart = now.difference(_runStartedAt!).inSeconds;
    final nextElapsed =
        _elapsedSeconds + (elapsedSinceStart < 0 ? 0 : elapsedSinceStart);
    _runStartedAt = now;

    final nextDisplayed = _displayedSecondsForElapsed(nextElapsed);
    final didComplete =
        widget.mode == TimerMode.countDown && nextDisplayed <= 0;

    setState(() {
      _elapsedSeconds = nextElapsed;
      _currentSeconds = nextDisplayed;
    });

    if (notifyTick) {
      widget.onTick?.call(_currentSeconds);
    }

    if (didComplete && !_didComplete) {
      _didComplete = true;
      _stopTimerInternal(syncClock: false, notify: false);
      widget.onTick?.call(_currentSeconds);
      widget.onComplete?.call();
    }
  }

  void _stopTimer({bool notify = true}) {
    _stopTimerInternal(syncClock: true, notify: notify);
  }

  void _stopTimerInternal({required bool syncClock, bool notify = true}) {
    if (!_isRunning) return;
    if (syncClock) {
      _syncFromClock();
    }
    _stopPeriodicTicker();
    _runStartedAt = null;
    setState(() => _isRunning = false);
    _pulseController
      ..stop()
      ..value = 1.0; // Reset scale
    if (notify) widget.onStateChange?.call(false);
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
    final maxSecs = widget.maxSeconds ??
        (widget.mode == TimerMode.countDown
            ? widget.initialSeconds
            : 3600); // Default 1hr base for countup
    double progress;
    if (widget.mode == TimerMode.countDown) {
      progress = maxSecs > 0 ? _currentSeconds / maxSecs : 0.0;
    } else {
      progress = maxSecs > 0
          ? (_currentSeconds % maxSecs) / maxSecs
          : 0.0; // Loop or fill? Let's just fill for now.
      if (_currentSeconds > maxSecs) progress = 1.0;
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final availableWidth = constraints.maxWidth.isFinite
            ? constraints.maxWidth
            : MediaQuery.sizeOf(context).width;
        final dialSize = availableWidth.clamp(168.0, 220.0);
        final timeFontSize = dialSize * 0.16;
        final controlIconSize = (dialSize * 0.36).clamp(64.0, 80.0);

        return Column(
          children: [
            AnimatedBuilder(
              animation: _pulseAnimation,
              builder: (context, child) => Transform.scale(
                scale: _isRunning ? _pulseAnimation.value : 1.0,
                child: child,
              ),
              child: CustomPaint(
                size: Size.square(dialSize),
                painter: _CircularTimerPainter(
                  progress: progress,
                  gradient: LinearGradient(
                    colors: [
                      DS.primaryBase.withValues(alpha: 0.95),
                      Color.lerp(
                        DS.primaryBase,
                        DS.surfaceTertiary,
                        Theme.of(context).brightness == Brightness.dark
                            ? 0.26
                            : 0.18,
                      )!
                          .withValues(alpha: 0.88),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  backgroundColor: DS.surfaceSecondary,
                ),
                child: SizedBox(
                  width: dialSize,
                  height: dialSize,
                  child: Center(
                    child: Text(
                      _formatTime(_currentSeconds),
                      style:
                          Theme.of(context).textTheme.displayMedium?.copyWith(
                                fontSize: timeFontSize,
                                fontWeight: DS.fontWeightBold,
                                letterSpacing: -1.0,
                                fontFeatures: const [
                                  FontFeature.tabularFigures(),
                                ],
                                fontFamilyFallback: sparkleFontFallback,
                                color: DS.textPrimary,
                              ),
                    ),
                  ),
                ),
              ),
            ),
            SizedBox(height: dialSize * 0.14),
            AnimatedSwitcher(
              duration: DS.durationFast,
              transitionBuilder: (child, animation) => ScaleTransition(
                scale: animation,
                child: FadeTransition(opacity: animation, child: child),
              ),
              child: GestureDetector(
                key: ValueKey(_isRunning),
                onTap: _toggleTimer,
                child: Icon(
                  _isRunning
                      ? Icons.pause_circle_filled
                      : Icons.play_circle_filled,
                  size: controlIconSize,
                  color: DS.primaryBase,
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _CircularTimerPainter extends CustomPainter {
  _CircularTimerPainter({
    required this.progress,
    required this.gradient,
    required this.backgroundColor,
  });
  final double progress;
  final Gradient gradient;
  final Color backgroundColor;

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
  bool shouldRepaint(covariant _CircularTimerPainter oldDelegate) =>
      oldDelegate.progress != progress ||
      oldDelegate.gradient != gradient ||
      oldDelegate.backgroundColor != backgroundColor;
}
