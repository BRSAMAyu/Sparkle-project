import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/empty_state.dart';
import 'package:sparkle/core/design/widgets/error_widget.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/errors/user_facing_error.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/utils/input_formatters.dart';
import 'package:sparkle/features/chat/data/services/chat_draft_store.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_draft_store_provider.dart';
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

  // N46 单机草稿（A-SPEC8A 会话连续性改造 #1）：群聊 composer 文本按
  // userId+groupId 持久化，切页/杀进程可恢复；发送成功即删草稿。
  // 输入框控制器由此屏持有并下传 CommunityChatInput（原为组件内态）。
  final TextEditingController _composerController = TextEditingController();
  late final ChatDraftStore _draftStore;
  String _draftUserId = 'anon';
  bool _draftUserResolved = false;
  bool _applyingStoredDraft = false;

  // SEARCH-EMPTY：命中定位基建——照 chat_screen 的「GlobalKey 表 +
  // Scrollable.ensureVisible」同款形制；短高亮由屏侧 Timer 收敛。
  final Map<String, GlobalKey> _messageKeys = <String, GlobalKey>{};
  String? _highlightedMessageId;
  Timer? _highlightTimer;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController()..addListener(_handleScroll);
    _draftStore = ref.read(chatDraftStoreProvider);
    _composerController.addListener(_handleComposerTextChanged);
    unawaited(_restoreComposerDraft());
  }

  @override
  void dispose() {
    // N46：离开页面即落盘草稿（覆盖防抖窗口内尚未写入的尾部输入）。
    if (_draftUserResolved) {
      unawaited(
        _draftStore.flush(
          scope: ChatDraftScope.groupChat,
          conversationId: widget.groupId,
          userId: _draftUserId,
          text: _composerController.text,
        ),
      );
    }
    _highlightTimer?.cancel();
    _scrollController
      ..removeListener(_handleScroll)
      ..dispose();
    _composerController
      ..removeListener(_handleComposerTextChanged)
      ..dispose();
    super.dispose();
  }

  /// N46：进入会话恢复草稿（composer 为空时才回填，不覆盖先于恢复的输入）。
  Future<void> _restoreComposerDraft() async {
    _draftUserId = await resolveChatDraftUserId(ref);
    if (!mounted) {
      return;
    }
    _draftUserResolved = true;
    final draft = await _draftStore.load(
      scope: ChatDraftScope.groupChat,
      conversationId: widget.groupId,
      userId: _draftUserId,
    );
    if (!mounted) {
      return;
    }
    final restored = draft ?? '';
    if (restored.isEmpty || _composerController.text.isNotEmpty) {
      return;
    }
    _applyingStoredDraft = true;
    try {
      _composerController.text = restored;
      _composerController.selection =
          TextSelection.collapsed(offset: restored.length);
    } finally {
      _applyingStoredDraft = false;
    }
  }

  /// N46：输入变化 → 防抖落盘；输入被清空（发送成功/用户删空）→ 删草稿。
  void _handleComposerTextChanged() {
    if (_applyingStoredDraft || !_draftUserResolved) {
      return;
    }
    _draftStore.scheduleSave(
      scope: ChatDraftScope.groupChat,
      conversationId: widget.groupId,
      userId: _draftUserId,
      text: _composerController.text,
    );
  }

  void _pruneMessageKeys(List<MessageInfo> messages) {
    final ids = messages.map((message) => message.id).toSet();
    _messageKeys.removeWhere((id, _) => !ids.contains(id));
  }

  GlobalKey _messageKeyFor(String id) =>
      _messageKeys.putIfAbsent(id, GlobalKey.new);

  void _handleScroll() {
    if (!_scrollController.hasClients) {
      return;
    }
    final position = _scrollController.position;
    if (position.pixels >= position.maxScrollExtent - 240) {
      unawaited(
        ref
            .read(groupChatProvider(widget.groupId).notifier)
            .loadOlderMessages(),
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
        AppFeedback.error(
          context,
          context.l10n.chatGroupFavoriteFailed(UserFacingError.from(e)),
        );
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
                Text(
                  context.l10n.chatGroupForwardToGroup,
                  style: const TextStyle(
                    fontWeight: DS.fontWeightBold,
                    fontSize: DS.fontSizeLg,
                  ),
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
                        subtitle: Text(
                          context.l10n.chatGroupMemberCount(g.memberCount),
                        ),
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
                            AppFeedback.success(
                              context,
                              context.l10n.chatGroupForwardedTo(g.name),
                            );
                          } catch (e) {
                            if (!mounted) return;
                            AppFeedback.error(
                              context,
                              context.l10n.chatGroupForwardFailed(
                                UserFacingError.from(e),
                              ),
                            );
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
                  Text(
                    context.l10n.chatGroupReportMessage,
                    style: const TextStyle(
                      fontWeight: DS.fontWeightBold,
                      fontSize: DS.fontSizeLg,
                    ),
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
                          (
                            ReportReason.harassment,
                            context.l10n.chatGroupReportHarassment,
                          ),
                          (
                            ReportReason.violence,
                            context.l10n.chatGroupReportViolence,
                          ),
                          (
                            ReportReason.hateSpeech,
                            context.l10n.chatGroupReportHate,
                          ),
                          (
                            ReportReason.inappropriate,
                            context.l10n.chatGroupReportInappropriate,
                          ),
                          (
                            ReportReason.misinformation,
                            context.l10n.chatGroupReportMisinfo,
                          ),
                          (
                            ReportReason.other,
                            context.l10n.chatGroupReportOther,
                          ),
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
                    decoration: InputDecoration(
                      hintText: context.l10n.chatGroupReportAdditionalNote,
                      border: const OutlineInputBorder(),
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
                          AppFeedback.success(
                            context,
                            context.l10n.chatGroupReportSubmitted,
                          );
                        } catch (e) {
                          if (!mounted) return;
                          AppFeedback.error(
                            context,
                            context.l10n.chatGroupReportFailed(
                              UserFacingError.from(e),
                            ),
                          );
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
                inputFormatters: SparkleInputFormatters.digitsOnly,
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
                    context.l10n.communityCheckInFailed(
                      UserFacingError.from(e),
                    ),
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
          semanticLabel: context.l10n.back,
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
                  CommunityRoutes.groupFiles.replaceFirst(
                    ':id',
                    widget.groupId,
                  ),
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
            semanticLabel: context.l10n.commonSearch,
            variant: ButtonVariant.ghost,
          ),
          SparkleIconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () {
              unawaited(
                context.push(
                  CommunityRoutes.groupDetail.replaceFirst(
                    ':id',
                    widget.groupId,
                  ),
                ),
              );
            },
            semanticLabel: context.l10n.communityGroupDetails,
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
                    return Center(child: Text(context.l10n.communityChatEmpty));
                  }
                  _pruneMessageKeys(mergedMessages);
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
                            padding: const EdgeInsets.only(
                              bottom: DS.spacing16,
                            ),
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
                          key: _messageKeyFor(message.id),
                          message: message,
                          groupId: widget.groupId,
                          highlighted: message.id == _highlightedMessageId,
                          onQuote: isCommunityAgentMessage(message)
                              ? null
                              : (msg) => setState(() {
                                    _quotedMessage = msg;
                                    ref
                                        .read(
                                          groupChatProvider(
                                            widget.groupId,
                                          ).notifier,
                                        )
                                        .setQuote(msg);
                                  }),
                          onRevoke: isCommunityAgentMessage(message)
                              ? null
                              : (msg) => ref
                                  .read(
                                    groupChatProvider(
                                      widget.groupId,
                                    ).notifier,
                                  )
                                  .revokeMessage(msg.id),
                          onEdit: isCommunityAgentMessage(message)
                              ? null
                              : (msg, content) => ref
                                  .read(
                                    groupChatProvider(
                                      widget.groupId,
                                    ).notifier,
                                  )
                                  .editMessage(msg.id, content),
                          onReaction: isCommunityAgentMessage(message)
                              ? null
                              : (msg, emoji) => ref
                                  .read(
                                    groupChatProvider(
                                      widget.groupId,
                                    ).notifier,
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
            // M-3：终态连接失败（网关拒帧 retryable:false / 上游 403、404）
            // 时 surfaced 明确错误；自动重连已停，提供用户显式重连入口。
            if (ref
                    .read(groupChatProvider(widget.groupId).notifier)
                    .connectionFailureReason !=
                null) ...[
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                  vertical: DS.spacing8,
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.cloud_off_rounded,
                      size: DS.fontSizeMd,
                      color: DS.error,
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Text(
                        context.l10n.communityChatConnectionLost,
                        style: TextStyle(
                          color: DS.error,
                          fontSize: DS.fontSizeSm,
                        ),
                      ),
                    ),
                    SparkleButton(
                      label: context.l10n.communityChatReconnect,
                      variant: ButtonVariant.text,
                      size: ButtonSize.small,
                      minWidth: 64,
                      minHeight: 40,
                      onPressed: () => unawaited(
                        ref
                            .read(groupChatProvider(widget.groupId).notifier)
                            .manualReconnect(),
                      ),
                    ),
                  ],
                ),
              ),
            ],
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
              controller: _composerController,
              enabled: !_agentMode || !agentState.isSending,
              hintText: _agentMode
                  ? context.l10n.communityAgentPromptHint
                  : context.l10n.communityMessageInputHint,
              fileUploadGroupId: widget.groupId,
              onFileUploaded: (file) async {
                try {
                  final repo = ref.read(fileRepositoryProvider);
                  await repo.shareToGroup(widget.groupId, file.id);
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
                    context.l10n.communityFileSharedFailed(
                      UserFacingError.from(e),
                    ),
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
                      .sendMessage(content: text, replyToId: actualReplyId),
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
          localizedName: context.l10n.communityAgentName,
        ),
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
                // U-01 Step 1：FilterChip → SemanticPill（selected 态经 owner 扩展 API）。
                SemanticPill(
                  label: _agentMode
                      ? context.l10n.communityAgentCollabOn
                      : context.l10n.communityAgentCollabOff,
                  tone: PillTone.brand,
                  selected: _agentMode,
                  icon: Icons.auto_awesome,
                  onTap: () {
                    setState(() {
                      _agentMode = !_agentMode;
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
                        fontSize: DS.fontSizeSm, color: DS.neutral500,),
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

  /// SEARCH-EMPTY（N28-⑤ 命中可达）：点搜索结果→关 sheet→消息列表滚动
  /// 定位+短高亮——替换原「tap 只 pop」的 pop-only 死链。
  void _locateSearchHit(MessageInfo msg) {
    _highlightTimer?.cancel();
    setState(() => _highlightedMessageId = msg.id);
    // 高亮驻留窗（非动画时长，seconds 形制照 openclaw_connection_panel
    // 的 _saveHighlightTimer 先例）：2s 后收敛，容器经 300ms 淡出。
    _highlightTimer = Timer(const Duration(seconds: 2), () {
      if (mounted) {
        setState(() => _highlightedMessageId = null);
      }
    });
    unawaited(_scrollToMessage(msg.id));
  }

  Future<void> _scrollToMessage(String messageId) async {
    final notifier = ref.read(groupChatProvider(widget.groupId).notifier);
    // 目标可能在未加载的更早分页里：有界向前翻页直至命中或翻尽。
    var guard = 0;
    while (!_loadedMessagesContain(messageId) &&
        notifier.hasMoreMessages &&
        guard < 30) {
      guard++;
      await notifier.loadOlderMessages();
    }
    if (!mounted) {
      return;
    }
    if (!_loadedMessagesContain(messageId)) {
      AppFeedback.info(context, context.l10n.chatGroupLocateUnavailable);
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_revealMessage(messageId));
    });
  }

  bool _loadedMessagesContain(String messageId) =>
      (ref.read(groupChatProvider(widget.groupId)).valueOrNull ?? const []).any(
        (message) => message.id == messageId,
      );

  /// 复用 chat_screen 的 ensureVisible 定位；因 ListView 懒构建，目标
  /// 未物化时按平均项高 jumpTo 逼近（N28-⑤ 一期：滚动定位即达标），
  /// 有界重试直至可见。
  Future<void> _revealMessage(String messageId, {int attempt = 0}) async {
    if (!mounted) {
      return;
    }
    final targetContext = _messageKeys[messageId]?.currentContext;
    if (targetContext != null) {
      await Scrollable.ensureVisible(
        targetContext,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutCubic,
        alignment: 0.22,
      );
      return;
    }
    if (attempt >= 12 || !_scrollController.hasClients) {
      return;
    }
    final messages =
        ref.read(groupChatProvider(widget.groupId)).valueOrNull ?? const [];
    final index = messages.indexWhere((message) => message.id == messageId);
    if (index < 0) {
      return;
    }
    final position = _scrollController.position;
    final itemCount = messages.length + 1;
    final averageExtent = itemCount > 1 && position.maxScrollExtent > 0
        ? position.maxScrollExtent / (itemCount - 1)
        : 240.0;
    // reverse 列表：index 0 贴 offset 0（最新在底部），越旧 offset 越大。
    final target = (index * averageExtent - position.viewportDimension * 0.5)
        .clamp(0.0, position.maxScrollExtent);
    _scrollController.jumpTo(target);
    await WidgetsBinding.instance.endOfFrame;
    await _revealMessage(messageId, attempt: attempt + 1);
  }

  Future<void> _showSearchSheet() async {
    final notifier = ref.read(groupChatProvider(widget.groupId).notifier);
    final controller = TextEditingController();
    var results = <MessageInfo>[];
    var isLoading = false;
    // N28-③：区分「没搜过」（引导提示）与「搜了没有」（专用无结果态）
    // 与「搜失败」（人话错误）三态——替换原静默空白。
    var hasSearched = false;
    var searchFailed = false;
    var lastQuery = '';

    try {
      await showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (sheetContext) => StatefulBuilder(
          builder: (sheetContext, setSheetState) => DecoratedBox(
            decoration: BoxDecoration(
              color: Theme.of(sheetContext).scaffoldBackgroundColor,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(24),
              ),
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: EdgeInsets.only(
                  left: DS.spacing16,
                  right: DS.spacing16,
                  top: DS.spacing16,
                  bottom: MediaQuery.of(sheetContext).viewInsets.bottom +
                      DS.spacing16,
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
                      key: const ValueKey('group-chat-search-field'),
                      controller: controller,
                      decoration: InputDecoration(
                        hintText:
                            sheetContext.l10n.communitySearchGroupMessages,
                        prefixIcon: const Icon(Icons.search),
                        // N28-④：有词即显 clear 钮（清词并回到未搜过态）。
                        suffixIcon: ValueListenableBuilder<TextEditingValue>(
                          valueListenable: controller,
                          builder: (context, value, _) => value.text.isEmpty
                              ? const SizedBox.shrink()
                              // A11Y-BATCH3 同源形制：tooltip 与 Icon
                              // semanticLabel 同一 l10n 键——隐藏期 Tooltip
                              // 只挂 semantics.tooltip（非按钮名），名字由
                              // Icon semanticLabel 反推上提到按钮节点。
                              : IconButton(
                                  tooltip: context.l10n.commonClear,
                                  icon: Icon(
                                    Icons.clear,
                                    semanticLabel: context.l10n.commonClear,
                                  ),
                                  onPressed: () {
                                    controller.clear();
                                    setSheetState(() {
                                      results = [];
                                      hasSearched = false;
                                      searchFailed = false;
                                      lastQuery = '';
                                    });
                                  },
                                ),
                        ),
                      ),
                      onSubmitted: (value) async {
                        final keyword = value.trim();
                        if (keyword.isEmpty) return;
                        setSheetState(() {
                          isLoading = true;
                          searchFailed = false;
                        });
                        try {
                          results = await notifier.searchMessages(keyword);
                          hasSearched = true;
                          lastQuery = keyword;
                        } catch (e) {
                          // SR-G1：不再静默吞错——人话映射（N16 单源）入 sheet 态。
                          results = [];
                          hasSearched = true;
                          lastQuery = keyword;
                          searchFailed = true;
                          if (kDebugMode) {
                            debugPrint('[GroupChatSearch] search failed: $e');
                          }
                        } finally {
                          setSheetState(() => isLoading = false);
                        }
                      },
                    ),
                    const SizedBox(height: DS.spacing16),
                    if (isLoading)
                      const LoadingIndicator()
                    else if (searchFailed)
                      SizedBox(
                        height: 280,
                        child: CompactEmptyState(
                          icon: Icons.error_outline,
                          message: sheetContext.l10n.communityGroupSearchFailed,
                        ),
                      )
                    else if (hasSearched && results.isEmpty)
                      SizedBox(
                        height: 280,
                        // 小视口防溢出：空态内容高于 280 时可滚动。
                        child: SingleChildScrollView(
                          child: EmptyState.noResults(
                            searchQuery: lastQuery,
                            customAction: SparkleButton.ghost(
                              label: sheetContext.l10n.commonClearSearch,
                              onPressed: () {
                                controller.clear();
                                setSheetState(() {
                                  results = [];
                                  hasSearched = false;
                                  lastQuery = '';
                                });
                              },
                            ),
                          ),
                        ),
                      )
                    else if (results.isNotEmpty)
                      SizedBox(
                        height: 280,
                        child: ListView.builder(
                          itemCount: results.length,
                          itemBuilder: (context, index) {
                            final msg = results[index];
                            return ListTile(
                              title: Text(
                                msg.content ??
                                    sheetContext.l10n.communityMessageFallback,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                              subtitle: Text(
                                '${msg.sender?.displayName ?? sheetContext.l10n.communityMemberFallback} • '
                                '${DateFormat('MM/dd HH:mm').format(msg.createdAt)}',
                              ),
                              onTap: () {
                                Navigator.pop(sheetContext);
                                _locateSearchHit(msg);
                              },
                            );
                          },
                        ),
                      )
                    else
                      Padding(
                        padding: const EdgeInsets.symmetric(
                          vertical: DS.spacing40,
                        ),
                        child: Text(
                          sheetContext.l10n.communityGroupSearchEmptyHint,
                          style: TextStyle(
                            color: DS.textSecondary,
                            fontSize: DS.fontSizeSm,
                          ),
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
  Widget build(BuildContext context) => SemanticPill(
        label: label,
        tone: PillTone.brand,
        dense: true,
        onTap: onTap,
      );
}
