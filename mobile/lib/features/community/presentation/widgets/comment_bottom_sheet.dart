import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/design/widgets/sparkle_skeleton.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:timeago/timeago.dart' as timeago;

/// Shows a bottom sheet with comments for a post and an input field.
Future<void> showCommentSheet(
  BuildContext context,
  WidgetRef ref,
  String postId, {
  String? postContent,
}) {
  return showSensoryModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) => _CommentSheetContent(
      postId: postId,
      postContent: postContent,
    ),
  );
}

class _CommentSheetContent extends ConsumerStatefulWidget {
  const _CommentSheetContent({
    required this.postId,
    required this.postContent,
  });

  final String postId;
  final String? postContent;

  @override
  ConsumerState<_CommentSheetContent> createState() =>
      _CommentSheetContentState();
}

class _CommentSheetContentState extends ConsumerState<_CommentSheetContent> {
  final _inputController = TextEditingController();
  List<Map<String, dynamic>> _comments = [];
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadComments();
  }

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  Future<void> _loadComments() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.dio.get<Map<String, dynamic>>(
        ApiEndpoints.communityPostComments(widget.postId),
      );
      if (!mounted) return;
      final items = ApiResponseParser.unwrapList(
        resp.data,
        action: 'loadPostComments',
      );
      setState(() {
        _comments = items
            .whereType<Map>()
            .map((item) => Map<String, dynamic>.from(item))
            .toList(growable: false);
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _submitComment() async {
    final content = _inputController.text.trim();
    if (content.isEmpty || _submitting) return;
    setState(() => _submitting = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.dio.post<Map<String, dynamic>>(
        ApiEndpoints.communityPostComments(widget.postId),
        data: {'content': content},
      );
      if (!mounted) return;
      _inputController.clear();
      await _loadComments();
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          context.l10n.communityCommentSendFailed,
        );
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  Future<void> _deleteComment(String commentId) async {
    try {
      final api = ref.read(apiClientProvider);
      await api.dio.delete<Map<String, dynamic>>(
        ApiEndpoints.communityPostComment(widget.postId, commentId),
      );
      if (!mounted) return;
      await _loadComments();
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          context.l10n.communityCommentDeleteFailed,
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = context.l10n;
    return DraggableScrollableSheet(
      initialChildSize: 0.6,
      maxChildSize: 0.9,
      minChildSize: 0.3,
      expand: false,
      builder: (context, scrollController) => Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Text(
                  l10n.communityCommentsTitle,
                  style: theme.textTheme.titleMedium,
                ),
                const Spacer(),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close, size: 20),
                ),
              ],
            ),
          ),
          if (widget.postContent != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                widget.postContent!,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          const Divider(),
          Expanded(
            child: _loading
                ? const SparkleListSkeleton(count: 3)
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.error_outline, size: 32, color: DS.textTertiary),
                            const SizedBox(height: DS.sm),
                            Text(l10n.communityCommentRetry,
                                style: TextStyle(color: DS.textSecondary)),
                            TextButton(
                              onPressed: _loadComments,
                              child: Text(l10n.communityCommentRetry),
                            ),
                          ],
                        ),
                      )
                    : _comments.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.chat_bubble_outline, size: 32, color: DS.textTertiary),
                                const SizedBox(height: DS.sm),
                                Text(
                                  l10n.communityCommentEmpty,
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    color: DS.textSecondary,
                                  ),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            controller: scrollController,
                            itemCount: _comments.length,
                            itemBuilder: (context, index) {
                              final c = _comments[index];
                              final author = c['user'] as Map<String, dynamic>?;
                              final username = author?['display_name'] as String? ??
                                  author?['username'] as String? ??
                                  context.l10n.communityMemberFallback;
                              final avatarUrl = author?['avatar_url'] as String?;
                              final dateStr = c['created_at'] as String? ?? '';
                              final date = dateStr.isNotEmpty
                                  ? timeago.format(DateTime.tryParse(dateStr) ?? DateTime.now())
                                  : '';
                              final isOwner = c['is_owner'] == true;
                              return Padding(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 16,
                                  vertical: 8,
                                ),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    CircleAvatar(
                                      radius: 14,
                                      backgroundColor: DS.avatarFallbackBackground,
                                      backgroundImage: avatarUrl != null
                                          ? NetworkImage(avatarUrl)
                                          : null,
                                      child: avatarUrl == null
                                          ? Text(
                                              username[0].toUpperCase(),
                                              style: TextStyle(
                                                color: DS.avatarFallbackForeground,
                                                fontSize: 12,
                                              ),
                                            )
                                          : null,
                                    ),
                                    const SizedBox(width: DS.sm),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Text(
                                                username,
                                                style: TextStyle(
                                                  fontWeight: DS.fontWeightMedium,
                                                  fontSize: 13,
                                                  color: DS.textPrimary,
                                                ),
                                              ),
                                              const SizedBox(width: DS.sm),
                                              Text(
                                                date,
                                                style: TextStyle(
                                                  fontSize: 11,
                                                  color: DS.textTertiary,
                                                ),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            c['content'] as String? ?? '',
                                            style: TextStyle(
                                              fontSize: 14,
                                              color: DS.textPrimary,
                                              height: 1.4,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    if (isOwner)
                                      GestureDetector(
                                        onTap: () {
                                          final id = c['id']?.toString();
                                          if (id == null || id.isEmpty) return;
                                          unawaited(_deleteComment(id));
                                        },
                                        child: Padding(
                                          padding: const EdgeInsets.all(4),
                                          child: Icon(
                                            Icons.delete_outline,
                                            size: 16,
                                            color: DS.textTertiary,
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              );
                            },
                          ),
          ),
          const Divider(height: 1),
          SafeArea(
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                12,
                8,
                12,
                MediaQuery.of(context).viewInsets.bottom + 8,
              ),
              child: Container(
                decoration: BoxDecoration(
                  color: DS.surfaceSecondary,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: DS.borderSubtle),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _inputController,
                        decoration: InputDecoration(
                          hintText: l10n.communityCommentHint,
                          border: InputBorder.none,
                          contentPadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 10,
                          ),
                          isDense: true,
                        ),
                        onSubmitted: (_) => _submitComment(),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: IconButton(
                        onPressed: _submitting ? null : _submitComment,
                        icon: Icon(Icons.send,
                            color: _submitting ? DS.textTertiary : DS.brandPrimary),
                        iconSize: 20,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
