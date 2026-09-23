import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/navigation/cold_start_motion.dart';

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
  late final Animation<double> _brandFade;

  @override
  void initState() {
    super.initState();
    // N20（A-SPEC4）：splash 四段并两段、900ms → ColdStartMotion.splash
    // （scene 档 400ms，D-3「splash ≤400ms 一轮」执行口径）。认证判定与
    // 本动画并行（auth stale-while-revalidate + 路由品牌窗），不再把
    // splash 拉成加载闸；落地段与第二段尾部交叠（crossfade 盖入）。
    final reduceMotion = WidgetsBinding
        .instance.platformDispatcher.accessibilityFeatures.disableAnimations;
    _ctrl = AnimationController(
      vsync: this,
      duration: reduceMotion ? Duration.zero : ColdStartMotion.splash,
    );
    unawaited(_ctrl.forward());

    // 段一：logo（scale + fade 同轴，即首帧渐显——原全壳 _ColdStartFade
    // 320ms 已并入此段，app 级不再另起一段）。
    _logoScale = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.0, 0.6, curve: Curves.easeOutBack),
    );
    _logoFade = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.0, 0.55, curve: AnimationSystem.easeOut),
    );
    // 段二：品牌文 + 副标题 + 指示器合为一段，与 logo 段尾部并行。
    _brandFade = CurvedAnimation(
      parent: _ctrl,
      curve: const Interval(0.35, 1.0, curve: AnimationSystem.easeOut),
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
                  // 段二：品牌文（标题+副标题+指示器）单段渐显
                  FadeTransition(
                    opacity: _brandFade,
                    child: Column(
                      children: [
                        Text(
                          'Sparkle',
                          style: TextStyle(
                            fontSize: 34,
                            fontWeight: DS.fontWeightBold,
                            color: Theme.of(context).colorScheme.secondary,
                            letterSpacing: 1.2,
                          ),
                        ),
                        const SizedBox(height: DS.spacing12),
                        Text(
                          context.l10n.splashSubtitle,
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 15,
                            color: DS.textOnPrimary.withValues(alpha: 0.78),
                            height: 1.62,
                          ),
                        ),
                        const SizedBox(height: DS.xl),
                        LoadingIndicator(
                          color: DS.textOnPrimary.withValues(alpha: 0.7),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}
