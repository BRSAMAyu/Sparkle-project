import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/data/models/user_model.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/chat/ai_status_indicator.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';

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

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            if (_avatarUrl != null)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: SparkleAvatar(radius: 16, url: _avatarUrl, fallbackText: _displayName),
              ),
            Text(_displayName ?? '聊天'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () => _showSearchSheet(context, notifier),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: chatState.when(
              data: (messages) {
                final mergedMessages = _mergeMessages(messages, agentState, currentUser);
                final showAgentStatus = agentState.isSending && agentState.streamingContent.isEmpty;

                if (mergedMessages.isEmpty) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.chat_bubble_outline, size: 48, color: DS.neutral300),
                        const SizedBox(height: DS.lg),
                        Text('开始对话吧!', style: TextStyle(color: DS.neutral500)),
                      ],
                    ),
                  );
                }
                return ListView.builder(
                  reverse: true,
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 16),
                  itemCount: mergedMessages.length + (showAgentStatus ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (showAgentStatus && index == 0) {
                      return const Padding(
                        padding: EdgeInsets.only(bottom: DS.md),
                        child: AiStatusIndicator(
                          status: 'THINKING',
                          details: 'AI助手正在整理思路...',
                        ),
                      );
                    }

                    final messageIndex = showAgentStatus ? index - 1 : index;
                    final message = mergedMessages[messageIndex];
                    final isAgent = isPrivateAgentMessage(message);
                    return ChatBubble(
                      message: message,
                      currentUserId: currentUser?.id,
                      onQuote: isAgent ? null : (msg) => setState(() => notifier.setQuote(msg)),
                      onRevoke: isAgent ? null : (msg) => notifier.revokeMessage(msg.id),
                      onEdit: isAgent ? null : (msg, content) => notifier.editMessage(msg.id, content),
                      onReaction: isAgent ? null : (msg, emoji) => notifier.toggleReaction(msg.id, emoji),
                    );
                  },
                );
              },
              loading: () => const Center(child: LoadingIndicator()),
              error: (e, s) => Center(
                child: CustomErrorWidget.page(
                  message: e.toString(),
                  onRetry: () => ref.read(privateChatProvider(widget.friendId).notifier).loadMessages(),
                ),
              ),
            ),
          ),
          if (agentState.error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: DS.lg, vertical: DS.sm),
              child: Text(
                agentState.error!,
                style: TextStyle(color: DS.error, fontSize: 12),
              ),
            ),
          _buildAgentToolbar(
            context,
            agentState: agentState,
            messages: chatState.valueOrNull ?? const [],
          ),
          ChatInput(
            enabled: !_agentMode || !agentState.isSending,
            hintText: _agentMode ? '让AI帮你想回复' : '输入消息...',
            quotedMessage: _agentMode ? null : notifier.quotedMessage,
            onCancelQuote: () => setState(() => notifier.setQuote(null)),
            onSend: (text, {replyToId}) {
              if (_agentMode) {
                _sendAgentPrompt(
                  prompt: text,
                  agentState: agentState,
                  messages: chatState.valueOrNull ?? const [],
                );
                return;
              }
              notifier.sendMessage(content: text, replyToId: replyToId);
            },
          ),
        ],
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
      merged.add(_buildStreamingAgentMessage(agentState.streamingContent, currentUser));
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

  PrivateMessageInfo _buildStreamingAgentMessage(String content, UserModel? currentUser) => PrivateMessageInfo(
        id: 'agent_streaming_${DateTime.now().millisecondsSinceEpoch}',
        sender: buildCommunityAgentUser(),
        receiver: _currentUserBrief(currentUser),
        messageType: MessageType.text,
        content: content,
        contentData: {kAgentMetadataKey: true, 'agent_streaming': true},
        isRead: true,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

  UserBrief _currentUserBrief(UserModel? user) => UserBrief(
        id: user?.id ?? 'guest',
        username: user?.username ?? 'guest',
        nickname: user?.nickname ?? user?.username ?? '访客',
        avatarUrl: user?.avatarUrl,
        flameLevel: user?.flameLevel ?? 1,
        flameBrightness: user?.flameBrightness ?? 0.4,
        status: user?.status ?? UserStatus.online,
      );

  void _sendAgentPrompt({
    required String prompt,
    required AgentChatState<PrivateMessageInfo> agentState,
    required List<PrivateMessageInfo> messages,
  }) {
    if (agentState.isSending) return;
    ref.read(privateChatAgentProvider(widget.friendId).notifier).sendAgentMessage(
          prompt: prompt,
          friendName: _displayName ?? widget.friendName,
          recentMessages: messages,
        );
  }

  Widget _buildAgentToolbar(
    BuildContext context, {
    required AgentChatState<PrivateMessageInfo> agentState,
    required List<PrivateMessageInfo> messages,
  }) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.sm, DS.lg, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              FilterChip(
                selected: _agentMode,
                label: Text(_agentMode ? 'AI回复助手' : 'AI助手'),
                avatar: Icon(Icons.auto_awesome, size: 16, color: _agentMode ? DS.brandPrimary : DS.neutral500),
                onSelected: (value) {
                  setState(() {
                    _agentMode = value;
                    if (_agentMode) {
                      ref.read(privateChatProvider(widget.friendId).notifier).setQuote(null);
                    }
                  });
                },
              ),
              const SizedBox(width: DS.md),
              if (_agentMode)
                Text(
                  '仅你可见',
                  style: TextStyle(fontSize: 12, color: DS.neutral500),
                ),
              const Spacer(),
              if (agentState.isSending)
                Text(
                  'AI处理中...',
                  style: TextStyle(fontSize: 12, color: DS.brandPrimary70),
                ),
            ],
          ),
          if (_agentMode)
            Padding(
              padding: const EdgeInsets.only(top: DS.sm),
              child: Wrap(
                spacing: DS.sm,
                runSpacing: DS.xs,
                children: [
                  _AgentQuickChip(
                    label: '帮我回复',
                    onTap: () => _sendAgentPrompt(
                      prompt: '根据最近对话，帮我生成一条自然、有礼貌的回复。',
                      agentState: agentState,
                      messages: messages,
                    ),
                  ),
                  _AgentQuickChip(
                    label: '润色语气',
                    onTap: () => _sendAgentPrompt(
                      prompt: '请将我想说的话润色得更友好、更简洁。',
                      agentState: agentState,
                      messages: messages,
                    ),
                  ),
                  _AgentQuickChip(
                    label: '给出建议',
                    onTap: () => _sendAgentPrompt(
                      prompt: '根据这段对话，给我2个沟通建议或下一步思路。',
                      agentState: agentState,
                      messages: messages,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _AgentQuickChip extends StatelessWidget {
  const _AgentQuickChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
        label: Text(label, style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
        backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
        onPressed: onTap,
      );
}

Future<void> _showSearchSheet(BuildContext context, PrivateChatNotifier notifier) async {
  final controller = TextEditingController();
  List<PrivateMessageInfo> results = [];
  bool isLoading = false;

  try {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => DecoratedBox(
          decoration: BoxDecoration(
            color: Theme.of(context).scaffoldBackgroundColor,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: SafeArea(
            top: false,
            child: Padding(
              padding: EdgeInsets.only(
                left: DS.lg,
                right: DS.lg,
                top: DS.lg,
                bottom: MediaQuery.of(context).viewInsets.bottom + DS.lg,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 36,
                    height: 4,
                    decoration: BoxDecoration(
                      color: DS.neutral300,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  const SizedBox(height: DS.md),
                  TextField(
                    controller: controller,
                    decoration: const InputDecoration(
                      hintText: '搜索私信',
                      prefixIcon: Icon(Icons.search),
                    ),
                    onSubmitted: (value) async {
                      if (value.trim().isEmpty) return;
                      setState(() => isLoading = true);
                      results = await notifier.searchMessages(value.trim());
                      setState(() => isLoading = false);
                    },
                  ),
                  const SizedBox(height: DS.md),
                  if (isLoading) const LoadingIndicator(),
                  if (!isLoading)
                    SizedBox(
                      height: 280,
                      child: ListView.builder(
                        itemCount: results.length,
                        itemBuilder: (context, index) {
                          final msg = results[index];
                          return ListTile(
                            title: Text(msg.content ?? '消息'),
                            subtitle: Text('${msg.sender.displayName} • ${msg.createdAt}'),
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
