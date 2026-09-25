import 'dart:async';

import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/adaptive/emotion_responsive_theme.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/global_particle_counter.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

enum SparkleCelebrationIntensity { small, medium, large }

class SparkleConfetti extends StatefulWidget {
  const SparkleConfetti({
    super.key,
    this.play = false,
    this.child,
    this.onComplete,
    this.intensity = SparkleCelebrationIntensity.medium,
    this.alignment = Alignment.topCenter,
    this.enableSensory = true,
    this.particleCount,
    this.colors,
    this.evidenceText,
    this.messageText,
  });

  final bool play;
  final Widget? child;
  final VoidCallback? onComplete;
  final SparkleCelebrationIntensity intensity;
  final Alignment alignment;
  final bool enableSensory;
  final int? particleCount;
  final List<Color>? colors;
  final String? evidenceText;
  final String? messageText;

  @override
  State<SparkleConfetti> createState() => _SparkleConfettiState();
}

class _SparkleConfettiState extends State<SparkleConfetti> {
  late final ConfettiController _controller;
  bool _hasPlayed = false;
  int _registeredParticleCount = 0;

  /// build 期缓存的低刺激/挑战徽章抑制位（U-02）。
  ///
  /// [_play] 在 initState（inherited 访问不安全）与 didUpdateWidget 两个
  /// 时机被调用，build 先行缓存抑制位，播放路径据此整体短路——低刺激下
  /// 不再发射庆祝触感/声效、不再启动粒子控制器（此前仅视觉层被抑制，
  /// 属半截减法；庆祝态 celebrate × low 档预算粒子为 0、弹性撤除）。
  bool _celebrationSuppressed = false;

  Duration get _duration => switch (widget.intensity) {
        SparkleCelebrationIntensity.small => const Duration(milliseconds: 900),
        SparkleCelebrationIntensity.medium => DS.durationSlow,
        SparkleCelebrationIntensity.large => const Duration(milliseconds: 1800),
      };

  int get _particleCount =>
      widget.particleCount ??
      switch (widget.intensity) {
        SparkleCelebrationIntensity.small => 12,
        SparkleCelebrationIntensity.medium => 20,
        SparkleCelebrationIntensity.large => 34,
      };

  SensoryFeedbackEvent get _feedbackEvent => switch (widget.intensity) {
        SparkleCelebrationIntensity.small => SensoryFeedbackEvent.success,
        SparkleCelebrationIntensity.medium => SensoryFeedbackEvent.streak,
        SparkleCelebrationIntensity.large =>
          SensoryFeedbackEvent.achievementLegendary,
      };

  @override
  void initState() {
    super.initState();
    _controller = ConfettiController(duration: _duration)
      ..addListener(_handleStateChange);
    if (widget.play) {
      // 首帧 build 完成后再播：_celebrationSuppressed 由 build 缓存，
      // 低刺激挂载即播的场景不会漏发一次庆祝刺激。
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _play();
      });
    }
  }

  void _handleStateChange() {
    if (_controller.state == ConfettiControllerState.stopped) {
      widget.onComplete?.call();
    }
  }

  void _play() {
    if (_celebrationSuppressed) {
      return;
    }
    final desiredCount = _particleCount;
    if (_registeredParticleCount != desiredCount) {
      if (_registeredParticleCount > 0) {
        GlobalParticleCounter.releaseParticles(_registeredParticleCount);
        _registeredParticleCount = 0;
      }
      if (!GlobalParticleCounter.tryAddParticles(desiredCount)) {
        return;
      }
      _registeredParticleCount = desiredCount;
    }
    if (widget.enableSensory && !_hasPlayed) {
      _hasPlayed = true;
      unawaited(SensoryFeedbackService.emit(_feedbackEvent));
    }
    _controller.play();
  }

  @override
  void didUpdateWidget(covariant SparkleConfetti oldWidget) {
    super.didUpdateWidget(oldWidget);
    // 低刺激可在播放中生效（设置切换）：挂载后可安全读 inherited，
    // 即时停控制器并退回粒子预算，防止抑制生效后仍有残留庆祝刺激。
    if (context.hideChallengeBadges || context.emotionLowStimulus) {
      _celebrationSuppressed = true;
      _controller.stop();
      if (_registeredParticleCount > 0) {
        GlobalParticleCounter.releaseParticles(_registeredParticleCount);
        _registeredParticleCount = 0;
      }
      return;
    }
    _celebrationSuppressed = false;
    if (widget.play && !oldWidget.play) {
      _hasPlayed = false;
      _play();
    } else if (!widget.play && oldWidget.play) {
      _controller.stop();
      if (_registeredParticleCount > 0) {
        GlobalParticleCounter.releaseParticles(_registeredParticleCount);
        _registeredParticleCount = 0;
      }
    }
  }

  @override
  void dispose() {
    if (_registeredParticleCount > 0) {
      GlobalParticleCounter.releaseParticles(_registeredParticleCount);
    }
    _controller
      ..removeListener(_handleStateChange)
      ..dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // U-02：低刺激/隐藏挑战徽章 = 庆祝刺激整体短路（视觉 + 触感 + 控制器），
    // 不是空设置值。
    final suppressed =
        context.hideChallengeBadges || context.emotionLowStimulus;
    _celebrationSuppressed = suppressed;
    if (suppressed) {
      return widget.child ?? const SizedBox.shrink();
    }

    final evidence = widget.evidenceText?.trim();
    final message = widget.messageText?.trim();
    final hasFeedback = (evidence != null && evidence.isNotEmpty) ||
        (message != null && message.isNotEmpty);
    final scheme = Theme.of(context).colorScheme;

    return Stack(
      children: [
        if (widget.child != null) widget.child!,
        Align(
          alignment: widget.alignment,
          child: RepaintBoundary(
            child: ConfettiWidget(
              confettiController: _controller,
              blastDirectionality: BlastDirectionality.explosive,
              colors: widget.colors ??
                  [
                    DS.primaryBase,
                    DS.brandSecondary,
                    DS.success,
                    DS.info,
                    DS.warning,
                  ],
              gravity: widget.intensity == SparkleCelebrationIntensity.small
                  ? 0.34
                  : 0.28,
              emissionFrequency:
                  widget.intensity == SparkleCelebrationIntensity.large
                      ? 0.07
                      : 0.05,
              numberOfParticles: _particleCount,
              maxBlastForce:
                  widget.intensity == SparkleCelebrationIntensity.large
                      ? 120
                      : 100,
              minBlastForce:
                  widget.intensity == SparkleCelebrationIntensity.small
                      ? 60
                      : 80,
            ),
          ),
        ),
        if (hasFeedback)
          Align(
            alignment: Alignment.bottomCenter,
            child: SafeArea(
              minimum: const EdgeInsets.all(DS.spacing16),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainerHighest,
                    borderRadius: DS.borderRadius16,
                    border: Border.all(color: scheme.outlineVariant),
                    boxShadow: [
                      BoxShadow(
                        color: scheme.shadow.withValues(alpha: 0.16),
                        blurRadius: 18,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(DS.spacing14),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (message != null && message.isNotEmpty)
                          Text(
                            message,
                            style: Theme.of(context)
                                .textTheme
                                .titleSmall
                                ?.copyWith(
                                  color: scheme.onSurface,
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                        if (message != null &&
                            message.isNotEmpty &&
                            evidence != null &&
                            evidence.isNotEmpty)
                          const SizedBox(height: DS.spacing6),
                        if (evidence != null && evidence.isNotEmpty)
                          Text(
                            evidence,
                            style:
                                Theme.of(context).textTheme.bodySmall?.copyWith(
                                      color: scheme.onSurfaceVariant,
                                      height: 1.35,
                                    ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
