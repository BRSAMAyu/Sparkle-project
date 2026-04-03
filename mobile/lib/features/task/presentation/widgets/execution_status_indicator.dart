import 'dart:async';
import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/data/models/execution_intent_model.dart';

class ExecutionStatusIndicator extends StatefulWidget {
  const ExecutionStatusIndicator({
    required this.status,
    super.key,
    this.dispatchedAt,
    this.size = 48,
  });

  final ExecutionIntentStatus status;
  final DateTime? dispatchedAt;
  final double size;

  @override
  State<ExecutionStatusIndicator> createState() =>
      _ExecutionStatusIndicatorState();
}

class _ExecutionStatusIndicatorState extends State<ExecutionStatusIndicator>
    with TickerProviderStateMixin {
  Timer? _timer;
  late final AnimationController _spinController;
  late final AnimationController _successController;
  late final AnimationController _errorController;
  Duration _elapsed = Duration.zero;
  ExecutionIntentStatus? _previousStatus;

  @override
  void initState() {
    super.initState();
    _spinController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _successController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
      lowerBound: 1,
      upperBound: 1.15,
    )..value = 1;
    _errorController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _previousStatus = widget.status;
    _syncStatusEffects(initial: true);
  }

  @override
  void didUpdateWidget(covariant ExecutionStatusIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.status != widget.status ||
        oldWidget.dispatchedAt != widget.dispatchedAt) {
      _previousStatus = oldWidget.status;
      _syncStatusEffects();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _spinController.dispose();
    _successController.dispose();
    _errorController.dispose();
    super.dispose();
  }

  bool get _reduceMotion {
    final mediaQuery = MediaQuery.maybeOf(context);
    return context.reduceMotion ||
        (mediaQuery?.disableAnimations ?? false) ||
        (mediaQuery?.accessibleNavigation ?? false);
  }

  void _syncStatusEffects({bool initial = false}) {
    _timer?.cancel();
    if (_isActiveStatus(widget.status) && widget.dispatchedAt != null) {
      _tickElapsed();
      _timer = Timer.periodic(const Duration(seconds: 1), (_) => _tickElapsed());
    } else if (widget.dispatchedAt != null) {
      _tickElapsed();
    } else {
      _elapsed = Duration.zero;
    }

    if (widget.status == ExecutionIntentStatus.running && !_reduceMotion) {
      unawaited(_spinController.repeat());
    } else {
      _spinController
        ..stop()
        ..value = 0;
    }

    if (initial || _reduceMotion) {
      return;
    }

    if (_previousStatus != widget.status &&
        widget.status == ExecutionIntentStatus.succeeded) {
      _successController.value = 1;
      unawaited(
        _successController.animateTo(1.15, curve: Curves.elasticOut).then((_) {
          if (mounted) {
            unawaited(
              _successController.animateTo(1, curve: Curves.easeOutCubic),
            );
          }
        }),
      );
    }

    if (_previousStatus != widget.status &&
        (widget.status == ExecutionIntentStatus.failed ||
            widget.status == ExecutionIntentStatus.timedOut)) {
      _errorController.value = 0;
      unawaited(_errorController.forward(from: 0));
    }
  }

  void _tickElapsed() {
    final dispatchedAt = widget.dispatchedAt;
    if (dispatchedAt == null) {
      return;
    }
    setState(() {
      _elapsed = DateTime.now().difference(dispatchedAt);
    });
  }

  bool _isActiveStatus(ExecutionIntentStatus status) =>
      status == ExecutionIntentStatus.dispatched ||
      status == ExecutionIntentStatus.running ||
      status == ExecutionIntentStatus.waitingApproval;

  _ExecutionVisualSpec _specFor(ExecutionIntentStatus status) {
    switch (status) {
      case ExecutionIntentStatus.draft:
        return _ExecutionVisualSpec(
          color: DS.textTertiary,
          icon: Icons.edit_note_rounded,
        );
      case ExecutionIntentStatus.ready:
        return _ExecutionVisualSpec(
          color: DS.info,
          icon: Icons.check_circle_outline_rounded,
        );
      case ExecutionIntentStatus.queued:
        return _ExecutionVisualSpec(
          color: DS.info,
          icon: Icons.schedule_send_rounded,
          pulse: true,
        );
      case ExecutionIntentStatus.dispatched:
        return _ExecutionVisualSpec(
          color: DS.info,
          icon: Icons.send_rounded,
          pulse: true,
        );
      case ExecutionIntentStatus.running:
        return _ExecutionVisualSpec(
          color: DS.semanticWarning,
          icon: Icons.autorenew_rounded,
          pulse: true,
          rotating: true,
        );
      case ExecutionIntentStatus.waitingApproval:
        return _ExecutionVisualSpec(
          color: DS.semanticWarning,
          icon: Icons.pending_actions_rounded,
          pulse: true,
          pulseScaleRange: 0.024,
        );
      case ExecutionIntentStatus.succeeded:
        return _ExecutionVisualSpec(
          color: DS.semanticSuccess,
          icon: Icons.check_circle_rounded,
          successBounce: true,
        );
      case ExecutionIntentStatus.partial:
        return _ExecutionVisualSpec(
          color: DS.semanticWarning,
          icon: Icons.rule_rounded,
        );
      case ExecutionIntentStatus.failed:
        return _ExecutionVisualSpec(
          color: DS.semanticError,
          icon: Icons.error_outline_rounded,
          shake: true,
        );
      case ExecutionIntentStatus.canceled:
        return _ExecutionVisualSpec(
          color: DS.textTertiary,
          icon: Icons.cancel_outlined,
        );
      case ExecutionIntentStatus.timedOut:
        return _ExecutionVisualSpec(
          color: DS.semanticError,
          icon: Icons.timer_off_rounded,
          shake: true,
        );
      case ExecutionIntentStatus.handedBack:
        return _ExecutionVisualSpec(
          color: DS.textSecondary,
          icon: Icons.undo_rounded,
        );
      case ExecutionIntentStatus.unknown:
        return _ExecutionVisualSpec(
          color: DS.textSecondary,
          icon: Icons.more_horiz_rounded,
        );
    }
  }

  String _formatElapsed(Duration elapsed) {
    if (elapsed.inSeconds < 60) {
      return '${elapsed.inSeconds}s';
    }
    final minutes = elapsed.inMinutes;
    final seconds = elapsed.inSeconds % 60;
    return '$minutes:${seconds.toString().padLeft(2, '0')}';
  }

  String _statusLabel() {
    switch (widget.status) {
      case ExecutionIntentStatus.draft:
        return '待准备';
      case ExecutionIntentStatus.ready:
        return '准备完成';
      case ExecutionIntentStatus.queued:
        return '排队中';
      case ExecutionIntentStatus.dispatched:
        return '已发送';
      case ExecutionIntentStatus.running:
        return '执行中';
      case ExecutionIntentStatus.waitingApproval:
        return '等待确认';
      case ExecutionIntentStatus.succeeded:
        return '执行成功';
      case ExecutionIntentStatus.partial:
        return '部分完成';
      case ExecutionIntentStatus.failed:
        return '执行失败';
      case ExecutionIntentStatus.canceled:
        return '已取消';
      case ExecutionIntentStatus.timedOut:
        return '执行超时';
      case ExecutionIntentStatus.handedBack:
        return '已交还';
      case ExecutionIntentStatus.unknown:
        return '状态未知';
    }
  }

  @override
  Widget build(BuildContext context) {
    final spec = _specFor(widget.status);
    final iconSize = widget.size * 0.46;
    final showElapsed =
        widget.dispatchedAt != null &&
        (_isActiveStatus(widget.status) || _elapsed > Duration.zero);

    return Semantics(
      label: '执行状态: ${_statusLabel()}',
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedSwitcher(
            duration: _reduceMotion ? Duration.zero : DS.normal,
            switchInCurve: Curves.easeOutCubic,
            switchOutCurve: Curves.easeInCubic,
            transitionBuilder: (child, animation) {
              if (_reduceMotion) {
                return FadeTransition(opacity: animation, child: child);
              }
              return FadeTransition(
                opacity: animation,
                child: ScaleTransition(scale: animation, child: child),
              );
            },
            child: _buildIcon(spec, iconSize),
          ),
          if (showElapsed) ...[
            const SizedBox(height: DS.spacing6),
            Text(
              _formatElapsed(_elapsed),
              style: TextStyle(
                fontSize: 11,
                color: spec.color.withValues(alpha: 0.82),
                fontFeatures: const [FontFeature.tabularFigures()],
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildIcon(_ExecutionVisualSpec spec, double iconSize) {
    Widget icon = Icon(
      spec.icon,
      color: spec.color,
      size: iconSize,
    );

    if (spec.rotating && !_reduceMotion) {
      icon = RotationTransition(
        turns: _spinController,
        child: icon,
      );
    }

    if (spec.successBounce && !_reduceMotion) {
      icon = ScaleTransition(scale: _successController, child: icon);
    }

    if (spec.shake && !_reduceMotion) {
      icon = AnimatedBuilder(
        animation: _errorController,
        child: icon,
        builder: (context, child) {
          final t = _errorController.value;
          final offsets = [-4.0, 4.0, -2.0, 2.0, 0.0];
          final segment = math.min((t * (offsets.length - 1)).floor(), offsets.length - 2);
          final localT = (t * (offsets.length - 1)) - segment;
          final dx = lerpDouble(offsets[segment], offsets[segment + 1], localT) ?? 0;
          return Transform.translate(offset: Offset(dx, 0), child: child);
        },
      );
    }

    final core = Container(
      key: ValueKey(widget.status.name),
      width: widget.size,
      height: widget.size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            spec.color.withValues(alpha: 0.14),
            spec.color.withValues(alpha: 0.06),
          ],
        ),
        border: Border.all(
          color: spec.color.withValues(alpha: 0.18),
        ),
      ),
      alignment: Alignment.center,
      child: icon,
    );

    if (spec.pulse && !_reduceMotion) {
      return SparkleAttentionPulse(
        glowColor: spec.color,
        scaleRange: spec.pulseScaleRange,
        child: core,
      );
    }
    return core;
  }
}

class _ExecutionVisualSpec {
  const _ExecutionVisualSpec({
    required this.color,
    required this.icon,
    this.pulse = false,
    this.rotating = false,
    this.successBounce = false,
    this.shake = false,
    this.pulseScaleRange = 0.018,
  });

  final Color color;
  final IconData icon;
  final bool pulse;
  final bool rotating;
  final bool successBounce;
  final bool shake;
  final double pulseScaleRange;
}
