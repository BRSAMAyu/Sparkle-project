import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/utils/error_messages.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
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

  final name = groupName ?? (I18nService.instance.isChinese ? '学习小组' : 'Study Group');
  final zh = I18nService.instance.isChinese;
  if (zh) {
    return '''
你是Sparkle内置的群聊AI助手，正在协助群聊「$name」。
你的任务是产出一条最终可直接发送到群里的中文消息。
只输出消息正文本身，不要解释，不要加前言，不要写”我来帮你””你可以这样发””建议发送”，不要使用项目符号或备注，不要冒充系统说明。
语气自然、简洁、友好，像群成员会直接发出去的话。
如果需要列点，只允许使用 `1. ` 或 `- `，不要使用 `•`、`◦`、emoji 项目符号、半残 Markdown。

最近对话:
$contextLines

用户问题:
$input
''';
  }
  return '''
You are Sparkle's built-in group chat AI assistant, helping in the group “$name”.
Your task is to produce a single message ready to send directly in the group.
Output only the message body — no explanations, no preambles, no “I can help” or “You could say” or “Suggested reply”, no bullet points or notes, no system impersonation.
Tone: natural, concise, friendly — like something a group member would actually send.
If you need to list items, only use `1. ` or `- `. No `•`, `◦`, emoji bullets, or broken Markdown.

Recent conversation:
$contextLines

User question:
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

  final name = friendName ?? (I18nService.instance.isChinese ? '好友' : 'Friend');
  final zh = I18nService.instance.isChinese;
  if (zh) {
    return '''
你是Sparkle内置的私聊AI助手，正在协助我与「$name」的对话。
你的任务是产出一条最终可直接发送给对方的中文私聊回复。
只输出回复正文本身，不要解释，不要加前言，不要写”我来帮你””你可以这样回””建议回复”，不要附带分析或备注。
语气自然、礼貌、克制，像我会直接按下发送的内容。
如果需要列点，只允许使用 `1. ` 或 `- `，不要使用特殊项目符号或半残 Markdown。

最近对话:
$contextLines

用户问题:
$input
''';
  }
  return '''
You are Sparkle's built-in private chat AI assistant, helping with my conversation with “$name”.
Your task is to produce a single private reply ready to send directly.
Output only the reply body — no explanations, no preambles, no “I can help” or “You could reply” or “Suggested reply”, no analysis or notes.
Tone: natural, polite, restrained — like something I would actually hit send on.
If you need to list items, only use `1. ` or `- `. No special bullets or broken Markdown.

Recent conversation:
$contextLines

User question:
$input
''';
}

String buildGroupAssistantPresetPrompt(
  String preset, {
  String? groupName,
}) {
  final zh = I18nService.instance.isChinese;
  final name = groupName ?? (zh ? '学习小组' : 'Study Group');
  switch (preset) {
    case 'summary':
      return zh
          ? '请基于最近群聊内容，为「$name」生成一段可直接发到群里的快速总结，包含当前讨论焦点和下一步。'
          : 'Based on recent group chat, generate a quick summary for "$name" that can be sent directly, including current discussion focus and next steps.';
    case 'reminder':
      return zh
          ? '请基于最近群聊内容，为「$name」生成一段可直接发到群里的简短提醒，推动成员继续行动，语气自然。'
          : 'Based on recent group chat, generate a brief reminder for "$name" to push members to keep acting, with a natural tone.';
    case 'consensus':
      return zh
          ? '请基于最近群聊内容，为「$name」生成一段可直接发到群里的共识总结，明确大家已经一致的结论和下一步。'
          : 'Based on recent group chat, generate a consensus summary for "$name" that clarifies agreed conclusions and next steps.';
    default:
      return preset;
  }
}

String buildPrivateAssistantPresetPrompt(
  String preset, {
  String? friendName,
}) {
  final zh = I18nService.instance.isChinese;
  final name = friendName ?? (zh ? '好友' : 'Friend');
  switch (preset) {
    case 'polish_reply':
      return zh
          ? '请根据最近私聊内容，帮我生成一条可以直接发给「$name」的自然回复，要求简洁、友好、准确承接上下文。'
          : 'Based on recent chat, help me generate a natural reply to send directly to "$name" — concise, friendly, and contextually accurate.';
    case 'gentle_reminder':
      return zh
          ? '请根据最近私聊内容，帮我生成一条可以直接发给「$name」的温和提醒，不催促、不生硬。'
          : 'Based on recent chat, help me generate a gentle reminder for "$name" — no pushing, not blunt.';
    case 'schedule_sync':
      return zh
          ? '请根据最近私聊内容，帮我生成一条可以直接发给「$name」的时间协调消息，用于约定下一步或确认安排。'
          : 'Based on recent chat, help me generate a scheduling message for "$name" to align on next steps or confirm plans.';
    case 'summary':
      return zh
          ? '请根据最近私聊内容，生成一段简短总结，帮我看清我和「$name」目前已经确认了什么、还缺什么，要求直接可读、可执行。'
          : 'Based on recent chat, generate a brief summary showing what "$name" and I have confirmed and what\'s still pending — direct, readable, actionable.';
    case 'next_step':
      return zh
          ? '请根据最近私聊内容，帮我提炼出最值得现在就发送给「$name」的一条下一步推进消息，要求明确、自然、可执行。'
          : 'Based on recent chat, extract the most worthwhile next-step message to send "$name" right now — clear, natural, actionable.';
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
  final normalized = normalizeRichText(content);
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

  final zh = I18nService.instance.isChinese;
  if (lines.isEmpty) {
    return switch (preset) {
      'summary' => zh
          ? '我先帮大家收一下：目前还没有形成完整讨论，可以先补充目标、难点和下一步安排。'
          : 'Let me summarize: no full discussion yet. Let\'s start by sharing goals, blockers, and next steps.',
      'reminder' => zh
          ? '提醒一下，大家可以先明确各自负责的事项和完成时间，这样后续推进会更顺。'
          : 'Quick reminder: let\'s clarify who owns what and when it\'s due — it\'ll make progress smoother.',
      'consensus' => zh
          ? '目前还没有形成稳定共识，建议先确认目标、分工和时间点，再继续推进。'
          : 'No stable consensus yet. Let\'s confirm goals, division of work, and timelines before pushing forward.',
      _ => zh
          ? '我先帮你整理成一句更清楚的话：把目标、当前进度和下一步写出来会更容易推进。'
          : 'Let me rephrase that more clearly: writing down goals, current progress, and next steps will help move things forward.',
    };
  }

  final joined = lines.join(zh ? '；' : '; ');
  return switch (preset) {
    'summary' => zh
        ? '我先快速总结一下：$joined。当前重点是先把下一步动作说清楚并开始推进。'
        : 'Quick summary: $joined. The focus now is clarifying next actions and getting started.',
    'reminder' => zh
        ? '提醒一下：$joined。建议现在先各自确认下一步并同步进度。'
        : 'Reminder: $joined. Let\'s each confirm our next step and sync progress.',
    'consensus' => zh
        ? '目前大家比较一致的是：$joined。可以按这个方向继续推进。'
        : 'Everyone agrees on: $joined. Let\'s keep pushing in this direction.',
    _ => joined,
  };
}

String _fallbackPrivateAgentOutput(
  String preset,
  List<PrivateMessageInfo> recentMessages,
  String? friendName,
) {
  final zh = I18nService.instance.isChinese;
  final name = friendName ?? (zh ? '你' : 'you');
  final lines = recentMessages
      .where((msg) => msg.content != null && msg.content!.trim().isNotEmpty)
      .where((msg) => !isPrivateAgentMessage(msg))
      .take(2)
      .map((msg) => _compressContent(msg.content ?? ''))
      .toList();

  final context = lines.isEmpty ? '' : (zh ? '我结合我们刚才聊的内容看，' : 'Based on what we just discussed, ');
  return switch (preset) {
    'polish_reply' => zh
        ? '${context}可以这样回$name：我这边看到了，我们按这个方向继续，我稍后给你一个更明确的进展。'
        : '${context}You could reply to $name: "Got it, let\'s keep going in this direction — I\'ll follow up with a clearer update soon."',
    'gentle_reminder' => zh
        ? '${context}可以这样提醒$name：想跟你确认一下这件事的进度，如果方便的话我们今天把下一步也一起定下来。'
        : '${context}You could gently remind $name: "Just checking on the progress — if convenient, let\'s nail down the next step today."',
    'schedule_sync' => zh
        ? '${context}可以这样发给$name：我们把下一步时间对一下吧，你这两天什么时候方便，我这边可以配合安排。'
        : '${context}You could send to $name: "Let\'s align on timing for the next step. When are you free in the next couple of days?"',
    _ => lines.isEmpty
        ? (zh ? '我先帮你整理成一句更自然的回复。' : 'Let me help rephrase that more naturally.')
        : lines.join(zh ? '；' : '; '),
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
