import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class ChatInput extends StatefulWidget {
  final Future<void> Function(String) onSend;
  final bool enabled;
  final String placeholder;

  const ChatInput({
    required this.onSend, super.key,
    this.enabled = true,
    this.placeholder = 'Ask anything...',
  });

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
  final _controller = TextEditingController();
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() {
      setState(() {}); 
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleSend() async {
    if (_controller.text.trim().isEmpty || _isSending) return;

    final text = _controller.text;
    setState(() {
      _isSending = true;
    });

    try {
      await widget.onSend(text);
      _controller.clear();
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
    final bool canSend = widget.enabled && !_isSending && _controller.text.trim().isNotEmpty;

    return SafeArea(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16, vertical: AppDesignTokens.spacing12),
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: AppDesignTokens.neutral100,
                  borderRadius: AppDesignTokens.borderRadius24,
                  border: Border.all(color: AppDesignTokens.neutral200),
                ),
                child: TextField(
                  controller: _controller,
                  minLines: 1,
                  maxLines: 5,
                  textCapitalization: TextCapitalization.sentences,
                  style: const TextStyle(fontSize: AppDesignTokens.fontSizeBase),
                  decoration: InputDecoration(
                    hintText: widget.placeholder,
                    hintStyle: const TextStyle(color: AppDesignTokens.neutral500),
                    contentPadding: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16, vertical: AppDesignTokens.spacing12),
                    border: InputBorder.none,
                    isDense: true,
                  ),
                ),
              ),
            ),
            const SizedBox(width: AppDesignTokens.spacing12),
            GestureDetector(
              onTap: canSend ? _handleSend : null,
              child: AnimatedContainer(
                duration: AppDesignTokens.durationFast,
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  gradient: canSend ? AppDesignTokens.primaryGradient : null,
                  color: canSend ? null : AppDesignTokens.neutral200,
                  shape: BoxShape.circle,
                  boxShadow: canSend ? AppDesignTokens.shadowPrimary : null,
                ),
                child: Center(
                  child: _isSending
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        )
                      : Icon(
                          Icons.arrow_upward_rounded,
                          color: canSend ? Colors.white : AppDesignTokens.neutral500,
                          size: 24,
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