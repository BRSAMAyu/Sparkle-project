import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/widgets/scene_atmosphere_layer.dart';

class SceneAudioScope extends StatefulWidget {
  const SceneAudioScope({
    required this.policy,
    required this.child,
    super.key,
    this.auroraStatus,
    this.enableAuroraAudio = true,
  });

  final SceneAudioPolicy policy;
  final Widget child;
  final String? auroraStatus;
  final bool enableAuroraAudio;

  @override
  State<SceneAudioScope> createState() => _SceneAudioScopeState();
}

class _SceneAudioScopeState extends State<SceneAudioScope> {
  Object? _bgmToken;
  Object? _auroraBgmToken;
  bool _ambientActivated = false;
  int _ambientRequestVersion = 0;
  String? _lastAuroraStatus;
  BgmTrack? _lastAuroraSceneTrack;

  @override
  void initState() {
    super.initState();
    unawaited(_configureAudio(initial: true));
  }

  @override
  void didUpdateWidget(covariant SceneAudioScope oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.policy != widget.policy ||
        oldWidget.auroraStatus != widget.auroraStatus ||
        oldWidget.enableAuroraAudio != widget.enableAuroraAudio) {
      unawaited(_configureAudio());
    }
  }

  Future<void> _configureAudio({bool initial = false}) async {
    final policy = widget.policy;
    final requestVersion = ++_ambientRequestVersion;

    if (policy.suppressBgm || policy.track == null) {
      if (_bgmToken != null) {
        unawaited(BgmService.deactivate(_bgmToken!));
        _bgmToken = null;
      }
    } else if (_bgmToken == null || initial) {
      _bgmToken = BgmService.activate(
        policy.track!,
        priority: policy.priority,
        switchBehavior: policy.switchBehavior,
      );
    } else {
      unawaited(
        BgmService.update(
          _bgmToken!,
          track: policy.track!,
          priority: policy.priority,
          switchBehavior: policy.switchBehavior,
        ),
      );
    }

    if (!policy.wantsAmbient) {
      if (_ambientActivated) {
        _ambientActivated = false;
        unawaited(SensoryFeedbackService.stopAmbient());
      }
      unawaited(_configureAuroraAudio(policy));
      return;
    }

    final ambientScene = policy.ambientScene ??
        await SensoryFeedbackService.getSavedAmbientScene();
    if (!mounted || requestVersion != _ambientRequestVersion) {
      return;
    }
    _ambientActivated = ambientScene != AmbientScene.none;
    if (_ambientActivated) {
      unawaited(SensoryFeedbackService.playAmbient(ambientScene));
      unawaited(_configureAuroraAudio(policy));
      return;
    }
    unawaited(SensoryFeedbackService.stopAmbient());
    unawaited(_configureAuroraAudio(policy));
  }

  Future<void> _configureAuroraAudio(SceneAudioPolicy policy) async {
    final status = widget.auroraStatus?.trim();
    final sceneTrack = policy.track;
    if (_lastAuroraStatus == status && _lastAuroraSceneTrack == sceneTrack) {
      return;
    }
    _lastAuroraStatus = status;
    _lastAuroraSceneTrack = sceneTrack;

    try {
      final enabled = widget.enableAuroraAudio &&
          await SensoryFeedbackService.isAuroraLinkageEnabled();
      _auroraBgmToken = await BgmService.applyAuroraStatus(
        status: status,
        token: _auroraBgmToken,
        sceneTrack: sceneTrack,
        enabled: enabled,
      );
    } catch (_) {
      // Audio linkage is ambient polish; never block the route surface.
    }
  }

  @override
  void dispose() {
    _ambientRequestVersion++;
    if (_bgmToken != null) {
      unawaited(BgmService.deactivate(_bgmToken!));
    }
    unawaited(BgmService.clearAuroraStatus(_auroraBgmToken));
    if (_ambientActivated && widget.policy.stopAmbientOnDispose) {
      unawaited(SensoryFeedbackService.stopAmbient());
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.policy.atmosphere == ExperienceAtmosphere.none) {
      return widget.child;
    }
    return Stack(
      fit: StackFit.expand,
      children: [
        widget.child,
        Positioned.fill(
          child: SceneAtmosphereLayer(
            atmosphere: widget.policy.atmosphere,
          ),
        ),
      ],
    );
  }
}
