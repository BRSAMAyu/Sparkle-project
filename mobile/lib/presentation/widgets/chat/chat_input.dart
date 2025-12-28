import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/data/models/community_model.dart';
import 'package:sparkle/presentation/providers/settings_provider.dart';

class ChatInput extends ConsumerStatefulWidget {

  const ChatInput({
    super.key,
    this.enabled = true,
    this.hintText,
    this.onSend,
    this.quotedMessage,
    this.onCancelQuote,
  });
  final bool enabled;
  final String? hintText;
  final Function(String text, {String? replyToId})? onSend;
  final PrivateMessageInfo? quotedMessage;
  final VoidCallback? onCancelQuote;

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
    final canSend = widget.enabled && !_isSending && _controller.text.trim().isNotEmpty;
    final enterToSend = ref.watch(enterToSendProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Quote Preview
          if (widget.quotedMessage != null) _buildQuotePreview(isDark),
          
          Padding(
            padding: const EdgeInsets.all(DS.spacing8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: isDark ? DS.neutral800 : DS.neutral100,
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(
                        color: isDark ? DS.neutral700 : DS.neutral300,
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
                          color: isDark ? DS.neutral400 : DS.neutral500,
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: DS.spacing16,
                          vertical: DS.spacing10,
                        ),
                        border: InputBorder.none,
                        isDense: true,
                      ),
                      onSubmitted: canSend && enterToSend ? (_) => _handleSend() : null,
                    ),
                  ),
                ),
                const SizedBox(width: DS.spacing12),
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
                        gradient: canSend ? DS.primaryGradient : null,
                        color: canSend ? null : (isDark ? DS.neutral800 : DS.neutral200),
                        shape: BoxShape.circle,
                        boxShadow: canSend 
                          ? [
                              BoxShadow(
                                color: DS.brandPrimary.withValues(alpha: 0.3),
                                blurRadius: 8,
                                offset: const Offset(0, 4),
                              ),
                            ] 
                          : null,
                      ),
                      child: Center(
                        child: _isSending
                            ? SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(strokeWidth: 2, color: DS.brandPrimary),
                              )
                            : Icon(
                                Icons.arrow_upward_rounded,
                                color: canSend ? DS.brandPrimary : (isDark ? DS.brandPrimary30 : DS.brandPrimary38),
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

  Widget _buildQuotePreview(bool isDark) => Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: isDark ? DS.neutral800 : DS.brandPrimary200,
        borderRadius: BorderRadius.circular(12),
        border: Border(
          left: BorderSide(color: DS.brandPrimary, width: 4),
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
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightBold,
                    color: DS.brandPrimary,
                  ),
                ),
                const SizedBox(height: DS.spacing4),
                Text(
                  widget.quotedMessage!.content ?? '',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: isDark ? DS.neutral400 : DS.neutral600,
                  ),
                ),
              ],
            ),
          ),
          SizedBox(
            width: DS.touchTargetMinSize,
            height: DS.touchTargetMinSize,
            child: IconButton(
              icon: Icon(Icons.close_rounded,
                size: DS.iconSizeSm,
                color: DS.neutral600,),
              onPressed: widget.onCancelQuote,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
            ),
          ),
        ],
      ),
    );
}
