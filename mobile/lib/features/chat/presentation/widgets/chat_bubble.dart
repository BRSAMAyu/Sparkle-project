import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/action_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_reasoning_bubble_v2.dart';
import 'package:sparkle/features/chat/presentation/widgets/agent_workflow_panel.dart';
import 'package:sparkle/features/chat/presentation/widgets/assistant_message_metadata_tray.dart';
import 'package:sparkle/features/chat/presentation/widgets/message_detail_view.dart';
import 'package:sparkle/features/chat/presentation/widgets/mode_suggestion_card.dart';
import 'package:sparkle/features/chat/presentation/widgets/orchestration_trace_panel.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/providers/community_agent_provider.dart';
import 'package:url_launcher/url_launcher.dart';

const _chatContentFontFallback = <String>[
  'PingFang SC',
  'Hiragino Sans GB',
  'Heiti SC',
  'Noto Sans SC',
  'Noto Sans CJK SC',
  'Source Han Sans SC',
  'Microsoft YaHei',
  'Arial Unicode MS',
];

class ChatBubble extends StatefulWidget {
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
  final bool isLatestAssistantMessage;

  @override
  State<ChatBubble> createState() => _ChatBubbleState();
}

class _ChatBubbleState extends State<ChatBubble> with TickerProviderStateMixin {
  late AnimationController _entryController;
  late Animation<double> _scale;
  late Animation<Offset> _position;

  bool _showHeart = false;
  bool _isPressed = false;

  @override
  void initState() {
    super.initState();
    _entryController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );

    _scale = Tween<double>(begin: 0.9, end: 1.0).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.elasticOut),
    );

    _position = Tween<Offset>(
      begin: const Offset(0, 0.5),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(parent: _entryController, curve: Curves.easeOutQuart),
    );

    unawaited(_entryController.forward());
  }

  @override
  void dispose() {
    _entryController.dispose();
    super.dispose();
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

  bool get _shouldUseMarkdown => _hasStrongMarkdownSyntax(_content);

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
            return false;
          default:
            return true;
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

    // Allow revocation within 24 hours for user messages
    final canRevoke =
        _isUser && DateTime.now().difference(_createdAt).inHours < 24;

    unawaited(
      showModalBottomSheet<void>(
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
                if (!_isUser &&
                    _responseId != null &&
                    _responseId!.isNotEmpty &&
                    widget.onResponseFeedback != null &&
                    widget.message is ChatMessageModel)
                  ListTile(
                    leading: const Icon(Icons.thumb_up_alt_rounded),
                    title: const Text('有帮助'),
                    onTap: () {
                      Navigator.pop(context);
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
                    title: const Text('没帮助'),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onResponseFeedback!(
                        widget.message as ChatMessageModel,
                        'down',
                      );
                    },
                  ),
                if (widget.onQuote != null &&
                    widget.message is PrivateMessageInfo)
                  ListTile(
                    leading: const Icon(Icons.format_quote_rounded),
                    title: const Text('引用'),
                    onTap: () {
                      if (mounted) {
                        Navigator.pop(context);
                        widget.onQuote!(widget.message);
                      }
                    },
                  ),
                ListTile(
                  leading: const Icon(Icons.copy_rounded),
                  title: const Text('复制'),
                  onTap: () {
                    unawaited(
                      Clipboard.setData(ClipboardData(text: _content)),
                    );
                    if (mounted) {
                      Navigator.pop(context);
                      AppFeedback.info(context, '已复制到剪贴板');
                    }
                  },
                ),
                if (canRevoke && widget.onRevoke != null)
                  ListTile(
                    leading: Icon(Icons.undo_rounded, color: DS.error),
                    title: Text('撤销', style: TextStyle(color: DS.error)),
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

  @override
  Widget build(BuildContext context) {
    if (_isRevoked) return _buildRevokedPlaceholder();

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
    final agentsInvolved = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).agentsInvolved
        : const <String>[];
    final agentActivities = widget.message is ChatMessageModel
        ? (widget.message as ChatMessageModel).agentActivities
        : const <Map<String, dynamic>>[];
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
                                            DS.brandPrimary,
                                            DS.brandPrimary
                                                .withValues(alpha: 0.85),
                                          ],
                                        ),
                                        shadows: [
                                          BoxShadow(
                                            color: DS.brandPrimary
                                                .withValues(alpha: 0.2),
                                            blurRadius: 4,
                                            offset: const Offset(0, 2),
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
                                    if (widget.message is ChatMessageModel &&
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
                                    // Use constrained height for long messages
                                    LayoutBuilder(
                                      builder: (context, constraints) {
                                        // Calculate max height based on screen size
                                        final maxHeight =
                                            MediaQuery.of(context).size.height *
                                                0.5;
                                        final contentWidget = _shouldUseMarkdown
                                            ? MarkdownBody(
                                                data: _content,
                                                styleSheet: _getMarkdownStyle(
                                                  context,
                                                  isUser,
                                                ),
                                                onTapLink:
                                                    (text, href, title) async {
                                                  if (href == null) return;
                                                  final uri =
                                                      Uri.tryParse(href);
                                                  if (uri == null) return;

                                                  final scheme =
                                                      uri.scheme.toLowerCase();
                                                  const allowedSchemes = [
                                                    'http',
                                                    'https',
                                                  ];
                                                  if (!allowedSchemes
                                                      .contains(scheme)) {
                                                    return;
                                                  }

                                                  try {
                                                    if (await canLaunchUrl(
                                                      uri,
                                                    )) {
                                                      unawaited(
                                                        launchUrl(
                                                          uri,
                                                          mode: LaunchMode
                                                              .externalApplication,
                                                        ),
                                                      );
                                                    }
                                                  } catch (e) {
                                                    debugPrint(
                                                      'Failed to launch URL: $e',
                                                    );
                                                  }
                                                },
                                              )
                                            : Text(
                                                _content,
                                                style: TextStyle(
                                                  color: isUser
                                                      ? DS.chatBubbleUserText
                                                      : DS.chatBubbleOtherText,
                                                  fontSize: 16,
                                                  height: 1.5,
                                                  fontFamilyFallback:
                                                      _chatContentFontFallback,
                                                ),
                                              );

                                        // Try to estimate content height and decide if scrolling is needed
                                        // For long content (heuristic: >500 chars), use constrained scrollable
                                        final shouldConstrain =
                                            _content.length > 500;

                                        if (!shouldConstrain) {
                                          return contentWidget;
                                        }

                                        return SizedBox(
                                          height: maxHeight,
                                          child: SingleChildScrollView(
                                            physics:
                                                const ClampingScrollPhysics(),
                                            child: contentWidget,
                                          ),
                                        );
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            if (_metadataWidgets.isNotEmpty ||
                                (widget.message is ChatMessageModel &&
                                    (widget.message as ChatMessageModel)
                                            .aiStatus !=
                                        null))
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
                                  onWidgetAction: widget.onWidgetAction,
                                ),
                              ),
                            if (!isUser && modeSuggestion != null)
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
                            if (!isUser && orchestrationTrace != null)
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
                            if (!isUser &&
                                agentActivities.isEmpty &&
                                ((collaborationNarrative != null &&
                                        collaborationNarrative.isNotEmpty) ||
                                    agentsInvolved.isNotEmpty))
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
                            if (!isUser && agentActivities.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(
                                  top: 8.0,
                                  right: 8.0,
                                  left: 8.0,
                                ),
                                child: AgentWorkflowPanel(
                                  snapshotActivities: agentActivities,
                                  narrative: collaborationNarrative,
                                ),
                              ),
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
                                    onWidgetAction: widget.onWidgetAction,
                                  ),
                                );
                              },
                            ),
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
      return bubble;
    }

    return SlideTransition(
      position: _position,
      child: ScaleTransition(
        scale: _scale,
        child: bubble,
      ),
    );
  }

  double _bubbleMaxWidth(BuildContext context) {
    final screenWidth = ResponsiveSystem.width(context);
    final contentMaxWidth = ContentConstraintSystem.maxWidth(context);
    final baseMax = contentMaxWidth.isFinite ? contentMaxWidth : screenWidth;
    return min(screenWidth * 0.72, baseMax * 0.9);
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
            _isUser ? '你撤回了一条消息' : '对方撤回了一条消息',
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
              '已读',
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
    var initial = '?';

    if (_isAgent) {
      final agent = buildCommunityAgentUser();
      avatarUrl = agent.avatarUrl;
      initial = 'AI';
    } else if (widget.message is ChatMessageModel) {
      initial = isUser ? 'U' : 'AI';
    } else if (widget.message is PrivateMessageInfo) {
      final msg = widget.message as PrivateMessageInfo;
      avatarUrl = msg.sender.avatarUrl;
      initial = msg.sender.displayName[0].toUpperCase();
    } else if (widget.message is MessageInfo) {
      final msg = widget.message as MessageInfo;
      avatarUrl = msg.sender?.avatarUrl;
      initial = (msg.sender?.displayName ?? 'S')[0].toUpperCase();
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
              ? Image.network(
                  avatarUrl,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Center(child: Text(initial)),
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

  MarkdownStyleSheet _getMarkdownStyle(BuildContext context, bool isUser) =>
      MarkdownStyleSheet(
        p: TextStyle(
          color: isUser ? DS.chatBubbleUserText : DS.chatBubbleOtherText,
          fontSize: 16,
          height: 1.4,
          fontFamilyFallback: _chatContentFontFallback,
        ),
        h1: TextStyle(
          color: isUser ? DS.chatBubbleUserText : DS.chatBubbleOtherText,
          fontSize: 24,
          fontWeight: FontWeight.bold,
          fontFamilyFallback: _chatContentFontFallback,
        ),
        code: TextStyle(
          backgroundColor: isUser
              ? DS.chatBubbleUserText.withValues(alpha: 0.2)
              : DS.surfaceTertiary,
          fontFamily: 'monospace',
          fontSize: 14,
          color: isUser ? DS.chatBubbleUserText : DS.brandSecondary,
        ),
        codeblockDecoration: BoxDecoration(
          color: isUser
              ? DS.chatBubbleUserText.withValues(alpha: 0.1)
              : DS.surfaceTertiary,
          borderRadius: BorderRadius.circular(12),
        ),
        a: TextStyle(
          color: isUser ? DS.chatBubbleUserText : DS.brandPrimary,
          decoration: TextDecoration.underline,
          fontFamilyFallback: _chatContentFontFallback,
        ),
      );

  bool _hasStrongMarkdownSyntax(String content) {
    if (content.isEmpty) {
      return false;
    }

    final trimmed = content.trim();
    final strongPatterns = <RegExp>[
      RegExp(r'(^|\n)#{1,6}\s', multiLine: true),
      RegExp('```'),
      RegExp(r'`[^`\n]+`'),
      RegExp(r'\[[^\]]+\]\([^)]+\)'),
      RegExp(r'(^|\n)>\s', multiLine: true),
      RegExp(r'(^|\n)\|.+\|', multiLine: true),
      RegExp(r'(\*\*|__)[^*_]+(\*\*|__)'),
    ];

    return strongPatterns.any((pattern) => pattern.hasMatch(trimmed));
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
        borderColor: DS.border.withValues(alpha: 0.8),
      );
    }

    // Light mode: use neutral100 for the AI bubble
    return SparkleMaterial(
      backgroundColor: DS.neutral100,
      glowColor: DS.brandPrimary.withValues(alpha: 0.1),
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
}

Color _chatBubbleHexToColor(String hex, BuildContext context) {
  final cleaned = hex.replaceFirst('#', '');
  final normalized = cleaned.length == 6 ? 'FF$cleaned' : cleaned;
  return Color(int.tryParse(normalized, radix: 16) ?? 0xFF6B7280);
}

String _formatAgentLabel(String raw) {
  switch (raw) {
    case 'galaxy_guide':
      return '星图导航';
    case 'exam_oracle':
      return '考试策略师';
    case 'time_tutor':
      return '时间教练';
    case 'deep_analyst':
      return '深度分析师';
    case 'error_analyst':
      return '纠错专家';
    case 'study_buddy':
      return '学伴';
    case 'math_agent':
      return '数学专家';
    case 'code_agent':
      return '编程专家';
    case 'writing_agent':
      return '写作专家';
    case 'science_agent':
      return '理科专家';
    case 'search_agent':
      return '搜索专家';
    default:
      return raw.replaceAll('_', ' ').trim();
  }
}

String _formatCollaborationModeLabel(String? mode) {
  switch ((mode ?? '').trim()) {
    case 'parallel':
      return '并行协作';
    case 'debate':
      return '辩论协作';
    case 'delegation':
      return '委派协作';
    case 'sequential':
      return '分步协作';
    default:
      return '专家协作';
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
      final snapshot = activitySnapshots.cast<Map<String, dynamic>?>().firstWhere(
        (item) => item?['agent_id']?.toString() == normalized,
        orElse: () => null,
      );
      final label = snapshot?['display_name']?.toString() ?? _formatAgentLabel(normalized);
      final color = _chatBubbleHexToColor(
        snapshot?['color']?.toString() ?? '#6B7280',
        context,
      );
      widgets.add(
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing8,
            vertical: DS.spacing4,
          ),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: color.withValues(alpha: 0.18)),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ),
      );
    }
    return widgets;
  }
}
