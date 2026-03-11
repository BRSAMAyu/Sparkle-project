import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_bubble.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/focus/presentation/providers/mindfulness_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/shared/entities/task_model.dart';

class FocusAgentSheet extends ConsumerWidget {
  const FocusAgentSheet({required this.task, super.key});

  final TaskModel task;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final chatState = ref.watch(taskChatProvider(task.id));
    final mindfulness = ref.watch(mindfulnessProvider);
    final elapsedMinutes = (mindfulness.elapsedSeconds / 60).floor();
    final l10n = context.l10n;

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
                child: Icon(
                  Icons.auto_awesome,
                  color: DS.brandPrimaryConst,
                  size: 18,
                ),
              ),
              const SizedBox(width: DS.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.focusCoachTitle,
                      style: const TextStyle(
                        fontWeight: DS.fontWeightBold,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      l10n.focusCoachSummary(task.title, elapsedMinutes),
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
                  label: l10n.focusCoachPromptBreakdown,
                  onTap: () => _sendPrompt(
                    ref,
                    task,
                    l10n.focusCoachPromptBreakdownMessage(task.title),
                  ),
                ),
                _QuickPromptChip(
                  label: l10n.focusCoachPromptRefocus,
                  onTap: () => _sendPrompt(
                    ref,
                    task,
                    l10n.focusCoachPromptRefocusMessage,
                  ),
                ),
                _QuickPromptChip(
                  label: l10n.focusCoachPromptNextAction,
                  onTap: () => _sendPrompt(
                    ref,
                    task,
                    l10n.focusCoachPromptNextActionMessage,
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
                      l10n.focusCoachEmpty,
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
            hintText: l10n.focusCoachHint,
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
            Text(label, style: TextStyle(fontSize: 12, color: DS.primaryBase)),
        backgroundColor: DS.primaryBase.withValues(alpha: 0.08),
        side: BorderSide(color: DS.primaryBase.withValues(alpha: 0.2)),
        onPressed: onTap,
      );
}
