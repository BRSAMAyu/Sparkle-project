import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class ChatInput extends StatefulWidget {
  final Future<void> Function(String) onSend;
  final bool enabled;
  final String placeholder;

  const ChatInput({
    required this.onSend,
    super.key,
    this.enabled = true,
    this.placeholder = '有什么问题可以问我...',
  });

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput>
    with SingleTickerProviderStateMixin {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  bool _isSending = false;
  bool _isFocused = false;

  late AnimationController _sendButtonController;
  late Animation<double> _sendButtonRotation;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      setState(() {});
    });
    _focusNode.addListener(() {
      setState(() {
        _isFocused = _focusNode.hasFocus;
      });
    });

    _sendButtonController = AnimationController(
      duration: AppDesignTokens.durationNormal,
      vsync: this,
    );
    _sendButtonRotation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _sendButtonController,
        curve: AppDesignTokens.curveEaseInOut,
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _sendButtonController.dispose();
    super.dispose();
  }

  Future<void> _handleSend() async {
    if (_controller.text.trim().isEmpty || _isSending) return;

    HapticFeedback.mediumImpact();
    _sendButtonController.forward().then((_) {
      _sendButtonController.reset();
    });

    final text = _controller.text;
    setState(() {
      _isSending = true;
    });

    try {
      await widget.onSend(text);
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
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SafeArea(
      child: ClipRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppDesignTokens.spacing16,
              vertical: AppDesignTokens.spacing12,
            ),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  (isDark ? AppDesignTokens.neutral900 : Colors.white).withOpacity(0.9),
                  (isDark ? AppDesignTokens.neutral900 : Colors.white).withOpacity(0.95),
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
              border: Border(
                top: BorderSide(
                  color: (isDark ? Colors.white12 : AppDesignTokens.neutral200).withOpacity(0.5),
                  width: 1.0,
                ),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: AnimatedContainer(
                    duration: AppDesignTokens.durationFast,
                    decoration: BoxDecoration(
                      color: _isFocused
                          ? (isDark ? AppDesignTokens.neutral800 : Colors.white)
                          : (isDark ? AppDesignTokens.neutral800.withOpacity(0.5) : AppDesignTokens.neutral100),
                      borderRadius: AppDesignTokens.borderRadius24,
                      border: Border.all(
                        color: _isFocused
                            ? AppDesignTokens.primaryBase
                            : Colors.transparent,
                        width: 2.0, // Consistent width to avoid layout shift, but transparent when not focused
                      ),
                      boxShadow: _isFocused ? AppDesignTokens.shadowSm : null,
                    ),
                    child: TextField(
                      controller: _controller,
                      focusNode: _focusNode,
                      enabled: widget.enabled && !_isSending,
                      minLines: 1,
                      maxLines: 5,
                      textCapitalization: TextCapitalization.sentences,
                      style: TextStyle(
                        fontSize: AppDesignTokens.fontSizeBase,
                        color: isDark ? Colors.white : AppDesignTokens.neutral900,
                      ),
                      decoration: InputDecoration(
                        hintText: widget.placeholder,
                        hintStyle: TextStyle(
                          color: isDark ? Colors.white38 : AppDesignTokens.neutral500,
                          fontSize: AppDesignTokens.fontSizeBase,
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: AppDesignTokens.spacing16,
                          vertical: AppDesignTokens.spacing10,
                        ),
                        border: InputBorder.none,
                        isDense: true,
                      ),
                      onSubmitted: canSend ? (_) => _handleSend() : null,
                    ),
                  ),
                ),
                const SizedBox(width: AppDesignTokens.spacing12),
                GestureDetector(
                  onTap: canSend ? _handleSend : null,
                  child: AnimatedContainer(
                    duration: AppDesignTokens.durationFast,
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      gradient: canSend ? AppDesignTokens.primaryGradient : null,
                      color: canSend ? null : (isDark ? AppDesignTokens.neutral800 : AppDesignTokens.neutral300),
                      shape: BoxShape.circle,
                      boxShadow: canSend ? AppDesignTokens.shadowPrimary : null,
                    ),
                    child: Center(
                      child: _isSending
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.5,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                    Colors.white,),
                              ),
                            )
                          : RotationTransition(
                              turns: _sendButtonRotation,
                              child: Icon(
                                Icons.arrow_upward_rounded,
                                color: canSend
                                    ? Colors.white
                                    : (isDark ? Colors.white38 : AppDesignTokens.neutral500),
                                size: AppDesignTokens.iconSizeBase,
                              ),
                            ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}