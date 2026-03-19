import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/models/chat_response_model.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/data/models/expert_catalog_model.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';

class ChatRepository {
  ChatRepository(
    this._dio, {
    required ProviderContainer container,
    WebSocketChatServiceV2? wsService,
  }) : _wsService = wsService ?? WebSocketChatServiceV2(container: container);
  final Dio _dio;
  final WebSocketChatServiceV2 _wsService;

  /// 获取 WebSocket 连接状态流
  Stream<WsConnectionState> get connectionStateStream =>
      _wsService.connectionStateStream;

  /// 当前 WebSocket 连接状态
  WsConnectionState get connectionState => _wsService.connectionState;

  /// 手动触发重连
  Future<void> reconnect() => _wsService.manualReconnect();

  /// 释放资源
  void dispose() {
    _wsService.dispose();
  }

  /// 发送任务相关消息 (非流式)
  Future<ChatResponseModel> sendMessageToTask(
    String taskId,
    String message,
    String? conversationId,
  ) async {
    if (DemoDataService.isDemoMode) {
      return ChatResponseModel(
        message: 'Demo response to task: $message',
        conversationId: 'demo_id',
      );
    }
    final response = await _dio.post<Map<String, dynamic>>(
      '/chat/task/$taskId',
      data: {
        'message': message,
        'conversation_id': conversationId,
      },
    );
    final payload =
        ApiResponseParser.unwrapMap(response.data, action: 'sendMessageToTask');
    return ChatResponseModel.fromJson(payload);
  }

  /// 获取对话历史
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) async {
    if (DemoDataService.isDemoMode) {
      return DemoDataService().demoChatHistory;
    }

    final queryParams = <String, dynamic>{};
    if (limit != null) queryParams['limit'] = limit;
    if (offset != null) queryParams['offset'] = offset;

    final response = await _dio.get<dynamic>(
      '/chat/history/$conversationId',
      queryParameters: queryParams.isEmpty ? null : queryParams,
    );

    // Handle both list response and wrapped response
    dynamic data = response.data;
    if (data is Map<String, dynamic> && data.containsKey('data')) {
      data = data['data'];
    }
    if (data is! List) {
      return [];
    }

    return data
        .map((item) => ChatMessageModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// 获取最近对话列表
  Future<List<Map<String, dynamic>>> getRecentConversations() async {
    if (DemoDataService.isDemoMode) {
      return [
        {
          'id': 'demo_conv_1',
          'title': '关于数学复习的建议',
          'updated_at': DateTime.now().toIso8601String(),
        },
      ];
    }
    final response = await _dio.get<dynamic>('/chat/sessions');
    final data = ApiResponseParser.unwrapList(response.data,
        action: 'getRecentConversations',);
    return List<Map<String, dynamic>>.from(
      data.map((item) => item as Map<String, dynamic>),
    );
  }

  Future<MultiAgentCatalog> getMultiAgentCatalog() async {
    final response =
        await _dio.get<Map<String, dynamic>>('/multi-agent/catalog');
    return MultiAgentCatalog.fromJson(response.data ?? const {});
  }

  Future<ExpertCatalogExpert> createCustomExpert({
    required String name,
    required String description,
    required String systemPrompt,
    String? baseExpertId,
    String? preferredModelKey,
    String reasoningMode = 'balanced',
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/multi-agent/custom-experts',
      data: {
        'name': name,
        'description': description,
        'system_prompt': systemPrompt,
        if (baseExpertId != null && baseExpertId.isNotEmpty)
          'base_expert_id': baseExpertId,
        if (preferredModelKey != null && preferredModelKey.isNotEmpty)
          'preferred_model_key': preferredModelKey,
        'reasoning_mode': reasoningMode,
      },
    );
    return ExpertCatalogExpert.fromJson(response.data ?? const {});
  }

  Future<ExpertCatalogTeam> createCustomTeam({
    required String name,
    required List<String> expertIds,
    required List<String> answerExpertIds,
    required String collaborationMode,
    String? description,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/multi-agent/custom-teams',
      data: {
        'name': name,
        'description': description,
        'expert_ids': expertIds,
        'answer_expert_ids': answerExpertIds,
        'collaboration_mode': collaborationMode,
      },
    );
    return ExpertCatalogTeam.fromJson(response.data ?? const {});
  }

  /// 流式聊天（WebSocket）
  Stream<ChatStreamEvent> chatStream(
    String message,
    String? conversationId, {
    String? userId,
    String? nickname,
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
    String? chatMode,
  }) =>
    // 🎭 演示模式：LLM对话仍然使用真实API，保证核心功能可用
    // 只有历史数据使用预设内容
    // 使用 WebSocket 服务
    _wsService.sendMessage(
      message: message,
      userId: userId ?? 'anonymous',
      sessionId: conversationId,
      nickname: nickname,
      extraContext: extraContext,
      token: token,
      fileIds: fileIds,
      includeReferences: includeReferences,
      chatMode: chatMode,
    );

  /// 发送 ActionCard 确认/忽略反馈
  void sendActionFeedback({
    required String action,
    required String toolResultId,
    required String widgetType,
  }) {
    _wsService.sendActionFeedback(
      action: action,
      toolResultId: toolResultId,
      widgetType: widgetType,
    );
  }

  void sendInterventionFeedback({
    required String requestId,
    required String feedbackType,
    Map<String, dynamic>? extraData,
  }) {
    _wsService.sendInterventionFeedback(
      requestId: requestId,
      feedbackType: feedbackType,
      extraData: extraData,
    );
  }

  void sendResponseFeedback({
    required String responseId,
    required String feedbackType,
    List<String>? reasons,
    String? freeText,
    String? workflowId,
    String? promptVersion,
    String? traceId,
    Map<String, dynamic>? meta,
  }) {
    _wsService.sendResponseFeedback(
      responseId: responseId,
      feedbackType: feedbackType,
      reasons: reasons,
      freeText: freeText,
      workflowId: workflowId,
      promptVersion: promptVersion,
      traceId: traceId,
      meta: meta,
    );
  }

  /// 发送计划审查反馈
  void sendPlanReviewFeedback({
    required String reviewId,
    required String userDecision,
    String? planId,
    String? userComment,
  }) {
    _wsService.sendPlanReviewFeedback(
      reviewId: reviewId,
      userDecision: userDecision,
      planId: planId,
      userComment: userComment,
    );
  }

  /// 流式聊天（SSE - 保留用于向后兼容）
  @Deprecated('Use chatStream with WebSocket instead')
  Stream<ChatStreamEvent> chatStreamSSE(
    String message,
    String? conversationId,
  ) {
    late StreamController<ChatStreamEvent> controller;
    controller = StreamController<ChatStreamEvent>(
      onCancel: () {
        if (!controller.isClosed) {
          unawaited(controller.close());
        }
      },
    );

    unawaited(
      _startSSEConnection(
        message: message,
        conversationId: conversationId,
        controller: controller,
      ),
    );

    return controller.stream;
  }

  Future<void> _startSSEConnection({
    required String message,
    required StreamController<ChatStreamEvent> controller,
    String? conversationId,
  }) async {
    try {
      final response = await _dio.post<ResponseBody>(
        '/chat/stream',
        data: {
          'message': message,
          'conversation_id': conversationId,
        },
        options: Options(
          responseType: ResponseType.stream,
          headers: {'Accept': 'text/event-stream'},
        ),
      );

      final stream = response.data!.stream;
      var buffer = '';

      await for (final chunk
          in stream.cast<List<int>>().transform(utf8.decoder)) {
        // ignore: use_string_buffers
        buffer += chunk;

        // 解析 SSE 事件
        while (buffer.contains('\n\n')) {
          final eventEnd = buffer.indexOf('\n\n');
          final eventStr = buffer.substring(0, eventEnd);
          buffer = buffer.substring(eventEnd + 2);

          if (eventStr.startsWith('data: ')) {
            final dataStr = eventStr.substring(6);
            try {
              final data = json.decode(dataStr);
              if (!controller.isClosed) {
                controller.add(_parseEvent(data as Map<String, dynamic>));
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }

      if (!controller.isClosed) {
        unawaited(controller.close());
      }
    } catch (e) {
      if (!controller.isClosed) {
        controller.addError(e);
        unawaited(controller.close());
      }
    }
  }

  ChatStreamEvent _parseEvent(Map<String, dynamic> data) {
    final type = data['type'] as String;

    switch (type) {
      case 'text':
        return TextEvent(content: data['content'] as String);

      case 'tool_start':
        return ToolStartEvent(toolName: data['tool'] as String);

      case 'tool_result':
        return ToolResultEvent(
          result:
              ToolResultModel.fromJson(data['result'] as Map<String, dynamic>),
        );

      case 'widget':
        return WidgetEvent(
          widgetType: data['widget_type'] as String,
          widgetData: data['widget_data'] as Map<String, dynamic>,
        );

      case 'intervention':
        final intervention =
            data['intervention'] as Map<String, dynamic>? ?? {};
        final content = intervention['content'] as Map<String, dynamic>? ?? {};
        final widgetType =
            content['widget_type'] as String? ?? 'intervention_card';
        final widgetData = (content['widget_data'] as Map<String, dynamic>?) ??
            Map<String, dynamic>.from(content);
        widgetData['intervention_id'] ??= intervention['id'];
        widgetData['intervention_topic'] ??= intervention['topic'];
        widgetData['intervention_level'] ??= intervention['level'];
        return WidgetEvent(widgetType: widgetType, widgetData: widgetData);

      case 'done':
        return DoneEvent();

      case 'intervention_feedback_ack':
        return ActionStatusEvent(
          actionId: data['request_id'] as String? ?? '',
          status: data['status'] as String? ?? 'unknown',
          message: data['message'] as String?,
          widgetType: 'intervention',
          timestamp: data['timestamp'] as int?,
        );

      case 'response_feedback_ack':
        return ActionStatusEvent(
          actionId: data['response_id'] as String? ?? '',
          status: data['status'] as String? ?? 'unknown',
          message: data['message'] as String?,
          widgetType: 'response_feedback',
          timestamp: data['timestamp'] as int?,
        );

      default:
        return UnknownEvent(data: data);
    }
  }
}
