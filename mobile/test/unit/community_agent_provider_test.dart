import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/guest_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/agent_session_provider.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';

import '../shared/i18n_test_helper.dart';

UserBrief _user(String id, String name) => UserBrief(
      id: id,
      username: name,
      nickname: name,
    );

MessageInfo _groupMessage(String id, String content, UserBrief sender) =>
    MessageInfo(
      id: id,
      messageType: MessageType.text,
      sender: sender,
      content: content,
      createdAt: DateTime(2024),
      updatedAt: DateTime(2024),
    );

PrivateMessageInfo _privateMessage(
  String id,
  String content,
  UserBrief sender,
  UserBrief receiver,
) =>
    PrivateMessageInfo(
      id: id,
      sender: sender,
      receiver: receiver,
      messageType: MessageType.text,
      isRead: true,
      content: content,
      createdAt: DateTime(2024),
      updatedAt: DateTime(2024),
    );

/// 提示词构建纯函数测试（wt276 前已存在，由 main 调用注册）。
void promptBuilderTests() {
  test('buildGroupAgentPrompt filters agent messages and limits context', () {
    final alice = _user('u1', 'Alice');
    final bob = _user('u2', 'Bob');

    final messages = [
      _groupMessage('7', 'msg-7', alice),
      _groupMessage('6', 'msg-6', bob),
      _groupMessage('5', 'msg-5', alice),
      _groupMessage('4', 'msg-4', bob),
      _groupMessage('3', 'msg-3', alice),
      _groupMessage('2', 'msg-2', bob),
      MessageInfo(
        id: 'agent',
        messageType: MessageType.text,
        sender: buildCommunityAgentUser(),
        content: 'AGENT_SHOULD_NOT_APPEAR',
        contentData: {kAgentMetadataKey: true},
        createdAt: DateTime(2024),
        updatedAt: DateTime(2024),
      ),
      _groupMessage('1', 'msg-1', alice),
    ];

    final prompt = buildGroupAgentPrompt(
      input: 'Hello',
      recentMessages: messages,
      groupName: 'TestGroup',
    );

    expect(prompt.contains('TestGroup'), isTrue);
    expect(prompt.contains('Hello'), isTrue);
    expect(prompt.contains('AGENT_SHOULD_NOT_APPEAR'), isFalse);
    expect(prompt.contains('msg-1'), isFalse);
    expect(prompt.contains('msg-7'), isTrue);
  });

  test('buildPrivateAgentPrompt compresses long content', () {
    final alice = _user('u1', 'Alice');
    final bob = _user('u2', 'Bob');
    final longContent = 'a' * 200;
    final messages = [
      _privateMessage('1', longContent, alice, bob),
    ];

    final prompt = buildPrivateAgentPrompt(
      input: 'Reply',
      recentMessages: messages,
      friendName: 'Bob',
    );

    final expected = '${'a' * 160}…';
    expect(prompt.contains(expected), isTrue);
    expect(prompt.contains('Bob'), isTrue);
  });

  test('normalizeCommunityAgentOutput uses shared markdown normalization', () {
    const raw = '''
- **学习规划**：先复习线代
？ **任务管理**：晚上做题
❓ **进度跟踪**：记得打卡
''';

    final normalized = normalizeCommunityAgentOutput(raw);

    expect(normalized, contains('- **学习规划**：先复习线代'));
    expect(normalized, contains('- **任务管理**：晚上做题'));
    expect(normalized, contains('- **进度跟踪**：记得打卡'));
  });
}

// ============ wt276 诚实性红线：代写消息发送失败不得伪造成功 ============

class _NoopApiClient extends ApiClient {
  _NoopApiClient() : super(_UnusedRef());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeAuthRepository extends AuthRepository {
  _FakeAuthRepository()
      : super(
          _NoopApiClient(),
          SecureTokenStorage(storage: const FlutterSecureStorage()),
        );

  @override
  Future<String?> getAccessToken() async => 'test-token';
}

class _FakeChatRepository extends ChatRepository {
  _FakeChatRepository(this.streamFactory)
      : super(Dio(), container: ProviderContainer());

  final Stream<ChatStreamEvent> Function() streamFactory;

  @override
  Stream<ChatStreamEvent> chatStream(
    String message,
    String? conversationId, {
    String? userId,
    String? requestId,
    String? nickname,
    Map<String, dynamic>? extraContext,
    String? token,
    List<String>? fileIds,
    bool includeReferences = false,
    String? chatMode,
    bool? useDocumentContext,
  }) =>
      streamFactory();

  @override
  Stream<WsConnectionState> get connectionStateStream =>
      const Stream<WsConnectionState>.empty();

  @override
  void dispose() {}
}

/// 失败注入点：sendPrivateMessage / sendMessage 按 [failSends] 决定抛错或
/// 返回服务器消息（id 固定 srv-1，isRead:false 诚实初值）。
class _FakeCommunityRepository extends CommunityRepository {
  _FakeCommunityRepository() : super(_NoopApiClient());

  bool failSends = false;
  int sendPrivateCalls = 0;
  int sendGroupCalls = 0;

  PrivateMessageInfo _serverPrivateMessage(PrivateMessageSend message) =>
      PrivateMessageInfo(
        id: 'srv-1',
        sender: buildCommunityAgentUser(),
        receiver: _user('guest-user', 'Guest'),
        messageType: MessageType.text,
        content: message.content,
        contentData: message.contentData,
        isRead: false,
        createdAt: DateTime(2024),
        updatedAt: DateTime(2024),
      );

  MessageInfo _serverGroupMessage({
    required String groupId,
    required String? content,
    required Map<String, dynamic>? contentData,
  }) =>
      MessageInfo(
        id: 'srv-1',
        messageType: MessageType.text,
        sender: buildCommunityAgentUser(),
        content: content,
        contentData: contentData,
        createdAt: DateTime(2024),
        updatedAt: DateTime(2024),
      );

  @override
  Future<PrivateMessageInfo> sendPrivateMessage(
    PrivateMessageSend message,
  ) async {
    sendPrivateCalls++;
    if (failSends) {
      throw Exception('network down');
    }
    return _serverPrivateMessage(message);
  }

  @override
  Future<MessageInfo> sendMessage(
    String groupId, {
    required MessageType type,
    String? content,
    Map<String, dynamic>? contentData,
    String? replyToId,
    String? threadRootId,
    List<String>? mentionUserIds,
    String? nonce,
  }) async {
    sendGroupCalls++;
    if (failSends) {
      throw Exception('network down');
    }
    return _serverGroupMessage(
      groupId: groupId,
      content: content,
      contentData: contentData,
    );
  }
}

class _FakeRef implements Ref {
  _FakeRef({
    required this.guestService,
    required this.authRepository,
    required this.agentSessionStore,
    required this.communityRepository,
  }) : _providers = <ProviderListenable<Object?>, Object?>{
          currentUserProvider: null,
          guestServiceProvider: guestService,
          authRepositoryProvider: authRepository,
          agentSessionStoreProvider: agentSessionStore,
          communityRepositoryProvider: communityRepository,
        };

  final GuestService guestService;
  final AuthRepository authRepository;
  final AgentSessionStore agentSessionStore;
  final CommunityRepository communityRepository;
  final Map<ProviderListenable<Object?>, Object?> _providers;

  @override
  T read<T>(ProviderListenable<T> provider) {
    if (!_providers.containsKey(provider)) {
      throw UnimplementedError('Unsupported provider read: $provider');
    }
    return _providers[provider] as T;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Future<({PrivateAgentChatNotifier notifier, _FakeRef ref})>
    _createPrivateNotifier({
  required ChatRepository chatRepository,
  required _FakeCommunityRepository communityRepository,
  String friendId = 'friend-1',
}) async {
  SharedPreferences.setMockInitialValues(<String, Object>{});
  final prefs = await SharedPreferences.getInstance();
  final ref = _FakeRef(
    guestService: GuestService(prefs),
    authRepository: _FakeAuthRepository(),
    agentSessionStore: AgentSessionStore(prefs),
    communityRepository: communityRepository,
  );
  return (
    notifier: PrivateAgentChatNotifier(chatRepository, ref, friendId),
    ref: ref,
  );
}

Future<GroupAgentChatNotifier> _createGroupNotifier({
  required ChatRepository chatRepository,
  required _FakeCommunityRepository communityRepository,
  String groupId = 'group-1',
}) async {
  SharedPreferences.setMockInitialValues(<String, Object>{});
  final prefs = await SharedPreferences.getInstance();
  final ref = _FakeRef(
    guestService: GuestService(prefs),
    authRepository: _FakeAuthRepository(),
    agentSessionStore: AgentSessionStore(prefs),
    communityRepository: communityRepository,
  );
  return GroupAgentChatNotifier(chatRepository, ref, groupId);
}

ChatRepository _chatRepoWithDraft(String draft) =>
    _FakeChatRepository(
      () => Stream<ChatStreamEvent>.fromIterable([
            TextEvent(content: draft),
            DoneEvent(finishReason: 'STOP'),
          ]),
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(setUpI18nForTesting);
  promptBuilderTests();

  group('PrivateAgentChatNotifier.sendAgentMessage honesty (wt276)', () {
    test('persist failure exposes local failed message, never fake success',
        () async {
      final communityRepo = _FakeCommunityRepository()..failSends = true;
      final notifier = (await _createPrivateNotifier(
        chatRepository: _chatRepoWithDraft('AI 起草的回复'),
        communityRepository: communityRepo,
      ))
          .notifier;
      addTearDown(notifier.dispose);

      await notifier.sendAgentMessage(prompt: '帮我想一条回复');

      expect(communityRepo.sendPrivateCalls, 1);
      final messages = notifier.state.messages;
      expect(messages, hasLength(1));
      final failed = messages.single;
      expect(failed.id, startsWith('local_'));
      expect(
        failed.hasError,
        isTrue,
        reason: '失败必须以 failed 态暴露给用户',
      );
      expect(failed.isSending, isFalse);
      expect(
        failed.isRead,
        isFalse,
        reason: '绝不伪造 isRead:true 的成功消息',
      );
      expect(failed.content, 'AI 起草的回复');
      expect(notifier.state.error, isNotNull);
      expect(notifier.state.isSending, isFalse);
    });

    test('persist success replaces local pending with server message',
        () async {
      final communityRepo = _FakeCommunityRepository();
      final notifier = (await _createPrivateNotifier(
        chatRepository: _chatRepoWithDraft('AI 起草的回复'),
        communityRepository: communityRepo,
      ))
          .notifier;
      addTearDown(notifier.dispose);

      await notifier.sendAgentMessage(prompt: '帮我想一条回复');

      expect(communityRepo.sendPrivateCalls, 1);
      final messages = notifier.state.messages;
      expect(messages, hasLength(1));
      expect(messages.single.id, 'srv-1');
      expect(messages.single.hasError, isFalse);
      expect(messages.single.isSending, isFalse);
      expect(notifier.state.error, isNull);
    });

    test('retryAgentMessage re-persists and settles the failed message',
        () async {
      final communityRepo = _FakeCommunityRepository()..failSends = true;
      final notifier = (await _createPrivateNotifier(
        chatRepository: _chatRepoWithDraft('AI 起草的回复'),
        communityRepository: communityRepo,
      ))
          .notifier;
      addTearDown(notifier.dispose);

      await notifier.sendAgentMessage(prompt: '帮我想一条回复');
      final failedId = notifier.state.messages.single.id;

      communityRepo.failSends = false;
      await notifier.retryAgentMessage(failedId);

      expect(communityRepo.sendPrivateCalls, 2);
      final messages = notifier.state.messages;
      expect(messages, hasLength(1));
      expect(messages.single.id, 'srv-1');
      expect(messages.single.hasError, isFalse);
      expect(notifier.state.error, isNull);
    });

    test('retryAgentMessage keeps failed state visible when retry fails again',
        () async {
      final communityRepo = _FakeCommunityRepository()..failSends = true;
      final notifier = (await _createPrivateNotifier(
        chatRepository: _chatRepoWithDraft('AI 起草的回复'),
        communityRepository: communityRepo,
      ))
          .notifier;
      addTearDown(notifier.dispose);

      await notifier.sendAgentMessage(prompt: '帮我想一条回复');
      final failedId = notifier.state.messages.single.id;

      await notifier.retryAgentMessage(failedId);

      expect(communityRepo.sendPrivateCalls, 2);
      final messages = notifier.state.messages;
      expect(messages, hasLength(1));
      expect(messages.single.id, failedId);
      expect(messages.single.hasError, isTrue);
      expect(messages.single.isRead, isFalse);
      expect(notifier.state.error, isNotNull);
    });

    test('removeLocalDraft deletes the failed message', () async {
      final communityRepo = _FakeCommunityRepository()..failSends = true;
      final notifier = (await _createPrivateNotifier(
        chatRepository: _chatRepoWithDraft('AI 起草的回复'),
        communityRepository: communityRepo,
      ))
          .notifier;
      addTearDown(notifier.dispose);

      await notifier.sendAgentMessage(prompt: '帮我想一条回复');
      final failedId = notifier.state.messages.single.id;

      notifier.removeLocalDraft(failedId);

      expect(notifier.state.messages, isEmpty);
    });
  });

  group('GroupAgentChatNotifier.sendAgentMessage honesty (wt276)', () {
    test('persist failure surfaces error state with no phantom message',
        () async {
      final communityRepo = _FakeCommunityRepository()..failSends = true;
      final notifier = await _createGroupNotifier(
        chatRepository: _chatRepoWithDraft('群内总结'),
        communityRepository: communityRepo,
      );
      addTearDown(notifier.dispose);

      await notifier.sendAgentMessage(prompt: '总结一下');

      expect(communityRepo.sendGroupCalls, 1);
      expect(
        notifier.state.messages,
        isEmpty,
        reason: '发送失败绝不追加伪造消息',
      );
      expect(notifier.state.error, isNotNull);
      expect(notifier.state.isSending, isFalse);
    });

    test('persist success appends the real server message', () async {
      final communityRepo = _FakeCommunityRepository();
      final notifier = await _createGroupNotifier(
        chatRepository: _chatRepoWithDraft('群内总结'),
        communityRepository: communityRepo,
      );
      addTearDown(notifier.dispose);

      await notifier.sendAgentMessage(prompt: '总结一下');

      expect(communityRepo.sendGroupCalls, 1);
      expect(notifier.state.messages, hasLength(1));
      expect(notifier.state.messages.single.id, 'srv-1');
      expect(notifier.state.messages.single.content, '群内总结');
      expect(notifier.state.error, isNull);
    });
  });
}
