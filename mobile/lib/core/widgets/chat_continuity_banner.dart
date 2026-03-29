import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

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
      ChatContinuityKind.chat => '承接刚才的对话',
      ChatContinuityKind.journey => '承接刚才的探索流程',
    };
    final resolvedSubtitle = subtitle ?? switch (kind) {
      ChatContinuityKind.chat => '这一页会承接上一个聊天上下文，你可以随时回到原对话继续追问。',
      ChatContinuityKind.journey => '这一页会沿着刚才的探索继续展开，你可以随时回到原对话或上一段流程继续追问。',
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
                        fontWeight: FontWeight.w800,
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
            child: const Text('回到对话'),
          ),
        ],
      ),
    );
  }
}
