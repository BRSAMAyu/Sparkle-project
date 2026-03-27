import 'dart:async';
import 'dart:collection';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_network_image.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/utils/grapheme_utils.dart';
import 'package:sparkle/core/widgets/sparkle_markdown.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_workflow_panel.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_message_metadata_tray.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_accessory_pill.dart';
import 'package:sparkle/features/chat/presentation/widgets/expert_roundtable_widget.dart';
import 'package:sparkle/features/chat/presentation/widgets/message_detail_view.dart';
import 'package:sparkle/features/chat/presentation/widgets/mode_suggestion_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/orchestration_trace_panel.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_share_repository.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/features/community/presentation/widgets/share_cards/share_cards.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/features/plan/presentation/widgets/plan_context_summary.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/report_routes.dart';
import 'package:sparkle/features/simulation/simulation_routes.dart';
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart';
import 'package:sparkle/features/theater/theater_routes.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

class ChatBubble extends ConsumerStatefulWidget {
  const ChatBubble({
    required this.message,
    super.key,
    this.showAvatar = true,
    this.currentUserId,
    this.onQuote,
    this.onRevoke,
    this.onActionConfirm,
    this.onActionDismiss,
    this.onResponseFeedback,
    this.onWidgetAction,
    this.onPromoteSelfVisibleDraft,
    this.isLatestAssistantMessage = false,
  });
  final dynamic message; // ChatMessageModel or PrivateMessageInfo
  final bool showAvatar;
  final String? currentUserId;
  final void Function(dynamic message)? onQuote;
  final void Function(dynamic message)? onRevoke;
  final void Function(WidgetPayload action)? onActionConfirm;
  final void Function(WidgetPayload action)? onActionDismiss;
  final void Function(ChatMessageModel message, String feedbackType)?
      onResponseFeedback;
  final Future<void> Function(String actionType, Map<String, dynamic> payload)?
      onWidgetAction;
  final void Function(dynamic message)? onPromoteSelfVisibleDraft;
  final bool isLatestAssistantMessage;

  @override
  ConsumerState<ChatBubble> createState() => _ChatBubbleState();
}

class _ChatBubbleState extends ConsumerState<ChatBubble>
    with TickerProviderStateMixin {
  static const int _maxResponseFeedbackSelections = 200;
  static const Duration _informationalAccessoryLifetime = Duration(seconds: 5);
  static final LinkedHashMap<String, String> _responseFeedbackSelections =
      LinkedHashMap<String, String>();
  static final Set<String> _collapsedInformationalMessageIds = <String>{};
  late AnimationController _entryController;
  late Animation<double> _scale;
  late Animation<Offset> _position;
  Timer? _informationalCollapseTimer;

  bool _showHeart = false;
  bool _isPressed = false;
  late bool _showExpandedInformationalAccessories;

  bool get _isFreshUserBubble {
    if (widget.message is! ChatMessageModel) {
      return false;
    }
    final message = widget.message as ChatMessageModel;
    if (message.role != MessageRole.user) {
      return false;
    }
    return message.id.startsWith('temp_user_') ||
        DateTime.now().difference(message.createdAt).inSeconds <= 2;
  }

  bool get _isFreshAssistantBubble {
    if (widget.message is! ChatMessageModel) {
      return false;
    }
    final message = widget.message as ChatMessageModel;
    if (message.role != MessageRole.assistant) {
      return false;
    }
    return widget.isLatestAssistantMessage &&
        DateTime.now().difference(message.createdAt).inSeconds <= 3;
  }

  bool get _isStreamingAssistantBubble {
    if (widget.message is! ChatMessageModel) {
      return false;
    }
    final message = widget.message as ChatMessageModel;
    if (message.role != MessageRole.assistant) {
      return false;
    }
    final status = message.aiStatus?.toUpperCase();
    return widget.isLatestAssistantMessage &&
        (status == 'GENERATING' || status == 'THINKING');
  }

  String? get _messageId => widget.message is ChatMessageModel
      ? (widget.message as ChatMessageModel).id
      : null;

  bool get _isAssistantChatMessage {
    if (widget.message is! ChatMessageModel) {
      return false;
    }
    return (widget.message as ChatMessageModel).role == MessageRole.assistant;
  }

  bool _shouldShowExpandedInformationalAccessoriesInitially() {
    if (!_isAssistantChatMessage || _messageId == null) {
      return false;
    }
    if (_collapsedInformationalMessageIds.contains(_messageId)) {
      return false;
    }
    final message = widget.message as ChatMessageModel;
    return widget.isLatestAssistantMessage ||
        DateTime.now().difference(message.createdAt) <=
            const Duration(seconds: 10);
  }

  @override
  void initState() {
    super.initState();
    _showExpandedInformationalAccessories =
        _shouldShowExpandedInformationalAccessoriesInitially();
    final isFreshUserBubble = _isFreshUserBubble;
    final isFreshAssistantBubble = _isFreshAssistantBubble;
    _entryController = AnimationController(
      duration: isFreshUserBubble
          ? const Duration(milliseconds: 200)
          : isFreshAssistantBubble
              ? const Duration(milliseconds: 220)
              : const Duration(milliseconds: 320),
      vsync: this,
    );

    _scale = Tween<double>(
      begin: isFreshUserBubble
          ? 0.8
          : isFreshAssistantBubble
              ? 0.96
              : 0.92,
      end: 1.0,
    ).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: isFreshUserBubble || isFreshAssistantBubble
            ? Curves.easeOutBack
            : Curves.easeOutQuart,
      ),
    );

    _position = Tween<Offset>(
      begin: isFreshUserBubble
          ? const Offset(0.16, 0.18)
          : isFreshAssistantBubble
              ? const Offset(0, 0.08)
              : const Offset(0, 0.14),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _entryController,
        curve: isFreshUserBubble || isFreshAssistantBubble
            ? Curves.easeOutBack
            : Curves.easeOutQuart,
      ),
    );

    unawaited(_entryController.forward());
    _scheduleInformationalAccessoryCollapse();
  }

  @override
  void didUpdateWidget(covariant ChatBubble oldWidget) {
    super.didUpdateWidget(oldWidget);
    final previousId = oldWidget.message is ChatMessageModel
        ? (oldWidget.message as ChatMessageModel).id
        : null;
    if (previousId != _messageId) {
      _informationalCollapseTimer?.cancel();
      _showExpandedInformationalAccessories =
          _shouldShowExpandedInformationalAccessoriesInitially();
      _scheduleInformationalAccessoryCollapse();
    }
  }

  @override
  void dispose() {
    _informationalCollapseTimer?.cancel();
    _entryController.dispose();
    super.dispose();
  }

  void _scheduleInformationalAccessoryCollapse() {
    if (!_isAssistantChatMessage || !_showExpandedInformationalAccessories) {
      return;
    }
    _informationalCollapseTimer = Timer(
      _informationalAccessoryLifetime,
      () {
        if (!mounted || _messageId == null) return;
        setState(() {
          _showExpandedInformationalAccessories = false;
        });
        _collapsedInformationalMessageIds.add(_messageId!);
      },
    );
  }

  bool get _isUser {
    final myId = widget.currentUserId ?? 'me';
    var isUser = false;
    if (widget.message is ChatMessageModel) {
      isUser = (widget.message as ChatMessageModel).role == MessageRole.user;
    } else if (widget.message is PrivateMessageInfo) {
      final msg = widget.message as PrivateMessageInfo;
      isUser = msg.sender.id == myId;
    } else if (widget.message is MessageInfo) {
      final msg = widget.message as MessageInfo;
      isUser = msg.sender?.id == myId;
    }
    if (_isAgent) {
      return false;
    }
    return isUser;
  }

  bool get _isAgent {
    if (widget.message is PrivateMessageInfo) {
      return isPrivateAgentMessage(widget.message as PrivateMessageInfo);
    }
    if (widget.message is MessageInfo) {
      return isCommunityAgentMessage(widget.message as MessageInfo);
    }
    return false;
  }

  bool get _isRevoked {
    if (widget.message is MessageInfo) {
      return (widget.message as MessageInfo).isRevoked;
    }
    if (widget.message is PrivateMessageInfo) {
      return (widget.message as PrivateMessageInfo).isRevoked;
    }
    return false;
  }

  String get _content => (widget.message is ChatMessageModel)
      ? (widget.message as ChatMessageModel).content
      : (widget.message is PrivateMessageInfo)
          ? (widget.message as PrivateMessageInfo).content ?? ''
          : (widget.message as MessageInfo).content ?? '';

  DateTime get _createdAt => (widget.message is ChatMessageModel)
      ? (widget.message as ChatMessageModel).createdAt
      : (widget.message is PrivateMessageInfo)
          ? (widget.message as PrivateMessageInfo).createdAt
          : (widget.message as MessageInfo).createdAt;

  String? get _responseId => (widget.message is ChatMessageModel)
      ? (widget.message as ChatMessageModel).responseId
      : null;

  String? get _responseFeedbackSelection =>
      _responseId == null ? null : _responseFeedbackSelections[_responseId!];

  void _rememberResponseFeedbackSelection(String responseId, String selection) {
    _responseFeedbackSelections.remove(responseId);
    _responseFeedbackSelections[responseId] = selection;
    if (_responseFeedbackSelections.length > _maxResponseFeedbackSelections) {
      _responseFeedbackSelections
          .remove(_responseFeedbackSelections.keys.first);
    }
  }

  List<WidgetPayload> get _widgets => widget.message is ChatMessageModel
      ? (widget.message as ChatMessageModel).widgets ?? const []
      : const [];

  List<WidgetPayload> get _metadataWidgets => _widgets.where((widgetItem) {
        switch (widgetItem.type) {
          case 'continuity_banner':
          case 'mode_explanation':
          case 'source_summary':
            return true;
          case 'next_actions':
            return widget.isLatestAssistantMessage;
          default:
            return false;
        }
      }).toList();

  List<WidgetPayload> get _actionableWidgets => _widgets.where((widgetItem) {
        switch (widgetItem.type) {
          case 'continuity_banner':
          case 'mode_explanation':
          case 'source_summary':
          case 'next_actions':
          case 'plan_context_summary':
          case 'plan_state':
            return false;
          default:
            return true;
        }
      }).toList();

  List<WidgetPayload> get _informationalWidgets => _widgets.where((widgetItem) {
        switch (widgetItem.type) {
          case 'plan_context_summary':
          case 'plan_state':
            return true;
          default:
            return false;
        }
      }).toList();

  void _handleDoubleTap() {
    if (_isUser || _isRevoked || !mounted || context.reduceMotion) return;
    setState(() => _showHeart = true);
    Future.delayed(const Duration(milliseconds: 1000), () {
      if (mounted) setState(() => _showHeart = false);
    });
  }

  void _handleTap(BuildContext context) {
    if (_isRevoked || !mounted) return;

    // 只为ChatMessageModel类型的消息打开详情视图
    if (widget.message is ChatMessageModel) {
      final chatMessage = widget.message as ChatMessageModel;

      // 如果消息内容太短（少于100个字符），不需要放大查看
      if (chatMessage.content.length < 100) return;

      // 生成唯一的Hero tag
      final heroTag = 'message_${chatMessage.id}';

      // 打开详情视图
      unawaited(
        Navigator.of(context).push(
          PageRouteBuilder<void>(
            opaque: false, // 使用半透明背景
            barrierColor: DS.overlay30.withValues(alpha: 0),
            pageBuilder: (context, animation, secondaryAnimation) =>
                FadeTransition(
              opacity: animation,
              child: MessageDetailView(
                message: chatMessage,
                heroTag: heroTag,
              ),
            ),
            transitionDuration: const Duration(milliseconds: 250),
          ),
        ),
      );
    }
  }

  void _showContextMenu(BuildContext context) {
    if (_isRevoked || !mounted) return;
    final chatPureMode = ref.read(chatPureModeProvider);
    final isSelfVisibleAgentDraft = widget.message is PrivateMessageInfo &&
        isPrivateAgentMessage(widget.message as PrivateMessageInfo) &&
        ((widget.message as PrivateMessageInfo)
                .contentData?[kAgentVisibilityKey]
                ?.toString() ==
            kAgentVisibilitySelf);

    // Allow revocation within 24 hours for user messages
    final canRevoke = (_isUser || isSelfVisibleAgentDraft) &&
        DateTime.now().difference(_createdAt).inHours < 24;

    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.overlay30.withValues(alpha: 0),
        builder: (context) => DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(context).scaffoldBackgroundColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (isSelfVisibleAgentDraft)
                  ListTile(
                    leading: const Icon(Icons.visibility_off_outlined),
                    title: const Text('仅自己可见'),
                    subtitle: const Text('这条 AI 草稿只保存在你的当前私聊视图里。'),
                    onTap: () => Navigator.pop(context),
                  ),
                if (isSelfVisibleAgentDraft &&
                    widget.onPromoteSelfVisibleDraft != null)
                  ListTile(
                    leading: const Icon(Icons.visibility_outlined),
                    title: const Text('改为双方都可见'),
                    subtitle: const Text('把这条草稿放回输入框，由你确认后发送给对方。'),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onPromoteSelfVisibleDraft!(widget.message);
                    },
                  ),
                if (!_isUser &&
                    _responseId != null &&
                    _responseId!.isNotEmpty &&
                    widget.onResponseFeedback != null &&
                    widget.message is ChatMessageModel)
                  ListTile(
                    leading: const Icon(Icons.thumb_up_alt_rounded),
                    title: Text(context.l10n.chatHelpful),
                    onTap: () {
                      Navigator.pop(context);
                      if (_responseId != null) {
                        setState(() {
                          _rememberResponseFeedbackSelection(
                            _responseId!,
                            'up',
                          );
                        });
                      }
                      widget.onResponseFeedback!(
                        widget.message as ChatMessageModel,
                        'up',
                      );
                    },
                  ),
                if (!_isUser &&
                    _responseId != null &&
                    _responseId!.isNotEmpty &&
                    widget.onResponseFeedback != null &&
                    widget.message is ChatMessageModel)
                  ListTile(
                    leading: const Icon(Icons.thumb_down_alt_rounded),
                    title: Text(context.l10n.chatNotHelpful),
                    onTap: () {
                      Navigator.pop(context);
                      if (_responseId != null) {
                        setState(() {
                          _rememberResponseFeedbackSelection(
                            _responseId!,
                            'down',
                          );
                        });
                      }
                      widget.onResponseFeedback!(
                        widget.message as ChatMessageModel,
                        'down',
                      );
                    },
                  ),
                if (chatPureMode && _hasPureModeHiddenAccessoryContent)
                  ListTile(
                    leading: const Icon(Icons.layers_outlined),
                    title: const Text('查看附加内容'),
                    subtitle: const Text('在纯净模式下临时展开任务卡和快捷入口'),
                    onTap: () {
                      Navigator.pop(context);
                      _showPureModeAccessorySheet(context);
                    },
                  ),
                if (widget.onQuote != null &&
                    widget.message is PrivateMessageInfo)
                  ListTile(
                    leading: const Icon(Icons.format_quote_rounded),
                    title: Text(context.l10n.chatQuote),
                    onTap: () {
                      if (mounted) {
                        Navigator.pop(context);
                        widget.onQuote!(widget.message);
                      }
                    },
                  ),
                ListTile(
                  leading: const Icon(Icons.copy_rounded),
                  title: Text(context.l10n.chatCopy),
                  onTap: () async {
                    await Clipboard.setData(ClipboardData(text: _content));
                    if (!context.mounted) return;
                    Navigator.of(context).pop();
                    AppFeedback.success(context, context.l10n.chatCopied);
                  },
                ),
                if (canRevoke && widget.onRevoke != null)
                  ListTile(
                    leading: Icon(Icons.undo_rounded, color: DS.error),
                    title: Text(
                      context.l10n.chatUndo,
                      style: TextStyle(color: DS.error),
                    ),
                    onTap: () {
                      if (mounted) {
                        Navigator.pop(context);
                        widget.onRevoke!(widget.message);
                      }
                    },
                  ),
                const SizedBox(height: DS.sm),
              ],
            ),
          ),
        ),
      ),
    );
  }

  bool get _hasPureModeHiddenAccessoryContent {
    if (widget.message is! ChatMessageModel) {
      return false;
    }
    final message = widget.message as ChatMessageModel;
    final collaboration = message.agentCollaboration ?? const {};
    final hasPreviewShortcut =
        collaboration['prediction_preview'] is Map<dynamic, dynamic> ||
            collaboration['simulation_preview'] is Map<dynamic, dynamic> ||
            collaboration['report_preview'] is Map<dynamic, dynamic>;
    return _actionableWidgets.isNotEmpty || hasPreviewShortcut;
  }

  void _showPureModeAccessorySheet(BuildContext context) {
    if (widget.message is! ChatMessageModel) {
      return;
    }
    final chatMessage = widget.message as ChatMessageModel;
    Map<String, dynamic>? asMap(dynamic value) {
      if (value is Map<dynamic, dynamic>) {
        return Map<String, dynamic>.from(value);
      }
      return null;
    }

    final predictionPreview =
        asMap(chatMessage.agentCollaboration?['prediction_preview']);
    final simulationPreview =
        asMap(chatMessage.agentCollaboration?['simulation_preview']);
    final reportPreview =
        asMap(chatMessage.agentCollaboration?['report_preview']);
    final theaterDeepLink =
        chatMessage.agentCollaboration?['deep_link']?.toString();
    final simulationDeepLink =
        chatMessage.agentCollaboration?['simulation_deep_link']?.toString();
    final reportDeepLink =
        chatMessage.agentCollaboration?['report_deep_link']?.toString();
    final sourceChatSessionId =
        chatMessage.agentCollaboration?['source_chat_session_id']?.toString();

    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        backgroundColor: DS.overlay30.withValues(alpha: 0),
        isScrollControlled: true,
        builder: (sheetContext) => DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(sheetContext).scaffoldBackgroundColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: SafeArea(
            top: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(DS.spacing16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '附加内容',
                    style:
                        Theme.of(sheetContext).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                  ),
                  const SizedBox(height: DS.spacing12),
                  if (_actionableWidgets.isNotEmpty) ...[
                    ..._actionableWidgets.map(
                      (w) {
                        final actionable = (w.data['id'] ??
                                w.data['tool_result_id'] ??
                                w.data['intervention_id'] ??
                                w.data['request_id']) !=
                            null;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: DS.spacing12),
                          child: ActionCard(
                            action: w,
                            onConfirm:
                                actionable && widget.onActionConfirm != null
                                    ? () => widget.onActionConfirm!(w)
                                    : null,
                            onDismiss:
                                actionable && widget.onActionDismiss != null
                                    ? () => widget.onActionDismiss!(w)
                                    : null,
                            onConfirmTasks: (toolResultId) async {
                              final planId = w.data['plan_id']?.toString() ??
                                  w.data['planId']?.toString();
                              await _confirmGeneratedTasks(
                                toolResultId: toolResultId,
                                planId: planId,
                              );
                            },
                            onConfirmAllTasks: (toolResultId) async {
                              final planId = w.data['plan_id']?.toString() ??
                                  w.data['planId']?.toString();
                              await _confirmGeneratedTasks(
                                toolResultId: toolResultId,
                                planId: planId,
                              );
                            },
                            onPlanNavigation: (planId) {
                              unawaited(
                                ref.read(planListProvider.notifier).refresh(),
                              );
                            },
                            onWidgetAction: widget.onWidgetAction,
                          ),
                        );
                      },
                    ),
                  ],
                  if (predictionPreview != null && predictionPreview.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing8),
                      child: _buildTheaterPreviewCard(
                        sheetContext,
                        preview: predictionPreview,
                        deepLink: theaterDeepLink,
                        sourceChatSessionId: sourceChatSessionId,
                      ),
                    ),
                  if (simulationPreview != null && simulationPreview.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: DS.spacing8),
                      child: _buildSimulationPreviewCard(
                        sheetContext,
                        preview: simulationPreview,
                        deepLink: simulationDeepLink,
                        sourceChatSessionId: sourceChatSessionId,
                      ),
                    ),
                  if (reportPreview != null && reportPreview.isNotEmpty)
                    _buildReportPreviewCard(
                      sheetContext,
                      preview: reportPreview,
                      deepLink: reportDeepLink,
                      sourceChatSessionId: sourceChatSessionId,
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isRevoked) return _buildRevokedPlaceholder();

    final chatPureMode = ref.watch(chatPureModeProvider);
    final chatMessage = widget.message is ChatMessageModel
        ? widget.message as ChatMessageModel
        : null;
    final showExpandedInformationalAccessories =
        _showExpandedInformationalAccessories && !chatPureMode;
    final isUser = _isUser;
    final timeStr = DateFormat('HH:mm').format(_createdAt);
    final reduceMotion = context.reduceMotion;
    final orchestrationTrace = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).orchestrationTrace
        : null;
    final modeSuggestion = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).modeSuggestion
        : null;
    final collaborationNarrative = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).collaborationNarrative
        : null;
    final collaborationMode = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).collaborationMode
        : null;
    final routingPreview = widget.message is ChatMessageModel
        ? ((widget.message as ChatMessageModel)
            .agentCollaboration?['routing_preview'] as Map<String, dynamic>?)
        : null;
    final roundtableTurns = widget.message is ChatMessageModel
        ? ((((widget.message as ChatMessageModel)
                        .agentCollaboration?['roundtable_turns']
                    as List<dynamic>?) ??
                const [])
            .whereType<Map<dynamic, dynamic>>()
            .map(Map<String, dynamic>.from)
            .toList())
        : const <Map<String, dynamic>>[];
    final agentsInvolved = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).agentsInvolved
        : const <String>[];
    final agentActivities = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).agentActivities
        : const <Map<String, dynamic>>[];
    final predictionPreview = widget.message is ChatMessageModel
        ? ((widget.message as ChatMessageModel)
            .agentCollaboration?['prediction_preview'] as Map<String, dynamic>?)
        : null;
    final simulationPreview = widget.message is ChatMessageModel
        ? ((widget.message as ChatMessageModel)
            .agentCollaboration?['simulation_preview'] as Map<String, dynamic>?)
        : null;
    final reportPreview = widget.message is ChatMessageModel
        ? ((widget.message as ChatMessageModel)
            .agentCollaboration?['report_preview'] as Map<String, dynamic>?)
        : null;
    final theaterDeepLink =
        chatMessage?.agentCollaboration?['deep_link']?.toString();
    final simulationDeepLink =
        chatMessage?.agentCollaboration?['simulation_deep_link']?.toString();
    final reportDeepLink =
        chatMessage?.agentCollaboration?['report_deep_link']?.toString();
    final sourceChatSessionId =
        chatMessage?.agentCollaboration?['source_chat_session_id']?.toString();
    final primaryAgentId = widget.message is ChatMessageModel
        ? ((widget.message as ChatMessageModel)
                .agentCollaboration?['primary_agent']
                ?.toString() ??
            (agentsInvolved.isNotEmpty ? agentsInvolved.first : null))
        : null;
    Map<String, dynamic>? primarySnapshot;
    if (primaryAgentId != null && primaryAgentId.isNotEmpty) {
      for (final item in agentActivities) {
        if (item['agent_id']?.toString() == primaryAgentId) {
          primarySnapshot = item;
          break;
        }
      }
    }
    final bubble = Container(
      margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 12.0),
      child: Column(
        children: [
          Row(
            mainAxisAlignment:
                isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              if (!isUser && widget.showAvatar) _buildAvatar(false),
              if (!isUser && !widget.showAvatar)
                const SizedBox(width: DS.touchTargetMinSize - DS.spacing4),
              Flexible(
                child: GestureDetector(
                  onTap: () => _handleTap(context),
                  onDoubleTap: _handleDoubleTap,
                  onLongPress: () => _showContextMenu(context),
                  onTapDown: (_) {
                    if (mounted) setState(() => _isPressed = true);
                  },
                  onTapUp: (_) {
                    if (mounted) setState(() => _isPressed = false);
                  },
                  onTapCancel: () {
                    if (mounted) setState(() => _isPressed = false);
                  },
                  child: AnimatedScale(
                    scale: _isPressed ? 0.98 : 1.0,
                    duration: reduceMotion
                        ? Duration.zero
                        : const Duration(milliseconds: 100),
                    curve: Curves.easeInOut,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Column(
                          crossAxisAlignment: isUser
                              ? CrossAxisAlignment.end
                              : CrossAxisAlignment.start,
                          children: [
                            Container(
                              margin:
                                  const EdgeInsets.symmetric(horizontal: 8.0),
                              constraints: BoxConstraints(
                                maxWidth: _bubbleMaxWidth(context),
                              ),
                              child: MaterialStyler(
                                material: isUser
                                    ? SparkleMaterial(
                                        backgroundGradient: LinearGradient(
                                          begin: Alignment.topLeft,
                                          end: Alignment.bottomRight,
                                          colors: [
                                            Color.lerp(
                                                  DS.brandPrimary,
                                                  DS.info,
                                                  0.16,
                                                ) ??
                                                DS.brandPrimary,
                                            DS.brandPrimary
                                                .withValues(alpha: 0.9),
                                          ],
                                        ),
                                        borderColor: Colors.white
                                            .withValues(alpha: 0.18),
                                        shadows: [
                                          BoxShadow(
                                            color: DS.brandPrimary
                                                .withValues(alpha: 0.16),
                                            blurRadius: 14,
                                            offset: const Offset(0, 8),
                                          ),
                                        ],
                                      )
                                    : _getAIMessageMaterial(context),
                                shapeBorder: ContinuousRectangleBorder(
                                  borderRadius: BorderRadius.circular(24),
                                ),
                                padding: const EdgeInsets.symmetric(
                                  vertical: 10,
                                  horizontal: 14,
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (!chatPureMode &&
                                        !isUser &&
                                        primaryAgentId != null &&
                                        primaryAgentId.isNotEmpty)
                                      Padding(
                                        padding: const EdgeInsets.only(
                                          bottom: DS.spacing8,
                                        ),
                                        child: AssistantAgentBadge(
                                          agentId: primaryAgentId,
                                          displayName:
                                              primarySnapshot?['display_name']
                                                  ?.toString(),
                                          colorHex: primarySnapshot?['color']
                                              ?.toString(),
                                          iconName: primarySnapshot?['icon']
                                              ?.toString(),
                                        ),
                                      ),
                                    if (widget.message is PrivateMessageInfo &&
                                        (widget.message as PrivateMessageInfo)
                                                .quotedMessage !=
                                            null)
                                      _buildQuoteArea(
                                        context,
                                        isUser,
                                        (widget.message as PrivateMessageInfo)
                                            .quotedMessage!,
                                      ),
                                    if (!chatPureMode &&
                                        widget.message is ChatMessageModel &&
                                        (widget.message as ChatMessageModel)
                                                .reasoningSteps !=
                                            null)
                                      Padding(
                                        padding:
                                            const EdgeInsets.only(bottom: 8.0),
                                        child: AgentReasoningBubble(
                                          steps: (widget.message
                                                  as ChatMessageModel)
                                              .reasoningSteps!,
                                          totalDurationMs:
                                              _calculateReasoningDuration(
                                            widget.message as ChatMessageModel,
                                          ),
                                        ),
                                      ),
                                    // Share card for private messages
                                    if (_isShareMessage())
                                      _buildPrivateShareCard() ??
                                          const SizedBox.shrink()
                                    else
                                      // Use constrained height for long messages
                                      LayoutBuilder(
                                        builder: (context, constraints) {
                                          // Calculate max height based on screen size
                                          final maxHeight =
                                              MediaQuery.of(context)
                                                      .size
                                                      .height *
                                                  0.5;
                                          final contentWidget = SparkleMarkdown(
                                            content: _content,
                                            textColor: isUser
                                                ? DS.chatBubbleUserText
                                                : DS.chatBubbleOtherText,
                                            codeBackgroundColor: isUser
                                                ? DS.chatBubbleUserText
                                                    .withValues(alpha: 0.12)
                                                : DS.surfaceTertiary,
                                            linkColor: isUser
                                                ? DS.chatBubbleUserText
                                                : DS.brandPrimary,
                                            isStreaming:
                                                _isStreamingAssistantBubble,
                                            contentRole:
                                                SparkleMarkdownRole.chatBubble,
                                          );

                                          // Try to estimate content height and decide if scrolling is needed
                                          // For long content (heuristic: >500 chars), use constrained scrollable
                                          final shouldConstrain =
                                              _content.length > 500;

                                          final animatedContent = AnimatedSize(
                                            duration: context.reduceMotion
                                                ? Duration.zero
                                                : DS.motionDuration(
                                                    SparkleMotionToken.micro,
                                                  ),
                                            curve: Curves.easeOutCubic,
                                            alignment: Alignment.topLeft,
                                            child: shouldConstrain
                                                ? SizedBox(
                                                    height: maxHeight,
                                                    child:
                                                        SingleChildScrollView(
                                                      physics:
                                                          const ClampingScrollPhysics(),
                                                      child: contentWidget,
                                                    ),
                                                  )
                                                : contentWidget,
                                          );

                                          if (!shouldConstrain) {
                                            return animatedContent;
                                          }

                                          return animatedContent;
                                        },
                                      ),
                                  ],
                                ),
                              ),
                            ),
                            if (!chatPureMode &&
                                (_metadataWidgets.isNotEmpty ||
                                    (widget.message is ChatMessageModel &&
                                        ((widget.message as ChatMessageModel)
                                                    .aiStatus !=
                                                null ||
                                            (widget.message as ChatMessageModel)
                                                    .meta !=
                                                null))))
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: AssistantMessageMetadataTray(
                                  actions: _metadataWidgets,
                                  isLatestMessage:
                                      widget.isLatestAssistantMessage,
                                  status: widget.message is ChatMessageModel
                                      ? (widget.message as ChatMessageModel)
                                          .aiStatus
                                      : null,
                                  messageMeta:
                                      widget.message is ChatMessageModel
                                          ? (widget.message as ChatMessageModel)
                                              .meta
                                          : null,
                                  onWidgetAction: widget.onWidgetAction,
                                ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                modeSuggestion != null &&
                                showExpandedInformationalAccessories)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: ModeSuggestionCard(
                                  suggestion: modeSuggestion,
                                ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                orchestrationTrace != null &&
                                showExpandedInformationalAccessories)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: OrchestrationTracePanel(
                                  traceData: orchestrationTrace,
                                ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                (routingPreview != null ||
                                    roundtableTurns.isNotEmpty))
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: ExpertRoundtableWidget(
                                  routingPreview: routingPreview,
                                  turns: roundtableTurns,
                                  compact: true,
                                  collapseId: chatMessage?.id,
                                ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                predictionPreview != null &&
                                predictionPreview.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: showExpandedInformationalAccessories
                                    ? _buildTheaterPreviewCard(
                                        context,
                                        preview: predictionPreview,
                                        deepLink: theaterDeepLink,
                                        sourceChatSessionId:
                                            sourceChatSessionId,
                                      )
                                    : _buildInsightShortcutPill(
                                        title: '查看推演详情',
                                        icon: Icons.auto_graph_rounded,
                                        onTap: () => context.push(
                                          _resolveInsightDeepLink(
                                            deepLink: theaterDeepLink,
                                            fallbackPath: TheaterRoutes.theater,
                                            fallbackQuery: {
                                              'topic':
                                                  predictionPreview['topic']
                                                          ?.toString() ??
                                                      '当前学习主题',
                                            },
                                            sourceChatSessionId:
                                                sourceChatSessionId,
                                          ),
                                        ),
                                      ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                simulationPreview != null &&
                                simulationPreview.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: showExpandedInformationalAccessories
                                    ? _buildSimulationPreviewCard(
                                        context,
                                        preview: simulationPreview,
                                        deepLink: simulationDeepLink,
                                        sourceChatSessionId:
                                            sourceChatSessionId,
                                      )
                                    : _buildInsightShortcutPill(
                                        title: '查看模拟详情',
                                        icon: Icons.groups_rounded,
                                        onTap: () => context.push(
                                          _resolveInsightDeepLink(
                                            deepLink: simulationDeepLink,
                                            fallbackPath:
                                                SimulationRoutes.simulation,
                                            fallbackQuery: {
                                              'topic':
                                                  simulationPreview['topic']
                                                          ?.toString() ??
                                                      '当前学习主题',
                                              'scenario_key': simulationPreview[
                                                          'scenario_key']
                                                      ?.toString() ??
                                                  'study_group',
                                            },
                                            sourceChatSessionId:
                                                sourceChatSessionId,
                                          ),
                                        ),
                                      ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                reportPreview != null &&
                                reportPreview.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: showExpandedInformationalAccessories
                                    ? _buildReportPreviewCard(
                                        context,
                                        preview: reportPreview,
                                        deepLink: reportDeepLink,
                                        sourceChatSessionId:
                                            sourceChatSessionId,
                                      )
                                    : _buildCompactReportPreviewPill(
                                        context,
                                        preview: reportPreview,
                                        deepLink: reportDeepLink,
                                        sourceChatSessionId:
                                            sourceChatSessionId,
                                      ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                agentActivities.isEmpty &&
                                ((collaborationNarrative != null &&
                                        collaborationNarrative.isNotEmpty) ||
                                    agentsInvolved.isNotEmpty) &&
                                showExpandedInformationalAccessories)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: _CollaborationSignatureCard(
                                  narrative: collaborationNarrative,
                                  collaborationMode: collaborationMode,
                                  agentIds: agentsInvolved,
                                  activitySnapshots: agentActivities,
                                ),
                              ),
                            if (!chatPureMode &&
                                !isUser &&
                                agentActivities.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: showExpandedInformationalAccessories
                                    ? AgentWorkflowPanel(
                                        snapshotActivities: agentActivities,
                                        narrative: collaborationNarrative,
                                      )
                                    : _buildStaticAccessoryPill(
                                        icon: Icons.hub_rounded,
                                        label: '协作过程',
                                      ),
                              ),
                            if (!chatPureMode)
                              ..._informationalWidgets.map(
                                (w) => Padding(
                                  padding: const EdgeInsets.only(
                                    top: 8.0,
                                    right: 8.0,
                                    left: 8.0,
                                  ),
                                  child: showExpandedInformationalAccessories
                                      ? _buildInformationalWidget(w)
                                      : _buildInformationalWidgetPill(w),
                                ),
                              ),
                            if (!chatPureMode)
                              ..._actionableWidgets.map(
                                (w) {
                                  final actionable = (w.data['id'] ??
                                          w.data['tool_result_id'] ??
                                          w.data['intervention_id'] ??
                                          w.data['request_id']) !=
                                      null;
                                  return Padding(
                                    padding: const EdgeInsets.only(
                                      top: 8.0,
                                      right: 8.0,
                                      left: 8.0,
                                    ),
                                    child: ActionCard(
                                      action: w,
                                      onConfirm: actionable &&
                                              widget.onActionConfirm != null
                                          ? () => widget.onActionConfirm!(w)
                                          : null,
                                      onDismiss: actionable &&
                                              widget.onActionDismiss != null
                                          ? () => widget.onActionDismiss!(w)
                                          : null,
                                      onConfirmTasks: (toolResultId) async {
                                        final planId =
                                            w.data['plan_id']?.toString() ??
                                                w.data['planId']?.toString();
                                        await _confirmGeneratedTasks(
                                          toolResultId: toolResultId,
                                          planId: planId,
                                        );
                                      },
                                      onConfirmAllTasks: (toolResultId) async {
                                        final planId =
                                            w.data['plan_id']?.toString() ??
                                                w.data['planId']?.toString();
                                        await _confirmGeneratedTasks(
                                          toolResultId: toolResultId,
                                          planId: planId,
                                        );
                                      },
                                      onPlanNavigation: (planId) {
                                        unawaited(
                                          ref
                                              .read(planListProvider.notifier)
                                              .refresh(),
                                        );
                                      },
                                      onWidgetAction: widget.onWidgetAction,
                                    ),
                                  );
                                },
                              ),
                            if (!chatPureMode && !isUser)
                              _buildResponseFeedbackRow(context),
                          ],
                        ),
                        if (_showHeart) _buildHeartAnimation(context),
                      ],
                    ),
                  ),
                ),
              ),
              if (isUser && widget.showAvatar) _buildAvatar(true),
              if (isUser && !widget.showAvatar)
                const SizedBox(width: DS.touchTargetMinSize - DS.spacing4),
            ],
          ),
          Padding(
            padding: EdgeInsets.only(
              top: 4,
              left: isUser ? 0 : 52,
              right: isUser ? 52 : 0,
            ),
            child: Row(
              mainAxisAlignment:
                  isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
              children: [
                if (isUser) _buildMessageStatus(),
                if (!chatPureMode &&
                    !isUser &&
                    widget.message is ChatMessageModel &&
                    (widget.message as ChatMessageModel).meta != null)
                  _buildTimingBadge((widget.message as ChatMessageModel).meta),
                const SizedBox(width: DS.xs),
                Text(
                  timeStr,
                  style: TextStyle(fontSize: 10, color: DS.neutral500),
                ),
              ],
            ),
          ),
        ],
      ),
    );

    if (reduceMotion) {
      return RepaintBoundary(child: bubble);
    }

    return RepaintBoundary(
      child: FadeTransition(
        opacity: CurvedAnimation(
          parent: _entryController,
          curve: Curves.easeOutCubic,
        ),
        child: SlideTransition(
          position: _position,
          child: ScaleTransition(
            scale: _scale,
            child: bubble,
          ),
        ),
      ),
    );
  }

  double _bubbleMaxWidth(BuildContext context) {
    final screenWidth = ResponsiveSystem.width(context);
    final contentMaxWidth = ContentConstraintSystem.maxWidth(context);
    final baseMax = contentMaxWidth.isFinite ? contentMaxWidth : screenWidth;
    return min(screenWidth * 0.72, baseMax * 0.9);
  }

  Widget _buildInformationalWidget(WidgetPayload widgetPayload) {
    switch (widgetPayload.type) {
      case 'plan_context_summary':
      case 'plan_state':
        return PlanContextSummary(contextData: widgetPayload.data);
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildInformationalWidgetPill(WidgetPayload widgetPayload) {
    switch (widgetPayload.type) {
      case 'plan_context_summary':
        return _buildStaticAccessoryPill(
          icon: Icons.summarize_outlined,
          label: '计划上下文',
        );
      case 'plan_state':
        return _buildStaticAccessoryPill(
          icon: Icons.flag_outlined,
          label: '计划状态',
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildInsightShortcutPill({
    required String title,
    required IconData icon,
    required VoidCallback onTap,
  }) =>
      ChatAccessoryPill(
        icon: icon,
        label: title,
        onTap: onTap,
        emphasize: true,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
      );

  Widget _buildStaticAccessoryPill({
    required IconData icon,
    required String label,
  }) =>
      ChatAccessoryPill(
        icon: icon,
        label: label,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
      );

  Future<void> _continueInlinePrompt(String prompt) async {
    final normalized = prompt.trim();
    if (normalized.isEmpty) {
      return;
    }
    await SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
    await ref.read(chatProvider.notifier).sendMessage(normalized);
  }

  List<_InlinePromptAction> _theaterPromptActions(
    Map<String, dynamic> preview,
  ) {
    final topic = preview['topic']?.toString() ?? '当前学习主题';
    final paths = (preview['paths'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final actions = <_InlinePromptAction>[
      _InlinePromptAction(
        label: '继续细化这条路径',
        prompt: '继续围绕「$topic」细化第一周最该先做的步骤。',
        onTap: () => _continueInlinePrompt(
          '继续围绕「$topic」细化第一周最该先做的步骤。',
        ),
      ),
    ];
    if (paths.length >= 2) {
      actions.add(
        _InlinePromptAction(
          label: '比较两条路线',
          prompt:
              '比较一下「${paths[0]['title'] ?? '路线 A'}」和「${paths[1]['title'] ?? '路线 B'}」的取舍。',
          onTap: () => _continueInlinePrompt(
            '比较一下「${paths[0]['title'] ?? '路线 A'}」和「${paths[1]['title'] ?? '路线 B'}」的取舍。',
          ),
        ),
      );
    } else {
      actions.add(
        _InlinePromptAction(
          label: '先补什么前置',
          prompt: '如果我现在就开始学「$topic」，最该先补的前置是什么？',
          onTap: () => _continueInlinePrompt(
            '如果我现在就开始学「$topic」，最该先补的前置是什么？',
          ),
        ),
      );
    }
    return actions;
  }

  List<_InlinePromptAction> _simulationPromptActions(
    Map<String, dynamic> preview,
  ) {
    final topic = preview['topic']?.toString() ?? '当前学习主题';
    final rounds = (preview['round_preview'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final actions = <_InlinePromptAction>[
      _InlinePromptAction(
        label: '继续模拟一轮',
        prompt: '继续围绕「$topic」模拟一轮，我想继续跟进这个学习场景。',
        onTap: () => _continueInlinePrompt(
          '继续围绕「$topic」模拟一轮，我想继续跟进这个学习场景。',
        ),
      ),
    ];
    if (rounds.isNotEmpty) {
      final speaker = rounds.first['speaker']?.toString() ?? '其中一个角色';
      actions.add(
        _InlinePromptAction(
          label: '让我来回答',
          prompt: '让 $speaker 围绕「$topic」继续追问我一个关键问题，我来回答。',
          onTap: () => _continueInlinePrompt(
            '让 $speaker 围绕「$topic」继续追问我一个关键问题，我来回答。',
          ),
        ),
      );
    }
    return actions;
  }

  List<_InlinePromptAction> _reportPromptActions(
    Map<String, dynamic> preview,
  ) {
    final report = LearningReport.fromJson(preview);
    final highlight = (preview['highlights'] as List<dynamic>? ?? const [])
        .map((item) => item.toString())
        .where((item) => item.isNotEmpty)
        .cast<String?>()
        .firstWhere((item) => item != null, orElse: () => null);
    final actions = <_InlinePromptAction>[
      _InlinePromptAction(
        label: '排今天行动顺序',
        prompt: '根据这份学习报告，帮我排一个今天就能开始的行动顺序。',
        onTap: () => _continueInlinePrompt(
          '根据这份学习报告，帮我排一个今天就能开始的行动顺序。',
        ),
      ),
    ];
    if ((highlight ?? '').isNotEmpty) {
      actions.add(
        _InlinePromptAction(
          label: '展开重点问题',
          prompt: '展开讲讲为什么「$highlight」最值得先处理。',
          onTap: () => _continueInlinePrompt(
            '展开讲讲为什么「$highlight」最值得先处理。',
          ),
        ),
      );
    } else if (report.mastery.isNotEmpty) {
      actions.add(
        _InlinePromptAction(
          label: '先补哪一块',
          prompt: '根据这份报告，先帮我解释为什么「${report.mastery.first.nodeName}」应该优先处理。',
          onTap: () => _continueInlinePrompt(
            '根据这份报告，先帮我解释为什么「${report.mastery.first.nodeName}」应该优先处理。',
          ),
        ),
      );
    }
    return actions;
  }

  Widget _buildTheaterPreviewCard(
    BuildContext context, {
    required Map<String, dynamic> preview,
    required String? deepLink,
    required String? sourceChatSessionId,
  }) {
    final topic = preview['topic']?.toString() ?? '当前学习主题';
    final paths = (preview['paths'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final resolvedDeepLink = _resolveInsightDeepLink(
      deepLink: deepLink,
      fallbackPath: TheaterRoutes.theater,
      fallbackQuery: {'topic': topic},
      sourceChatSessionId: sourceChatSessionId,
    );
    final promptActions = _theaterPromptActions(preview);
    return _InsightLinkCard(
      icon: Icons.auto_graph_rounded,
      title: '推演剧场',
      subtitle: topic,
      bullets: paths
          .take(3)
          .map(
            (item) =>
                '${item['title'] ?? '路径'} · 掌握度 ${(item['estimated_mastery'] as num?)?.toStringAsFixed(0) ?? '--'}%',
          )
          .toList(),
      caption: (sourceChatSessionId?.isNotEmpty ?? false) ? '承接当前对话' : null,
      onTap: () => context.push(resolvedDeepLink),
      promptActions: promptActions,
      primaryLabel: '查看完整版',
      onPrimaryTap: () => context.push(resolvedDeepLink),
      secondaryLabel: '继续在对话里',
      onSecondaryTap: () => _continueInlinePrompt(promptActions.first.prompt),
    );
  }

  Widget _buildSimulationPreviewCard(
    BuildContext context, {
    required Map<String, dynamic> preview,
    required String? deepLink,
    required String? sourceChatSessionId,
  }) {
    final topic = preview['topic']?.toString() ?? '当前学习主题';
    final scenarioKey = preview['scenario_key']?.toString() ?? 'study_group';
    final rounds = (preview['round_preview'] as List<dynamic>? ?? const [])
        .whereType<Map<dynamic, dynamic>>()
        .map(Map<String, dynamic>.from)
        .toList();
    final resolvedDeepLink = _resolveInsightDeepLink(
      deepLink: deepLink,
      fallbackPath: SimulationRoutes.simulation,
      fallbackQuery: {
        'topic': topic,
        'scenario_key': scenarioKey,
      },
      sourceChatSessionId: sourceChatSessionId,
    );
    final promptActions = _simulationPromptActions(preview);
    return _InsightLinkCard(
      icon: Icons.groups_rounded,
      title: '学习仿真',
      subtitle: topic,
      bullets: rounds
          .take(3)
          .map(
            (item) => '${item['speaker'] ?? '参与者'}: ${item['message'] ?? ''}',
          )
          .toList(),
      caption: (sourceChatSessionId?.isNotEmpty ?? false) ? '承接当前对话' : null,
      onTap: () => context.push(resolvedDeepLink),
      promptActions: promptActions,
      primaryLabel: '进入仿真',
      onPrimaryTap: () => context.push(resolvedDeepLink),
      secondaryLabel: '继续在对话里',
      onSecondaryTap: () => _continueInlinePrompt(promptActions.first.prompt),
    );
  }

  Widget _buildReportPreviewCard(
    BuildContext context, {
    required Map<String, dynamic> preview,
    required String? deepLink,
    required String? sourceChatSessionId,
  }) {
    final report = LearningReport.fromJson(preview);
    final highlights = (preview['highlights'] as List<dynamic>? ?? const [])
        .map((item) => item.toString())
        .where((item) => item.isNotEmpty)
        .toList();
    final summary = preview['summary']?.toString() ?? '查看最新学习报告';
    final triggerSummary = report.triggerSummary;
    final promptActions = _reportPromptActions(preview);
    final resolvedDeepLink = _resolveInsightDeepLink(
      deepLink: deepLink,
      fallbackPath: ReportRoutes.learningReport,
      fallbackQuery: const <String, String>{},
      sourceChatSessionId: sourceChatSessionId,
    );
    return _InsightLinkCard(
      icon: Icons.article_outlined,
      title: '查看学习报告',
      subtitle: summary,
      bullets: highlights.isNotEmpty
          ? highlights.map((item) => '重点关注: $item').toList()
          : report.mastery
              .take(3)
              .map(
                (item) =>
                    '${item.nodeName} · 掌握度 ${item.masteryScore.toStringAsFixed(0)}%',
              )
              .toList(),
      caption: (sourceChatSessionId?.isNotEmpty ?? false) ? '承接当前对话' : null,
      onTap: () {
        if (report.reportId.isNotEmpty || report.markdown.isNotEmpty) {
          unawaited(context.push(resolvedDeepLink, extra: report));
          return;
        }
        unawaited(context.push(resolvedDeepLink));
      },
      badgeLabel: triggerSummary?.title,
      promptActions: promptActions,
      actionButtons: report.actionCards
          .take(2)
          .map(
            (item) => _InlineActionButton(
              label: item.ctaLabel,
              onTap: () => context.push(
                _resolveInsightDeepLink(
                  deepLink: item.deepLink,
                  fallbackPath: ReportRoutes.learningReport,
                  fallbackQuery: const <String, String>{},
                  sourceChatSessionId: sourceChatSessionId,
                ),
              ),
            ),
          )
          .toList(),
      primaryLabel: '查看完整报告',
      onPrimaryTap: () {
        if (report.reportId.isNotEmpty || report.markdown.isNotEmpty) {
          unawaited(context.push(resolvedDeepLink, extra: report));
          return;
        }
        unawaited(context.push(resolvedDeepLink));
      },
      secondaryLabel: '继续在对话里',
      onSecondaryTap: () => _continueInlinePrompt(promptActions.first.prompt),
    );
  }

  Widget _buildCompactReportPreviewPill(
    BuildContext context, {
    required Map<String, dynamic> preview,
    required String? deepLink,
    required String? sourceChatSessionId,
  }) {
    final report = LearningReport.fromJson(preview);
    final resolvedDeepLink = _resolveInsightDeepLink(
      deepLink: deepLink,
      fallbackPath: ReportRoutes.learningReport,
      fallbackQuery: const <String, String>{},
      sourceChatSessionId: sourceChatSessionId,
    );
    return _buildInsightShortcutPill(
      title: '查看学习报告',
      icon: Icons.article_outlined,
      onTap: () {
        if (report.reportId.isNotEmpty || report.markdown.isNotEmpty) {
          unawaited(context.push(resolvedDeepLink, extra: report));
          return;
        }
        unawaited(context.push(resolvedDeepLink));
      },
    );
  }

  String _resolveInsightDeepLink({
    required String? deepLink,
    required String fallbackPath,
    required Map<String, String> fallbackQuery,
    required String? sourceChatSessionId,
  }) {
    final baseUri = Uri.parse(
      (deepLink?.isNotEmpty ?? false)
          ? deepLink!
          : Uri(path: fallbackPath, queryParameters: fallbackQuery).toString(),
    );
    final query = Map<String, String>.from(baseUri.queryParameters);
    if ((sourceChatSessionId?.isNotEmpty ?? false) &&
        !query.containsKey('source_chat_session_id')) {
      query['source_chat_session_id'] = sourceChatSessionId!;
    }
    return baseUri
        .replace(queryParameters: query.isEmpty ? null : query)
        .toString();
  }

  Widget _buildTimingBadge(MessageMeta? meta) {
    final durationMs = meta?.totalDurationMs ?? meta?.latencyMs;
    if (durationMs == null || durationMs <= 0) {
      return const SizedBox.shrink();
    }
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final accent = durationMs >= 60000
        ? Color.lerp(DS.warning, DS.error, 0.18) ?? DS.warning
        : durationMs >= 10000
            ? Color.lerp(DS.info, DS.brandPrimary, 0.28) ?? DS.info
            : Color.lerp(DS.success, DS.info, 0.22) ?? DS.success;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: isDark
            ? Color.alphaBlend(
                accent.withValues(alpha: 0.12),
                DS.surfaceSecondary,
              )
            : accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: accent.withValues(alpha: isDark ? 0.26 : 0.16),
        ),
        boxShadow: [
          BoxShadow(
            color: accent.withValues(alpha: isDark ? 0.1 : 0.05),
            blurRadius: 12,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.schedule_rounded,
            size: 11,
            color: accent.withValues(alpha: 0.88),
          ),
          const SizedBox(width: 4),
          Text(
            _formatDurationBadge(durationMs),
            style: TextStyle(
              fontSize: 10,
              color: isDark ? DS.textPrimary : accent.withValues(alpha: 0.96),
              fontWeight: DS.fontWeightBold,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResponseFeedbackRow(BuildContext context) {
    if (widget.message is! ChatMessageModel ||
        _responseId == null ||
        _responseId!.isEmpty ||
        widget.onResponseFeedback == null) {
      return const SizedBox.shrink();
    }

    final selection = _responseFeedbackSelection;
    final isPositive = selection == 'up';
    final isNegative = selection == 'down';

    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing8),
      child: Wrap(
        spacing: DS.spacing6,
        runSpacing: DS.spacing6,
        children: [
          _buildFeedbackChip(
            context,
            label: context.l10n.chatHelpful,
            icon: Icons.thumb_up_alt_rounded,
            selected: isPositive,
            onTap: selection == null
                ? () {
                    unawaited(
                      SensoryFeedbackService.emit(
                        SensoryFeedbackEvent.confirm,
                      ),
                    );
                    if (_responseId != null) {
                      setState(() {
                        _rememberResponseFeedbackSelection(_responseId!, 'up');
                      });
                    }
                    widget.onResponseFeedback!(
                      widget.message as ChatMessageModel,
                      'up',
                    );
                  }
                : null,
          ),
          _buildFeedbackChip(
            context,
            label: context.l10n.chatNotHelpful,
            icon: Icons.thumb_down_alt_rounded,
            selected: isNegative,
            onTap: selection == null
                ? () {
                    unawaited(
                      SensoryFeedbackService.emit(
                        SensoryFeedbackEvent.confirm,
                      ),
                    );
                    if (_responseId != null) {
                      setState(() {
                        _rememberResponseFeedbackSelection(
                          _responseId!,
                          'down',
                        );
                      });
                    }
                    widget.onResponseFeedback!(
                      widget.message as ChatMessageModel,
                      'down',
                    );
                  }
                : null,
          ),
        ],
      ),
    );
  }

  Widget _buildFeedbackChip(
    BuildContext context, {
    required String label,
    required IconData icon,
    required bool selected,
    required VoidCallback? onTap,
  }) =>
      ChatAccessoryPill(
        icon: icon,
        label: label,
        onTap: onTap,
        selected: selected,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
      );

  String _formatDurationBadge(int durationMs) {
    final seconds = durationMs / 1000.0;
    if (seconds < 1) {
      return '${durationMs}ms';
    }
    if (seconds < 10) {
      return '${seconds.toStringAsFixed(1)}s';
    }
    if (seconds < 60) {
      return '${seconds.round()}s';
    }
    final minutes = durationMs ~/ 60000;
    final remainingSeconds = (durationMs % 60000) ~/ 1000;
    if (remainingSeconds == 0) {
      return '${minutes}m';
    }
    return '${minutes}m ${remainingSeconds}s';
  }

  Widget _buildQuoteArea(
    BuildContext context,
    bool isUser,
    PrivateMessageInfo msg,
  ) {
    final backgroundColor =
        isUser ? Colors.white.withValues(alpha: 0.18) : DS.surfacePanel;
    final senderColor = isUser ? DS.textOnPrimary : DS.brandPrimary;
    final contentColor =
        isUser ? DS.textOnPrimary.withValues(alpha: 0.9) : DS.textPrimary;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(8),
        border: Border(
          left: BorderSide(
            color: isUser
                ? DS.brandPrimary.withValues(alpha: 0.7)
                : DS.brandPrimary,
            width: 3,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            msg.sender.displayName,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: senderColor,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            msg.content ?? '',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              color: contentColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRevokedPlaceholder() => Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(
            _isUser
                ? context.l10n.chatRecalledSelf
                : context.l10n.chatRecalledPeer,
            style: TextStyle(
              fontSize: 12,
              color: DS.neutral400,
            ),
          ),
        ),
      );

  Widget _buildMessageStatus() {
    if (widget.message is! PrivateMessageInfo) return const SizedBox.shrink();
    final msg = widget.message as PrivateMessageInfo;

    if (msg.isSending) {
      return const SizedBox(
        width: 12,
        height: 12,
        child: CircularProgressIndicator(strokeWidth: 1),
      );
    }
    if (msg.hasError) {
      return Icon(
        Icons.error_outline,
        color: DS.error,
        size: 14,
      );
    }

    final isRead = msg.isRead || msg.readAt != null;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          isRead ? Icons.done_all_rounded : Icons.done_rounded,
          size: 14,
          color: isRead ? DS.info : DS.neutral400,
        ),
        if (isRead)
          Padding(
            padding: const EdgeInsets.only(left: 2),
            child: Text(
              context.l10n.chatRead,
              style: TextStyle(
                fontSize: 10,
                color: DS.info,
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildAvatar(bool isUser) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    String? avatarUrl;
    var initial = 'S';

    if (_isAgent) {
      final agent = buildCommunityAgentUser(
        localizedName: context.l10n.communityAgentName,
      );
      avatarUrl = agent.avatarUrl;
      initial = 'AI';
    } else if (widget.message is ChatMessageModel) {
      initial = isUser ? 'U' : 'AI';
    } else if (widget.message is PrivateMessageInfo) {
      final msg = widget.message as PrivateMessageInfo;
      avatarUrl = msg.sender.avatarUrl;
      initial = (GraphemeUtils.graphemeAt(msg.sender.displayName, 0) ?? 'S')
          .toUpperCase();
    } else if (widget.message is MessageInfo) {
      final msg = widget.message as MessageInfo;
      avatarUrl = msg.sender?.avatarUrl;
      initial =
          (GraphemeUtils.graphemeAt(msg.sender?.displayName ?? 'S', 0) ?? 'S')
              .toUpperCase();
    }

    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        gradient: isUser ? DS.primaryGradient : DS.secondaryGradient,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: (isUser ? DS.brandPrimary : DS.brandSecondary)
                .withValues(alpha: 0.2),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Center(
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: isUser
                ? DS.brandPrimary
                : (isDark ? DS.neutral200 : DS.brandPrimary),
            shape: BoxShape.circle,
          ),
          clipBehavior: Clip.antiAlias,
          child: avatarUrl != null
              ? SparkleNetworkImage(
                  imageUrl: avatarUrl,
                  width: 32,
                  height: 32,
                  errorWidget: Center(child: Text(initial)),
                )
              : Center(
                  child: Text(
                    initial,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: isUser ? DS.onBrandPrimary : DS.onBrandPrimary,
                    ),
                  ),
                ),
        ),
      ),
    );
  }

  int? _calculateReasoningDuration(ChatMessageModel message) {
    if (message.reasoningSteps == null || message.reasoningSteps!.isEmpty) {
      return null;
    }

    // Calculate from first step to last completed step
    final firstStep = message.reasoningSteps!.first;
    final lastStep = message.reasoningSteps!.last;

    if (firstStep.createdAt != null && lastStep.completedAt != null) {
      return lastStep.completedAt!
          .difference(firstStep.createdAt!)
          .inMilliseconds;
    }

    // Fallback to summary parsing if available
    if (message.reasoningSummary != null) {
      final match =
          RegExp(r'(\d+(?:\.\d+)?)s').firstMatch(message.reasoningSummary!);
      if (match != null) {
        final seconds = double.tryParse(match.group(1)!);
        if (seconds != null) {
          return (seconds * 1000).toInt();
        }
      }
    }

    return null;
  }

  /// Get the material for AI message bubbles with proper contrast in dark mode
  ///
  /// Dark mode: Uses a lighter gray (#2A2A2A) for better contrast
  /// Light mode: Uses standard ceramic material
  SparkleMaterial _getAIMessageMaterial(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (isDark) {
      final darkSurface = Color.alphaBlend(
        DS.neutral200.withValues(alpha: 0.08),
        DS.surfaceSecondary,
      );
      return SparkleMaterial(
        backgroundColor: darkSurface,
        borderColor: DS.border.withValues(alpha: 0.72),
        glowColor: Colors.white.withValues(alpha: 0.04),
      );
    }

    // Light mode: use neutral100 for the AI bubble
    return SparkleMaterial(
      backgroundColor: Color.alphaBlend(
        DS.brandPrimary.withValues(alpha: 0.025),
        DS.neutral100,
      ),
      borderColor: DS.border.withValues(alpha: 0.42),
      glowColor: DS.brandPrimary.withValues(alpha: 0.06),
    );
  }

  Widget _buildHeartAnimation(BuildContext context) {
    if (context.reduceMotion) {
      return Icon(Icons.favorite, color: DS.error, size: 48);
    }
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: const Duration(milliseconds: 500),
      curve: Curves.elasticOut,
      builder: (context, value, child) => Transform.scale(
        scale: value,
        child: Icon(
          Icons.favorite,
          color: DS.error,
          size: 48,
          shadows: [
            Shadow(
              blurRadius: 10,
              color: DS.brandPrimary26,
              offset: const Offset(0, 4),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmGeneratedTasks({
    required String toolResultId,
    String? planId,
  }) async {
    try {
      final result = await ref
          .read(taskRepositoryProvider)
          .confirmGeneratedTasks(toolResultId);
      if (!mounted) return;
      unawaited(ref.read(taskListProvider.notifier).refreshTasks());
      unawaited(ref.read(planListProvider.notifier).refresh());

      final countRaw = result['count'];
      final count = countRaw is num
          ? countRaw.toInt()
          : int.tryParse(countRaw?.toString() ?? '') ?? 1;
      final actionLabel = planId != null ? '查看计划' : '去任务列表';
      final route = planId != null ? '/plans/$planId' : '/tasks';
      AppFeedback.undoable(
        context: context,
        message: '已确认 $count 个任务，开始执行！',
        actionLabel: actionLabel,
        onAction: () => context.push(route),
      );
    } catch (e) {
      if (!mounted) return;
      AppFeedback.error(context, '确认失败: $e');
      rethrow;
    }
  }

  // ============================================================
  // Share Card Support for Private Messages
  // ============================================================

  /// Check if private message is a share message
  bool _isShareMessage() {
    if (widget.message is! PrivateMessageInfo) return false;
    final msg = widget.message as PrivateMessageInfo;
    return msg.messageType != MessageType.text && msg.contentData != null;
  }

  /// Get shareable content type from message type
  ShareableContentType? _getShareContentType(
    MessageType messageType,
    Map<String, dynamic> data,
  ) {
    if (messageType == MessageType.capsuleShare &&
        data['resource_type']?.toString() == 'knowledge_node') {
      return ShareableContentType.knowledgeNode;
    }
    return switch (messageType) {
      MessageType.taskShare => ShareableContentType.taskCompletion,
      MessageType.planShare => ShareableContentType.planProgress,
      MessageType.capsuleShare => ShareableContentType.capsule,
      MessageType.prismShare => ShareableContentType.cognitivePrism,
      MessageType.achievement => ShareableContentType.achievement,
      _ => null,
    };
  }

  /// Build share card for private message
  Widget? _buildPrivateShareCard() {
    if (widget.message is! PrivateMessageInfo) return null;
    final msg = widget.message as PrivateMessageInfo;
    final data = msg.contentData ?? {};

    final contentType = _getShareContentType(msg.messageType, data);
    if (contentType == null) return null;

    final sharedResourceId = data['shared_resource_id']?.toString();
    // resource_meta contains task/plan specific fields (progress, estimated_minutes, etc.)
    // Fall back to data itself for non-task/plan types (capsule, prism, achievement)
    final meta = (data['resource_meta'] as Map<String, dynamic>?) ?? data;
    final payload = UniversalSharePayload(
      contentType: contentType,
      resourceId: _getResourceId(msg.messageType, data),
      title: _getShareTitle(msg.messageType, data, msg.content),
      subtitle: _getShareSubtitle(msg.messageType, data),
      metadata: meta,
    );

    return ShareCardFactory.fromPayload(
      payload,
      onTap: () => _handleShareCardTap(payload),
      sharedResourceId: sharedResourceId,
      onAdopt: sharedResourceId == null ||
              (contentType != ShareableContentType.taskCompletion &&
                  contentType != ShareableContentType.planProgress)
          ? null
          : () => _handleAdopt(
                context,
                sharedResourceId,
                contentType == ShareableContentType.planProgress
                    ? 'plan'
                    : 'task',
              ),
    );
  }

  Future<void> _handleAdopt(
    BuildContext context,
    String sharedResourceId,
    String resourceType,
  ) async {
    if (sharedResourceId.trim().isEmpty) {
      AppFeedback.error(context, '分享资源 ID 无效，无法采纳');
      return;
    }
    try {
      final result = await ref
          .read(communityShareRepositoryProvider)
          .adoptResource(sharedResourceId: sharedResourceId);
      if (!context.mounted) return;
      AppFeedback.success(context, '已采纳，跳转中...');
      final entityCard = result['entity_card'] is Map<String, dynamic>
          ? EntityCardPayload.fromRaw(
              {'entity_card': result['entity_card'] as Map<String, dynamic>},
              fallbackType: resourceType,
            )
          : null;
      final actualResourceType =
          result['resource_type']?.toString() ?? resourceType;
      final newId = result['new_resource_id']?.toString();
      final route = entityCard?.detailRoute ??
          (newId == null
              ? null
              : actualResourceType == 'plan'
                  ? '/plans/$newId'
                  : '/tasks/$newId');
      if (actualResourceType == 'plan') {
        unawaited(ref.read(planListProvider.notifier).refresh());
      } else if (actualResourceType == 'task') {
        unawaited(ref.read(taskListProvider.notifier).refreshTasks());
      }
      if (route != null && route.isNotEmpty) {
        unawaited(context.push(route));
      }
    } catch (e) {
      if (!context.mounted) return;
      AppFeedback.error(context, '采纳失败: $e');
    }
  }

  /// Get resource ID from content data based on message type
  String _getResourceId(MessageType type, Map<String, dynamic> data) {
    // 安全地将各种数值类型转换为字符串
    String safeGetString(dynamic value) {
      if (value == null) return '';
      if (value is String) return value;
      return value.toString();
    }

    String preferFirstNonEmpty(dynamic primary, dynamic fallback) {
      final primaryValue = safeGetString(primary);
      if (primaryValue.isNotEmpty) return primaryValue;
      return safeGetString(fallback);
    }

    return switch (type) {
      MessageType.taskShare => safeGetString(data['resource_id']),
      MessageType.planShare => safeGetString(data['resource_id']),
      MessageType.capsuleShare =>
        preferFirstNonEmpty(data['resource_id'], data['capsule_id']),
      MessageType.prismShare => safeGetString(data['prism_id']),
      MessageType.achievement => safeGetString(data['achievement_id']),
      _ => '',
    };
  }

  /// Get share title from content data
  String _getShareTitle(
    MessageType type,
    Map<String, dynamic> data,
    String? fallbackContent,
  ) {
    // 安全地将各种数值类型转换为字符串
    String? safeGetString(dynamic value) {
      if (value == null) return null;
      if (value is String) return value.isEmpty ? null : value;
      return value.toString();
    }

    final title = switch (type) {
      MessageType.taskShare => safeGetString(data['resource_title']),
      MessageType.planShare => safeGetString(data['resource_title']),
      MessageType.capsuleShare =>
        safeGetString(data['resource_title']) ?? safeGetString(data['title']),
      MessageType.prismShare =>
        safeGetString(data['resource_title']) ?? safeGetString(data['title']),
      MessageType.achievement => safeGetString(data['name']),
      _ => null,
    };
    return title ?? fallbackContent ?? '';
  }

  /// Get share subtitle from content data
  String? _getShareSubtitle(MessageType type, Map<String, dynamic> data) {
    // 安全地将数值类型转换为字符串
    String? safeGetString(dynamic value) {
      if (value == null) return null;
      if (value is String) return value.isEmpty ? null : value;
      return value.toString();
    }

    // 安全地将数值转换为 double
    double? safeGetDouble(dynamic value) {
      if (value == null) return null;
      if (value is double) return value;
      if (value is num) return value.toDouble();
      return null;
    }

    // 安全地将数值转换为 int
    int? safeGetInt(dynamic value) {
      if (value == null) return null;
      if (value is int) return value;
      if (value is num) return value.toInt();
      return null;
    }

    final meta = (data['resource_meta'] as Map<String, dynamic>?) ?? {};
    return switch (type) {
      MessageType.taskShare => () {
          final duration = safeGetInt(meta['estimated_minutes']) ?? 0;
          return duration > 0 ? '已完成 · $duration分钟' : '已完成';
        }(),
      MessageType.planShare => () {
          final progress = safeGetDouble(meta['progress']);
          return progress != null
              ? '进度: ${(progress * 100).toStringAsFixed(0)}%'
              : null;
        }(),
      MessageType.capsuleShare => safeGetString(data['resource_summary']) ??
          safeGetString(data['summary']),
      MessageType.prismShare => safeGetString(data['resource_summary']) ??
          safeGetString(data['insight']),
      MessageType.achievement => safeGetString(data['description']),
      _ => null,
    };
  }

  /// Handle share card tap - navigate to resource
  void _handleShareCardTap(UniversalSharePayload payload) {
    final deepLink = payload.deepLink;
    if (deepLink.isNotEmpty) {
      DeepLinkService.handleDeepLink(context, deepLink);
    }
  }
}

class _InsightLinkCard extends StatelessWidget {
  const _InsightLinkCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.bullets,
    required this.onTap,
    this.caption,
    this.badgeLabel,
    this.promptActions = const [],
    this.actionButtons = const [],
    this.primaryLabel,
    this.onPrimaryTap,
    this.secondaryLabel,
    this.onSecondaryTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final List<String> bullets;
  final VoidCallback onTap;
  final String? caption;
  final String? badgeLabel;
  final List<_InlinePromptAction> promptActions;
  final List<_InlineActionButton> actionButtons;
  final String? primaryLabel;
  final VoidCallback? onPrimaryTap;
  final String? secondaryLabel;
  final VoidCallback? onSecondaryTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: DS.brandPrimary.withValues(alpha: 0.14),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, size: 18, color: DS.brandPrimary),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 13,
                      ),
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded, size: 16),
                ],
              ),
              if (caption != null && caption!.isNotEmpty) ...[
                const SizedBox(height: DS.spacing6),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.info.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    caption!,
                    style: TextStyle(
                      color: DS.info,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
              if (badgeLabel != null && badgeLabel!.isNotEmpty) ...[
                const SizedBox(height: DS.spacing6),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    badgeLabel!,
                    style: TextStyle(
                      color: DS.brandPrimary,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: DS.spacing4),
              Text(
                subtitle,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: DS.textSecondary,
                  fontSize: 12,
                ),
              ),
              if (bullets.isNotEmpty) ...[
                const SizedBox(height: DS.spacing6),
                ...bullets.take(2).map(
                      (line) => Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          '• $line',
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 11.5),
                        ),
                      ),
                    ),
              ],
              if (actionButtons.isNotEmpty) ...[
                const SizedBox(height: DS.spacing8),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: actionButtons
                      .map(
                        (item) => FilledButton.tonalIcon(
                          onPressed: item.onTap,
                          icon:
                              const Icon(Icons.arrow_outward_rounded, size: 16),
                          label: Text(item.label),
                        ),
                      )
                      .toList(),
                ),
              ],
              if (promptActions.isNotEmpty) ...[
                const SizedBox(height: DS.spacing8),
                Text(
                  '继续在对话里',
                  style: TextStyle(
                    color: DS.textSecondary,
                    fontSize: 11.5,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const SizedBox(height: DS.spacing6),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: promptActions
                      .map(
                        (item) => ActionChip(
                          avatar: const Icon(
                            Icons.chat_bubble_outline_rounded,
                            size: 16,
                          ),
                          label: Text(item.label),
                          onPressed: item.onTap,
                        ),
                      )
                      .toList(),
                ),
              ],
              if ((primaryLabel ?? '').isNotEmpty ||
                  (secondaryLabel ?? '').isNotEmpty) ...[
                const SizedBox(height: DS.spacing8),
                Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    if ((primaryLabel ?? '').isNotEmpty && onPrimaryTap != null)
                      FilledButton.icon(
                        onPressed: onPrimaryTap,
                        icon: const Icon(Icons.open_in_new_rounded, size: 16),
                        label: Text(primaryLabel!),
                      ),
                    if ((secondaryLabel ?? '').isNotEmpty &&
                        onSecondaryTap != null)
                      OutlinedButton.icon(
                        onPressed: onSecondaryTap,
                        icon: const Icon(Icons.forum_rounded, size: 16),
                        label: Text(secondaryLabel!),
                      ),
                  ],
                ),
              ],
            ],
          ),
        ),
      );
}

class _InlinePromptAction {
  const _InlinePromptAction({
    required this.label,
    required this.prompt,
    this.onTap,
  });

  final String label;
  final String prompt;
  final VoidCallback? onTap;
}

class _InlineActionButton {
  const _InlineActionButton({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;
}

Color _chatBubbleHexToColor(String hex, BuildContext context) {
  final cleaned = hex.replaceFirst('#', '');
  final normalized = cleaned.length == 6 ? 'FF$cleaned' : cleaned;
  return Color(int.tryParse(normalized, radix: 16) ?? 0xFF6B7280);
}

String _formatAgentLabel(String raw) {
  final l10n = I18nService.instance.l10n;
  switch (raw) {
    case 'galaxy_guide':
      return l10n.chatAgentNavigator;
    case 'exam_oracle':
      return l10n.chatAgentExamStrategist;
    case 'time_tutor':
      return l10n.chatAgentTimeCoach;
    case 'deep_analyst':
      return l10n.chatAgentDeepAnalyst;
    case 'error_analyst':
      return l10n.chatAgentCorrectionExpert;
    case 'study_buddy':
      return l10n.chatAgentLearningBuddy;
    case 'math_agent':
      return l10n.chatAgentMathExpert;
    case 'code_agent':
      return l10n.chatAgentCodingExpert;
    case 'writing_agent':
      return l10n.chatAgentWritingExpert;
    case 'science_agent':
      return l10n.chatAgentScienceExpert;
    case 'search_agent':
      return l10n.chatAgentSearchExpert;
    default:
      return raw.replaceAll('_', ' ').trim();
  }
}

String _formatCollaborationModeLabel(String? mode) {
  final l10n = I18nService.instance.l10n;
  switch ((mode ?? '').trim()) {
    case 'parallel':
      return l10n.chatCollabParallel;
    case 'debate':
      return l10n.chatCollabDebate;
    case 'delegation':
      return l10n.chatCollabDelegation;
    case 'sequential':
      return l10n.chatCollabSequential;
    default:
      return l10n.chatCollabExpert;
  }
}

class _CollaborationSignatureCard extends StatelessWidget {
  const _CollaborationSignatureCard({
    required this.agentIds,
    required this.activitySnapshots,
    this.narrative,
    this.collaborationMode,
  });

  final String? narrative;
  final String? collaborationMode;
  final List<String> agentIds;
  final List<Map<String, dynamic>> activitySnapshots;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final chips = _buildChips(context);
    return Container(
      padding: const EdgeInsets.all(DS.spacing10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: theme.colorScheme.outlineVariant.withValues(alpha: 0.32),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.auto_awesome_rounded,
                size: 14,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: DS.spacing6),
              Text(
                _formatCollaborationModeLabel(collaborationMode),
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
          if (chips.isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing6,
              runSpacing: DS.spacing6,
              children: chips,
            ),
          ],
          if (narrative != null && narrative!.trim().isNotEmpty) ...[
            const SizedBox(height: DS.spacing8),
            Text(
              narrative!,
              style: TextStyle(
                fontSize: 11,
                height: 1.45,
                color: theme.colorScheme.onSurface,
              ),
            ),
          ],
        ],
      ),
    );
  }

  List<Widget> _buildChips(BuildContext context) {
    final seen = <String>{};
    final widgets = <Widget>[];
    for (final agentId in agentIds) {
      final normalized = agentId.trim();
      if (normalized.isEmpty || !seen.add(normalized)) {
        continue;
      }
      final snapshot =
          activitySnapshots.cast<Map<String, dynamic>?>().firstWhere(
                (item) => item?['agent_id']?.toString() == normalized,
                orElse: () => null,
              );
      final label = snapshot?['display_name']?.toString() ??
          _formatAgentLabel(normalized);
      final color = _chatBubbleHexToColor(
        snapshot?['color']?.toString() ?? '#6B7280',
        context,
      );
      widgets.add(
        ChatAccessoryPill(
          icon: Icons.person_outline_rounded,
          label: label,
          accentColor: color,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing6,
          ),
        ),
      );
    }
    return widgets;
  }
}
