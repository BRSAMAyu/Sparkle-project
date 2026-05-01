import 'dart:async';

import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/chat/presentation/providers/aurora_status_provider.dart';

/// Records user interactions with Aurora predicted reply chips.
///
/// Chip telemetry feeds Aurora's model update pipeline.
/// Freeform corrections and disconfirming selections are especially
/// important signal sources — they help Aurora learn where it was wrong.
class AuroraTelemetryService {
  const AuroraTelemetryService(this._apiClient);

  final ApiClient _apiClient;

  Future<void> recordChipSelected({
    required AuroraPredictedReplyOption option,
    required String groupId,
    required String bandStatus,
    String? conversationId,
    String? sessionId,
  }) async {
    try {
      await _apiClient.post<void>(
        ApiEndpoints.auroraChipTelemetry,
        data: {
          'chip_id': option.id,
          'telemetry_id': option.telemetryId,
          'semantic_value': option.semanticValue,
          'is_freeform': option.isFreeform,
          'is_disconfirming': option.isDisconfirming,
          'context_source': option.contextSource,
          'band_status': bandStatus,
          'conversation_id': conversationId,
          'session_id': sessionId,
          'group_id': groupId,
        },
      );
    } catch (_) {
      // Telemetry failures must never propagate to the user.
    }
  }

  Future<void> recordStatusBandCorrection({
    required String label,
    required String semanticValue,
    required bool isDisconfirming,
    required String bandStatus,
    bool isFreeform = false,
    String telemetryId = '',
    String? groupId,
    String? freeformText,
  }) async {
    try {
      await _apiClient.post<void>(
        ApiEndpoints.auroraChipTelemetry,
        data: {
          'chip_id': 'status_band_correction',
          'telemetry_id': telemetryId,
          'semantic_value': semanticValue,
          'is_freeform': isFreeform,
          'is_disconfirming': isDisconfirming,
          'context_source': 'home_status_band',
          'band_status': bandStatus,
          'source': 'dashboard_correction_chip',
          if (freeformText != null && freeformText.trim().isNotEmpty)
            'freeform_text': freeformText.trim(),
          if (groupId != null) 'group_id': groupId,
        },
      );
    } catch (_) {}
  }
}
