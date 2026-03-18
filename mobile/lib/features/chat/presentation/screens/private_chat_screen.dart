import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_status_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/community_chat_input.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class PrivateChatScreen extends ConsumerStatefulWidget {
  const PrivateChatScreen({
    required this.friendId,
    this.friendName,
    super.key,
  });
  final String friendId;
  final String? friendName;

  @override
  ConsumerState<PrivateChatScreen> createState() => _PrivateChatScreenState();
}

class _PrivateChatScreenState extends ConsumerState<PrivateChatScreen> {
  String? _displayName;
  String? _avatarUrl;
  bool _isSharing = false;
  bool _agentMode = false;

  @override
  void initState() {
    super.initState();
    _displayName = widget.friendName;
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(privateChatProvider(widget.friendId));
    final notifier = ref.read(privateChatProvider(widget.friendId).notifier);
    final currentUser = ref.watch(currentUserProvider);
    final agentState = ref.watch(privateChatAgentProvider(widget.friendId));

    // Try to get friend info from messages if name not provided
    chatState.whenData((messages) {
      if (_displayName == null && messages.isNotEmpty) {
        final friendMsg = messages.firstWhere(
          (m) => m.sender.id == widget.friendId,
          orElse: () => messages.first,
        );
        if (friendMsg.sender.id == widget.friendId) {
          _displayName = friendMsg.sender.displayName;
          _avatarUrl = friendMsg.sender.avatarUrl;
        } else if (friendMsg.receiver.id == widget.friendId) {
          _displayName = friendMsg.receiver.displayName;
          _avatarUrl = friendMsg.receiver.avatarUrl;
        }
      }
    });

    return GraphiteScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Row(
          children: [
            if (_avatarUrl != null)
              Padding(
                padding: const EdgeInsets.only(right: DS.spacing8),
                child: SparkleAvatar(
                  url: _avatarUrl,
                  fallbackText: _displayName,
                ),
              ),
            Text(_displayName ?? context.l10n.privateChatDefaultTitle),
          ],
        ),
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            Expanded(
              child: chatState.when(
                data: (messages) {
                  final mergedMessages =
                      _mergeMessages(messages, agentState, currentUser);
                  final showAgentStatus = agentState.isSending &&
                      agentState.streamingContent.isEmpty;
                  if (mergedMessages.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.chat_bubble_outline,
                            size: DS.iconSize3xl,
                            color: DS.neutral300,
                          ),
                          const SizedBox(height: DS.spacing24),
                          Text(
                            context.l10n.privateChatEmptyPrompt,
                            style: TextStyle(
                              color: DS.neutral500,
                              fontSize: DS.fontSizeBase,
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  return Align(
                    alignment: Alignment.topCenter,
                    child: ListView.builder(
                      reverse: true,
                      shrinkWrap: true,
                      padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing8, vertical: DS.spacing16,),
                      itemCount:
                          mergedMessages.length + (showAgentStatus ? 1 : 0),
                      itemBuilder: (context, index) {
                      if (showAgentStatus && index == 0) {
                        return Padding(
                          padding: EdgeInsets.only(bottom: DS.spacing16),
                          child: AiStatusIndicator(
                            status: 'THINKING',
                            details: '思考中...',
                          ),
                        );
                      }

                      final messageIndex = showAgentStatus ? index - 1 : index;
                      final message = mergedMessages[messageIndex];
                      return ChatBubble(
                        message: message,
                        currentUserId: currentUser?.id,
                        onQuote: isPrivateAgentMessage(message)
                            ? null
                            : (msg) => setState(() =>
                                notifier.setQuote(msg as PrivateMessageInfo?),),
                        onRevoke: isPrivateAgentMessage(message)
                            ? null
                            : (msg) => notifier
                                .revokeMessage((msg as PrivateMessageInfo).id),
                      );
                    },
                    ),
                  );
                },
                loading: () => const Center(child: LoadingIndicator()),
                error: (e, s) => Center(
                  child: CustomErrorWidget.page(
                    context: context,
                    message: e.toString(),
                    onRetry: () => ref
                        .read(privateChatProvider(widget.friendId).notifier)
                        .loadMessages(),
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(
                  DS.spacing16, DS.spacing8, DS.spacing16, 0,),
              child: Row(
                children: [
                  FilterChip(
                    selected: _agentMode,
                    label: Text(_agentMode ? 'AI助手 已开启' : 'AI助手'),
                    avatar: Icon(
                      Icons.auto_awesome,
                      size: DS.iconSizeXs,
                      color: _agentMode ? DS.brandPrimary : DS.neutral500,
                    ),
                    onSelected: (v) => setState(() => _agentMode = v),
                  ),
                  const Spacer(),
                  if (agentState.isSending)
                    Text(
                      '思考中...',
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        color: DS.brandPrimary70,
                      ),
                    ),
                ],
              ),
            ),
            CommunityChatInput(
              quotedMessage: notifier.quotedMessage,
              onCancelQuote: () => setState(() => notifier.setQuote(null)),
              onSend: (text, {replyToId}) {
                if (_agentMode) {
                  _sendAgentPrompt(text, agentState);
                } else {
                  notifier.sendMessage(content: text, replyToId: replyToId);
                }
              },
              onQuickShare: _isSharing ? null : (payload) => _handleQuickShare(payload),
              enabled: !_isSharing && (!_agentMode || !agentState.isSending),
            ),
          ],
        ),
      ),
    );
  }

  List<PrivateMessageInfo> _mergeMessages(
    List<PrivateMessageInfo> messages,
    AgentChatState<PrivateMessageInfo> agentState,
    UserModel? currentUser,
  ) {
    final merged = [...messages, ...agentState.messages];
    if (agentState.streamingContent.isNotEmpty) {
      merged.add(_buildStreamingAgentMessage(
        agentState.streamingContent,
        currentUser,
      ));
    }
    final byId = <String, PrivateMessageInfo>{};
    for (final message in merged) {
      final existing = byId[message.id];
      if (existing == null || message.createdAt.isAfter(existing.createdAt)) {
        byId[message.id] = message;
      }
    }
    final deduped = byId.values.toList()
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return deduped;
  }

  PrivateMessageInfo _buildStreamingAgentMessage(
    String content,
    UserModel? currentUser,
  ) {
    final receiver = currentUser != null
        ? UserBrief(
            id: currentUser.id,
            username: currentUser.username,
            nickname: currentUser.nickname,
            avatarUrl: currentUser.avatarUrl,
            flameLevel: currentUser.flameLevel,
            flameBrightness: currentUser.flameBrightness,
            status: currentUser.status,
          )
        : UserBrief(id: '', username: context.l10n.commonUnknown);

    return PrivateMessageInfo(
      id: 'agent_streaming_${DateTime.now().millisecondsSinceEpoch}',
      sender: buildCommunityAgentUser(
        localizedName: context.l10n.communityAgentName,
      ),
      receiver: receiver,
      messageType: MessageType.text,
      content: content,
      contentData: {kAgentMetadataKey: true, 'agent_streaming': true},
      isRead: true,
      createdAt: DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }

  void _sendAgentPrompt(
    String prompt,
    AgentChatState<PrivateMessageInfo> agentState,
  ) {
    if (agentState.isSending) return;
    unawaited(
      ref
          .read(privateChatAgentProvider(widget.friendId).notifier)
          .sendAgentMessage(
            prompt: prompt,
            friendName: widget.friendName,
            recentMessages:
                ref.read(privateChatProvider(widget.friendId)).valueOrNull ??
                    [],
          ),
    );
  }

  Future<void> _handleQuickShare(UniversalSharePayload payload) async {
    if (_isSharing) return;

    setState(() => _isSharing = true);
    try {
      await ref.read(communityShareRepositoryProvider).shareResource(
            resourceType: payload.contentType.stringValue,
            resourceId: payload.resourceId,
            targetUserId: widget.friendId, // 私聊分享给好友
            comment: payload.shareMessage,
          );
      if (!mounted) return;
      ref.invalidate(privateChatProvider(widget.friendId));
      AppFeedback.success(context, context.l10n.shareResourceSuccess);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, context.l10n.shareResourceFailed(e));
    } finally {
      if (mounted) {
        setState(() => _isSharing = false);
      }
    }
  }
}
