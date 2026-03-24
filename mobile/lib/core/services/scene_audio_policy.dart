import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

enum ExperienceAtmosphere {
  none,
  dashboardGlow,
  galaxyDrift,
  achievementGlow,
  focusBreath,
  socialWarm,
  seedsOrganic,
  insightsMist,
}

class SceneAudioPolicy {
  const SceneAudioPolicy({
    this.track,
    this.priority = BgmPriority.route,
    this.useSavedAmbient = false,
    this.ambientScene,
    this.atmosphere = ExperienceAtmosphere.none,
    this.stopAmbientOnDispose = false,
    this.suppressBgm = false,
  });

  final BgmTrack? track;
  final BgmPriority priority;
  final bool useSavedAmbient;
  final AmbientScene? ambientScene;
  final ExperienceAtmosphere atmosphere;
  final bool stopAmbientOnDispose;
  final bool suppressBgm;

  static const Object _unset = Object();

  bool get wantsAmbient => useSavedAmbient || ambientScene != null;

  SceneAudioPolicy copyWith({
    BgmTrack? track,
    BgmPriority? priority,
    bool? useSavedAmbient,
    Object? ambientScene = _unset,
    ExperienceAtmosphere? atmosphere,
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
        atmosphere: atmosphere ?? this.atmosphere,
        stopAmbientOnDispose: stopAmbientOnDispose ?? this.stopAmbientOnDispose,
        suppressBgm: suppressBgm ?? this.suppressBgm,
      );

  static const SceneAudioPolicy silent = SceneAudioPolicy(suppressBgm: true);
}
