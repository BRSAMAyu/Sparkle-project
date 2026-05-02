import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_status_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/community_chat_input.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
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
  final TextEditingController _composerController = TextEditingController();
  final FocusNode _composerFocusNode = FocusNode();
  late final ScrollController _scrollController;
  String? _displayName;
  String? _avatarUrl;
  bool _isSharing = false;
  bool _agentMode = false;
  String? _assistantOriginalDraft;
  String? _lastNewestMessageId;

  @override
  void initState() {
    super.initState();
    _displayName = widget.friendName;
    _scrollController = ScrollController();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _composerController.dispose();
    _composerFocusNode.dispose();
    super.dispose();
  }

  void _scheduleScrollToLatest() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) {
        return;
      }
      final target = 0.0;
      final position = _scrollController.position;
      if ((position.pixels - target).abs() < 8) {
        _scrollController.jumpTo(target);
        return;
      }
      unawaited(
        _scrollController.animateTo(
          target,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
        ),
      );
    });
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
                  final newestMessageId =
                      mergedMessages.isEmpty ? null : mergedMessages.first.id;
                  String? latestAssistantMessageId;
                  for (final message in mergedMessages) {
                    if (isPrivateAgentMessage(message)) {
                      latestAssistantMessageId = message.id;
                      break;
                    }
                  }
                  if (newestMessageId != null &&
                      newestMessageId != _lastNewestMessageId) {
                    _lastNewestMessageId = newestMessageId;
                    _scheduleScrollToLatest();
                  }
                  final showAgentStatus = agentState.isSending &&
                      agentState.streamingContent.trim().isEmpty;
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
                      controller: _scrollController,
                      reverse: true,
                      shrinkWrap: true,
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing16,
                      ),
                      itemCount:
                          mergedMessages.length + (showAgentStatus ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (showAgentStatus && index == 0) {
                          return Padding(
                            padding: EdgeInsets.only(bottom: DS.spacing16),
                            child: AiStatusIndicator(
                              status: 'THINKING',
                              details: context.l10n.chatPrivateThinking,
                              enableStatusTrack: false,
                            ),
                          );
                        }

                        final messageIndex =
                            showAgentStatus ? index - 1 : index;
                        final message = mergedMessages[messageIndex];
                        return ChatBubble(
                          message: message,
                          currentUserId: currentUser?.id,
                          isLatestAssistantMessage:
                              latestAssistantMessageId != null &&
                                  message.id == latestAssistantMessageId,
                          onQuote: isPrivateAgentMessage(message)
                              ? null
                              : (msg) => setState(
                                    () => notifier
                                        .setQuote(msg as PrivateMessageInfo?),
                                  ),
                          onRevoke: isPrivateAgentMessage(message)
                              ? (msg) => ref
                                  .read(
                                    privateChatAgentProvider(widget.friendId)
                                        .notifier,
                                  )
                                  .removeLocalDraft(
                                    (msg as PrivateMessageInfo).id,
                                  )
                              : (msg) => notifier.revokeMessage(
                                  (msg as PrivateMessageInfo).id),
                          onPromoteSelfVisibleDraft:
                              isPrivateAgentMessage(message)
                                  ? (msg) => _promoteAgentDraftToComposer(
                                        msg as PrivateMessageInfo,
                                      )
                                  : null,
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
                DS.spacing16,
                DS.spacing8,
                DS.spacing16,
                0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      FilterChip(
                        selected: _agentMode,
                        label: Text(_agentMode
                            ? context.l10n.chatPrivateAiAssistantOn
                            : context.l10n.chatPrivateAiAssistant),
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
                          context.l10n.chatPrivateThinking,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            color: DS.brandPrimary70,
                          ),
                        ),
                    ],
                  ),
                  if (_agentMode)
                    Padding(
                      padding: const EdgeInsets.only(top: DS.spacing8),
                      child: Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing4,
                        children: [
                          _PrivateAgentQuickChip(
                            label: context.l10n.chatPrivatePolishReply,
                            onTap: () => _runAssistantPreset(
                              preset: 'polish_reply',
                              sendStyle:
                                  _PrivateAssistantSendStyle.replaceInput,
                            ),
                          ),
                          _PrivateAgentQuickChip(
                            label: context.l10n.chatPrivateGentleReminder,
                            onTap: () => _runAssistantPreset(
                              preset: 'gentle_reminder',
                              sendStyle:
                                  _PrivateAssistantSendStyle.replaceInput,
                            ),
                          ),
                          _PrivateAgentQuickChip(
                            label: context.l10n.chatPrivateScheduleTime,
                            onTap: () => _runAssistantPreset(
                              preset: 'schedule_sync',
                              sendStyle:
                                  _PrivateAssistantSendStyle.replaceInput,
                              reasoningMode: 'balanced',
                            ),
                          ),
                          _PrivateAgentQuickChip(
                            label: context.l10n.chatPrivateQuickSummary,
                            onTap: () => _runAssistantPreset(
                              preset: 'summary',
                              sendStyle:
                                  _PrivateAssistantSendStyle.visibilityChoice,
                            ),
                          ),
                          _PrivateAgentQuickChip(
                            label: context.l10n.chatPrivateExtractNextSteps,
                            onTap: () => _runAssistantPreset(
                              preset: 'next_step',
                              sendStyle:
                                  _PrivateAssistantSendStyle.visibilityChoice,
                            ),
                          ),
                        ],
                      ),
                    ),
                  if (_assistantOriginalDraft != null)
                    Padding(
                      padding: const EdgeInsets.only(top: DS.spacing8),
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing12,
                          vertical: DS.spacing10,
                        ),
                        decoration: BoxDecoration(
                          color: DS.brandPrimary.withValues(alpha: 0.08),
                          borderRadius: DS.borderRadius12,
                          border: Border.all(
                            color: DS.brandPrimary.withValues(alpha: 0.18),
                          ),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: Text(
                                context.l10n.chatPrivateDraftInComposer,
                                style: TextStyle(
                                  fontSize: DS.fontSizeSm,
                                  color: DS.neutral700,
                                ),
                              ),
                            ),
                            TextButton(
                              onPressed: _restoreOriginalDraft,
                              child:
                                  Text(context.l10n.chatPrivateRestoreOriginal),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
            CommunityChatInput(
              controller: _composerController,
              focusNode: _composerFocusNode,
              quotedMessage: notifier.quotedMessage,
              onCancelQuote: () => setState(() => notifier.setQuote(null)),
              onSend: (text, {replyToId}) {
                setState(() => _assistantOriginalDraft = null);
                unawaited(
                  notifier.sendMessage(content: text, replyToId: replyToId),
                );
              },
              onQuickShare: _isSharing ? null : _handleQuickShare,
              enabled: !_isSharing && !agentState.isSending,
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
    if (agentState.streamingContent.trim().isNotEmpty) {
      merged.add(
        _buildStreamingAgentMessage(
          agentState.streamingContent,
          currentUser,
        ),
      );
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
    final now = DateTime.now();
    return PrivateMessageInfo(
      id: 'private_agent_streaming_${now.microsecondsSinceEpoch}',
      sender: buildCommunityAgentUser(
        localizedName: context.l10n.communityAgentName,
      ),
      receiver: UserBrief(
        id: widget.friendId,
        username: _displayName ?? 'friend',
        nickname: _displayName,
      ),
      content: content,
      messageType: MessageType.text,
      isRead: true,
      createdAt: now,
      updatedAt: now,
      contentData: {
        kAgentMetadataKey: true,
        'agent_streaming': true,
        if (currentUser != null) kAgentVisibleToKey: [currentUser.id],
      },
    );
  }

  Future<void> _runAssistantPreset({
    required String preset,
    required _PrivateAssistantSendStyle sendStyle,
    String reasoningMode = 'fast',
  }) async {
    final agentState = ref.read(privateChatAgentProvider(widget.friendId));
    if (agentState.isSending) return;

    final composerText = _composerController.text.trim();
    if ((preset == 'polish_reply' ||
            preset == 'gentle_reminder' ||
            preset == 'schedule_sync') &&
        composerText.isEmpty) {
      AppFeedback.info(context, context.l10n.chatPrivateWriteFirst);
      _composerFocusNode.requestFocus();
      return;
    }

    final prompt = _buildPresetPrompt(
      preset,
      composerText: composerText,
    );
    final notifier =
        ref.read(privateChatAgentProvider(widget.friendId).notifier);
    final draft = await notifier.composeDraft(
      prompt: prompt,
      friendName: _displayName ?? widget.friendName,
      recentMessages:
          ref.read(privateChatProvider(widget.friendId)).valueOrNull ?? [],
      preset: preset,
      reasoningMode: reasoningMode,
      chatMode: preset == 'schedule_sync' ? 'standard' : 'fast',
    );
    if (!mounted) return;
    if (draft == null || draft.trim().isEmpty) {
      final error = ref.read(privateChatAgentProvider(widget.friendId)).error;
      AppFeedback.error(
          context, error ?? context.l10n.chatPrivateGenerationFailed);
      return;
    }
    await _showDraftPreview(
      preset: preset,
      draft: draft,
      sendStyle: sendStyle,
      originalText: composerText,
    );
  }

  String _buildPresetPrompt(
    String preset, {
    required String composerText,
  }) {
    final friendName = _displayName ?? widget.friendName;
    final base = buildPrivateAssistantPresetPrompt(
      preset,
      friendName: friendName,
    );
    if (composerText.isEmpty) {
      return base;
    }
    return switch (preset) {
      'polish_reply' =>
        context.l10n.chatPrivatePolishPrompt(base, composerText),
      'gentle_reminder' =>
        context.l10n.chatPrivateGentlePrompt(base, composerText),
      'schedule_sync' =>
        context.l10n.chatPrivateSchedulePrompt(base, composerText),
      _ => base,
    };
  }

  Future<void> _showDraftPreview({
    required String preset,
    required String draft,
    required _PrivateAssistantSendStyle sendStyle,
    required String originalText,
  }) async {
    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfaceSecondary,
      builder: (sheetContext) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            DS.spacing16,
            DS.spacing16,
            DS.spacing24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _previewTitleForPreset(preset),
                style: const TextStyle(
                  fontSize: DS.fontSizeLg,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
              const SizedBox(height: DS.spacing12),
              Container(
                width: double.infinity,
                constraints: const BoxConstraints(maxHeight: 260),
                padding: const EdgeInsets.all(DS.spacing16),
                decoration: BoxDecoration(
                  color: DS.surfacePrimary,
                  borderRadius: DS.borderRadius16,
                  border: Border.all(
                    color: DS.neutral200,
                  ),
                ),
                child: SingleChildScrollView(
                  child: SparkleMarkdown(
                    content: draft,
                    textColor: DS.textPrimary,
                    codeBackgroundColor: DS.surfaceSecondary,
                    linkColor: DS.brandPrimary,
                    contentRole: SparkleMarkdownRole.chatBubble,
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing16),
              if (sendStyle == _PrivateAssistantSendStyle.visibilityChoice)
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    _PreviewActionButton(
                      label: context.l10n.chatPrivateOnlyVisibleToMe,
                      onTap: () async {
                        Navigator.of(sheetContext).pop();
                        await ref
                            .read(privateChatAgentProvider(widget.friendId)
                                .notifier)
                            .saveSelfVisibleDraft(content: draft);
                        if (!mounted) return;
                        AppFeedback.success(
                            context, context.l10n.chatPrivateSavedOnlyToMe);
                      },
                    ),
                    _PreviewActionButton(
                      label: context.l10n.chatPrivateVisibleToBoth,
                      primary: true,
                      onTap: () {
                        Navigator.of(sheetContext).pop();
                        _applyDraftToComposer(
                          draft,
                          originalText: originalText,
                        );
                      },
                    ),
                    _PreviewActionButton(
                      label: I18nService.instance.isChinese ? '取消' : 'Cancel',
                      onTap: () => Navigator.of(sheetContext).pop(),
                    ),
                  ],
                )
              else
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    _PreviewActionButton(
                      label: I18nService.instance.isChinese ? '取消' : 'Cancel',
                      onTap: () => Navigator.of(sheetContext).pop(),
                    ),
                    _PreviewActionButton(
                      label: context.l10n.chatPrivatePutInComposer,
                      primary: true,
                      onTap: () {
                        Navigator.of(sheetContext).pop();
                        _applyDraftToComposer(
                          draft,
                          originalText: originalText,
                        );
                      },
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }

  String _previewTitleForPreset(String preset) => switch (preset) {
        'polish_reply' => context.l10n.chatPrivatePolishedReply,
        'gentle_reminder' => context.l10n.chatPrivateGentleReminderDraft,
        'schedule_sync' => context.l10n.chatPrivateScheduleDraft,
        'summary' => context.l10n.chatPrivateQuickSummary,
        'next_step' => context.l10n.chatPrivateExtractedNextSteps,
        _ => context.l10n.chatPrivateAiGeneratedResult,
      };

  void _applyDraftToComposer(
    String draft, {
    required String originalText,
  }) {
    setState(() {
      _assistantOriginalDraft = originalText;
      _composerController.text = draft;
      _composerController.selection = TextSelection.collapsed(
        offset: _composerController.text.length,
      );
    });
    _composerFocusNode.requestFocus();
    AppFeedback.success(context, context.l10n.chatPrivatePutInComposerConfirm);
  }

  void _restoreOriginalDraft() {
    final originalText = _assistantOriginalDraft;
    if (originalText == null) return;
    setState(() {
      _composerController.text = originalText;
      _composerController.selection = TextSelection.collapsed(
        offset: _composerController.text.length,
      );
      _assistantOriginalDraft = null;
    });
    _composerFocusNode.requestFocus();
    AppFeedback.info(context, context.l10n.chatPrivateOriginalRestored);
  }

  void _promoteAgentDraftToComposer(PrivateMessageInfo message) {
    final draft = (message.content ?? '').trim();
    if (draft.isEmpty) {
      return;
    }
    ref
        .read(privateChatAgentProvider(widget.friendId).notifier)
        .removeLocalDraft(message.id);
    _applyDraftToComposer(
      draft,
      originalText: _composerController.text.trim(),
    );
    AppFeedback.info(context, context.l10n.chatPrivateSwitchedBothVisible);
  }

  Future<void> _handleQuickShare(UniversalSharePayload payload) async {
    if (_isSharing) return;

    setState(() => _isSharing = true);
    try {
      if (payload.contentType == ShareableContentType.achievement) {
        await ref.read(communityRepositoryProvider).sendPrivateMessage(
              PrivateMessageSend(
                targetUserId: widget.friendId,
                messageType: MessageType.achievement,
                content: payload.shareMessage,
                contentData: {
                  'achievement_id': payload.resourceId,
                  'name': payload.title,
                  'description': payload.subtitle,
                  ...?payload.metadata,
                },
              ),
            );
      } else {
        await ref.read(communityShareRepositoryProvider).shareResource(
              resourceType: payload.contentType.stringValue,
              resourceId: payload.resourceId,
              targetUserId: widget.friendId, // 私聊分享给好友
              comment: payload.shareMessage,
            );
      }
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

enum _PrivateAssistantSendStyle {
  replaceInput,
  visibilityChoice,
}

class _PrivateAgentQuickChip extends StatelessWidget {
  const _PrivateAgentQuickChip({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
        label: Text(
          label,
          style: TextStyle(
            fontSize: DS.fontSizeSm,
            color: DS.brandPrimary,
          ),
        ),
        backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
        onPressed: onTap,
      );
}

class _PreviewActionButton extends StatelessWidget {
  const _PreviewActionButton({
    required this.label,
    required this.onTap,
    this.primary = false,
  });

  final String label;
  final VoidCallback onTap;
  final bool primary;

  @override
  Widget build(BuildContext context) => FilledButton.tonal(
        style: FilledButton.styleFrom(
          backgroundColor: primary
              ? DS.brandPrimary
              : DS.surfaceSecondary.withValues(alpha: 0.9),
          foregroundColor: primary ? DS.textOnPrimary : DS.neutral800,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing10,
          ),
        ),
        onPressed: onTap,
        child: Text(label),
      );
}
