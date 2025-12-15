import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
// For _handleDioError, consider moving it to a shared place

class ChatRepository {
  final ApiClient _apiClient;

  ChatRepository(this._apiClient);

  // Note: This is duplicated from TaskRepository. It would be better to have a base repository class
  // or a shared error handling mixin.
  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage = e.response?.data?['detail'] ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  Future<ChatResponse> sendMessage(ChatRequest request) async {
    try {
      final response = await _apiClient.post(ApiEndpoints.chat, data: request.toJson());
      return ChatResponse.fromJson(response.data);
    } on DioException catch (e) {
      return _handleDioError(e, 'sendMessage');
    }
  }

  Future<List<ChatSession>> getSessions({int limit = 20}) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.chatSessions, queryParameters: {'limit': limit});
       final List<dynamic> data = response.data;
      return data.map((json) => ChatSession.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getSessions');
    }
  }

  Future<List<ChatMessageModel>> getSessionMessages(String sessionId, {int limit = 50}) async {
    try {
      final response = await _apiClient.get(ApiEndpoints.sessionMessages(sessionId), queryParameters: {'limit': limit});
       final List<dynamic> data = response.data;
      return data.map((json) => ChatMessageModel.fromJson(json)).toList();
    } on DioException catch (e) {
      return _handleDioError(e, 'getSessionMessages');
    }
  }

  Future<void> deleteSession(String sessionId) async {
    try {
      // Assuming the endpoint is something like DELETE /chat/sessions/{id}
      // This is not explicitly defined in ApiEndpoints, so I'm making an assumption.
      await _apiClient.delete('${ApiEndpoints.chatSessions}/$sessionId');
    } on DioException catch (e) {
      return _handleDioError(e, 'deleteSession');
    }
  }

}

// Provider for ChatRepository
final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return ChatRepository(apiClient);
});
