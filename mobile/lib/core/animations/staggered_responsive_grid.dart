import 'package:flutter/material.dart';
import 'package:sparkle/core/design/responsive_layout.dart';

class StaggeredResponsiveGrid extends StatefulWidget {
  const StaggeredResponsiveGrid({
    required this.builder,
    required this.itemCount,
    super.key,
    this.delay = const Duration(milliseconds: 50),
    this.duration = const Duration(milliseconds: 350),
    this.childAspectRatio,
  });
  final Widget Function(BuildContext, int, Animation<double>) builder;
  final int itemCount;
  final Duration delay;
  final Duration duration;
  final double? childAspectRatio;

  @override
  State<StaggeredResponsiveGrid> createState() =>
      _StaggeredResponsiveGridState();
}

class _StaggeredResponsiveGridState extends State<StaggeredResponsiveGrid>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    // Calculate total duration to cover all items
    final totalDuration = widget.duration + (widget.delay * widget.itemCount);

    _controller = AnimationController(
      duration: totalDuration,
      vsync: this,
    );
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ResponsiveGrid(
        childAspectRatio: widget.childAspectRatio,
        children: List.generate(widget.itemCount, (index) {
          final startTime = widget.delay.inMilliseconds * index;
          final endTime = startTime + widget.duration.inMilliseconds;
          final totalTime = _controller.duration!.inMilliseconds;

          final start = (startTime / totalTime).clamp(0.0, 1.0);
          final end = (endTime / totalTime).clamp(0.0, 1.0);

          final animation = CurvedAnimation(
            parent: _controller,
            curve: Interval(
              start,
              end,
              curve: Curves.easeOut,
            ),
          );

          return widget.builder(context, index, animation);
        }),
      );
}
