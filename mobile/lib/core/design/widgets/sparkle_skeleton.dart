import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class SparkleSkeleton extends StatefulWidget {
  const SparkleSkeleton({
    super.key,
    this.width,
    this.height = 16,
    this.borderRadius = 8,
  });

  final double? width;
  final double height;
  final double borderRadius;

  @override
  State<SparkleSkeleton> createState() => _SparkleSkeletonState();
}

class _SparkleSkeletonState extends State<SparkleSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = context.reduceMotion;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = isDark ? DS.surfaceSecondary : DS.surfaceTertiary;
    final highlightColor = isDark ? DS.surfaceTertiary : DS.surfaceSecondary;

    final child = Container(
      width: widget.width,
      height: widget.height,
      decoration: BoxDecoration(
        color: baseColor,
        borderRadius: BorderRadius.circular(widget.borderRadius),
      ),
    );

    if (reduceMotion) {
      return child;
    }

    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: _controller,
        child: child,
        builder: (context, skeletonChild) {
          final t = _controller.value;
          final breathingScale =
              0.995 + (math.sin(t * math.pi * 2) + 1) * 0.0025;
          return Transform.scale(
            scale: breathingScale,
            child: ShaderMask(
              shaderCallback: (bounds) => LinearGradient(
                begin: Alignment(-1.5 + t * 2.5, -0.5),
                end: Alignment(-0.5 + t * 2.5, 0.5),
                colors: [
                  baseColor,
                  highlightColor,
                  baseColor,
                ],
                stops: const [0.1, 0.5, 0.9],
              ).createShader(bounds),
              blendMode: BlendMode.srcATop,
              child: skeletonChild,
            ),
          );
        },
      ),
    );
  }
}

class SparkleCardSkeleton extends StatelessWidget {
  const SparkleCardSkeleton({
    super.key,
    this.padding = const EdgeInsets.all(DS.spacing16),
  });

  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
        padding: padding,
        decoration: BoxDecoration(
          color: Theme.of(context).brightness == Brightness.dark
              ? DS.surfacePrimary
              : DS.surfacePanel,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: const [
            SparkleSkeleton(width: 148, height: 22, borderRadius: 10),
            SizedBox(height: DS.spacing12),
            SparkleSkeleton(height: 14, borderRadius: 8),
            SizedBox(height: DS.spacing8),
            SparkleSkeleton(width: 220, height: 14, borderRadius: 8),
            SizedBox(height: DS.spacing16),
            SparkleSkeleton(height: 10, borderRadius: 999),
          ],
        ),
      );
}

class SparkleListSkeleton extends StatelessWidget {
  const SparkleListSkeleton({
    super.key,
    this.count = 3,
    this.padding = const EdgeInsets.fromLTRB(
      DS.spacing16,
      DS.spacing12,
      DS.spacing16,
      DS.spacing32,
    ),
  });

  final int count;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => ListView.separated(
        physics: const NeverScrollableScrollPhysics(),
        padding: padding,
        itemCount: count,
        separatorBuilder: (_, __) => const SizedBox(height: DS.spacing12),
        itemBuilder: (context, index) => SparkleStaggerItem(
          index: index,
          motionToken: SparkleMotionToken.micro,
          child: const SparkleCardSkeleton(),
        ),
      );
}

class SparkleChatBubbleSkeleton extends StatelessWidget {
  const SparkleChatBubbleSkeleton({
    super.key,
    this.isUser = false,
  });

  final bool isUser;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
        child: Row(
          mainAxisAlignment:
              isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!isUser) ...[
              const SparkleSkeleton(
                width: 36,
                height: 36,
                borderRadius: 999,
              ),
              const SizedBox(width: DS.spacing12),
            ],
            Flexible(
              child: Container(
                padding: const EdgeInsets.all(DS.spacing12),
                decoration: BoxDecoration(
                  color: Theme.of(context).brightness == Brightness.dark
                      ? DS.surfaceSecondary
                      : DS.surfacePanel,
                  borderRadius: DS.borderRadius16,
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SparkleSkeleton(height: 14),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(width: 180, height: 14),
                    SizedBox(height: DS.spacing8),
                    SparkleSkeleton(width: 132, height: 14),
                  ],
                ),
              ),
            ),
            if (isUser) ...[
              const SizedBox(width: DS.spacing12),
              const SparkleSkeleton(
                width: 36,
                height: 36,
                borderRadius: 999,
              ),
            ],
          ],
        ),
      );
}
