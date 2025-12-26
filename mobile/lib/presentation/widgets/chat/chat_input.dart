import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/settings_provider.dart';

class ChatInput extends ConsumerStatefulWidget {
  final bool enabled;
  final String? hintText;
  final Function(String text)? onSend;

  const ChatInput({
    super.key,
    this.enabled = true,
    this.hintText,
    this.onSend,
  });

  @override
  ConsumerState<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends ConsumerState<ChatInput> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _isSending = false;
  bool _isButtonPressed = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      setState(() {}); // Update send button state
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _handleSend() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSending) return;

    if (widget.onSend != null) {
      widget.onSend!(text);
      _controller.clear();
      _focusNode.requestFocus();
      return;
    }

    setState(() {
      _isSending = true;
    });

    try {
      // If no onSend callback, logic to send message via provider could go here
      // but standard usage in this project seems to prefer callbacks.
      _controller.clear();
      _focusNode.requestFocus();
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool canSend =
        widget.enabled && !_isSending && _controller.text.trim().isNotEmpty;
    final bool enterToSend = ref.watch(enterToSendProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(AppDesignTokens.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: isDark ? AppDesignTokens.neutral800 : AppDesignTokens.neutral100,
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(
                    color: isDark ? AppDesignTokens.neutral700 : AppDesignTokens.neutral300,
                  ),
                ),
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  maxLines: 5,
                  minLines: 1,
                  textInputAction: enterToSend ? TextInputAction.send : TextInputAction.newline,
                  decoration: InputDecoration(
                    hintText: widget.hintText ?? 'Type a message...',
                    hintStyle: TextStyle(
                      color: isDark ? AppDesignTokens.neutral400 : AppDesignTokens.neutral500,
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: AppDesignTokens.spacing16,
                      vertical: AppDesignTokens.spacing10,
                    ),
                    border: InputBorder.none,
                    isDense: true,
                  ),
                  onSubmitted: canSend && enterToSend ? (_) => _handleSend() : null,
                ),
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            GestureDetector(
              onTapDown: (_) => setState(() => _isButtonPressed = true),
              onTapUp: (_) => setState(() => _isButtonPressed = false),
              onTapCancel: () => setState(() => _isButtonPressed = false),
              onTap: canSend ? _handleSend : null,
              child: AnimatedScale(
                scale: _isButtonPressed ? 0.9 : 1.0,
                duration: const Duration(milliseconds: 100),
                curve: Curves.easeInOut,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    gradient: canSend ? AppDesignTokens.primaryGradient : null,
                    color: canSend ? null : (isDark ? AppDesignTokens.neutral800 : AppDesignTokens.neutral200),
                    shape: BoxShape.circle,
                    boxShadow: canSend 
                      ? [
                          BoxShadow(
                            color: AppDesignTokens.primaryBase.withValues(alpha: 0.3),
                            blurRadius: 8,
                            offset: const Offset(0, 4),
                          )
                        ] 
                      : null,
                  ),
                  child: Center(
                    child: _isSending
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : Icon(
                            Icons.arrow_upward_rounded,
                            color: canSend ? Colors.white : (isDark ? Colors.white30 : Colors.black38),
                            size: 24,
                          ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}