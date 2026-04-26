import 'dart:async';

import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';

/// Client for the Aurora Core Session (L3 interactive modeling session).
///
/// Sessions are limited to 6 user turns and 12 Aurora messages.
/// The session service manages state on the backend and returns the
/// updated session state after each interaction.
class AuroraCoreSessionService {
  const AuroraCoreSessionService(this._apiClient);

  final ApiClient _apiClient;

  /// Start a new L3 session or retrieve the existing active session.
  Future<AuroraCoreSession> startSession({
    String? conversationId,
    String surface = 'aurora_modeling',
    String sessionType = 'user_initiated',
    String? scope,
    List<String> wakeReasons = const [],
    String bandStatus = 'calibration_available',
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionStart,
      data: {
        'conversation_id': conversationId,
        'surface': surface,
        'session_type': sessionType,
        if (scope != null) 'scope': scope,
        'wake_reasons': wakeReasons,
        'band_status': bandStatus,
      },
    );
    return AuroraCoreSession.fromJson(response.data!);
  }

  /// Process a user response in the active session.
  Future<AuroraCoreSession> respond({
    required String sessionId,
    required String content,
    String? optionId,
    String? semanticValue,
    Map<String, dynamic>? modelWriteEffect,
    bool isFreeform = false,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionRespond,
      data: {
        'session_id': sessionId,
        'content': content,
        if (optionId != null) 'option_id': optionId,
        if (semanticValue != null) 'semantic_value': semanticValue,
        if (modelWriteEffect != null) 'model_write_effect': modelWriteEffect,
        'is_freeform': isFreeform,
      },
    );
    return AuroraCoreSession.fromJson(response.data!);
  }

  /// Get the current active session without modifying it.
  Future<AuroraCoreSession?> getCurrentSession() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionCurrent,
    );
    final data = response.data;
    if (data == null || data['active'] != true) return null;
    final sessionData = data['session'];
    if (sessionData is! Map<String, dynamic>) return null;
    return AuroraCoreSession.fromJson(sessionData);
  }

  /// Close the session (user-initiated exit).
  Future<AuroraCoreSession> closeSession(String sessionId) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionClose(sessionId),
    );
    return AuroraCoreSession.fromJson(response.data!);
  }
}
