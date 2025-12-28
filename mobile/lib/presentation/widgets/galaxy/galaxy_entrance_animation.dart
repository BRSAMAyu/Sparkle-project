import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';

class GalaxyEntranceAnimation extends StatefulWidget {
  final VoidCallback onComplete;

  const GalaxyEntranceAnimation({
    required this.onComplete, super.key,
  });

  @override
  State<GalaxyEntranceAnimation> createState() => _GalaxyEntranceAnimationState();
}

class _GalaxyEntranceAnimationState extends State<GalaxyEntranceAnimation> with TickerProviderStateMixin {
  late AnimationController _mainController;
  late Animation<double> _scaleAnim;
  late Animation<double> _flashAnim;

  @override
  void initState() {
    super.initState();
    _mainController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    );

    // Scale from tiny to overshoot then settle
    _scaleAnim = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 50.0).chain(CurveTween(curve: Curves.easeInExpo)), weight: 40),
      TweenSequenceItem(tween: Tween(begin: 50.0, end: 1.0).chain(CurveTween(curve: Curves.elasticOut)), weight: 60),
    ]).animate(_mainController);

    // Opacity for flash
    _flashAnim = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 40),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.0), weight: 60),
    ]).animate(_mainController);

    _mainController.forward().whenComplete(() {
      widget.onComplete();
    });
  }

  @override
  void dispose() {
    _mainController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _mainController,
      builder: (context, child) {
        return Stack(
          alignment: Alignment.center,
          children: [
            // The expanding spark
            Transform.scale(
              scale: _scaleAnim.value,
              child: Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: DS.brandPrimary,
                  boxShadow: [
                    BoxShadow(
                      color: DS.brandPrimaryAccent.withValues(alpha: 0.5),
                      blurRadius: 20,
                      spreadRadius: 10,
                    ),
                    BoxShadow(
                      color: Colors.purpleAccent.withValues(alpha: 0.3),
                      blurRadius: 40,
                      spreadRadius: 20,
                    ),
                  ],
                ),
              ),
            ),
            
            // Full screen flash at impact
            Opacity(
              opacity: _flashAnim.value,
              child: Container(
                color: DS.brandPrimary.withValues(alpha: 0.3),
              ),
            ),

            // Text text
            if (_mainController.value > 0.4 && _mainController.value < 0.8)
              Opacity(
                 opacity: (_mainController.value - 0.4) / 0.2, // Fade in
                 child: const Text(
                   'SPARKLE',
                   style: TextStyle(
                     color: DS.brandPrimary,
                     fontSize: 32,
                     fontWeight: FontWeight.bold,
                     letterSpacing: 10,
                   ),
                 ),
              ),
          ],
        );
      },
    );
  }
}
