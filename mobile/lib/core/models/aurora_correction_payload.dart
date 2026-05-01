import 'package:uuid/uuid.dart';

enum AuroraCorrectionSurface {
  dashboard('dashboard'),
  chat('chat'),
  statusBand('status_band'),
  push('push'),
  coreSession('core_session');

  const AuroraCorrectionSurface(this.value);

  final String value;
}

enum AuroraCorrectionSource {
  freeformInput('freeform_input'),
  predictedChip('predicted_chip'),
  calibrationOverride('calibration_override');

  const AuroraCorrectionSource(this.value);

  final String value;
}

class AuroraCorrectionPayload {
  AuroraCorrectionPayload({
    required this.surface,
    required this.source,
    required this.semanticValue,
    required this.label,
    required this.freeformText,
    required this.isFreeform,
    required this.isDisconfirming,
    required this.bandStatus,
    String? telemetryId,
    String? groupId,
    this.conversationId = '',
    this.messageId = '',
  })  : telemetryId = _nonEmptyOr(telemetryId, _uuid.v4()),
        groupId = _nonEmptyOr(groupId, _sessionGroupId);

  factory AuroraCorrectionPayload.freeform({
    required AuroraCorrectionSurface surface,
    required String semanticValue,
    required String label,
    required String freeformText,
    required bool isDisconfirming,
    required String bandStatus,
    String? telemetryId,
    String? groupId,
    String conversationId = '',
    String messageId = '',
  }) =>
      AuroraCorrectionPayload(
        surface: surface,
        source: AuroraCorrectionSource.freeformInput,
        semanticValue: semanticValue,
        label: label,
        freeformText: freeformText,
        isFreeform: true,
        isDisconfirming: isDisconfirming,
        bandStatus: bandStatus,
        telemetryId: telemetryId,
        groupId: groupId,
        conversationId: conversationId,
        messageId: messageId,
      );

  factory AuroraCorrectionPayload.chip({
    required AuroraCorrectionSurface surface,
    required String semanticValue,
    required String label,
    required bool isDisconfirming,
    required String bandStatus,
    String? telemetryId,
    String? groupId,
    String conversationId = '',
    String messageId = '',
  }) =>
      AuroraCorrectionPayload(
        surface: surface,
        source: AuroraCorrectionSource.predictedChip,
        semanticValue: semanticValue,
        label: label,
        freeformText: '',
        isFreeform: false,
        isDisconfirming: isDisconfirming,
        bandStatus: bandStatus,
        telemetryId: telemetryId,
        groupId: groupId,
        conversationId: conversationId,
        messageId: messageId,
      );

  factory AuroraCorrectionPayload.calibrationOverride({
    required AuroraCorrectionSurface surface,
    required String semanticValue,
    required String label,
    required String bandStatus,
    String? telemetryId,
    String? groupId,
    String conversationId = '',
    String messageId = '',
  }) =>
      AuroraCorrectionPayload(
        surface: surface,
        source: AuroraCorrectionSource.calibrationOverride,
        semanticValue: semanticValue,
        label: label,
        freeformText: '',
        isFreeform: false,
        isDisconfirming: false,
        bandStatus: bandStatus,
        telemetryId: telemetryId,
        groupId: groupId,
        conversationId: conversationId,
        messageId: messageId,
      );

  factory AuroraCorrectionPayload.fromJson(Map<String, dynamic> json) {
    final surface = _surfaceFromValue(json['surface'] as String?);
    final legacyType = json['type'] as String?;
    final source = _sourceFromValue(json['source'] as String?, legacyType);
    final freeformText = json['freeform_text'] as String? ?? '';
    return AuroraCorrectionPayload(
      surface: surface,
      source: source,
      semanticValue: json['semantic_value'] as String? ?? '',
      label: json['label'] as String? ?? freeformText,
      freeformText: freeformText,
      isFreeform: json['is_freeform'] as bool? ??
          source == AuroraCorrectionSource.freeformInput,
      isDisconfirming: json['is_disconfirming'] as bool? ?? false,
      bandStatus: json['band_status'] as String? ?? '',
      telemetryId: json['telemetry_id'] as String?,
      groupId: json['group_id'] as String?,
      conversationId: json['conversation_id'] as String? ?? '',
      messageId: json['message_id'] as String? ?? '',
    );
  }

  static const Uuid _uuid = Uuid();
  static final String _sessionGroupId =
      'aurora_correction_session_${_uuid.v4()}';

  final AuroraCorrectionSurface surface;
  final AuroraCorrectionSource source;
  final String semanticValue;
  final String label;
  final String freeformText;
  final bool isFreeform;
  final bool isDisconfirming;
  final String bandStatus;
  final String telemetryId;
  final String groupId;
  final String conversationId;
  final String messageId;

  AuroraCorrectionPayload copyWith({
    AuroraCorrectionSurface? surface,
    AuroraCorrectionSource? source,
    String? semanticValue,
    String? label,
    String? freeformText,
    bool? isFreeform,
    bool? isDisconfirming,
    String? bandStatus,
    String? telemetryId,
    String? groupId,
    String? conversationId,
    String? messageId,
  }) =>
      AuroraCorrectionPayload(
        surface: surface ?? this.surface,
        source: source ?? this.source,
        semanticValue: semanticValue ?? this.semanticValue,
        label: label ?? this.label,
        freeformText: freeformText ?? this.freeformText,
        isFreeform: isFreeform ?? this.isFreeform,
        isDisconfirming: isDisconfirming ?? this.isDisconfirming,
        bandStatus: bandStatus ?? this.bandStatus,
        telemetryId: telemetryId ?? this.telemetryId,
        groupId: groupId ?? this.groupId,
        conversationId: conversationId ?? this.conversationId,
        messageId: messageId ?? this.messageId,
      );

  Map<String, dynamic> toJson() => {
        'surface': surface.value,
        'source': source.value,
        'semantic_value': semanticValue,
        'label': label,
        'freeform_text': freeformText,
        'is_freeform': isFreeform,
        'is_disconfirming': isDisconfirming,
        'band_status': bandStatus,
        'telemetry_id': telemetryId,
        'group_id': groupId,
        'conversation_id': conversationId,
        'message_id': messageId,
      };

  static String _nonEmptyOr(String? value, String fallback) {
    final trimmed = value?.trim();
    return trimmed == null || trimmed.isEmpty ? fallback : trimmed;
  }

  static AuroraCorrectionSurface _surfaceFromValue(String? value) {
    for (final surface in AuroraCorrectionSurface.values) {
      if (surface.value == value) return surface;
    }
    return AuroraCorrectionSurface.chat;
  }

  static AuroraCorrectionSource _sourceFromValue(
    String? value, [
    String? type,
  ]) {
    for (final source in AuroraCorrectionSource.values) {
      if (source.value == value) return source;
    }
    if (type == 'freeform') return AuroraCorrectionSource.freeformInput;
    if (type == 'cooldown_override') {
      return AuroraCorrectionSource.calibrationOverride;
    }
    return AuroraCorrectionSource.predictedChip;
  }
}
