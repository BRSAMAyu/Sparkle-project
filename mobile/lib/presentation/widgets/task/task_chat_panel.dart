import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/chat_message_model.dart';
import 'package:sparkle/presentation/providers/task_chat_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';

class TaskChatPanel extends ConsumerStatefulWidget {
  final String taskId;

  const TaskChatPanel({
    super.key, 
    required this.taskId,
  });

  @override
  ConsumerState<TaskChatPanel> createState() => _TaskChatPanelState();
}

class _TaskChatPanelState extends ConsumerState<TaskChatPanel> {
  final TextEditingController _controller = TextEditingController();
  bool _isExpanded = false;

  void _sendMessage() {
    final text = _controller.text;
    if (text.isNotEmpty) {
      ref.read(taskChatProvider(widget.taskId).notifier).sendMessage(text);
      _controller.clear();
      if (!_isExpanded) {
        setState(() => _isExpanded = true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(taskChatProvider(widget.taskId));
    final messages = chatState.messages;
    final lastMessage = messages.isNotEmpty ? messages.last : null;

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: AppDesignTokens.borderRadius16,
        boxShadow: AppDesignTokens.shadowMd,
        border: Border.all(color: AppDesignTokens.neutral200),
      ),
      child: Column(
        children: [
          // Header
          InkWell(
            onTap: () => setState(() => _isExpanded = !_isExpanded),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(AppDesignTokens.spacing12),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      gradient: AppDesignTokens.secondaryGradient,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
                  ),
                  const SizedBox(width: AppDesignTokens.spacing12),
                  const Text(
                    'AI 学习助手',
                    style: TextStyle(
                      fontWeight: AppDesignTokens.fontWeightBold,
                      color: AppDesignTokens.neutral900,
                    ),
                  ),
                  const Spacer(),
                  Icon(_isExpanded ? Icons.expand_less : Icons.expand_more, color: AppDesignTokens.neutral500),
                ],
              ),
            ),
          ),
          
          if (!_isExpanded && lastMessage != null)
             Padding(
               padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
               child: Text(
                 "${lastMessage.role == MessageRole.user ? '我' : 'AI'}: ${lastMessage.content}",
                 maxLines: 1,
                 overflow: TextOverflow.ellipsis,
                 style: const TextStyle(color: AppDesignTokens.neutral600, fontSize: 12),
               ),
             ),

          if (_isExpanded) ...[
            const Divider(height: 1),
            Container(
              height: 300,
              color: AppDesignTokens.neutral50,
              child: messages.isEmpty 
                  ? Center(
                      child: Text(
                        '有问题尽管问我！', 
                        style: TextStyle(color: AppDesignTokens.neutral400),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: messages.length,
                      itemBuilder: (context, index) {
                        return ChatBubble(message: messages[index]);
                      },
                    ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: const InputDecoration(
                        hintText: '输入问题...',
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(horizontal: 16),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  if (chatState.isLoading)
                    const Padding(
                      padding: EdgeInsets.all(8.0),
                      child: SizedBox(
                        width: 16, 
                        height: 16, 
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  else
                    IconButton(
                      icon: const Icon(Icons.send, color: AppDesignTokens.primaryBase),
                      onPressed: _sendMessage,
                    ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
