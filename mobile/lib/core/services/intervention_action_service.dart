import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';

class InterventionActionService {
  InterventionActionService(this._ref);

  final Ref _ref;
  final Logger _logger = Logger();

  Future<void> reportAction({
    required String recordId,
    required String action,
    Map<String, dynamic>? actionPayload,
  }) async {
    final normalizedRecordId = recordId.trim();
    if (normalizedRecordId.isEmpty) {
      return;
    }

    try {
      final apiClient = _ref.read(apiClientProvider);
      await apiClient.post<Map<String, dynamic>>(
        ApiEndpoints.notificationCenterInterventionRecordAction(
          normalizedRecordId,
        ),
        data: {
          'action': action,
          'action_payload': actionPayload ?? <String, dynamic>{},
        },
      );
    } catch (e) {
      _logger.w(
        'Failed to report intervention action '
        '$action for $normalizedRecordId: $e',
      );
    }
  }

  Future<void> reportActionFromPayload({
    required Map<String, dynamic> payload,
    required String action,
    required String surface,
    Map<String, dynamic>? extraPayload,
  }) async {
    final recordId = extractRecordId(payload);
    if (recordId == null) {
      return;
    }

    await reportAction(
      recordId: recordId,
      action: action,
      actionPayload: {
        'surface': surface,
        ...?extraPayload,
      },
    );
  }

  String? extractRecordId(Map<String, dynamic> payload) {
    final recordId = payload['intervention_id']?.toString() ??
        payload['record_id']?.toString();
    if (recordId == null || recordId.trim().isEmpty) {
      return null;
    }
    return recordId.trim();
  }
}

final interventionActionServiceProvider =
    Provider<InterventionActionService>(InterventionActionService.new);
