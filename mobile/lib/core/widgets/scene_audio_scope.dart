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
  });

  final SceneAudioPolicy policy;
  final Widget child;

  @override
  State<SceneAudioScope> createState() => _SceneAudioScopeState();
}

class _SceneAudioScopeState extends State<SceneAudioScope> {
  Object? _bgmToken;
  bool _ambientActivated = false;
  int _ambientRequestVersion = 0;

  @override
  void initState() {
    super.initState();
    unawaited(_configureAudio(initial: true));
  }

  @override
  void didUpdateWidget(covariant SceneAudioScope oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.policy != widget.policy) {
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
      );
    } else {
      unawaited(
        BgmService.update(
          _bgmToken!,
          track: policy.track!,
          priority: policy.priority,
        ),
      );
    }

    if (!policy.wantsAmbient) {
      if (_ambientActivated) {
        _ambientActivated = false;
        unawaited(SensoryFeedbackService.stopAmbient());
      }
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
      return;
    }
    unawaited(SensoryFeedbackService.stopAmbient());
  }

  @override
  void dispose() {
    _ambientRequestVersion++;
    if (_bgmToken != null) {
      unawaited(BgmService.deactivate(_bgmToken!));
    }
    if (_ambientActivated && widget.policy.stopAmbientOnDispose) {
      unawaited(SensoryFeedbackService.stopAmbient());
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Stack(
        fit: StackFit.expand,
        children: [
          widget.child,
          if (widget.policy.atmosphere != ExperienceAtmosphere.none)
            Positioned.fill(
              child: SceneAtmosphereLayer(
                atmosphere: widget.policy.atmosphere,
              ),
            ),
        ],
      );
}
