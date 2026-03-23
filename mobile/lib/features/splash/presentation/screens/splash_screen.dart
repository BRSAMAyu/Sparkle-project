import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';

class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
      body: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [DS.deepSpaceStart, DS.deepSpaceEnd],
          ),
        ),
        child: ContentConstraint(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SparkleStaggerItem(
                  index: 0,
                  motionToken: SparkleMotionToken.hero,
                  child: SparkleAttentionPulse(
                    glowColor: DS.brandPrimary,
                    child: Container(
                      width: 132,
                      height: 132,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: LinearGradient(
                          colors: [DS.brandPrimaryConst, DS.capsuleAccent],
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: DS.brandPrimary.withValues(alpha: 0.35),
                            blurRadius: 42,
                            spreadRadius: 10,
                          ),
                        ],
                      ),
                      child: const Icon(
                        Icons.whatshot_rounded,
                        size: 74,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                SparkleStaggerItem(
                  index: 1,
                  motionToken: SparkleMotionToken.hero,
                  child: Text(
                    'Sparkle',
                    style: TextStyle(
                      fontSize: 34,
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.secondary,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                SparkleStaggerItem(
                  index: 2,
                  child: Text(
                    '从第一秒开始，进入更聪明也更有温度的学习旅程。',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 15,
                      color: DS.textOnPrimary.withValues(alpha: 0.78),
                      height: 1.5,
                    ),
                  ),
                ),
                const SizedBox(height: 40),
                const SparkleStaggerItem(
                  index: 3,
                  child: CircularProgressIndicator(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
}
