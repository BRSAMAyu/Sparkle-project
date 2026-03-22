import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

class SceneAudioPolicy {
  const SceneAudioPolicy({
    this.track,
    this.priority = BgmPriority.route,
    this.useSavedAmbient = false,
    this.ambientScene,
    this.stopAmbientOnDispose = false,
    this.suppressBgm = false,
  });

  final BgmTrack? track;
  final BgmPriority priority;
  final bool useSavedAmbient;
  final AmbientScene? ambientScene;
  final bool stopAmbientOnDispose;
  final bool suppressBgm;

  static const Object _unset = Object();

  bool get wantsAmbient => useSavedAmbient || ambientScene != null;

  SceneAudioPolicy copyWith({
    BgmTrack? track,
    BgmPriority? priority,
    bool? useSavedAmbient,
    Object? ambientScene = _unset,
    bool? stopAmbientOnDispose,
    bool? suppressBgm,
  }) =>
      SceneAudioPolicy(
        track: track ?? this.track,
        priority: priority ?? this.priority,
        useSavedAmbient: useSavedAmbient ?? this.useSavedAmbient,
        ambientScene: identical(ambientScene, _unset)
            ? this.ambientScene
            : ambientScene as AmbientScene?,
        stopAmbientOnDispose: stopAmbientOnDispose ?? this.stopAmbientOnDispose,
        suppressBgm: suppressBgm ?? this.suppressBgm,
      );

  static const SceneAudioPolicy silent = SceneAudioPolicy(suppressBgm: true);
}
