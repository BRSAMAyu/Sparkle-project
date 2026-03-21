import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;

class SparkleStaggerItem extends StatefulWidget {
  const SparkleStaggerItem({
    required this.index,
    required this.child,
    super.key,
    this.axis = Axis.vertical,
    this.initialDelay = const Duration(milliseconds: 20),
    this.stepDelay = const Duration(milliseconds: 50),
    this.offset = 0.06,
    this.beginScale = 0.985,
    this.motionToken = SparkleMotionToken.standard,
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
      final delay = widget.initialDelay + (widget.stepDelay * widget.index);
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
    final duration = DS.motionDuration(widget.motionToken);
    final curve = DS.motionCurve(widget.motionToken);
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
