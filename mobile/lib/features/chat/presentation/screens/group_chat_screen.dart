import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/ai_status_indicator.dart';
import 'package:sparkle/features/chat/presentation/widgets/community_chat_input.dart';
import 'package:sparkle/features/community/community_routes.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/features/community/presentation/providers/community_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/group_chat_bubble.dart';
import 'package:sparkle/features/community/presentation/widgets/thread_sheet.dart';
import 'package:sparkle/features/file/file.dart';

class GroupChatScreen extends ConsumerStatefulWidget {
  const GroupChatScreen({required this.groupId, super.key});
  final String groupId;

  @override
  ConsumerState<GroupChatScreen> createState() => _GroupChatScreenState();
}

class _GroupChatScreenState extends ConsumerState<GroupChatScreen> {
  MessageInfo? _quotedMessage;
  bool _agentMode = false;
  late final ScrollController _scrollController;
  String? _lastNewestMessageId;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController()..addListener(_handleScroll);
  }

  @override
  void dispose() {
    _scrollController
      ..removeListener(_handleScroll)
      ..dispose();
    super.dispose();
  }

  void _handleScroll() {
    if (!_scrollController.hasClients) {
      return;
    }
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - 240) {
      unawaited(
        ref.read(groupChatProvider(widget.groupId).notifier).loadOlderMessages(),
      );
    }
  }

  void _scheduleScrollToLatest() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) {
        return;
      }
      const target = 0.0;
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

  void _handleFavorite(MessageInfo msg) {
    unawaited(
      ref.read(communityRepositoryProvider).addFavorite(msg.id, null).then((_) {
        if (!mounted) return;
        AppFeedback.success(context, context.l10n.chatGroupFavorited);
      }).catchError((Object e) {
        if (!mounted) return;
        AppFeedback.error(context, context.l10n.chatGroupFavoriteFailed(error: e.toString()));
      }),
    );
  }

  void _handleForward(MessageInfo msg) {
    unawaited(_showForwardDialog(msg));
  }

  Future<void> _showForwardDialog(MessageInfo msg) async {
    final groups = await ref.read(communityRepositoryProvider).getMyGroups();
    if (!mounted) return;

    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (ctx) => DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(ctx).scaffoldBackgroundColor,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(DS.spacing16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  context.l10n.chatGroupForwardToGroup,
                  style: TextStyle(
                      fontWeight: FontWeight.bold, fontSize: DS.fontSizeLg,),
                ),
                const SizedBox(height: DS.spacing16),
                SizedBox(
                  height: 300,
                  child: ListView.builder(
                    itemCount: groups.length,
                    itemBuilder: (ctx, i) {
                      final g = groups[i];
                      return ListTile(
                        title: Text(g.name),
                        subtitle: Text(context.l10n.chatGroupMemberCount(count: g.memberCount)),
                        onTap: () async {
                          Navigator.pop(ctx);
                          try {
                            await ref
                                .read(communityRepositoryProvider)
                                .forwardMessage(
                                  msg.id,
                                  'group',
                                  targetGroupId: g.id,
                                );
                            if (!mounted) return;
                            AppFeedback.success(context, context.l10n.chatGroupForwardedTo(name: g.name));
                          } catch (e) {
                            if (!mounted) return;
                            AppFeedback.error(context, context.l10n.chatGroupForwardFailed(error: e.toString()));
                          }
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _handleReport(MessageInfo msg) {
    unawaited(_showReportSheet(msg));
  }

  Future<void> _showReportSheet(MessageInfo msg) async {
    var selectedReason = ReportReason.spam;
    final descController = TextEditingController();

    await showSensoryModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(ctx).scaffoldBackgroundColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: SafeArea(
            top: false,
            child: Padding(
              padding: EdgeInsets.only(
                left: DS.spacing16,
                right: DS.spacing16,
                top: DS.spacing16,
                bottom: MediaQuery.of(ctx).viewInsets.bottom + DS.spacing16,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    context.l10n.chatGroupReportMessage,
                    style: TextStyle(
                        fontWeight: FontWeight.bold, fontSize: DS.fontSizeLg,),
                  ),
                  const SizedBox(height: DS.spacing8),
                  RadioGroup<ReportReason>(
                    groupValue: selectedReason,
                    onChanged: (value) => setState(
                      () => selectedReason = value ?? ReportReason.spam,
                    ),
                    child: Column(
                      children: [
                        ...[
                          (ReportReason.spam, context.l10n.chatGroupReportSpam),
                          (ReportReason.harassment, '骚扰'),
                          (ReportReason.violence, '暴力'),
                          (ReportReason.hateSpeech, context.l10n.chatGroupReportHate),
                          (ReportReason.misinformation, context.l10n.chatGroupReportMisinfo),
                          (ReportReason.other, '其他'),
                        ].map(
                          (entry) => RadioListTile<ReportReason>(
                            title: Text(entry.$2),
                            value: entry.$1,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  TextField(
                    controller: descController,
                    decoration: const InputDecoration(
                      hintText: context.l10n.chatGroupReportAdditionalNote,
                      border: OutlineInputBorder(),
                    ),
                    maxLines: 2,
                  ),
                  const SizedBox(height: DS.spacing16),
                  SizedBox(
                    width: double.infinity,
                    child: SparkleButton.primary(
                      label: context.l10n.chatGroupReportSubmit,
                      onPressed: () async {
                        Navigator.pop(ctx);
                        try {
                          await ref
                              .read(communityRepositoryProvider)
                              .reportMessage(
                                msg.id,
                                selectedReason,
                                description: descController.text.trim().isEmpty
                                    ? null
                                    : descController.text.trim(),
                              );
                          if (!mounted) return;
                          AppFeedback.success(context, context.l10n.chatGroupReportSubmitted);
                        } catch (e) {
                          if (!mounted) return;
                          AppFeedback.error(context, context.l10n.chatGroupReportFailed(error: e.toString()));
                        }
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
    descController.dispose();
  }

  void _showCheckinDialog() {
    final durationController = TextEditingController(text: '60');
    final messageController = TextEditingController();

    unawaited(
      showSensoryDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(context.l10n.communityCheckInTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: durationController,
                decoration: InputDecoration(
                  labelText: context.l10n.communityCheckInDurationLabel,
                  suffixText: context.l10n.commonMinutesShort,
                ),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: DS.lg),
              TextField(
                controller: messageController,
                decoration: InputDecoration(
                  labelText: context.l10n.communityCheckInMessageLabel,
                  hintText: context.l10n.communityCheckInMessageHint,
                ),
              ),
            ],
          ),
          actions: [
            SparkleButton.ghost(
              label: context.l10n.cancel,
              onPressed: () => Navigator.pop(context),
            ),
            SparkleButton.primary(
              label: context.l10n.communityCheckInAction,
              onPressed: () async {
                final duration = int.tryParse(durationController.text) ?? 0;
                final message = messageController.text;
                Navigator.pop(context);

                try {
                  await ref
                      .read(groupDetailProvider(widget.groupId).notifier)
                      .checkin(duration, message);
                  if (!context.mounted) return;
                  // Refresh chat to see the checkin message
                  ref.invalidate(groupChatProvider(widget.groupId));

                  AppFeedback.success(
                    context,
                    context.l10n.communityCheckInSuccess,
                  );
                } catch (e) {
                  if (!context.mounted) return;
                  AppFeedback.error(
                    context,
                    context.l10n.communityCheckInFailed(e.toString()),
                  );
                }
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(groupChatProvider(widget.groupId));
    final groupInfoState = ref.watch(groupDetailProvider(widget.groupId));
    final agentState = ref.watch(groupChatAgentProvider(widget.groupId));

    return GraphiteScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: groupInfoState.when(
          data: (group) => InkWell(
            onTap: () {
              // Go to details? No, we are linked from details.
            },
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  group.name,
                  style: const TextStyle(fontSize: DS.fontSizeBase),
                ),
                Text(
                  context.l10n.communityGroupMembersCount(group.memberCount),
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: DS.brandPrimary54,
                  ),
                ),
              ],
            ),
          ),
          loading: () => Text(context.l10n.communityChatTitle),
          error: (_, __) => Text(context.l10n.communityChatTitle),
        ),
        actions: [
          SparkleIconButton(
            icon: const Icon(Icons.folder_open_rounded),
            onPressed: () {
              unawaited(
                context.push(
                  CommunityRoutes.groupFiles
                      .replaceFirst(':id', widget.groupId),
                ),
              );
            },
            semanticLabel: context.l10n.communityGroupFiles,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: const Icon(Icons.assignment_outlined),
            onPressed: () => unawaited(
              context.push(
                CommunityRoutes.groupTasks.replaceFirst(':id', widget.groupId),
              ),
            ),
            semanticLabel: context.l10n.chatGroupTasks,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: Icon(Icons.local_fire_department, color: DS.brandPrimary),
            onPressed: _showCheckinDialog,
            semanticLabel: context.l10n.communityCheckInAction,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: const Icon(Icons.search),
            onPressed: _showSearchSheet,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () {
              unawaited(
                context.push(
                  CommunityRoutes.groupDetail
                      .replaceFirst(':id', widget.groupId),
                ),
              );
            },
            variant: ButtonVariant.ghost,
          ),
        ],
      ),
      child: ContentConstraint(
        child: Column(
          children: [
            Expanded(
              child: chatState.when(
                data: (messages) {
                  final mergedMessages = _mergeMessages(messages, agentState);
                  final newestMessageId =
                      mergedMessages.isEmpty ? null : mergedMessages.first.id;
                  if (newestMessageId != null &&
                      newestMessageId != _lastNewestMessageId) {
                    _lastNewestMessageId = newestMessageId;
                    _scheduleScrollToLatest();
                  }
                  final showAgentStatus = agentState.isSending &&
                      agentState.streamingContent.isEmpty;

                  if (mergedMessages.isEmpty) {
                    return Center(
                      child: Text(context.l10n.communityChatEmpty),
                    );
                  }
                  return Align(
                    alignment: Alignment.topCenter,
                    child: ListView.builder(
                      controller: _scrollController,
                      reverse: true,
                      shrinkWrap: true,
                      padding: const EdgeInsets.all(DS.spacing16),
                      itemCount:
                          mergedMessages.length + (showAgentStatus ? 1 : 0),
                      itemBuilder: (context, index) {
                        if (showAgentStatus && index == 0) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: DS.spacing16),
                            child: AiStatusIndicator(
                              status: 'THINKING',
                              details: context.l10n.communityAgentThinking,
                              enableStatusTrack: false,
                            ),
                          );
                        }

                        final messageIndex =
                            showAgentStatus ? index - 1 : index;
                        final message = mergedMessages[messageIndex];
                        return GroupChatBubble(
                          message: message,
                          groupId: widget.groupId,
                          onQuote: isCommunityAgentMessage(message)
                              ? null
                              : (msg) => setState(() {
                                    _quotedMessage = msg;
                                    ref
                                        .read(
                                          groupChatProvider(widget.groupId)
                                              .notifier,
                                        )
                                        .setQuote(msg);
                                  }),
                          onRevoke: isCommunityAgentMessage(message)
                              ? null
                              : (msg) => ref
                                  .read(
                                    groupChatProvider(widget.groupId).notifier,
                                  )
                                  .revokeMessage(msg.id),
                          onEdit: isCommunityAgentMessage(message)
                              ? null
                              : (msg, content) => ref
                                  .read(
                                    groupChatProvider(widget.groupId).notifier,
                                  )
                                  .editMessage(msg.id, content),
                          onReaction: isCommunityAgentMessage(message)
                              ? null
                              : (msg, emoji) => ref
                                  .read(
                                    groupChatProvider(widget.groupId).notifier,
                                  )
                                  .toggleReaction(msg.id, emoji),
                          onThread: _openThread,
                          onFavorite: isCommunityAgentMessage(message)
                              ? null
                              : _handleFavorite,
                          onForward: isCommunityAgentMessage(message)
                              ? null
                              : _handleForward,
                          onReport: isCommunityAgentMessage(message)
                              ? null
                              : _handleReport,
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
                        .read(groupChatProvider(widget.groupId).notifier)
                        .refresh(),
                  ),
                ),
              ),
            ),
            if (agentState.error != null)
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                  vertical: DS.spacing8,
                ),
                child: Text(
                  agentState.error!,
                  style: TextStyle(color: DS.error, fontSize: DS.fontSizeSm),
                ),
              ),
            _buildAgentToolbar(
              context,
              agentState: agentState,
              groupInfo: groupInfoState.valueOrNull,
              messages: chatState.valueOrNull ?? [],
            ),
            CommunityChatInput(
              enabled: !_agentMode || !agentState.isSending,
              hintText: _agentMode
                  ? context.l10n.communityAgentPromptHint
                  : context.l10n.communityMessageInputHint,
              fileUploadGroupId: widget.groupId,
              onFileUploaded: (file) async {
                try {
                  final repo = ref.read(fileRepositoryProvider);
                  await repo.shareToGroup(
                    widget.groupId,
                    file.id,
                  );
                  ref.invalidate(groupChatProvider(widget.groupId));
                  if (!context.mounted) return;
                  AppFeedback.success(
                    context,
                    context.l10n.communityFileSharedSuccess,
                  );
                } catch (e) {
                  if (!context.mounted) return;
                  AppFeedback.error(
                    context,
                    context.l10n.communityFileSharedFailed(e.toString()),
                  );
                }
              },
              quotedMessage: !_agentMode && _quotedMessage != null
                  ? PrivateMessageInfo(
                      id: _quotedMessage!.id,
                      sender: _quotedMessage!.sender ??
                          UserBrief(
                            id: '',
                            username: context.l10n.commonUnknown,
                          ),
                      receiver: UserBrief(id: '', username: ''),
                      messageType: _quotedMessage!.messageType,
                      content: _quotedMessage!.content,
                      createdAt: _quotedMessage!.createdAt,
                      updatedAt: _quotedMessage!.updatedAt,
                      isRevoked: _quotedMessage!.isRevoked,
                      isRead: false,
                    )
                  : null,
              onCancelQuote: () => setState(() {
                _quotedMessage = null;
                ref
                    .read(groupChatProvider(widget.groupId).notifier)
                    .setQuote(null);
              }),
              onSend: (text, {replyToId}) {
                if (_agentMode) {
                  _sendAgentPrompt(
                    prompt: text,
                    agentState: agentState,
                    groupInfo: groupInfoState.valueOrNull,
                    messages: chatState.valueOrNull ?? const [],
                  );
                  return;
                }

                final actualReplyId = _quotedMessage?.id ?? replyToId;
                setState(() => _quotedMessage = null);
                unawaited(
                  ref
                      .read(groupChatProvider(widget.groupId).notifier)
                      .sendMessage(
                        content: text,
                        replyToId: actualReplyId,
                      ),
                );
              },
              onQuickShare: _handleQuickShare,
            ),
          ],
        ),
      ),
    );
  }

  List<MessageInfo> _mergeMessages(
    List<MessageInfo> messages,
    AgentChatState<MessageInfo> agentState,
  ) {
    final merged = [...messages, ...agentState.messages];
    if (agentState.streamingContent.isNotEmpty) {
      merged.add(_buildStreamingAgentMessage(agentState.streamingContent));
    }
    final byId = <String, MessageInfo>{};
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

  MessageInfo _buildStreamingAgentMessage(String content) => MessageInfo(
        id: 'agent_streaming_${DateTime.now().millisecondsSinceEpoch}',
        messageType: MessageType.text,
        sender: buildCommunityAgentUser(
            localizedName: context.l10n.communityAgentName,),
        content: content,
        contentData: {kAgentMetadataKey: true, 'agent_streaming': true},
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

  void _sendAgentPrompt({
    required String prompt,
    required AgentChatState<MessageInfo> agentState,
    required List<MessageInfo> messages,
    GroupInfo? groupInfo,
    String preset = 'custom',
    String reasoningMode = 'fast',
  }) {
    if (agentState.isSending) return;
    unawaited(
      ref
          .read(groupChatAgentProvider(widget.groupId).notifier)
          .sendAgentMessage(
            prompt: prompt,
            groupName: groupInfo?.name,
            recentMessages: messages,
            preset: preset,
            reasoningMode: reasoningMode,
          ),
    );
  }

  Future<void> _handleQuickShare(UniversalSharePayload payload) async {
    try {
      if (payload.contentType == ShareableContentType.achievement) {
        await ref.read(communityRepositoryProvider).sendMessage(
              widget.groupId,
              type: MessageType.achievement,
              content: payload.shareMessage,
              contentData: {
                'achievement_id': payload.resourceId,
                'name': payload.title,
                'description': payload.subtitle,
                ...?payload.metadata,
              },
            );
      } else {
        await ref.read(communityShareRepositoryProvider).shareResource(
              resourceType: payload.contentType.stringValue,
              resourceId: payload.resourceId,
              targetGroupId: widget.groupId,
              comment: payload.shareMessage,
            );
      }
      if (!mounted) return;
      ref.invalidate(groupChatProvider(widget.groupId));
      AppFeedback.success(context, context.l10n.shareResourceSuccess);
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, context.l10n.shareResourceFailed(e));
    }
  }

  Widget _buildAgentToolbar(
    BuildContext context, {
    required AgentChatState<MessageInfo> agentState,
    required GroupInfo? groupInfo,
    required List<MessageInfo> messages,
  }) =>
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
                  label: Text(
                    _agentMode
                        ? context.l10n.communityAgentCollabOn
                        : context.l10n.communityAgentCollabOff,
                  ),
                  avatar: Icon(
                    Icons.auto_awesome,
                    size: DS.iconSizeXs,
                    color: _agentMode ? DS.brandPrimary : DS.neutral500,
                  ),
                  onSelected: (value) {
                    setState(() {
                      _agentMode = value;
                      if (_agentMode) {
                        _quotedMessage = null;
                        ref
                            .read(groupChatProvider(widget.groupId).notifier)
                            .setQuote(null);
                      }
                    });
                  },
                ),
                const SizedBox(width: DS.spacing8),
                if (_agentMode)
                  Text(
                    context.l10n.communityAgentOnlyYou,
                    style: TextStyle(
                      fontSize: DS.fontSizeSm,
                      color: DS.neutral500,
                    ),
                  ),
                const Spacer(),
                if (agentState.isSending)
                  Text(
                    context.l10n.communityAgentProcessing,
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
                    _AgentQuickChip(
                      label: context.l10n.communityAgentQuickSummary,
                      onTap: () => _sendAgentPrompt(
                        prompt: buildGroupAssistantPresetPrompt(
                          'summary',
                          groupName: groupInfo?.name,
                        ),
                        agentState: agentState,
                        groupInfo: groupInfo,
                        messages: messages,
                        preset: 'summary',
                      ),
                    ),
                    _AgentQuickChip(
                      label: context.l10n.communityAgentQuickReminder,
                      onTap: () => _sendAgentPrompt(
                        prompt: buildGroupAssistantPresetPrompt(
                          'reminder',
                          groupName: groupInfo?.name,
                        ),
                        agentState: agentState,
                        groupInfo: groupInfo,
                        messages: messages,
                        preset: 'reminder',
                      ),
                    ),
                    _AgentQuickChip(
                      label: context.l10n.communityAgentQuickConsensus,
                      onTap: () => _sendAgentPrompt(
                        prompt: buildGroupAssistantPresetPrompt(
                          'consensus',
                          groupName: groupInfo?.name,
                        ),
                        agentState: agentState,
                        groupInfo: groupInfo,
                        messages: messages,
                        preset: 'consensus',
                        reasoningMode: 'balanced',
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      );

  void _openThread(MessageInfo message) {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (context) =>
            ThreadSheet(groupId: widget.groupId, rootMessage: message),
      ),
    );
  }

  Future<void> _showSearchSheet() async {
    final notifier = ref.read(groupChatProvider(widget.groupId).notifier);
    final controller = TextEditingController();
    var results = <MessageInfo>[];
    var isLoading = false;

    try {
      await showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (context) => StatefulBuilder(
          builder: (context, setState) => DecoratedBox(
            decoration: BoxDecoration(
              color: Theme.of(context).scaffoldBackgroundColor,
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: EdgeInsets.only(
                  left: DS.spacing16,
                  right: DS.spacing16,
                  top: DS.spacing16,
                  bottom:
                      MediaQuery.of(context).viewInsets.bottom + DS.spacing16,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: DS.spacing40,
                      height: DS.spacing4,
                      decoration: BoxDecoration(
                        color: DS.neutral300,
                        borderRadius: BorderRadius.circular(DS.spacing4),
                      ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    TextField(
                      controller: controller,
                      decoration: InputDecoration(
                        hintText: context.l10n.communitySearchGroupMessages,
                        prefixIcon: const Icon(Icons.search),
                      ),
                      onSubmitted: (value) async {
                        if (value.trim().isEmpty) return;
                        setState(() => isLoading = true);
                        try {
                          results = await notifier.searchMessages(value.trim());
                        } catch (_) {
                          results = [];
                        } finally {
                          setState(() => isLoading = false);
                        }
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    if (isLoading) const LoadingIndicator(),
                    if (!isLoading)
                      SizedBox(
                        height: 280,
                        child: ListView.builder(
                          itemCount: results.length,
                          itemBuilder: (context, index) {
                            final msg = results[index];
                            return ListTile(
                              title: Text(
                                msg.content ??
                                    context.l10n.communityMessageFallback,
                              ),
                              subtitle: Text(
                                '${msg.sender?.displayName ?? context.l10n.communityMemberFallback} • ${msg.createdAt}',
                              ),
                              onTap: () => Navigator.pop(context),
                            );
                          },
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    } finally {
      controller.dispose();
    }
  }
}

class _AgentQuickChip extends StatelessWidget {
  const _AgentQuickChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
        label: Text(
          label,
          style: TextStyle(fontSize: DS.fontSizeSm, color: DS.brandPrimary),
        ),
        backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
        onPressed: onTap,
      );
}
