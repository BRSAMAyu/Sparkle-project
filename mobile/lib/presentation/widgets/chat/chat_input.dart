import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/settings_provider.dart';

class ChatInput extends ConsumerStatefulWidget {
  final bool enabled;
  final String? hintText;
  final Function(String text, {String? replyToId})? onSend;
  final PrivateMessageInfo? quotedMessage;
  final VoidCallback? onCancelQuote;

  const ChatInput({
    super.key,
    this.enabled = true,
    this.hintText,
    this.onSend,
    this.quotedMessage,
    this.onCancelQuote,
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
  void didUpdateWidget(ChatInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.quotedMessage != null && oldWidget.quotedMessage == null) {
      _focusNode.requestFocus();
    }
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
      widget.onSend!(text, replyToId: widget.quotedMessage?.id);
      _controller.clear();
      if (widget.onCancelQuote != null) widget.onCancelQuote!();
      _focusNode.requestFocus();
      return;
    }

    setState(() => _isSending = true);
    try {
      _controller.clear();
      _focusNode.requestFocus();
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool canSend = widget.enabled && !_isSending && _controller.text.trim().isNotEmpty;
    final bool enterToSend = ref.watch(enterToSendProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Quote Preview
          if (widget.quotedMessage != null) _buildQuotePreview(isDark),
          
          Padding(
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
                              ),
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
        ],
      ),
    );
  }

  Widget _buildQuotePreview(bool isDark) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isDark ? AppDesignTokens.neutral800 : Colors.grey[200],
        borderRadius: BorderRadius.circular(12),
        border: const Border(
          left: BorderSide(color: AppDesignTokens.primaryBase, width: 4),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '引用 ${widget.quotedMessage!.sender.displayName}',
                  style: const TextStyle(
                    fontSize: AppDesignTokens.fontSizeXs,
                    fontWeight: AppDesignTokens.fontWeightBold,
                    color: AppDesignTokens.primaryBase,
                  ),
                ),
                const SizedBox(height: AppDesignTokens.spacing4),
                Text(
                  widget.quotedMessage!.content ?? '',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: AppDesignTokens.fontSizeXs,
                    color: isDark ? AppDesignTokens.neutral400 : AppDesignTokens.neutral600,
                  ),
                ),
              ],
            ),
          ),
          SizedBox(
            width: AppDesignTokens.touchTargetMinSize,
            height: AppDesignTokens.touchTargetMinSize,
            child: IconButton(
              icon: const Icon(Icons.close_rounded,
                size: AppDesignTokens.iconSizeSm,
                color: AppDesignTokens.neutral600,),
              onPressed: widget.onCancelQuote,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
            ),
          ),
        ],
      ),
    );
  }
}
