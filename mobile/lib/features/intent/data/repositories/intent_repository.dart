import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/intent/data/models/intent_data.dart';

/// Intent Repository Provider
final intentRepositoryProvider = Provider<IntentRepository>((ref) {
  return IntentRepository(ref.read(apiClientProvider));
});

/// Intent Repository
///
/// Handles all multi-intent related API calls
class IntentRepository {
  const IntentRepository(this._apiClient);

  final ApiClient _apiClient;

  /// Preview detected intents in a message
  ///
  /// Calls POST /multi-intent/preview
  ///
  /// Request body:
  /// ```json
  /// {
  ///   "message": "用户消息"
  /// }
  /// ```
  ///
  /// Response:
  /// ```json
  /// {
  ///   "success": true,
  ///   "data": {
  ///     "original_message": "明天要复习Python闭包",
  ///     "detected_intents": [...],
  ///     "execution_plan": "...",
  ///     "estimated_time": 120
  ///   }
  /// }
  /// ```
  Future<IntentPreviewResponse> previewIntents(String message) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.multiIntentPreview,
      data: {'message': message},
    );

    final responseData = response.data;
    if (responseData == null) {
      throw Exception('Empty response from intent preview API');
    }

    if (responseData['success'] != true) {
      throw Exception(responseData['error'] ?? 'Intent preview failed');
    }

    final data = responseData['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw Exception('No data in response from intent preview API');
    }

    return IntentPreviewResponse.fromJson(data);
  }

  /// Execute intents
  ///
  /// Calls POST /multi-intent/execute
  Future<IntentExecuteResponse> executeIntents(
    String message, {
    bool confirmIntents = true,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.multiIntentExecute,
      data: {
        'message': message,
        'confirm_intents': confirmIntents,
      },
    );

    final responseData = response.data;
    if (responseData == null) {
      throw Exception('Empty response from intent execute API');
    }

    return IntentExecuteResponse.fromJson(responseData);
  }

  /// Parse message into intents (returns raw intent data)
  ///
  /// Calls POST /multi-intent/parse
  Future<List<IntentData>> parseIntents(String message) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.multiIntentParse,
      data: {'message': message},
    );

    final responseData = response.data;
    if (responseData == null) {
      throw Exception('Empty response from intent parse API');
    }

    if (responseData['success'] != true) {
      throw Exception(responseData['error'] ?? 'Intent parse failed');
    }

    final data = responseData['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw Exception('No data in response from intent parse API');
    }

    final intentsList = data['intents'] as List?;
    if (intentsList == null) {
      return const [];
    }

    return intentsList
        .map((e) => IntentData.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get available intent types
  ///
  /// Calls GET /multi-intent/intent-types
  Future<List<IntentTypeMetadata>> getIntentTypes() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.multiIntentTypes,
    );

    final responseData = response.data;
    if (responseData == null) {
      throw Exception('Empty response from intent types API');
    }

    if (responseData['success'] != true) {
      throw Exception(responseData['error'] ?? 'Get intent types failed');
    }

    final data = responseData['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw Exception('No data in response from intent types API');
    }

    final typesList = data['intent_types'] as List?;
    if (typesList == null) {
      return const [];
    }

    return typesList
        .map((e) => IntentTypeMetadata.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Analyze and optionally execute intents in one call
  ///
  /// Calls POST /multi-intent/analyze-and-execute
  ///
  /// This endpoint handles the entire flow:
  /// - Single intent or auto_execute=true: Returns execution_result
  /// - Multi intent and auto_execute=false: Returns preview with needs_confirmation=true
  ///
  /// Request body:
  /// ```json
  /// {
  ///   "message": "用户消息",
  ///   "auto_execute": false,
  ///   "context": {}
  /// }
  /// ```
  Future<AnalyzeAndExecuteResponse> analyzeAndExecute(
    String message, {
    bool autoExecute = false,
    Map<String, dynamic>? context,
  }) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.multiIntentAnalyzeExecute,
      data: {
        'message': message,
        'auto_execute': autoExecute,
        if (context != null) 'context': context,
      },
    );

    final responseData = response.data;
    if (responseData == null) {
      throw Exception('Empty response from analyze and execute API');
    }

    if (responseData['success'] != true) {
      throw Exception(responseData['error'] ?? 'Analyze and execute failed');
    }

    final data = responseData['data'] as Map<String, dynamic>?;
    if (data == null) {
      throw Exception('No data in response from analyze and execute API');
    }

    return AnalyzeAndExecuteResponse.fromJson(data);
  }
}
