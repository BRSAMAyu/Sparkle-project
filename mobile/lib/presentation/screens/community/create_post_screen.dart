import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/community_providers.dart';

class CreatePostScreen extends ConsumerStatefulWidget {
  const CreatePostScreen({super.key});

  @override
  ConsumerState<CreatePostScreen> createState() => _CreatePostScreenState();
}

class _CreatePostScreenState extends ConsumerState<CreatePostScreen> {
  final _contentController = TextEditingController();
  final _topicController = TextEditingController();
  bool _isPosting = false;

  Future<void> _submit() async {
    final content = _contentController.text.trim();
    if (content.isEmpty) return;

    setState(() => _isPosting = true);

    try {
      await ref.read(feedProvider.notifier).addPostOptimistically(
            content,
            [], // TODO: Image picker
            _topicController.text.trim(),
          );
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to post: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isPosting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppDesignTokens.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('New Post'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: TextButton(
              onPressed: _isPosting ? null : _submit,
              style: TextButton.styleFrom(
                backgroundColor: AppDesignTokens.primaryBase,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              child: _isPosting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                    )
                  : const Text('Post', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(
              controller: _contentController,
              autofocus: true,
              maxLines: 8,
              style: const TextStyle(color: Colors.white, fontSize: 16),
              decoration: const InputDecoration(
                hintText: "What's on your mind?",
                hintStyle: TextStyle(color: Colors.white30),
                border: InputBorder.none,
              ),
            ),
            const Divider(color: Colors.white24),
            TextField(
              controller: _topicController,
              style: const TextStyle(color: AppDesignTokens.secondaryBase),
              decoration: const InputDecoration(
                prefixText: '# ',
                hintText: 'Topic (optional)',
                hintStyle: TextStyle(color: Colors.white30),
                border: InputBorder.none,
              ),
            ),
            const Spacer(),
            // Toolbar (Placeholder)
            Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.image_outlined, color: AppDesignTokens.primaryBase),
                  onPressed: () {}, // TODO
                ),
                IconButton(
                  icon: const Icon(Icons.location_on_outlined, color: Colors.grey),
                  onPressed: () {}, // TODO
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
