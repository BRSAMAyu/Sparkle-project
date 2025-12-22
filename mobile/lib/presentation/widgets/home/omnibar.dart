
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/repositories/omnibar_repository.dart';

class OmniBar extends ConsumerStatefulWidget {
  const OmniBar({super.key});

  @override
  ConsumerState<OmniBar> createState() => _OmniBarState();
}

class _OmniBarState extends ConsumerState<OmniBar> {
  final TextEditingController _controller = TextEditingController();
  bool _isExpanded = false;
  bool _isLoading = false;

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _isLoading = true;
    });

    try {
      final result = await ref.read(omniBarRepositoryProvider).dispatch(text);
      if (mounted) {
        _handleResult(result);
        _controller.clear();
        setState(() {
          _isExpanded = false;
        });
        FocusScope.of(context).unfocus();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _handleResult(Map<String, dynamic> result) {
    final type = result['action_type'];
    final data = result['data'];

    if (type == 'CHAT') {
      // Navigate to chat with initial message
      // TODO: Pass data properly to chat screen
      // For now, we assume chat screen can fetch latest or we pass it
      context.go('/chat'); // Simple navigation for now
    } else if (type == 'TASK') {
       ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Task created: ${data['title']}'),
          backgroundColor: Colors.green,
        ),
      );
      // Refresh task list - TODO: Use provider to refresh
    } else if (type == 'CAPSULE') {
       ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Thought captured into Prism'),
          backgroundColor: Colors.purple,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      margin: EdgeInsets.only(
        left: 16, 
        right: 16, 
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: isDark ? AppDesignTokens.neutral800 : Colors.white,
        borderRadius: BorderRadius.circular(30),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 10,
            offset: const Offset(0, 5),
          ),
        ],
        border: Border.all(color: AppDesignTokens.primaryBase.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              onTap: () {
                setState(() {
                  _isExpanded = true;
                });
              },
              onSubmitted: (_) => _submit(),
              decoration: InputDecoration(
                hintText: '想做什么？或是随便聊聊...',
                border: InputBorder.none,
                hintStyle: TextStyle(color: isDark ? Colors.white38 : AppDesignTokens.neutral400),
                contentPadding: const EdgeInsets.symmetric(horizontal: 8),
              ),
              style: TextStyle(color: isDark ? Colors.white : Colors.black),
            ),
          ),
          if (_isLoading)
            const SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            IconButton(
              icon: const Icon(Icons.send_rounded),
              color: AppDesignTokens.primaryBase,
              onPressed: _submit,
            ),
        ],
      ),
    );
  }
}
