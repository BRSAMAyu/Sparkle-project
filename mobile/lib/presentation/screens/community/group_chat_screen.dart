import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/community_agent_provider.dart';
import 'package:sparkle/presentation/providers/community_provider.dart';
import 'package:sparkle/presentation/widgets/chat/ai_status_indicator.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/presentation/widgets/common/error_widget.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';
import 'package:sparkle/presentation/widgets/community/group_chat_bubble.dart';
import 'package:sparkle/presentation/widgets/community/thread_sheet.dart';

class GroupChatScreen extends ConsumerStatefulWidget {

  const GroupChatScreen({required this.groupId, super.key});
  final String groupId;

  @override
  ConsumerState<GroupChatScreen> createState() => _GroupChatScreenState();
}

class _GroupChatScreenState extends ConsumerState<GroupChatScreen> {
  MessageInfo? _quotedMessage;
  bool _agentMode = false;

  void _showCheckinDialog() {
    final durationController = TextEditingController(text: '60');
    final messageController = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Daily Check-in'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: durationController,
              decoration: const InputDecoration(
                labelText: 'Duration (minutes)',
                suffixText: 'min',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: DS.lg),
            TextField(
              controller: messageController,
              decoration: const InputDecoration(
                labelText: 'Message (optional)',
                hintText: 'What did you learn today?',
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.ghost(label: 'Cancel', onPressed: () => Navigator.pop(context)),
          TextButton(
            onPressed: () async {
              final duration = int.tryParse(durationController.text) ?? 0;
              final message = messageController.text;
              Navigator.pop(context);

              try {
                await ref.read(groupDetailProvider(widget.groupId).notifier).checkin(duration, message);
                // Refresh chat to see the checkin message
                ref.invalidate(groupChatProvider(widget.groupId));
                
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Checked in successfully!')));
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
              }
            },
            child: const Text('Check-in'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(groupChatProvider(widget.groupId));
    final groupInfoState = ref.watch(groupDetailProvider(widget.groupId));
    final agentState = ref.watch(groupChatAgentProvider(widget.groupId));

    return Scaffold(
      appBar: AppBar(
        title: groupInfoState.when(
          data: (group) => InkWell(
            onTap: () {
              // Go to details? No, we are linked from details.
            },
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(group.name, style: const TextStyle(fontSize: 16)),
                Text('${group.memberCount} members', style: TextStyle(fontSize: 12, color: DS.brandPrimary54)),
              ],
            ),
          ),
          loading: () => const Text('Chat'),
          error: (_, __) => const Text('Chat'),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.local_fire_department, color: DS.brandPrimary),
            onPressed: _showCheckinDialog,
            tooltip: 'Check-in',
          ),
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: _showSearchSheet,
          ),
          IconButton(
            icon: const Icon(Icons.info_outline),
            onPressed: () {
               // Assuming we might be deep linked, ensuring we can go to details
               // Actually we came from details usually. 
               // But let's allow going to details if we are just in chat view
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: chatState.when(
              data: (messages) {
                final mergedMessages = _mergeMessages(messages, agentState);
                final showAgentStatus = agentState.isSending && agentState.streamingContent.isEmpty;

                if (mergedMessages.isEmpty) {
                  return const Center(child: Text('No messages yet. Say hi!'));
                }
                return ListView.builder(
                  reverse: true,
                  padding: const EdgeInsets.all(DS.lg),
                  itemCount: mergedMessages.length + (showAgentStatus ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (showAgentStatus && index == 0) {
                      return Padding(
                        padding: const EdgeInsets.only(bottom: DS.md),
                        child: const AiStatusIndicator(
                          status: 'THINKING',
                          details: 'AI助手正在整理思路...',
                        ),
                      );
                    }

                    final messageIndex = showAgentStatus ? index - 1 : index;
                    final message = mergedMessages[messageIndex];
                    return GroupChatBubble(
                      message: message,
                      onQuote: isCommunityAgentMessage(message)
                          ? null
                          : (msg) => setState(() {
                                _quotedMessage = msg;
                                ref.read(groupChatProvider(widget.groupId).notifier).setQuote(msg);
                              }),
                      onRevoke: isCommunityAgentMessage(message)
                          ? null
                          : (msg) => ref.read(groupChatProvider(widget.groupId).notifier).revokeMessage(msg.id),
                      onEdit: isCommunityAgentMessage(message)
                          ? null
                          : (msg, content) => ref.read(groupChatProvider(widget.groupId).notifier).editMessage(msg.id, content),
                      onReaction: isCommunityAgentMessage(message)
                          ? null
                          : (msg, emoji) => ref.read(groupChatProvider(widget.groupId).notifier).toggleReaction(msg.id, emoji),
                      onThread: _openThread,
                    );
                  },
                );
              },
              loading: () => const Center(child: LoadingIndicator()),
              error: (e, s) => Center(
                child: CustomErrorWidget.page(
                  message: e.toString(),
                  onRetry: () => ref.read(groupChatProvider(widget.groupId).notifier).refresh(),
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
            groupInfo: groupInfoState.valueOrNull,
            messages: chatState.valueOrNull ?? const [],
          ),
          ChatInput(
            enabled: !_agentMode || !agentState.isSending,
            hintText: _agentMode ? '向AI提问（仅你可见）' : '输入消息...',
            quotedMessage: !_agentMode && _quotedMessage != null
                ? PrivateMessageInfo(
                    id: _quotedMessage!.id,
                    sender: _quotedMessage!.sender ?? UserBrief(id: '', username: 'Unknown'),
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
              ref.read(groupChatProvider(widget.groupId).notifier).setQuote(null);
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
              ref.read(groupChatProvider(widget.groupId).notifier).sendMessage(
                content: text,
                replyToId: actualReplyId,
              );
            },
          ),
        ],
      ),
    );
  }

  List<MessageInfo> _mergeMessages(List<MessageInfo> messages, AgentChatState<MessageInfo> agentState) {
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
        sender: buildCommunityAgentUser(),
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
  }) {
    if (agentState.isSending) return;
    ref.read(groupChatAgentProvider(widget.groupId).notifier).sendAgentMessage(
          prompt: prompt,
          groupName: groupInfo?.name,
          recentMessages: messages,
        );
  }

  Widget _buildAgentToolbar(
    BuildContext context, {
    required AgentChatState<MessageInfo> agentState,
    required GroupInfo? groupInfo,
    required List<MessageInfo> messages,
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
                label: Text(_agentMode ? 'AI协作已开启' : 'AI协作'),
                avatar: Icon(Icons.auto_awesome, size: 16, color: _agentMode ? DS.brandPrimary : DS.neutral500),
                onSelected: (value) {
                  setState(() {
                    _agentMode = value;
                    if (_agentMode) {
                      _quotedMessage = null;
                      ref.read(groupChatProvider(widget.groupId).notifier).setQuote(null);
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
                    label: '总结讨论',
                    onTap: () => _sendAgentPrompt(
                      prompt: '请用3条要点总结当前讨论，并给出下一步建议。',
                      agentState: agentState,
                      groupInfo: groupInfo,
                      messages: messages,
                    ),
                  ),
                  _AgentQuickChip(
                    label: '生成提醒',
                    onTap: () => _sendAgentPrompt(
                      prompt: '请给群里写一句温和的学习提醒，保持积极友好的语气。',
                      agentState: agentState,
                      groupInfo: groupInfo,
                      messages: messages,
                    ),
                  ),
                  _AgentQuickChip(
                    label: '共识整理',
                    onTap: () => _sendAgentPrompt(
                      prompt: '请找出群里目前的共识和待确认的问题，列表化输出。',
                      agentState: agentState,
                      groupInfo: groupInfo,
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

  void _openThread(MessageInfo message) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => ThreadSheet(groupId: widget.groupId, rootMessage: message),
    );
  }

  Future<void> _showSearchSheet() async {
    final notifier = ref.read(groupChatProvider(widget.groupId).notifier);
    final controller = TextEditingController();
    List<MessageInfo> results = [];
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
                        hintText: '搜索群消息',
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
                              subtitle: Text('${msg.sender?.displayName ?? '成员'} • ${msg.createdAt}'),
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
        label: Text(label, style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
        backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
        onPressed: onTap,
      );
}
