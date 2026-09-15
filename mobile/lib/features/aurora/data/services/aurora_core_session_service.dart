import 'dart:async';

import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/aurora/data/models/aurora_core_session.dart';

abstract class AuroraCoreSessionClient {
  Future<AuroraCoreSession> startSession({
    String? conversationId,
    String surface = 'aurora_modeling',
    String sessionType = 'user_initiated',
    String? scope,
    List<String> wakeReasons = const [],
    String bandStatus = 'calibration_available',
    AuroraCoreSessionEntryReason? entryReason,
    String? resumeToken,
  });

  Future<AuroraCoreSession> respond({
    required String sessionId,
    required String content,
    String? optionId,
    String? semanticValue,
    Map<String, dynamic>? modelWriteEffect,
    bool isFreeform = false,
  });

  Future<AuroraCoreSession?> getCurrentSession();

  Future<AuroraCoreSession> resumeSession(String resumeToken);

  Future<AuroraCoreSession> pauseSession(
    String sessionId, {
    String reason = 'user_request',
  });

  Future<AuroraCoreSession> closeSession(String sessionId);
}

/// Client for the Aurora Core Session (L3 interactive modeling session).
///
/// Sessions are limited to 6 user turns and 12 Aurora messages.
/// The session service manages state on the backend and returns the
/// updated session state after each interaction.
class AuroraCoreSessionService implements AuroraCoreSessionClient {
  const AuroraCoreSessionService(this._apiClient);

  final ApiClient _apiClient;

  /// Start a new L3 session or retrieve the existing active session.
  @override
  Future<AuroraCoreSession> startSession({
    String? conversationId,
    String surface = 'aurora_modeling',
    String sessionType = 'user_initiated',
    String? scope,
    List<String> wakeReasons = const [],
    String bandStatus = 'calibration_available',
    AuroraCoreSessionEntryReason? entryReason,
    String? resumeToken,
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
        if (entryReason != null) 'entry_reason': entryReason.toJson(),
        if (resumeToken != null && resumeToken.isNotEmpty)
          'resume_token': resumeToken,
      },
    );
    return AuroraCoreSession.fromJson(response.data!);
  }

  /// Resume an existing L3 session by opaque resume token.
  @override
  Future<AuroraCoreSession> resumeSession(String resumeToken) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionResume,
      data: {'resume_token': resumeToken},
    );
    return AuroraCoreSession.fromJson(response.data!);
  }

  /// Process a user response in the active session.
  @override
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
  @override
  Future<AuroraCoreSession?> getCurrentSession() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionCurrent,
    );
    final data = response.data;
    if (data == null) return null;
    final sessionData = data['session'];
    if (sessionData is! Map<String, dynamic>) return null;
    return AuroraCoreSession.fromJson(sessionData);
  }

  /// Pause the session and keep its resume token.
  @override
  Future<AuroraCoreSession> pauseSession(
    String sessionId, {
    String reason = 'user_request',
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionPause(sessionId),
      data: {'reason': reason},
    );
    return AuroraCoreSession.fromJson(response.data!);
  }

  /// Close the session (user-initiated exit).
  @override
  Future<AuroraCoreSession> closeSession(String sessionId) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.auroraCoreSessionClose(sessionId),
    );
    return AuroraCoreSession.fromJson(response.data!);
  }
}
