import 'dart:async';

import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';
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
  });

  final bool play;
  final Widget? child;
  final VoidCallback? onComplete;
  final SparkleCelebrationIntensity intensity;
  final Alignment alignment;
  final bool enableSensory;
  final int? particleCount;
  final List<Color>? colors;

  @override
  State<SparkleConfetti> createState() => _SparkleConfettiState();
}

class _SparkleConfettiState extends State<SparkleConfetti> {
  late final ConfettiController _controller;
  bool _hasPlayed = false;
  int _registeredParticleCount = 0;

  Duration get _duration => switch (widget.intensity) {
        SparkleCelebrationIntensity.small =>
          const Duration(milliseconds: 900),
        SparkleCelebrationIntensity.medium => DS.durationSlow,
        SparkleCelebrationIntensity.large =>
          const Duration(milliseconds: 1800),
      };

  int get _particleCount => widget.particleCount ?? switch (widget.intensity) {
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
      _play();
    }
  }

  void _handleStateChange() {
    if (_controller.state == ConfettiControllerState.stopped) {
      widget.onComplete?.call();
    }
  }

  void _play() {
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
  Widget build(BuildContext context) => Stack(
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
                      DS.accent,
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
        ],
      );
}
