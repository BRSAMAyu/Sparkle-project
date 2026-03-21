import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/task/presentation/providers/task_chat_provider.dart';

class TaskChatPanel extends ConsumerStatefulWidget {
  const TaskChatPanel({
    required this.taskId,
    this.isAvailable = true,
    super.key,
  });
  final String taskId;
  final bool isAvailable;

  @override
  ConsumerState<TaskChatPanel> createState() => _TaskChatPanelState();
}

class _TaskChatPanelState extends ConsumerState<TaskChatPanel> {
  final TextEditingController _controller = TextEditingController();
  bool _isExpanded = false;

  void _sendMessage() {
    final text = _controller.text;
    if (text.isNotEmpty) {
      unawaited(
        ref.read(taskChatProvider(widget.taskId).notifier).sendMessage(text),
      );
      _controller.clear();
      if (!_isExpanded) {
        setState(() => _isExpanded = true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAvailable) {
      return GraphiteCardSurface(
        child: Padding(
          padding: const EdgeInsets.all(DS.spacing16),
          child: Text(
            '任务助手仅在已同步到服务器的任务中可用。',
            style: TextStyle(color: DS.neutral500),
          ),
        ),
      );
    }

    final chatState = ref.watch(taskChatProvider(widget.taskId));
    final messages = chatState.messages;
    final lastMessage = messages.isNotEmpty ? messages.last : null;

    return GraphiteCardSurface(
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          // Header
          InkWell(
            onTap: () => setState(() => _isExpanded = !_isExpanded),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing12),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
                    decoration: BoxDecoration(
                      color: DS.surfaceSecondary,
                      shape: BoxShape.circle,
                      border: Border.all(color: DS.borderSubtle),
                    ),
                    child: Icon(
                      Icons.auto_awesome,
                      color: DS.primaryBase,
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: DS.spacing12),
                  Text(
                    context.l10n.taskChatAssistantTitle,
                    style: TextStyle(
                      fontWeight: DS.fontWeightBold,
                      color: DS.neutral900,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    _isExpanded ? Icons.expand_less : Icons.expand_more,
                    color: DS.neutral500,
                  ),
                ],
              ),
            ),
          ),

          if (!_isExpanded && lastMessage != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Text(
                '${lastMessage.role == MessageRole.user ? context.l10n.chatLabelMe : context.l10n.chatLabelAssistant}: ${lastMessage.content}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: DS.neutral600, fontSize: 12),
              ),
            ),

          if (_isExpanded) ...[
            const Divider(height: 1),
            if (chatState.error != null)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing16,
                  vertical: DS.spacing10,
                ),
                color: DS.error.withValues(alpha: 0.08),
                child: Text(
                  chatState.error!,
                  style: TextStyle(
                    color: DS.error,
                    fontSize: 12,
                  ),
                ),
              ),
            Container(
              height: 300,
              color: DS.surfaceSecondary,
              child: messages.isEmpty
                  ? Center(
                      child: Text(
                        context.l10n.taskChatEmptyPrompt,
                        style: TextStyle(color: DS.neutral400),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(DS.lg),
                      itemCount: messages.length,
                      itemBuilder: (context, index) =>
                          ChatBubble(message: messages[index]),
                    ),
            ),
            const Divider(height: 1),
            Padding(
              padding: const EdgeInsets.all(DS.sm),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: InputDecoration(
                        hintText: context.l10n.taskChatInputHint,
                        border: InputBorder.none,
                        contentPadding:
                            const EdgeInsets.symmetric(horizontal: 16),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  if (chatState.isLoading)
                    const Padding(
                      padding: EdgeInsets.all(DS.sm),
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  else
                    SparkleIconButton(
                      variant: ButtonVariant.ghost,
                      size: 36,
                      icon: Icon(Icons.send, color: DS.primaryBase),
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
