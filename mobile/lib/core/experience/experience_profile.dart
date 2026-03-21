import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/bgm_service.dart';
import 'package:sparkle/core/services/scene_audio_policy.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

enum ExperienceInfoDensity {
  compact,
  balanced,
  immersive,
}

class ExperienceProfile {
  const ExperienceProfile({
    required this.name,
    required this.pageRole,
    required this.motionToken,
    required this.routeTransition,
    required this.defaultTrack,
    required this.surfaceBorderOpacity,
    required this.surfaceGlowOpacity,
    required this.infoDensity,
    required this.primaryFeedback,
    this.preferSavedAmbient = false,
  });

  final String name;
  final SparklePageRole pageRole;
  final SparkleMotionToken motionToken;
  final SharedAxisTransitionType routeTransition;
  final BgmTrack defaultTrack;
  final double surfaceBorderOpacity;
  final double surfaceGlowOpacity;
  final ExperienceInfoDensity infoDensity;
  final SensoryFeedbackEvent primaryFeedback;
  final bool preferSavedAmbient;

  SceneAudioPolicy audioPolicy({
    BgmTrack? trackOverride,
    BgmPriority priority = BgmPriority.route,
    bool? useSavedAmbient,
  }) =>
      SceneAudioPolicy(
        track: trackOverride ?? defaultTrack,
        priority: priority,
        useSavedAmbient: useSavedAmbient ?? preferSavedAmbient,
        stopAmbientOnDispose: useSavedAmbient ?? preferSavedAmbient,
      );

  BoxDecoration decorationFor(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final glowOpacity = isDark ? surfaceGlowOpacity : surfaceGlowOpacity * 0.78;
    return BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          DS.surfacePrimary,
          Color.alphaBlend(
            accent.withValues(alpha: glowOpacity),
            DS.surfaceSecondary,
          ),
          DS.surfacePrimary,
        ],
      ),
    );
  }

  Color get accent {
    switch (name) {
      case 'focusImmersive':
        return DS.info;
      case 'assistantFlow':
        return DS.brandPrimary;
      case 'dashboardProductive':
        return DS.capsuleAccent;
      case 'socialWarm':
        return DS.warning;
      case 'celebrationRare':
        return DS.rarityEpic;
      default:
        return DS.primaryBase;
    }
  }
}

class ExperienceProfiles {
  ExperienceProfiles._();

  static const focusImmersive = ExperienceProfile(
    name: 'focusImmersive',
    pageRole: SparklePageRole.immersive,
    motionToken: SparkleMotionToken.scene,
    routeTransition: SharedAxisTransitionType.scaled,
    defaultTrack: BgmTrack.focusDeep,
    surfaceBorderOpacity: 0.18,
    surfaceGlowOpacity: 0.12,
    infoDensity: ExperienceInfoDensity.immersive,
    primaryFeedback: SensoryFeedbackEvent.confirm,
    preferSavedAmbient: true,
  );

  static const assistantFlow = ExperienceProfile(
    name: 'assistantFlow',
    pageRole: SparklePageRole.content,
    motionToken: SparkleMotionToken.scene,
    routeTransition: SharedAxisTransitionType.horizontal,
    defaultTrack: BgmTrack.chat,
    surfaceBorderOpacity: 0.14,
    surfaceGlowOpacity: 0.08,
    infoDensity: ExperienceInfoDensity.balanced,
    primaryFeedback: SensoryFeedbackEvent.messageSend,
  );

  static const dashboardProductive = ExperienceProfile(
    name: 'dashboardProductive',
    pageRole: SparklePageRole.dashboard,
    motionToken: SparkleMotionToken.standard,
    routeTransition: SharedAxisTransitionType.horizontal,
    defaultTrack: BgmTrack.dashboard,
    surfaceBorderOpacity: 0.12,
    surfaceGlowOpacity: 0.08,
    infoDensity: ExperienceInfoDensity.compact,
    primaryFeedback: SensoryFeedbackEvent.navigation,
  );

  static const socialWarm = ExperienceProfile(
    name: 'socialWarm',
    pageRole: SparklePageRole.content,
    motionToken: SparkleMotionToken.standard,
    routeTransition: SharedAxisTransitionType.horizontal,
    defaultTrack: BgmTrack.community,
    surfaceBorderOpacity: 0.16,
    surfaceGlowOpacity: 0.09,
    infoDensity: ExperienceInfoDensity.balanced,
    primaryFeedback: SensoryFeedbackEvent.selection,
  );

  static const celebrationRare = ExperienceProfile(
    name: 'celebrationRare',
    pageRole: SparklePageRole.immersive,
    motionToken: SparkleMotionToken.hero,
    routeTransition: SharedAxisTransitionType.scaled,
    defaultTrack: BgmTrack.celebration,
    surfaceBorderOpacity: 0.22,
    surfaceGlowOpacity: 0.14,
    infoDensity: ExperienceInfoDensity.immersive,
    primaryFeedback: SensoryFeedbackEvent.achievementRare,
  );
}
