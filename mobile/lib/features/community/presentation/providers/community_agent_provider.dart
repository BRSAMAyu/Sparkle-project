import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart';
import 'package:sparkle/features/chat/presentation/providers/agent_session_provider.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
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

UserBrief buildCommunityAgentUser({String? localizedName}) => UserBrief(
      id: kCommunityAgentUserId,
      username: 'sparkle_ai',
      nickname: localizedName ?? kCommunityAgentDisplayName,
      avatarUrl:
          'https://api.dicebear.com/9.x/avataaars/png?seed=$kCommunityAgentAvatarSeed',
      flameLevel: 9,
      flameBrightness: 0.85,
      status: UserStatus.online,
    );

bool isCommunityAgentMessage(MessageInfo message) =>
    message.sender?.id == kCommunityAgentUserId ||
    (message.contentData?[kAgentMetadataKey] == true);

bool isPrivateAgentMessage(PrivateMessageInfo message) =>
    message.sender.id == kCommunityAgentUserId ||
    (message.contentData?[kAgentMetadataKey] == true);

class AgentChatState<T> {
  const AgentChatState({
    this.isSending = false,
    this.streamingContent = '',
    this.messages = const [],
    this.error,
    this.lastDraft,
  });

  final bool isSending;
  final String streamingContent;
  final List<T> messages;
  final String? error;
  final String? lastDraft;

  AgentChatState<T> copyWith({
    bool? isSending,
    String? streamingContent,
    List<T>? messages,
    String? error,
    String? lastDraft,
    bool clearError = false,
    bool clearDraft = false,
  }) =>
      AgentChatState<T>(
        isSending: isSending ?? this.isSending,
        streamingContent: streamingContent ?? this.streamingContent,
        messages: messages ?? this.messages,
        error: clearError ? null : error ?? this.error,
        lastDraft: clearDraft ? null : lastDraft ?? this.lastDraft,
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
      .map(
        (msg) =>
            '${msg.sender?.displayName ?? "系统"}: ${_compressContent(msg.content ?? "")}',
      )
      .join('\n');

  final name = groupName ?? '学习小组';
  return '''
你是Sparkle内置的群聊AI助手，正在协助群聊「$name」。
你的任务是产出一条最终可直接发送到群里的中文消息。
只输出消息正文本身，不要解释，不要加前言，不要写“我来帮你”“你可以这样发”“建议发送”，不要使用项目符号或备注，不要冒充系统说明。
语气自然、简洁、友好，像群成员会直接发出去的话。
如果需要列点，只允许使用 `1. ` 或 `- `，不要使用 `•`、`◦`、emoji 项目符号、半残 Markdown。

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
      .map(
        (msg) =>
            '${msg.sender.displayName}: ${_compressContent(msg.content ?? "")}',
      )
      .join('\n');

  final name = friendName ?? '好友';
  return '''
你是Sparkle内置的私聊AI助手，正在协助我与「$name」的对话。
你的任务是产出一条最终可直接发送给对方的中文私聊回复。
只输出回复正文本身，不要解释，不要加前言，不要写“我来帮你”“你可以这样回”“建议回复”，不要附带分析或备注。
语气自然、礼貌、克制，像我会直接按下发送的内容。
如果需要列点，只允许使用 `1. ` 或 `- `，不要使用特殊项目符号或半残 Markdown。

最近对话:
$contextLines

用户问题:
$input
''';
}

String buildGroupAssistantPresetPrompt(
  String preset, {
  String? groupName,
}) {
  final name = groupName ?? '学习小组';
  switch (preset) {
    case 'summary':
      return '请基于最近群聊内容，为「$name」生成一段可直接发到群里的快速总结，包含当前讨论焦点和下一步。';
    case 'reminder':
      return '请基于最近群聊内容，为「$name」生成一段可直接发到群里的简短提醒，推动成员继续行动，语气自然。';
    case 'consensus':
      return '请基于最近群聊内容，为「$name」生成一段可直接发到群里的共识总结，明确大家已经一致的结论和下一步。';
    default:
      return preset;
  }
}

String buildPrivateAssistantPresetPrompt(
  String preset, {
  String? friendName,
}) {
  final name = friendName ?? '好友';
  switch (preset) {
    case 'polish_reply':
      return '请根据最近私聊内容，帮我生成一条可以直接发给「$name」的自然回复，要求简洁、友好、准确承接上下文。';
    case 'gentle_reminder':
      return '请根据最近私聊内容，帮我生成一条可以直接发给「$name」的温和提醒，不催促、不生硬。';
    case 'schedule_sync':
      return '请根据最近私聊内容，帮我生成一条可以直接发给「$name」的时间协调消息，用于约定下一步或确认安排。';
    case 'summary':
      return '请根据最近私聊内容，生成一段简短总结，帮我看清我和「$name」目前已经确认了什么、还缺什么，要求直接可读、可执行。';
    case 'next_step':
      return '请根据最近私聊内容，帮我提炼出最值得现在就发送给「$name」的一条下一步推进消息，要求明确、自然、可执行。';
    default:
      return preset;
  }
}

String _compressContent(String content) {
  final trimmed = content.trim();
  if (trimmed.length <= _maxContextChars) return trimmed;
  return '${trimmed.substring(0, _maxContextChars)}…';
}

String normalizeCommunityAgentOutput(String content) {
  var normalized = content
      .replaceAll(RegExp(r'```[\s\S]*?```'), '')
      .replaceAll(RegExp(r'^\s{0,3}#{1,6}\s*', multiLine: true), '')
      .replaceAll(RegExp(r'^\s*[-*+]\s+', multiLine: true), '')
      .replaceAll(RegExp(r'^\s*\d+\.\s+', multiLine: true), '');

  normalized = normalized
      .replaceAllMapped(
        RegExp(r'`([^`\n]+)`'),
        (match) => match.group(1) ?? '',
      )
      .replaceAllMapped(
        RegExp(r'\*\*([^*]+)\*\*'),
        (match) => match.group(1) ?? '',
      )
      .replaceAllMapped(
        RegExp(r'__([^_]+)__'),
        (match) => match.group(1) ?? '',
      )
      .replaceAllMapped(
        RegExp(r'(?<!\*)\*([^*\n]+)\*(?!\*)'),
        (match) => match.group(1) ?? '',
      )
      .replaceAllMapped(
        RegExp(r'(?<!_)_([^_\n]+)_(?!_)'),
        (match) => match.group(1) ?? '',
      );

  final lines = normalized
      .split('\n')
      .map((line) => line.trimRight())
      .where((line) => line.trim().isNotEmpty)
      .toList();

  return lines.join('\n').trim();
}

String _fallbackGroupAgentOutput(
  String preset,
  List<MessageInfo> recentMessages,
) {
  final lines = recentMessages
      .where((msg) => msg.content != null && msg.content!.trim().isNotEmpty)
      .where((msg) => !isCommunityAgentMessage(msg))
      .take(3)
      .map((msg) => _compressContent(msg.content ?? ''))
      .toList();

  if (lines.isEmpty) {
    return switch (preset) {
      'summary' => '我先帮大家收一下：目前还没有形成完整讨论，可以先补充目标、难点和下一步安排。',
      'reminder' => '提醒一下，大家可以先明确各自负责的事项和完成时间，这样后续推进会更顺。',
      'consensus' => '目前还没有形成稳定共识，建议先确认目标、分工和时间点，再继续推进。',
      _ => '我先帮你整理成一句更清楚的话：把目标、当前进度和下一步写出来会更容易推进。',
    };
  }

  final joined = lines.join('；');
  return switch (preset) {
    'summary' => '我先快速总结一下：$joined。当前重点是先把下一步动作说清楚并开始推进。',
    'reminder' => '提醒一下：$joined。建议现在先各自确认下一步并同步进度。',
    'consensus' => '目前大家比较一致的是：$joined。可以按这个方向继续推进。',
    _ => joined,
  };
}

String _fallbackPrivateAgentOutput(
  String preset,
  List<PrivateMessageInfo> recentMessages,
  String? friendName,
) {
  final name = friendName ?? '你';
  final lines = recentMessages
      .where((msg) => msg.content != null && msg.content!.trim().isNotEmpty)
      .where((msg) => !isPrivateAgentMessage(msg))
      .take(2)
      .map((msg) => _compressContent(msg.content ?? ''))
      .toList();

  final context = lines.isEmpty ? '' : '我结合我们刚才聊的内容看，';
  return switch (preset) {
    'polish_reply' => '${context}可以这样回$name：我这边看到了，我们按这个方向继续，我稍后给你一个更明确的进展。',
    'gentle_reminder' => '${context}可以这样提醒$name：想跟你确认一下这件事的进度，如果方便的话我们今天把下一步也一起定下来。',
    'schedule_sync' => '${context}可以这样发给$name：我们把下一步时间对一下吧，你这两天什么时候方便，我这边可以配合安排。',
    _ => lines.isEmpty ? '我先帮你整理成一句更自然的回复。' : lines.join('；'),
  };
}

class GroupAgentChatNotifier
    extends StateNotifier<AgentChatState<MessageInfo>> {
  GroupAgentChatNotifier(this._repository, this._ref, this._groupId)
      : super(const AgentChatState());

  final ChatRepository _repository;
  final Ref _ref;
  final String _groupId;

  Future<void> sendAgentMessage({
    required String prompt,
    String? groupName,
    List<MessageInfo> recentMessages = const [],
    String preset = 'custom',
    String reasoningMode = 'fast',
    String chatMode = 'standard',
  }) async {
    if (state.isSending) return;

    state =
        state.copyWith(isSending: true, streamingContent: '', clearError: true);

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
      'reasoning_mode': reasoningMode,
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
        chatMode: chatMode,
      )) {
        if (event is TextEvent) {
          buffer += event.content;
          state = state.copyWith(
            streamingContent: normalizeCommunityAgentOutput(buffer),
          );
        } else if (event is FullTextEvent) {
          buffer = event.content;
          state = state.copyWith(
            streamingContent: normalizeCommunityAgentOutput(buffer),
          );
        } else if (event is ErrorEvent) {
          final message =
              ErrorMessages.getUserFriendlyMessage(event.code, event.message);
          state = state.copyWith(
            isSending: false,
            streamingContent: '',
            error: message,
          );
          return;
        }
      }

      final content = (normalizeCommunityAgentOutput(buffer).trim().isNotEmpty
              ? normalizeCommunityAgentOutput(buffer).trim()
              : _fallbackGroupAgentOutput(preset, recentMessages))
          .trim();
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
      final message =
          ErrorMessages.getUserFriendlyMessage('UNKNOWN', e.toString());
      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        error: message,
      );
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

class PrivateAgentChatNotifier
    extends StateNotifier<AgentChatState<PrivateMessageInfo>> {
  PrivateAgentChatNotifier(this._repository, this._ref, this._friendId)
      : super(const AgentChatState());

  final ChatRepository _repository;
  final Ref _ref;
  final String _friendId;

  Future<String?> composeDraft({
    required String prompt,
    String? friendName,
    List<PrivateMessageInfo> recentMessages = const [],
    String preset = 'custom',
    String reasoningMode = 'fast',
    String chatMode = 'standard',
  }) async {
    if (state.isSending) return null;

    state = state.copyWith(
      isSending: true,
      streamingContent: '',
      clearError: true,
      clearDraft: true,
    );

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
      'reasoning_mode': reasoningMode,
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
        chatMode: chatMode,
      )) {
        if (event is TextEvent) {
          buffer += event.content;
          state = state.copyWith(
            streamingContent: normalizeCommunityAgentOutput(buffer),
          );
        } else if (event is FullTextEvent) {
          buffer = event.content;
          state = state.copyWith(
            streamingContent: normalizeCommunityAgentOutput(buffer),
          );
        } else if (event is ErrorEvent) {
          final message =
              ErrorMessages.getUserFriendlyMessage(event.code, event.message);
          state = state.copyWith(
            isSending: false,
            streamingContent: '',
            error: message,
          );
          return null;
        }
      }

      final content = (normalizeCommunityAgentOutput(buffer).trim().isNotEmpty
              ? normalizeCommunityAgentOutput(buffer).trim()
              : _fallbackPrivateAgentOutput(
                  preset,
                  recentMessages,
                  friendName,
                ))
          .trim();
      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        lastDraft: content.isEmpty ? null : content,
      );
      return content.isEmpty ? null : content;
    } catch (e) {
      final message =
          ErrorMessages.getUserFriendlyMessage('UNKNOWN', e.toString());
      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        error: message,
      );
      return null;
    }
  }

  Future<void> saveSelfVisibleDraft({
    required String content,
  }) async {
    final trimmed = normalizeCommunityAgentOutput(content).trim();
    if (trimmed.isEmpty) return;

    final userContext = await _resolveUserContext(_ref);
    final sessionId = _ref.read(agentSessionStoreProvider).getOrCreateSessionId(
          AgentSessionScope.privateChat,
          _friendId,
          userContext.userId,
        );
    final message = PrivateMessageInfo(
      id: const Uuid().v4(),
      sender: buildCommunityAgentUser(),
      receiver: userContext.userBrief,
      messageType: MessageType.text,
      content: trimmed,
      contentData: {
        kAgentMetadataKey: true,
        kAgentVisibilityKey: kAgentVisibilitySelf,
        kAgentVisibleToKey: userContext.userId,
        kAgentSessionIdKey: sessionId,
        kAgentContextTypeKey: 'private',
        kAgentContextIdKey: _friendId,
      },
      isRead: true,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );

    state = state.copyWith(
      messages: [message, ...state.messages],
      clearDraft: true,
    );
  }

  void removeLocalDraft(String messageId) {
    state = state.copyWith(
      messages: state.messages
          .where((message) => message.id != messageId)
          .toList(growable: false),
    );
  }

  Future<void> sendAgentMessage({
    required String prompt,
    String? friendName,
    List<PrivateMessageInfo> recentMessages = const [],
    String preset = 'custom',
    String reasoningMode = 'fast',
    String chatMode = 'standard',
  }) async {
    final content = await composeDraft(
      prompt: prompt,
      friendName: friendName,
      recentMessages: recentMessages,
      preset: preset,
      reasoningMode: reasoningMode,
      chatMode: chatMode,
    );
    if (content == null || content.isEmpty) {
      return;
    }
    try {
      final userContext = await _resolveUserContext(_ref);
      final sessionId =
          _ref.read(agentSessionStoreProvider).getOrCreateSessionId(
                AgentSessionScope.privateChat,
                _friendId,
                userContext.userId,
              );
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
          clearDraft: true,
        );
      }
    } catch (e) {
      final message =
          ErrorMessages.getUserFriendlyMessage('UNKNOWN', e.toString());
      state = state.copyWith(
        isSending: false,
        streamingContent: '',
        error: message,
      );
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

final groupChatAgentProvider = StateNotifierProvider.family<
    GroupAgentChatNotifier,
    AgentChatState<MessageInfo>,
    String>((ref, groupId) {
  final repository = ref.watch(chatRepositoryProvider);
  return GroupAgentChatNotifier(repository, ref, groupId);
});

final privateChatAgentProvider = StateNotifierProvider.family<
    PrivateAgentChatNotifier,
    AgentChatState<PrivateMessageInfo>,
    String>((ref, friendId) {
  final repository = ref.watch(chatRepositoryProvider);
  return PrivateAgentChatNotifier(repository, ref, friendId);
});
