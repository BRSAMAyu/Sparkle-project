import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

enum ChatContinuityKind {
  chat,
  journey,
}

class ChatContinuityBanner extends StatelessWidget {
  const ChatContinuityBanner({
    required this.sourceChatSessionId,
    super.key,
    this.kind = ChatContinuityKind.chat,
    this.title,
    this.subtitle,
    this.prompt,
  });

  final String sourceChatSessionId;
  final ChatContinuityKind kind;
  final String? title;
  final String? subtitle;
  final String? prompt;

  @override
  Widget build(BuildContext context) {
    final query = <String, String>{
      'session_id': sourceChatSessionId,
      if (prompt != null && prompt!.trim().isNotEmpty) 'prompt': prompt!.trim(),
    };
    final resolvedTitle = title ?? switch (kind) {
      ChatContinuityKind.chat => context.l10n.chatContinuityChatTitle,
      ChatContinuityKind.journey => context.l10n.chatContinuityJourneyTitle,
    };
    final resolvedSubtitle = subtitle ?? switch (kind) {
      ChatContinuityKind.chat => context.l10n.chatContinuityChatSubtitle,
      ChatContinuityKind.journey => context.l10n.chatContinuityJourneySubtitle,
    };
    return GraphiteCardSurface(
      surfaceRole: SparkleSurfaceRole.card,
      borderColor: DS.info.withValues(alpha: 0.18),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: DS.info.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              Icons.forum_rounded,
              color: DS.info,
            ),
          ),
          const SizedBox(width: DS.spacing12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  resolvedTitle,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  resolvedSubtitle,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(width: DS.spacing8),
          TextButton(
            onPressed: () => context.push(
              Uri(path: '/chat', queryParameters: query).toString(),
            ),
            child: Text(context.l10n.chatContinuityReturn),
          ),
        ],
      ),
    );
  }
}
