import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _logoScale;
  late final Animation<double> _logoFade;
  late final Animation<double> _titleFade;
  late final Animation<double> _subtitleFade;
  late final Animation<double> _indicatorFade;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    unawaited(_ctrl.forward());

    _logoScale = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.0, 0.55, curve: Curves.easeOutBack),
    );
    _logoFade = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.0, 0.45, curve: Curves.easeOut),
    );
    _titleFade = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.3, 0.65, curve: Curves.easeOut),
    );
    _subtitleFade = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.45, 0.75, curve: Curves.easeOut),
    );
    _indicatorFade = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.65, 1.0, curve: Curves.easeOut),
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
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
                  // Logo — scale + fade
                  FadeTransition(
                    opacity: _logoFade,
                    child: ScaleTransition(
                      scale: _logoScale,
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
                  const SizedBox(height: DS.spacing24),
                  // App name — fade in
                  FadeTransition(
                    opacity: _titleFade,
                    child: Text(
                      'Sparkle',
                      style: TextStyle(
                        fontSize: 34,
                        fontWeight: DS.fontWeightBold,
                        color: Theme.of(context).colorScheme.secondary,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  // Subtitle — fade in
                  FadeTransition(
                    opacity: _subtitleFade,
                    child: Text(
                      context.l10n.splashSubtitle,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 15,
                        color: DS.textOnPrimary.withValues(alpha: 0.78),
                        height: 1.62,
                      ),
                    ),
                  ),
                  const SizedBox(height: DS.xl),
                  // Loading indicator — fade in last
                  FadeTransition(
                    opacity: _indicatorFade,
                    child: CircularProgressIndicator(
                      color: DS.textOnPrimary.withValues(alpha: 0.7),
                      strokeWidth: 2.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
