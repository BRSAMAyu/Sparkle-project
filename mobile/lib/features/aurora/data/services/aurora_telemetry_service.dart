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
}
