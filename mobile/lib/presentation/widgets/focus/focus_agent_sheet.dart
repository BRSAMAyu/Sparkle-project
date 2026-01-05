import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/presentation/widgets/chat/chat_bubble.dart';
import 'package:sparkle/presentation/widgets/chat/chat_input.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class FocusAgentSheet extends ConsumerWidget {
  const FocusAgentSheet({required this.task, super.key});

  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final chatState = ref.watch(taskChatProvider(task.id));
    final mindfulness = ref.watch(mindfulnessProvider);
    final elapsedMinutes = (mindfulness.elapsedSeconds / 60).floor();

    return Container(
      padding: const EdgeInsets.fromLTRB(DS.lg, DS.md, DS.lg, DS.lg),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          Container(
            width: 40,
            height: 4,
            margin: const EdgeInsets.only(bottom: DS.lg),
            decoration: BoxDecoration(
              color: DS.neutral300,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  gradient: DS.secondaryGradient,
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.auto_awesome,
                    color: DS.brandPrimaryConst, size: 18,),
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('AI专注教练',
                        style: TextStyle(
                            fontWeight: DS.fontWeightBold, fontSize: 16,),),
                    Text(
                      '任务：${task.title} · 已专注$elapsedMinutes分钟',
                      style: TextStyle(color: DS.neutral500, fontSize: 12),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.md),
          Align(
            alignment: Alignment.centerLeft,
            child: Wrap(
              spacing: DS.sm,
              runSpacing: DS.xs,
              children: [
                _QuickPromptChip(
                  label: '拆解接下来15分钟',
                  onTap: () => _sendPrompt(
                    ref,
                    task,
                    '请根据任务「${task.title}」，帮我拆解接下来15分钟的专注计划。',
                  ),
                ),
                _QuickPromptChip(
                  label: '分心提醒',
                  onTap: () => _sendPrompt(
                    ref,
                    task,
                    '我刚刚有些分心，请给我一句简短的回归提示。',
                  ),
                ),
                _QuickPromptChip(
                  label: '下一步行动',
                  onTap: () => _sendPrompt(
                    ref,
                    task,
                    '请总结当前任务的下一步行动，保持简洁明确。',
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.md),
          Expanded(
            child: chatState.messages.isEmpty
                ? Center(
                    child: Text(
                      '需要帮助就问我！',
                      style: TextStyle(color: DS.neutral500),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(vertical: DS.sm),
                    itemCount: chatState.messages.length,
                    itemBuilder: (context, index) => ChatBubble(
                      message: chatState.messages[index],
                      showAvatar: false,
                    ),
                  ),
          ),
          if (chatState.error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.sm),
              child: Text(
                chatState.error!,
                style: TextStyle(color: DS.error, fontSize: 12),
              ),
            ),
          ChatInput(
            enabled: !chatState.isLoading,
            hintText: '问我：如何保持专注、拆解步骤...',
            onSend: (text, {replyToId}) => _sendPrompt(ref, task, text),
          ),
        ],
      ),
    );
  }

  void _sendPrompt(WidgetRef ref, TaskModel task, String text) {
    if (text.trim().isEmpty) return;
    ref.read(taskChatProvider(task.id).notifier).sendMessage(text);
  }
}

class _QuickPromptChip extends StatelessWidget {
  const _QuickPromptChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => ActionChip(
        label:
            Text(label, style: TextStyle(fontSize: 12, color: DS.brandPrimary)),
        backgroundColor: DS.brandPrimary.withValues(alpha: 0.1),
        onPressed: onTap,
      );
}
