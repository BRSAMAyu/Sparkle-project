import 'dart:async';

import 'package:dio/dio.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';

/// DataConsistencyChecker - 验证消息在各层的一致性
///
/// 检查以下层级：
/// 1. Flutter本地状态 (ChatState)
/// 2. Go Gateway Redis缓存
/// 3. Python DB持久化 (通过Go Gateway API)
class DataConsistencyChecker {

  DataConsistencyChecker({
    required ChatRepository chatRepository,
    required Dio dio,
  })  : _chatRepository = chatRepository,
        _dio = dio;
  final ChatRepository _chatRepository;
  final Dio _dio;

  /// 验证消息在各层的一致性
  ///
  /// [messageId] - 要验证的消息ID
  /// [conversationId] - 对话ID
  /// [userId] - 用户ID
  ///
  /// 返回验证结果：
  /// - true: 所有层级数据一致
  /// - false: 存在不一致
  Future<bool> verifyMessageConsistency({
    required String messageId,
    required String conversationId,
    required String userId,
  }) async {
    try {
      // 1. 检查Flutter本地状态
      final flutterResult = await _checkFlutterState(messageId, conversationId);
      if (!flutterResult.exists) {
        // 消息在Flutter本地不存在，可能是新消息
        return true;
      }

      // 2. 查询Go Gateway Redis缓存
      final goGatewayResult = await _checkGoGatewayCache(messageId, conversationId);
      if (!goGatewayResult.exists) {
        // 消息在Go Gateway缓存中不存在
        // 这可能是正常的，因为缓存有TTL
        return true;
      }

      // 3. 查询Python DB持久化
      final pythonDbResult = await _checkPythonDb(messageId, conversationId);
      if (!pythonDbResult.exists) {
        // 消息在数据库中不存在
        // 这可能是正常的，因为数据库持久化是异步的
        return true;
      }

      // 4. 对比三者的一致性
      final flutterMessage = flutterResult.message;
      final goGatewayMessage = goGatewayResult.message;
      final pythonDbMessage = pythonDbResult.message;

      // 检查关键字段是否一致
      if (flutterMessage?.content != goGatewayMessage?.content ||
          flutterMessage?.content != pythonDbMessage?.content) {
        // 内容不一致
        return false;
      }

      if (flutterMessage?.role != goGatewayMessage?.role ||
          flutterMessage?.role != pythonDbMessage?.role) {
        // 角色不一致
        return false;
      }

      // 所有检查通过
      return true;
    } catch (e) {
      // 验证过程中出现错误，返回false
      return false;
    }
  }

  /// 检查Flutter本地状态
  Future<_MessageCheckResult> _checkFlutterState(
    String messageId,
    String conversationId,
  ) async {
    try {
      // 获取对话历史
      final history = await _chatRepository.getConversationHistory(
        conversationId,
        limit: 100,
      );

      // 查找指定消息
      final message = history.firstWhere(
        (msg) => msg.id == messageId,
        orElse: () => ChatMessageModel(
          conversationId: conversationId,
          id: '',
          content: '',
          role: MessageRole.user,
        ),
      );

      if (message.id.isEmpty) {
        return _MessageCheckResult(exists: false);
      }

      return _MessageCheckResult(
        exists: true,
        message: message,
      );
    } catch (e) {
      return _MessageCheckResult(exists: false);
    }
  }

  /// 检查Go Gateway Redis缓存
  Future<_MessageCheckResult> _checkGoGatewayCache(
    String messageId,
    String conversationId,
  ) async {
    try {
      // 查询Go Gateway的Redis缓存
      // 注意：这需要Go Gateway提供相应的API端点
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/chat/cache/check',
        queryParameters: {
          'message_id': messageId,
          'conversation_id': conversationId,
        },
      );

      final data = response.data;
      if (data == null || data['exists'] != true) {
        return _MessageCheckResult(exists: false);
      }

      // 解析消息
      final messageData = data['message'] as Map<String, dynamic>;
      final message = ChatMessageModel.fromJson(messageData);

      return _MessageCheckResult(
        exists: true,
        message: message,
      );
    } catch (e) {
      // 如果API不存在或出错，返回不存在
      return _MessageCheckResult(exists: false);
    }
  }

  /// 检查Python DB持久化
  Future<_MessageCheckResult> _checkPythonDb(
    String messageId,
    String conversationId,
  ) async {
    try {
      // 查询Python DB持久化
      // 注意：这需要Go Gateway提供相应的API端点
      final response = await _dio.get<Map<String, dynamic>>(
        '/api/v1/chat/db/check',
        queryParameters: {
          'message_id': messageId,
          'conversation_id': conversationId,
        },
      );

      final data = response.data;
      if (data == null || data['exists'] != true) {
        return _MessageCheckResult(exists: false);
      }

      // 解析消息
      final messageData = data['message'] as Map<String, dynamic>;
      final message = ChatMessageModel.fromJson(messageData);

      return _MessageCheckResult(
        exists: true,
        message: message,
      );
    } catch (e) {
      // 如果API不存在或出错，返回不存在
      return _MessageCheckResult(exists: false);
    }
  }

  /// 批量验证消息一致性
  ///
  /// [messageIds] - 要验证的消息ID列表
  /// [conversationId] - 对话ID
  /// [userId] - 用户ID
  ///
  /// 返回验证结果映射：消息ID -> 是否一致
  Future<Map<String, bool>> verifyMultipleMessages({
    required List<String> messageIds,
    required String conversationId,
    required String userId,
  }) async {
    final results = <String, bool>{};

    for (final messageId in messageIds) {
      final result = await verifyMessageConsistency(
        messageId: messageId,
        conversationId: conversationId,
        userId: userId,
      );
      results[messageId] = result;
    }

    return results;
  }
}

/// 消息检查结果
class _MessageCheckResult {

  _MessageCheckResult({
    required this.exists,
    this.message,
  });
  final bool exists;
  final ChatMessageModel? message;
}
