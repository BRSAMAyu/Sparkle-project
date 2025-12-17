import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/data/models/chat_message_model.dart';

/// 流式聊天事件类型
enum StreamEventType {
  token,      // AI 正在输出的文字 chunk
  actions,    // AI 生成的 actions (如创建任务)
  parseStatus,// 解析状态 (是否降级)
  done,       // 完成
  error,      // 错误
}

/// 流式聊天事件
class ChatStreamEvent {
  final StreamEventType type;
  final String? content;       // token 类型时的文字内容
  final List<dynamic>? actions;// actions 类型时的动作列表
  final String? messageId;     // done 类型时返回的消息 ID
  final String? sessionId;     // done 类型时返回的会话 ID
  final String? errorMessage;  // error 类型时的错误信息
  final bool? degraded;        // parseStatus 类型时是否降级

  ChatStreamEvent({
    required this.type,
    this.content,
    this.actions,
    this.messageId,
    this.sessionId,
    this.errorMessage,
    this.degraded,
  });
}

class ChatRepository {
  final ApiClient _apiClient;

  ChatRepository(this._apiClient);

  // Note: This is duplicated from TaskRepository. It would be better to have a base repository class
  // or a shared error handling mixin.
  T _handleDioError<T>(DioException e, String functionName) {
    final errorMessage = e.response?.data?['detail'] ?? 'An unknown error occurred in $functionName';
    throw Exception(errorMessage);
  }

  /// 流式发送消息 (SSE)
  ///
  /// 返回一个 Stream<ChatStreamEvent>，可以实时接收 AI 的响应
  /// 当网络断开或出错时，会发送 error 事件而不是抛出异常
  Stream<ChatStreamEvent> sendMessageStream(ChatRequest request) async* {
    String accumulatedContent = '';  // 累积的内容，用于网络中断时保留已接收的文字

    try {
      await for (final sseEvent in _apiClient.postStream(
        ApiEndpoints.chatStream,
        data: request.toJson(),
      )) {
        final jsonData = sseEvent.jsonData;

        switch (sseEvent.event) {
          case 'token':
            final content = jsonData?['content'] as String? ?? '';
            accumulatedContent += content;
            yield ChatStreamEvent(type: StreamEventType.token, content: content);
            break;

          case 'actions':
            final actions = jsonData?['actions'] as List<dynamic>?;
            yield ChatStreamEvent(type: StreamEventType.actions, actions: actions);
            break;

          case 'parse_status':
            final degraded = jsonData?['degraded'] as bool? ?? false;
            yield ChatStreamEvent(type: StreamEventType.parseStatus, degraded: degraded);
            break;

          case 'done':
            yield ChatStreamEvent(
              type: StreamEventType.done,
              messageId: jsonData?['message_id'] as String?,
              sessionId: jsonData?['session_id'] as String?,
            );
            return;  // 正常结束

          case 'error':
            yield ChatStreamEvent(
              type: StreamEventType.error,
              errorMessage: jsonData?['message'] as String? ?? '未知错误',
            );
            return;

          default:
            // 未知事件类型，忽略
            break;
        }
      }

      // 如果流正常结束但没有收到 done 事件，也发送一个完成事件
      yield ChatStreamEvent(type: StreamEventType.done);

    } catch (e) {
      // 🚨 关键：网络错误时不崩溃，保留已累积的内容
      yield ChatStreamEvent(
        type: StreamEventType.error,
        errorMessage: '网络连接中断，已保留部分内容',
        content: accumulatedContent.isNotEmpty ? accumulatedContent : null,
      );
    }
  }

  /// 非流式发送消息 (兼容旧代码)
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
