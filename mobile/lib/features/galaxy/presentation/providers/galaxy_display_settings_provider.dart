import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/providers/persistent_state_notifier.dart';

const double kGalaxyTextFadeThresholdMin = 0.18;
const double kGalaxyTextFadeThresholdMax = 1.05;
const double kGalaxyNodeSizeScaleMin = 0.75;
const double kGalaxyNodeSizeScaleMax = 1.35;
const double kGalaxyLinkThicknessScaleMin = 0.7;
const double kGalaxyLinkThicknessScaleMax = 1.5;
const double kGalaxyCenterForceMin = 0.0006;
const double kGalaxyCenterForceMax = 0.004;
const double kGalaxyRepelForceMin = 6000;
const double kGalaxyRepelForceMax = 22000;
const double kGalaxyLinkForceMin = 0.02;
const double kGalaxyLinkForceMax = 0.09;
const double kGalaxyLinkDistanceMin = 84;
const double kGalaxyLinkDistanceMax = 176;
const double kGalaxySectorAffinityMin = 0.0;
const double kGalaxySectorAffinityMax = 1.0;
const double kGalaxyRevealTrailStrengthMin = 0.0;
const double kGalaxyRevealTrailStrengthMax = 1.0;
const double kGalaxyReplaySpeedMin = 0.4;
const double kGalaxyReplaySpeedMax = 2.4;

@immutable
class GalaxyDisplaySettings {
  const GalaxyDisplaySettings({
    this.textFadeThreshold = 0.54,
    this.nodeSizeScale = 0.98,
    this.linkThicknessScale = 0.9,
    this.centerForce = 0.0019,
    this.repelForce = 9600,
    this.linkForce = 0.056,
    this.linkDistance = 116,
    this.sectorAffinity = 0.28,
    this.revealTrailStrength = 0.72,
    this.replaySpeed = 1.0,
  });

  final double textFadeThreshold;
  final double nodeSizeScale;
  final double linkThicknessScale;
  final double centerForce;
  final double repelForce;
  final double linkForce;
  final double linkDistance;
  final double sectorAffinity;
  final double revealTrailStrength;
  final double replaySpeed;

  Map<String, dynamic> toJson() => {
        'textFadeThreshold': textFadeThreshold,
        'nodeSizeScale': nodeSizeScale,
        'linkThicknessScale': linkThicknessScale,
        'centerForce': centerForce,
        'repelForce': repelForce,
        'linkForce': linkForce,
        'linkDistance': linkDistance,
        'sectorAffinity': sectorAffinity,
        'revealTrailStrength': revealTrailStrength,
        'replaySpeed': replaySpeed,
      };

  static GalaxyDisplaySettings? fromJson(Map<String, dynamic> json) {
    try {
      return GalaxyDisplaySettings(
        textFadeThreshold: _readDouble(
          json['textFadeThreshold'],
          fallback: const GalaxyDisplaySettings().textFadeThreshold,
          min: kGalaxyTextFadeThresholdMin,
          max: kGalaxyTextFadeThresholdMax,
        ),
        nodeSizeScale: _readDouble(
          json['nodeSizeScale'],
          fallback: const GalaxyDisplaySettings().nodeSizeScale,
          min: kGalaxyNodeSizeScaleMin,
          max: kGalaxyNodeSizeScaleMax,
        ),
        linkThicknessScale: _readDouble(
          json['linkThicknessScale'],
          fallback: const GalaxyDisplaySettings().linkThicknessScale,
          min: kGalaxyLinkThicknessScaleMin,
          max: kGalaxyLinkThicknessScaleMax,
        ),
        centerForce: _readDouble(
          json['centerForce'],
          fallback: const GalaxyDisplaySettings().centerForce,
          min: kGalaxyCenterForceMin,
          max: kGalaxyCenterForceMax,
        ),
        repelForce: _readDouble(
          json['repelForce'],
          fallback: const GalaxyDisplaySettings().repelForce,
          min: kGalaxyRepelForceMin,
          max: kGalaxyRepelForceMax,
        ),
        linkForce: _readDouble(
          json['linkForce'],
          fallback: const GalaxyDisplaySettings().linkForce,
          min: kGalaxyLinkForceMin,
          max: kGalaxyLinkForceMax,
        ),
        linkDistance: _readDouble(
          json['linkDistance'],
          fallback: const GalaxyDisplaySettings().linkDistance,
          min: kGalaxyLinkDistanceMin,
          max: kGalaxyLinkDistanceMax,
        ),
        sectorAffinity: _readDouble(
          json['sectorAffinity'],
          fallback: const GalaxyDisplaySettings().sectorAffinity,
          min: kGalaxySectorAffinityMin,
          max: kGalaxySectorAffinityMax,
        ),
        revealTrailStrength: _readDouble(
          json['revealTrailStrength'],
          fallback: const GalaxyDisplaySettings().revealTrailStrength,
          min: kGalaxyRevealTrailStrengthMin,
          max: kGalaxyRevealTrailStrengthMax,
        ),
        replaySpeed: _readDouble(
          json['replaySpeed'],
          fallback: const GalaxyDisplaySettings().replaySpeed,
          min: kGalaxyReplaySpeedMin,
          max: kGalaxyReplaySpeedMax,
        ),
      );
    } catch (_) {
      return const GalaxyDisplaySettings();
    }
  }

  GalaxyDisplaySettings copyWith({
    double? textFadeThreshold,
    double? nodeSizeScale,
    double? linkThicknessScale,
    double? centerForce,
    double? repelForce,
    double? linkForce,
    double? linkDistance,
    double? sectorAffinity,
    double? revealTrailStrength,
    double? replaySpeed,
  }) =>
      GalaxyDisplaySettings(
        textFadeThreshold: textFadeThreshold ?? this.textFadeThreshold,
        nodeSizeScale: nodeSizeScale ?? this.nodeSizeScale,
        linkThicknessScale: linkThicknessScale ?? this.linkThicknessScale,
        centerForce: centerForce ?? this.centerForce,
        repelForce: repelForce ?? this.repelForce,
        linkForce: linkForce ?? this.linkForce,
        linkDistance: linkDistance ?? this.linkDistance,
        sectorAffinity: sectorAffinity ?? this.sectorAffinity,
        revealTrailStrength: revealTrailStrength ?? this.revealTrailStrength,
        replaySpeed: replaySpeed ?? this.replaySpeed,
      );

  double labelDensityForScale(
    double scale, {
    required int importance,
    required bool emphasized,
  }) {
    if (emphasized) {
      return 1;
    }

    var start = textFadeThreshold;
    if (importance >= 5) {
      start -= 0.18;
    } else if (importance >= 3) {
      start -= 0.08;
    }
    start =
        start.clamp(kGalaxyTextFadeThresholdMin, kGalaxyTextFadeThresholdMax);
    final end = (start + 0.22).clamp(
      start + 0.02,
      kGalaxyTextFadeThresholdMax + 0.26,
    );
    if (scale <= start) {
      return 0;
    }
    if (scale >= end) {
      return 1;
    }
    return ((scale - start) / (end - start)).clamp(0.0, 1.0);
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is GalaxyDisplaySettings &&
          runtimeType == other.runtimeType &&
          textFadeThreshold == other.textFadeThreshold &&
          nodeSizeScale == other.nodeSizeScale &&
          linkThicknessScale == other.linkThicknessScale &&
          centerForce == other.centerForce &&
          repelForce == other.repelForce &&
          linkForce == other.linkForce &&
          linkDistance == other.linkDistance &&
          sectorAffinity == other.sectorAffinity &&
          revealTrailStrength == other.revealTrailStrength &&
          replaySpeed == other.replaySpeed;

  @override
  int get hashCode => Object.hash(
        textFadeThreshold,
        nodeSizeScale,
        linkThicknessScale,
        centerForce,
        repelForce,
        linkForce,
        linkDistance,
        sectorAffinity,
        revealTrailStrength,
        replaySpeed,
      );
}

double galaxySpotlightNodeOpacity(
  String nodeId,
  Set<String> spotlightNodeIds,
) {
  if (spotlightNodeIds.isEmpty) {
    return 1;
  }
  return spotlightNodeIds.contains(nodeId) ? 1 : 0.2;
}

double galaxySpotlightLabelOpacity({
  required String nodeId,
  required String? spotlightAnchorId,
  required Set<String> spotlightNodeIds,
}) {
  if (spotlightNodeIds.isEmpty) {
    return 1;
  }
  if (nodeId == spotlightAnchorId) {
    return 1;
  }
  return spotlightNodeIds.contains(nodeId) ? 0.94 : 0.08;
}

double galaxySpotlightEdgeOpacity({
  required String sourceId,
  required String targetId,
  required String? spotlightAnchorId,
  required Set<String> spotlightNodeIds,
}) {
  if (spotlightNodeIds.isEmpty) {
    return 1;
  }

  final sourceInSpotlight = spotlightNodeIds.contains(sourceId);
  final targetInSpotlight = spotlightNodeIds.contains(targetId);
  if (sourceInSpotlight && targetInSpotlight) {
    if (sourceId == spotlightAnchorId || targetId == spotlightAnchorId) {
      return 1;
    }
    return 0.9;
  }
  if (sourceInSpotlight || targetInSpotlight) {
    return 0.24;
  }
  return 0.12;
}

double _readDouble(
  Object? value, {
  required double fallback,
  required double min,
  required double max,
}) =>
    (value as num?)?.toDouble().clamp(min, max) ?? fallback;

final galaxyDisplaySettingsProvider =
    StateNotifierProvider<GalaxyDisplaySettingsNotifier, GalaxyDisplaySettings>(
  GalaxyDisplaySettingsNotifier.new,
);

class GalaxyDisplaySettingsNotifier
    extends PersistentStateNotifier<GalaxyDisplaySettings> {
  GalaxyDisplaySettingsNotifier(super.ref)
      : super(
          namespace: 'galaxy',
          key: 'display_settings',
          defaultValue: const GalaxyDisplaySettings(),
          toJson: (state) => state.toJson(),
          fromJson: GalaxyDisplaySettings.fromJson,
        );

  void updateWith(
    GalaxyDisplaySettings Function(GalaxyDisplaySettings current) transform,
  ) {
    state = transform(state);
  }

  void resetToDefaults() {
    state = const GalaxyDisplaySettings();
  }
}
