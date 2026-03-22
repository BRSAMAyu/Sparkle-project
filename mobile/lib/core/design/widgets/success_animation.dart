import 'package:flutter/material.dart';
import 'package:sparkle/core/design/widgets/sparkle_confetti.dart';

class SuccessAnimation extends StatefulWidget {
  const SuccessAnimation({
    super.key,
    this.child,
    this.playAnimation = false,
    this.onAnimationComplete,
    this.intensity = SparkleCelebrationIntensity.medium,
  });
  final Widget? child;
  final bool playAnimation;
  final VoidCallback? onAnimationComplete;
  final SparkleCelebrationIntensity intensity;

  @override
  State<SuccessAnimation> createState() => _SuccessAnimationState();
}

class _SuccessAnimationState extends State<SuccessAnimation> {
  @override
  Widget build(BuildContext context) => SparkleConfetti(
        play: widget.playAnimation,
        intensity: widget.intensity,
        onComplete: widget.onAnimationComplete,
        child: widget.child,
      );
}
