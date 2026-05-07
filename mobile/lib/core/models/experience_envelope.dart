class ExperienceEnvelope {
  const ExperienceEnvelope({
    this.traceId,
    this.turnId,
    this.userState = const {},
    this.profileContext = const {},
    this.structuredCognitiveAdjustments = const [],
    this.presentationStyle,
    this.toneVariant,
    this.socialContextPresentation,
    this.sessionAdaptation,
    this.raw = const {},
    this.updatedAt,
  });

  factory ExperienceEnvelope.fromMetadata(Map<String, dynamic> metadata) {
    final profileContext = _mapValue(metadata['profile_context']);
    final userState = _mapValue(
      metadata['user_state_v1'] ?? profileContext['user_state_v1'],
    );
    final uxTurn = _mapValue(metadata['ux_turn']);
    return ExperienceEnvelope(
      traceId: _stringValue(metadata['trace_id']),
      turnId: _stringValue(metadata['turn_id']),
      userState: userState,
      profileContext: profileContext,
      structuredCognitiveAdjustments: _mapList(
        metadata['structured_cognitive_adjustments'] ??
            profileContext['structured_cognitive_adjustments'],
      ),
      presentationStyle: _stringValue(uxTurn['presentation_style']),
      toneVariant: _stringValue(uxTurn['tone_variant']),
      socialContextPresentation: _mapValue(uxTurn['social_context_presentation']),
      sessionAdaptation: _mapValue(metadata['session_adaptation']),
      raw: metadata,
      updatedAt: DateTime.now(),
    );
  }

  final String? traceId;
  final String? turnId;
  final Map<String, dynamic> userState;
  final Map<String, dynamic> profileContext;
  final List<Map<String, dynamic>> structuredCognitiveAdjustments;
  final String? presentationStyle;
  final String? toneVariant;
  final Map<String, dynamic>? socialContextPresentation;
  final Map<String, dynamic>? sessionAdaptation;
  final Map<String, dynamic> raw;
  final DateTime? updatedAt;

  bool get isEmpty =>
      userState.isEmpty &&
      profileContext.isEmpty &&
      structuredCognitiveAdjustments.isEmpty &&
      presentationStyle == null &&
      toneVariant == null &&
      (socialContextPresentation?.isEmpty ?? true) &&
      (sessionAdaptation?.isEmpty ?? true);

  bool get hasAdjustments => structuredCognitiveAdjustments.isNotEmpty;
  bool get hasPresentationMeta =>
      presentationStyle != null || toneVariant != null;
  bool get hasSocialContext => socialContextPresentation?.isNotEmpty ?? false;
  bool get hasSessionAdaptation => sessionAdaptation?.isNotEmpty ?? false;

  ExperienceEnvelope merge(ExperienceEnvelope next) {
    final nextSocial = next.socialContextPresentation;
    final nextSession = next.sessionAdaptation;
    return ExperienceEnvelope(
      traceId: next.traceId ?? traceId,
      turnId: next.turnId ?? turnId,
      userState: {...userState, ...next.userState},
      profileContext: {...profileContext, ...next.profileContext},
      structuredCognitiveAdjustments: next.hasAdjustments
          ? next.structuredCognitiveAdjustments
          : structuredCognitiveAdjustments,
      presentationStyle: next.presentationStyle ?? presentationStyle,
      toneVariant: next.toneVariant ?? toneVariant,
      socialContextPresentation:
          (nextSocial?.isNotEmpty ?? false) ? nextSocial : socialContextPresentation,
      sessionAdaptation:
          (nextSession?.isNotEmpty ?? false) ? nextSession : sessionAdaptation,
      raw: {...raw, ...next.raw},
      updatedAt: next.updatedAt ?? updatedAt,
    );
  }
}

Map<String, dynamic> _mapValue(Object? raw) {
  if (raw is Map<String, dynamic>) return raw;
  if (raw is Map<Object?, Object?>) return Map<String, dynamic>.from(raw);
  return const {};
}

List<Map<String, dynamic>> _mapList(Object? raw) {
  if (raw is! List) return const [];
  return raw
      .whereType<Map<Object?, Object?>>()
      .map(Map<String, dynamic>.from)
      .toList(growable: false);
}

String? _stringValue(Object? raw) {
  final value = raw?.toString().trim();
  return value == null || value.isEmpty ? null : value;
}
