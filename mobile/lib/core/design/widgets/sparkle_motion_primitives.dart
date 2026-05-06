import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/core/design/widgets/pulse_scope.dart';

class SparkleStaggerItem extends StatefulWidget {
  const SparkleStaggerItem({
    required this.index,
    required this.child,
    super.key,
    this.axis = Axis.vertical,
    this.initialDelay = const Duration(milliseconds: 30),
    this.stepDelay = const Duration(milliseconds: 40),
    this.offset = 0.04,
    this.beginScale = 0.978,
    this.motionToken = SparkleMotionToken.scene,
  });

  final int index;
  final Widget child;
  final Axis axis;
  final Duration initialDelay;
  final Duration stepDelay;
  final double offset;
  final double beginScale;
  final SparkleMotionToken motionToken;

  @override
  State<SparkleStaggerItem> createState() => _SparkleStaggerItemState();
}

class _SparkleStaggerItemState extends State<SparkleStaggerItem> {
  Timer? _timer;
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    _scheduleReveal();
  }

  @override
  void didUpdateWidget(covariant SparkleStaggerItem oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.index != widget.index) {
      _scheduleReveal(reset: true);
    }
  }

  void _scheduleReveal({bool reset = false}) {
    _timer?.cancel();
    if (reset) {
      _visible = false;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      if (context.reduceMotion) {
        setState(() {
          _visible = true;
        });
        return;
      }
      final rawDelay = widget.initialDelay.inMilliseconds +
          (widget.stepDelay.inMilliseconds *
                  math.pow(0.82, widget.index) *
                  widget.index)
              .round();
      final delay =
          Duration(milliseconds: rawDelay.clamp(0, 220));
      _timer = Timer(delay, () {
        if (!mounted) {
          return;
        }
        setState(() {
          _visible = true;
        });
      });
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (context.reduceMotion) {
      return widget.child;
    }
    final duration = widget.motionToken == SparkleMotionToken.scene
        ? const Duration(milliseconds: 400)
        : DS.motionDuration(widget.motionToken);
    final curve = widget.motionToken == SparkleMotionToken.scene
        ? Curves.easeOutQuart
        : DS.motionCurve(widget.motionToken);
    final offset = widget.axis == Axis.vertical
        ? Offset(0, _visible ? 0 : widget.offset)
        : Offset(_visible ? 0 : widget.offset, 0);

    return AnimatedSlide(
      duration: duration,
      curve: curve,
      offset: offset,
      child: AnimatedScale(
        duration: duration,
        curve: curve,
        scale: _visible ? 1 : widget.beginScale,
        child: AnimatedOpacity(
          duration: duration,
          curve: curve,
          opacity: _visible ? 1 : 0,
          child: widget.child,
        ),
      ),
    );
  }
}

class SparkleStaggerList extends StatelessWidget {
  const SparkleStaggerList({
    required this.children,
    super.key,
    this.padding,
    this.shrinkWrap = true,
    this.physics = const NeverScrollableScrollPhysics(),
    this.gap = 0,
    this.axis = Axis.vertical,
  });

  final List<Widget> children;
  final EdgeInsetsGeometry? padding;
  final bool shrinkWrap;
  final ScrollPhysics physics;
  final double gap;
  final Axis axis;

  @override
  Widget build(BuildContext context) => ListView.separated(
        padding: padding,
        shrinkWrap: shrinkWrap,
        physics: physics,
        itemCount: children.length,
        separatorBuilder: (_, __) => axis == Axis.vertical
            ? SizedBox(height: gap)
            : SizedBox(width: gap),
        itemBuilder: (context, index) => SparkleStaggerItem(
          index: index,
          axis: axis,
          child: children[index],
        ),
      );
}

class SparkleStaggerGrid extends StatelessWidget {
  const SparkleStaggerGrid({
    required this.children,
    required this.crossAxisCount,
    super.key,
    this.padding,
    this.shrinkWrap = true,
    this.physics = const NeverScrollableScrollPhysics(),
    this.mainAxisSpacing = DS.spacing12,
    this.crossAxisSpacing = DS.spacing12,
    this.childAspectRatio = 1,
  });

  final List<Widget> children;
  final int crossAxisCount;
  final EdgeInsetsGeometry? padding;
  final bool shrinkWrap;
  final ScrollPhysics physics;
  final double mainAxisSpacing;
  final double crossAxisSpacing;
  final double childAspectRatio;

  @override
  Widget build(BuildContext context) => GridView.builder(
        padding: padding,
        shrinkWrap: shrinkWrap,
        physics: physics,
        itemCount: children.length,
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: crossAxisCount,
          mainAxisSpacing: mainAxisSpacing,
          crossAxisSpacing: crossAxisSpacing,
          childAspectRatio: childAspectRatio,
        ),
        itemBuilder: (context, index) => SparkleStaggerItem(
          index: index,
          child: children[index],
        ),
      );
}

class SparkleStaggerWrap extends StatelessWidget {
  const SparkleStaggerWrap({
    required this.children,
    super.key,
    this.spacing = DS.spacing8,
    this.runSpacing = DS.spacing8,
    this.alignment = WrapAlignment.start,
    this.crossAxisAlignment = WrapCrossAlignment.start,
    this.axis = Axis.horizontal,
    this.motionToken = SparkleMotionToken.scene,
  });

  final List<Widget> children;
  final double spacing;
  final double runSpacing;
  final WrapAlignment alignment;
  final WrapCrossAlignment crossAxisAlignment;
  final Axis axis;
  final SparkleMotionToken motionToken;

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: spacing,
        runSpacing: runSpacing,
        alignment: alignment,
        crossAxisAlignment: crossAxisAlignment,
        children: children
            .asMap()
            .entries
            .map(
              (entry) => SparkleStaggerItem(
                index: entry.key,
                axis: axis,
                motionToken: motionToken,
                child: entry.value,
              ),
            )
            .toList(growable: false),
      );
}

class SparkleAttentionPulse extends StatefulWidget {
  const SparkleAttentionPulse({
    required this.child,
    super.key,
    this.active = true,
    this.scaleRange = 0.018,
    this.glowColor,
    this.duration = const Duration(milliseconds: 1600),
    this.padding = EdgeInsets.zero,
  });

  final Widget child;
  final bool active;
  final double scaleRange;
  final Color? glowColor;
  final Duration duration;
  final EdgeInsetsGeometry padding;

  @override
  State<SparkleAttentionPulse> createState() => _SparkleAttentionPulseState();
}

class SparkleCountUp extends StatelessWidget {
  const SparkleCountUp({
    required this.end,
    required this.style,
    super.key,
    this.begin = 0,
    this.duration = const Duration(milliseconds: 600),
    this.prefix = '',
    this.suffix = '',
    this.animate = true,
  });

  final int begin;
  final int end;
  final Duration duration;
  final TextStyle? style;
  final String prefix;
  final String suffix;
  final bool animate;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = context.reduceMotion;
    final shouldAnimate = animate && !reduceMotion;

    if (!shouldAnimate) {
      return Text('$prefix$end$suffix', style: style);
    }

    return TweenAnimationBuilder<int>(
      tween: IntTween(begin: begin, end: end),
      duration: duration,
      curve: Curves.easeOutCubic,
      builder: (context, value, child) =>
          Text('$prefix$value$suffix', style: style),
    );
  }
}

class _SparkleAttentionPulseState extends State<SparkleAttentionPulse>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  var _reduceMotion = false;
  var _hasSlot = false;
  PulseScope? _scope;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
    );
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reduceMotion = context.reduceMotion;
    _scope = PulseScope.maybeOf(context);
    _sync();
  }

  @override
  void didUpdateWidget(covariant SparkleAttentionPulse oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.active != widget.active ||
        oldWidget.duration != widget.duration) {
      if (oldWidget.duration != widget.duration) {
        _controller.duration = widget.duration;
      }
      _sync();
    }
  }

  void _sync() {
    if (!widget.active || _reduceMotion) {
      _releaseSlotIfHeld();
      _controller
        ..stop()
        ..value = 0;
      return;
    }
    if (_scope != null && !_hasSlot) {
      _hasSlot = _scope!.requestSlot();
      if (!_hasSlot) return; // degrade to static, no animation
    }
    unawaited(_controller.repeat(reverse: true));
  }

  void _releaseSlotIfHeld() {
    if (_hasSlot) {
      _scope?.releaseSlot();
      _hasSlot = false;
    }
  }

  @override
  void dispose() {
    _releaseSlotIfHeld();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.active || context.reduceMotion) {
      return Padding(
        padding: widget.padding,
        child: widget.child,
      );
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        final t = DS
            .motionCurve(SparkleMotionToken.scene)
            .transform(_controller.value);
        final scale = 1 + (widget.scaleRange * t);
        final glowOpacity = 0.06 + (0.10 * t);
        return Padding(
          padding: widget.padding,
          child: DecoratedBox(
            decoration: BoxDecoration(
              boxShadow: [
                if (widget.glowColor != null)
                  BoxShadow(
                    color: widget.glowColor!.withValues(alpha: glowOpacity),
                    blurRadius: 18 + (8 * t),
                    spreadRadius: 0.6 + (0.8 * t),
                  ),
              ],
            ),
            child: Transform.scale(
              scale: scale,
              child: child,
            ),
          ),
        );
      },
      child: widget.child,
    );
  }
}

class SparkleExitTransition extends StatelessWidget {
  const SparkleExitTransition({
    required this.visible,
    required this.child,
    super.key,
    this.motionToken = SparkleMotionToken.standard,
    this.maintainSize = true,
  });

  final bool visible;
  final Widget child;
  final SparkleMotionToken motionToken;
  final bool maintainSize;

  @override
  Widget build(BuildContext context) {
    final duration = DS.motionDuration(
      motionToken,
      reduceMotion: context.reduceMotion,
    );
    final curve = DS.motionCurve(motionToken);
    final animatedChild = IgnorePointer(
      ignoring: !visible,
      child: AnimatedOpacity(
        duration: duration,
        curve: curve,
        opacity: visible ? 1 : 0,
        child: AnimatedScale(
          duration: duration,
          curve: curve,
          scale: visible ? 1 : 0.8,
          child: child,
        ),
      ),
    );

    if (maintainSize) {
      return animatedChild;
    }
    return AnimatedSize(
      duration: duration,
      curve: curve,
      child: visible ? animatedChild : const SizedBox.shrink(),
    );
  }
}

class SparkleGalaxyArrivalOverlay extends StatefulWidget {
  const SparkleGalaxyArrivalOverlay({
    required this.labels,
    required this.summary,
    super.key,
    this.onComplete,
    this.duration = const Duration(milliseconds: 2200),
  });

  final List<String> labels;
  final String summary;
  final VoidCallback? onComplete;
  final Duration duration;

  @override
  State<SparkleGalaxyArrivalOverlay> createState() =>
      _SparkleGalaxyArrivalOverlayState();
}

class _SparkleGalaxyArrivalOverlayState
    extends State<SparkleGalaxyArrivalOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
    );
    unawaited(
      _controller.forward().whenComplete(() {
        if (mounted) {
          widget.onComplete?.call();
        }
      }),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final size = Size(constraints.maxWidth, constraints.maxHeight);
            final source = Offset(size.width / 2, size.height - 88);
            final targets = _buildTargets(size, widget.labels.length);
            return AnimatedBuilder(
              animation: _controller,
              builder: (context, child) {
                final progress = _controller.value;
                return Stack(
                  children: [
                    Positioned(
                      left: source.dx - 90,
                      top: source.dy - 90,
                      child: Opacity(
                        opacity: (1 - progress).clamp(0.0, 1.0) * 0.45,
                        child: Container(
                          width: 180,
                          height: 180,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(
                              colors: [
                                DS.brandPrimary.withValues(alpha: 0.24),
                                Colors.transparent,
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                    for (final entry in targets.asMap().entries)
                      _buildStar(
                        context: context,
                        index: entry.key,
                        source: source,
                        target: entry.value,
                        progress: progress,
                      ),
                    Positioned(
                      left: 24,
                      right: 24,
                      bottom: 24,
                      child: Opacity(
                        opacity: _badgeOpacity(progress),
                        child: Transform.translate(
                          offset: Offset(0, 18 * (1 - _badgeOpacity(progress))),
                          child: Center(
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                color: const Color(0xDD101A2C),
                                borderRadius: BorderRadius.circular(999),
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.1),
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withValues(alpha: 0.18),
                                    blurRadius: 18,
                                    offset: const Offset(0, 10),
                                  ),
                                ],
                              ),
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 12,
                                ),
                                child: Text(
                                  widget.summary,
                                  textAlign: TextAlign.center,
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodyMedium
                                      ?.copyWith(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w700,
                                      ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                );
              },
            );
          },
        ),
      );

  List<Offset> _buildTargets(Size size, int count) {
    if (count <= 0) {
      return const <Offset>[];
    }
    final safeCount = math.min(5, math.max(1, count));
    final center = Offset(size.width / 2, size.height * 0.33);
    const spreadX = 118.0;
    const spreadY = 44.0;
    return List<Offset>.generate(safeCount, (index) {
      final factor = safeCount == 1 ? 0.0 : (index / (safeCount - 1)) - 0.5;
      final dx = factor * spreadX * 2;
      final dy = math.sin((index + 1) * 0.9) * spreadY;
      return Offset(center.dx + dx, center.dy + dy);
    });
  }

  Widget _buildStar({
    required BuildContext context,
    required int index,
    required Offset source,
    required Offset target,
    required double progress,
  }) {
    final start = index * 0.08;
    final travel = ((progress - start) / 0.48).clamp(0.0, 1.0);
    final eased = Curves.easeOutCubic.transform(travel);
    final lift = 84 * math.sin(eased * math.pi);
    final control = Offset(
      (source.dx + target.dx) / 2,
      math.min(source.dy, target.dy) - 110 - (index * 18),
    );
    final position = _quadraticBezier(source, control, target, eased);
    final shimmer = (0.72 + (0.28 * math.sin((progress + index) * math.pi * 6)))
        .clamp(0.0, 1.0);
    final arrival = ((progress - (start + 0.42)) / 0.18).clamp(0.0, 1.0);
    final opacity = travel <= 0
        ? 0.0
        : progress > 0.9
            ? ((1 - progress) / 0.1).clamp(0.0, 1.0)
            : 1.0;

    return Positioned(
      left: position.dx - 12,
      top: position.dy - 12 - lift * 0.08,
      child: Opacity(
        opacity: opacity,
        child: Column(
          children: [
            Container(
              width: 24,
              height: 24,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    Colors.white,
                    DS.brandPrimary.withValues(alpha: shimmer),
                    Colors.transparent,
                  ],
                ),
                boxShadow: [
                  BoxShadow(
                    color: DS.brandPrimary.withValues(alpha: 0.32 * shimmer),
                    blurRadius: 18,
                    spreadRadius: 2 + (arrival * 2),
                  ),
                ],
              ),
            ),
            if (arrival > 0.05)
              Container(
                margin: const EdgeInsets.only(top: 6),
                width: 8 + (arrival * 30),
                height: 2,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: arrival * 0.85),
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
          ],
        ),
      ),
    );
  }

  double _badgeOpacity(double progress) {
    if (progress < 0.28) {
      return (progress / 0.28).clamp(0.0, 1.0);
    }
    if (progress > 0.9) {
      return ((1 - progress) / 0.1).clamp(0.0, 1.0);
    }
    return 1.0;
  }

  Offset _quadraticBezier(Offset a, Offset b, Offset c, double t) {
    final ab = Offset.lerp(a, b, t)!;
    final bc = Offset.lerp(b, c, t)!;
    return Offset.lerp(ab, bc, t)!;
  }
}
