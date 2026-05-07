import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/providers/locale_provider.dart';

/// Shows a bottom sheet with comments for a post and an input field.
Future<void> showCommentSheet(
  BuildContext context,
  WidgetRef ref,
  String postId, {
  String? postContent,
}) {
  final isChinese = ref.read(localeProvider).languageCode == 'zh';
  return showSensoryModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (sheetContext) => _CommentSheetContent(
      postId: postId,
      postContent: postContent,
      isChinese: isChinese,
    ),
  );
}

class _CommentSheetContent extends ConsumerStatefulWidget {
  const _CommentSheetContent({
    required this.postId,
    required this.postContent,
    required this.isChinese,
  });

  final String postId;
  final String? postContent;
  final bool isChinese;

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
      final resp = await api.dio.get(
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
      await api.dio.post(
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
          widget.isChinese ? '发送失败' : 'Failed to send',
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
      await api.dio.delete(
        ApiEndpoints.communityPostComment(widget.postId, commentId),
      );
      if (!mounted) return;
      await _loadComments();
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          widget.isChinese ? '删除失败' : 'Failed to delete',
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
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
                  widget.isChinese ? '评论' : 'Comments',
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
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: TextButton(
                          onPressed: _loadComments,
                          child: Text(widget.isChinese ? '重试' : 'Retry'),
                        ),
                      )
                    : _comments.isEmpty
                        ? Center(
                            child: Text(
                              widget.isChinese ? '暂无评论' : 'No comments yet',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                          )
                        : ListView.builder(
                            controller: scrollController,
                            itemCount: _comments.length,
                            itemBuilder: (context, index) {
                              final c = _comments[index];
                              final dateStr = c['created_at'] as String? ?? '';
                              final date = dateStr.length >= 10
                                  ? dateStr.substring(0, 10)
                                  : dateStr;
                              return ListTile(
                                dense: true,
                                title: Text(c['content'] as String? ?? ''),
                                subtitle: Text(date),
                                trailing: IconButton(
                                  icon: const Icon(
                                    Icons.delete_outline,
                                    size: 18,
                                  ),
                                  onPressed: () {
                                    final id = c['id']?.toString();
                                    if (id == null || id.isEmpty) return;
                                    unawaited(_deleteComment(id));
                                  },
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
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _inputController,
                      decoration: InputDecoration(
                        hintText:
                            widget.isChinese ? '写评论...' : 'Write a comment...',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 10,
                        ),
                        isDense: true,
                      ),
                      onSubmitted: (_) => _submitComment(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    onPressed: _submitting ? null : _submitComment,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
