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

  final l10n = I18nService.instance.l10n;
  final name = groupName ?? l10n.communityAgentStudyGroup;
  final zh = I18nService.instance.isChinese;
  return zh
      ? l10n.communityAgentGroupPromptZh(name, contextLines, input)
      : l10n.communityAgentGroupPromptEn(name, contextLines, input);
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

  final l10n = I18nService.instance.l10n;
  final name = friendName ?? l10n.communityAgentFriend;
  final zh = I18nService.instance.isChinese;
  return zh
      ? l10n.communityAgentPrivatePromptZh(name, contextLines, input)
      : l10n.communityAgentPrivatePromptEn(name, contextLines, input);
}

String buildGroupAssistantPresetPrompt(
  String preset, {
  String? groupName,
}) {
  final l10n = I18nService.instance.l10n;
  final name = groupName ?? l10n.communityAgentStudyGroup;
  final zh = I18nService.instance.isChinese;
  switch (preset) {
    case 'summary':
      return zh ? l10n.communityAgentPresetSummaryGroupZh(name) : l10n.communityAgentPresetSummaryGroupEn(name);
    case 'reminder':
      return zh ? l10n.communityAgentPresetReminderGroupZh(name) : l10n.communityAgentPresetReminderGroupEn(name);
    case 'consensus':
      return zh ? l10n.communityAgentPresetConsensusGroupZh(name) : l10n.communityAgentPresetConsensusGroupEn(name);
    default:
      return preset;
  }
}

String buildPrivateAssistantPresetPrompt(
  String preset, {
  String? friendName,
}) {
  final l10n = I18nService.instance.l10n;
  final name = friendName ?? l10n.communityAgentFriend;
  final zh = I18nService.instance.isChinese;
  switch (preset) {
    case 'polish_reply':
      return zh ? l10n.communityAgentPresetPolishReplyZh(name) : l10n.communityAgentPresetPolishReplyEn(name);
    case 'gentle_reminder':
      return zh ? l10n.communityAgentPresetGentleReminderZh(name) : l10n.communityAgentPresetGentleReminderEn(name);
    case 'schedule_sync':
      return zh ? l10n.communityAgentPresetScheduleSyncZh(name) : l10n.communityAgentPresetScheduleSyncEn(name);
    case 'summary':
      return zh ? l10n.communityAgentPresetPrivateSummaryZh(name) : l10n.communityAgentPresetPrivateSummaryEn(name);
    case 'next_step':
      return zh ? l10n.communityAgentPresetNextStepZh(name) : l10n.communityAgentPresetNextStepEn(name);
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

  final l10n = I18nService.instance.l10n;
  final zh = I18nService.instance.isChinese;
  if (lines.isEmpty) {
    return switch (preset) {
      'summary' => zh ? l10n.communityFallbackSummaryEmptyZh : l10n.communityFallbackSummaryEmptyEn,
      'reminder' => zh ? l10n.communityFallbackReminderEmptyZh : l10n.communityFallbackReminderEmptyEn,
      'consensus' => zh ? l10n.communityFallbackConsensusEmptyZh : l10n.communityFallbackConsensusEmptyEn,
      _ => zh ? l10n.communityFallbackDefaultEmptyZh : l10n.communityFallbackDefaultEmptyEn,
    };
  }

  final joined = lines.join(zh ? '；' : '; ');
  return switch (preset) {
    'summary' => zh ? l10n.communityFallbackSummaryZh(joined) : l10n.communityFallbackSummaryEn(joined),
    'reminder' => zh ? l10n.communityFallbackReminderZh(joined) : l10n.communityFallbackReminderEn(joined),
    'consensus' => zh ? l10n.communityFallbackConsensusZh(joined) : l10n.communityFallbackConsensusEn(joined),
    _ => joined,
  };
}

String _fallbackPrivateAgentOutput(
  String preset,
  List<PrivateMessageInfo> recentMessages,
  String? friendName,
) {
  final l10n = I18nService.instance.l10n;
  final zh = I18nService.instance.isChinese;
  final name = friendName ?? l10n.communityAgentYou;
  final lines = recentMessages
      .where((msg) => msg.content != null && msg.content!.trim().isNotEmpty)
      .where((msg) => !isPrivateAgentMessage(msg))
      .take(2)
      .map((msg) => _compressContent(msg.content ?? ''))
      .toList();

  final context = lines.isEmpty ? '' : (zh ? l10n.communityFallbackPrivateContextZh : l10n.communityFallbackPrivateContextEn);
  return switch (preset) {
    'polish_reply' => zh
        ? l10n.communityFallbackPrivatePolishZh(context, name)
        : l10n.communityFallbackPrivatePolishEn(context, name),
    'gentle_reminder' => zh
        ? l10n.communityFallbackPrivateGentleZh(context, name)
        : l10n.communityFallbackPrivateGentleEn(context, name),
    'schedule_sync' => zh
        ? l10n.communityFallbackPrivateScheduleZh(context, name)
        : l10n.communityFallbackPrivateScheduleEn(context, name),
    _ => lines.isEmpty
        ? (zh ? l10n.communityFallbackPrivateDefaultEmptyZh : l10n.communityFallbackPrivateDefaultEmptyEn)
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
