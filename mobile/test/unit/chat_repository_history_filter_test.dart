import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/chat/data/services/websocket_chat_service_v2.dart';

/// V13 D-04（`_onboarding_skip_` 控制串气泡泄漏）：历史拉取单点过滤钉。
/// 真实 ChatRepository + 罐头 HTTP 适配器，不 mock 仓库本身。
class _CannedJsonAdapter implements HttpClientAdapter {
  _CannedJsonAdapter(this.payload);

  final Object? payload;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    await Future<void>.delayed(Duration.zero);
    return ResponseBody.fromString(
      jsonEncode(payload),
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json; charset=utf-8'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// 仓库构造依赖 WS 服务；本测试只打 HTTP 历史路径，桩掉即可。
class _StubWsService implements WebSocketChatServiceV2 {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('not used in history filter test');
}

Map<String, dynamic> _message(
  String id,
  String role,
  String content,
) =>
    {
      'id': id,
      'conversation_id': 'conv-d04',
      'role': role,
      'content': content,
      'created_at': '2026-09-22T10:0${id.length}:00Z',
    };

ChatRepository _repoWithHistory(List<Map<String, dynamic>> messages) {
  final dio = Dio()
    ..httpClientAdapter = _CannedJsonAdapter({'data': messages});
  final container = ProviderContainer();
  addTearDown(container.dispose);
  return ChatRepository(
    dio,
    container: container,
    wsService: _StubWsService(),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ChatRepository 历史控制串过滤（V13 D-04）', () {
    test('isOnboardingControlMessage 识别两个引导哨兵（含空白容差）', () {
      expect(
        ChatRepository.isOnboardingControlMessage('_onboarding_skip_'),
        isTrue,
      );
      expect(
        ChatRepository.isOnboardingControlMessage('_onboarding_start_'),
        isTrue,
      );
      expect(
        ChatRepository.isOnboardingControlMessage('  _onboarding_skip_  '),
        isTrue,
      );
      expect(ChatRepository.isOnboardingControlMessage('普通用户消息'), isFalse);
      // 前缀/内嵌不算——只挡整条控制串。
      expect(
        ChatRepository.isOnboardingControlMessage('_onboarding_skip_ 补充'),
        isFalse,
      );
    });

    test('getConversationHistory 剔除控制串用户气泡，正常消息保留', () async {
      final repo = _repoWithHistory([
        _message('m1', 'assistant', '你好，我是 Sparkle。'),
        _message('m2', 'user', '_onboarding_skip_'),
        _message('m3', 'user', '_onboarding_start_'),
        _message('m4', 'user', '7天后考离散数学，最弱图论'),
        // 助手同名内容不受过滤（只挡 user 角色哨兵）。
        _message('m5', 'assistant', '_onboarding_skip_'),
      ]);

      final history = await repo.getConversationHistory('conv-d04');

      expect(history.map((m) => m.id), ['m1', 'm4', 'm5']);
      expect(
        history.any((m) => m.role == MessageRole.user &&
            ChatRepository.isOnboardingControlMessage(m.content),),
        isFalse,
      );
    });
  });
}
