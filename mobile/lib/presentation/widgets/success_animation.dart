import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

class SuccessAnimation extends StatefulWidget {
  const SuccessAnimation({
    super.key,
    this.child,
    this.playAnimation = false,
    this.onAnimationComplete,
  });
  final Widget? child;
  final bool playAnimation;
  final VoidCallback? onAnimationComplete;

  @override
  State<SuccessAnimation> createState() => _SuccessAnimationState();
}

class _SuccessAnimationState extends State<SuccessAnimation> {
  late ConfettiController _confettiController;

  @override
  void initState() {
    super.initState();
    _confettiController = ConfettiController(duration: DS.durationSlow);
    if (widget.playAnimation) {
      _confettiController.play();
    }
    _confettiController.addListener(_confettiListener);
  }

  void _confettiListener() {
    if (_confettiController.state == ConfettiControllerState.stopped &&
        widget.onAnimationComplete != null) {
      widget.onAnimationComplete!();
    }
  }

  @override
  void didUpdateWidget(covariant SuccessAnimation oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.playAnimation && !oldWidget.playAnimation) {
      _confettiController.play();
    } else if (!widget.playAnimation && oldWidget.playAnimation) {
      _confettiController.stop();
    }
  }

  @override
  void dispose() {
    _confettiController.removeListener(_confettiListener);
    _confettiController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Stack(
        children: [
          if (widget.child != null) widget.child!,
          Align(
            alignment: Alignment.topCenter,
            child: ConfettiWidget(
              confettiController: _confettiController,
              blastDirectionality:
                  BlastDirectionality.explosive, // All directions
              colors: [
                DS.primaryBase,
                DS.accent,
                DS.success,
                DS.info,
              ], // Customize colors
              gravity: 0.3,
              emissionFrequency: 0.05,
              numberOfParticles: 20, // number of particles to emit
              maxBlastForce: 100,
              minBlastForce: 80,
            ),
          ),
        ],
      );
}
