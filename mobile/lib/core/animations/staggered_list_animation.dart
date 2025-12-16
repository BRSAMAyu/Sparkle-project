import 'package:flutter/material.dart';

class StaggeredListAnimation extends StatefulWidget {
  final Widget Function(BuildContext, int, Animation<double>) builder;
  final int itemCount;
  final Duration delay;
  final Duration duration;

  const StaggeredListAnimation({
    super.key,
    required this.builder,
    required this.itemCount,
    this.delay = const Duration(milliseconds: 50),
    this.duration = const Duration(milliseconds: 350),
  });

  @override
  _StaggeredListAnimationState createState() => _StaggeredListAnimationState();
}

class _StaggeredListAnimationState extends State<StaggeredListAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: widget.duration,
      vsync: this,
    );
    _controller.forward();
  }

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      itemCount: widget.itemCount,
      padding: EdgeInsets.zero, // Allow parent to control padding
      physics: const NeverScrollableScrollPhysics(), // Usually wrapped in scroll view or expanded
      shrinkWrap: true,
      itemBuilder: (context, index) {
        final delay = widget.delay.inMilliseconds * index;
        final animation = CurvedAnimation(
          parent: _controller,
          curve: Interval(
            (delay / (widget.duration.inMilliseconds + delay)).clamp(0.0, 1.0),
            1.0,
            curve: Curves.easeOut,
          ),
        );

        return widget.builder(context, index, animation);
      },
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
