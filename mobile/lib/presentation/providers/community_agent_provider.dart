import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/agent_session_store.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/data/models/chat_stream_events.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/repositories/auth_repository.dart';
import 'package:sparkle/data/repositories/chat_repository.dart';
import 'package:sparkle/data/repositories/community_repository.dart';
import 'package:sparkle/presentation/providers/agent_session_provider.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/chat_provider.dart';
import 'package:sparkle/presentation/providers/guest_provider.dart';
import 'package:uuid/uuid.dart';

const String kCommunityAgentUserId = 'sparkle_agent';
const String kCommunityAgentDisplayName = 'Sparkle AI';
const String kCommunityAgentAvatarSeed = 'sparkle_agent';
const String kAgentMetadataKey = 'agent_message';
const String kAgentVisibilityKey = 'visibility';
const String kAgentVisibilitySelf = 'self';
const String kAgentVisibleToKey = 'visible_to';
const String kAgentSessionIdKey = 'agent_session_id';
const String kAgentContextTypeKey = 'agent_context_type';
const String kAgentContextIdKey = 'agent_context_id';

const int _maxContextMessages = 6;
const int _maxContextChars = 160;

UserBrief buildCommunityAgentUser() => UserBrief(
      id: kCommunityAgentUserId,
      username: 'sparkle_ai',
      nickname: kCommunityAgentDisplayName,
      avatarUrl: 'https://api.dicebear.com/9.x/avataaars/png?seed=$kCommunityAgentAvatarSeed',
      flameLevel: 9,
      flameBrightness: 0.85,
      status: UserStatus.online,
    );

bool isCommunityAgentMessage(MessageInfo message) =>
    message.sender?.id == kCommunityAgentUserId || (message.contentData?[kAgentMetadataKey] == true);

bool isPrivateAgentMessage(PrivateMessageInfo message) =>
    message.sender.id == kCommunityAgentUserId || (message.contentData?[kAgentMetadataKey] == true);

class AgentChatState<T> {
  const AgentChatState({
    this.isSending = false,
    this.streamingContent = '',
    this.messages = const [],
    this.error,
  });

  final bool isSending;
  final String streamingContent;
  final List<T> messages;
  final String? error;

  AgentChatState<T> copyWith({
    bool? isSending,
    String? streamingContent,
    List<T>? messages,
    String? error,
    bool clearError = false,
  }) =>
      AgentChatState<T>(
        isSending: isSending ?? this.isSending,
        streamingContent: streamingContent ?? this.streamingContent,
        messages: messages ?? this.messages,
        error: clearError ? null : error ?? this.error,
      );
}

class _AgentUserContext {
  const _AgentUserContext({
    required this.userId,
    required this.nickname,
    required this.userBrief,
  });

  final String userId;
  final String nickname;
  final UserBrief userBrief;
}

Future<_AgentUserContext> _resolveUserContext(Ref ref) async {
  final user = ref.read(currentUserProvider);
  if (user != null) {
    return _AgentUserContext(
      userId: user.id,
      nickname: user.nickname ?? user.username,
      userBrief: UserBrief(
        id: user.id,
        username: user.username,
        nickname: user.nickname,
        avatarUrl: user.avatarUrl,
        flameLevel: user.flameLevel,
        flameBrightness: user.flameBrightness,
        status: user.status,
      ),
    );
  }

  final guestService = ref.read(guestServiceProvider);
  final guestId = await guestService.getGuestId();
  final guestName = guestService.getGuestNickname();

  return _AgentUserContext(
    userId: guestId,
    nickname: guestName,
    userBrief: UserBrief(
      id: guestId,
      username: guestName,
      nickname: guestName,
      flameBrightness: 0.4,
      status: UserStatus.online,
    ),
  );
}

String buildGroupAgentPrompt({
  required String input,
  required List<MessageInfo> recentMessages,
  String? groupName,
}) {
  final contextLines = recentMessages
      .where((msg) => msg.content != null && msg.content!.trim().isNotEmpty)
      .where((msg) => !isCommunityAgentMessage(msg))
      .take(_maxContextMessages)
      .toList()
      .reversed
      .map((msg) => '${msg.sender?.displayName ?? "系统"}: ${_compressContent(msg.content ?? "")}')
      .join('\n');

  final name = groupName ?? '学习小组';
  return '''
你是Sparkle内置的群聊AI助手，正在协助群聊「$name」。
请基于最近对话给出简洁、可操作的建议或回复，不要冒充真实成员发言。

最近对话:
$contextLines

用户问题:
$input
''';
}

String buildPrivateAgentPrompt({
  required String input,
  required List<PrivateMessageInfo> recentMessages,
  String? friendName,
}) {
  final contextLines = recentMessages
      .where((msg) => msg.content != null && msg.content!.trim().isNotEmpty)
      .where((msg) => !isPrivateAgentMessage(msg))
      .take(_maxContextMessages)
      .toList()
      .reversed
      .map((msg) => '${msg.sender.displayName}: ${_compressContent(msg.content ?? "")}')
      .join('\n');

  final name = friendName ?? '好友';
  return '''
你是Sparkle内置的私聊AI助手，正在协助我与「$name」的对话。
请给出简洁、有礼貌、可直接发送的回复建议，避免过度输出。

最近对话:
$contextLines

用户问题:
$input
''';
}

String _compressContent(String content) {
  final trimmed = content.trim();
  if (trimmed.length <= _maxContextChars) return trimmed;
  return '${trimmed.substring(0, _maxContextChars)}…';
}

class GroupAgentChatNotifier extends StateNotifier<AgentChatState<MessageInfo>> {
  GroupAgentChatNotifier(this._repository, this._ref, this._groupId) : super(const AgentChatState());

  final ChatRepository _repository;
  final Ref _ref;
  final String _groupId;

  Future<void> sendAgentMessage({
    required String prompt,
    String? groupName,
    List<MessageInfo> recentMessages = const [],
  }) async {
    if (state.isSending) return;

    state = state.copyWith(isSending: true, streamingContent: '', clearError: true);

    final userContext = await _resolveUserContext(_ref);
    final sessionId = _ref.read(agentSessionStoreProvider).getOrCreateSessionId(
          AgentSessionScope.group,
          _groupId,
          userContext.userId,
        );
    final fullPrompt = buildGroupAgentPrompt(
      input: prompt,
      recentMessages: recentMessages,
      groupName: groupName,
    );
    final extraContext = {
      kAgentContextTypeKey: 'community_group',
      kAgentContextIdKey: _groupId,
      kAgentSessionIdKey: sessionId,
    };

    var buffer = '';
    try {
      final token = await _ref.read(authRepositoryProvider).getAccessToken();
      await for (final event in _repository.chatStream(
        fullPrompt,
        sessionId,
        userId: userContext.userId,
        nickname: userContext.nickname,
        extraContext: extraContext,
        token: token,
      )) {
        if (event is TextEvent) {
          buffer += event.content;
          state = state.copyWith(streamingContent: buffer);
        } else if (event is FullTextEvent) {
          buffer = event.content;
          state = state.copyWith(streamingContent: buffer);
        } else if (event is ErrorEvent) {
          final message = ErrorMessages.getUserFriendlyMessage(event.code, event.message);
          state = state.copyWith(isSending: false, streamingContent: '', error: message);
          return;
        }
      }

      final content = buffer.trim();
      if (content.isNotEmpty) {
        final message = await _persistGroupAgentMessage(
          userId: userContext.userId,
          content: content,
          sessionId: sessionId,
        );

        state = state.copyWith(
          isSending: false,
          streamingContent: '',
          messages: [message, ...state.messages],
        );
      } else {
        state = state.copyWith(isSending: false, streamingContent: '');
      }
    } catch (e) {
      final message = ErrorMessages.getUserFriendlyMessage('UNKNOWN', e.toString());
      state = state.copyWith(isSending: false, streamingContent: '', error: message);
    }
  }

  Future<MessageInfo> _persistGroupAgentMessage({
    required String userId,
    required String content,
    required String sessionId,
  }) async {
    final repository = _ref.read(communityRepositoryProvider);
    final contentData = {
      kAgentMetadataKey: true,
      kAgentVisibilityKey: kAgentVisibilitySelf,
      kAgentVisibleToKey: userId,
      kAgentSessionIdKey: sessionId,
      kAgentContextTypeKey: 'group',
      kAgentContextIdKey: _groupId,
    };

    try {
      return await repository.sendMessage(
        _groupId,
        type: MessageType.text,
        content: content,
        contentData: contentData,
      );
    } catch (_) {
      return MessageInfo(
        id: const Uuid().v4(),
        messageType: MessageType.text,
        sender: buildCommunityAgentUser(),
        content: content,
        contentData: contentData,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
    }
  }
}

class PrivateAgentChatNotifier extends StateNotifier<AgentChatState<PrivateMessageInfo>> {
  PrivateAgentChatNotifier(this._repository, this._ref, this._friendId) : super(const AgentChatState());

  final ChatRepository _repository;
  final Ref _ref;
  final String _friendId;

  Future<void> sendAgentMessage({
    required String prompt,
    String? friendName,
    List<PrivateMessageInfo> recentMessages = const [],
  }) async {
    if (state.isSending) return;

    state = state.copyWith(isSending: true, streamingContent: '', clearError: true);

    final userContext = await _resolveUserContext(_ref);
    final sessionId = _ref.read(agentSessionStoreProvider).getOrCreateSessionId(
          AgentSessionScope.privateChat,
          _friendId,
          userContext.userId,
        );
    final fullPrompt = buildPrivateAgentPrompt(
      input: prompt,
      recentMessages: recentMessages,
      friendName: friendName,
    );
    final extraContext = {
      kAgentContextTypeKey: 'community_private',
      kAgentContextIdKey: _friendId,
      kAgentSessionIdKey: sessionId,
    };

    var buffer = '';
    try {
      final token = await _ref.read(authRepositoryProvider).getAccessToken();
      await for (final event in _repository.chatStream(
        fullPrompt,
        sessionId,
        userId: userContext.userId,
        nickname: userContext.nickname,
        extraContext: extraContext,
        token: token,
      )) {
        if (event is TextEvent) {
          buffer += event.content;
          state = state.copyWith(streamingContent: buffer);
        } else if (event is FullTextEvent) {
          buffer = event.content;
          state = state.copyWith(streamingContent: buffer);
        } else if (event is ErrorEvent) {
          final message = ErrorMessages.getUserFriendlyMessage(event.code, event.message);
          state = state.copyWith(isSending: false, streamingContent: '', error: message);
          return;
        }
      }

      final content = buffer.trim();
      if (content.isNotEmpty) {
        final message = await _persistPrivateAgentMessage(
          userId: userContext.userId,
          content: content,
          sessionId: sessionId,
          receiver: userContext.userBrief,
        );

        state = state.copyWith(
          isSending: false,
          streamingContent: '',
          messages: [message, ...state.messages],
        );
      } else {
        state = state.copyWith(isSending: false, streamingContent: '');
      }
    } catch (e) {
      final message = ErrorMessages.getUserFriendlyMessage('UNKNOWN', e.toString());
      state = state.copyWith(isSending: false, streamingContent: '', error: message);
    }
  }

  Future<PrivateMessageInfo> _persistPrivateAgentMessage({
    required String userId,
    required String content,
    required String sessionId,
    required UserBrief receiver,
  }) async {
    final repository = _ref.read(communityRepositoryProvider);
    final contentData = {
      kAgentMetadataKey: true,
      kAgentVisibilityKey: kAgentVisibilitySelf,
      kAgentVisibleToKey: userId,
      kAgentSessionIdKey: sessionId,
      kAgentContextTypeKey: 'private',
      kAgentContextIdKey: _friendId,
    };

    try {
      return await repository.sendPrivateMessage(
        PrivateMessageSend(
          targetUserId: _friendId,
          content: content,
          contentData: contentData,
        ),
      );
    } catch (_) {
      return PrivateMessageInfo(
        id: const Uuid().v4(),
        sender: buildCommunityAgentUser(),
        receiver: receiver,
        messageType: MessageType.text,
        content: content,
        contentData: contentData,
        isRead: true,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
    }
  }
}

final groupChatAgentProvider = StateNotifierProvider.family<GroupAgentChatNotifier, AgentChatState<MessageInfo>, String>((ref, groupId) {
  final repository = ref.watch(chatRepositoryProvider);
  return GroupAgentChatNotifier(repository, ref, groupId);
});

final privateChatAgentProvider = StateNotifierProvider.family<PrivateAgentChatNotifier, AgentChatState<PrivateMessageInfo>, String>((ref, friendId) {
  final repository = ref.watch(chatRepositoryProvider);
  return PrivateAgentChatNotifier(repository, ref, friendId);
});
