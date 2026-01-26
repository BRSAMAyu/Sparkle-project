import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/presentation/widgets/voice_input_button.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/document/document.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/presentation/widgets/file_picker_with_presigned.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

class ChatInput extends ConsumerStatefulWidget {
  const ChatInput({
    super.key,
    this.enabled = true,
    this.hintText,
    this.onSend,
    this.quotedMessage,
    this.onCancelQuote,
    this.onFileUploaded,
    this.fileUploadGroupId,
    this.onTextChanged,
  });
  final bool enabled;
  final String? hintText;
  final void Function(String text, {String? replyToId})? onSend;
  final PrivateMessageInfo? quotedMessage;
  final VoidCallback? onCancelQuote;
  final void Function(StoredFile file)? onFileUploaded;
  final String? fileUploadGroupId;
  final void Function(String text)? onTextChanged;

  @override
  ConsumerState<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends ConsumerState<ChatInput> {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final ValueNotifier<bool> _textNotEmpty = ValueNotifier<bool>(false);
  bool _isSending = false;
  bool _isButtonPressed = false;

  void _showAttachmentSheet() {
    if (widget.onFileUploaded != null) {
      showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => FilePickerWithPresignedUpload(
          groupId: widget.fileUploadGroupId,
          onUploaded: (file) {
            Navigator.pop(context);
            widget.onFileUploaded?.call(file);
          },
          onError: (message) => ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(message)),
          ),
        ),
      );
      return;
    }

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => DocumentCleanerSheet(
        onResult: (result) {
          setState(() {
            _controller.text = result;
          });
          _focusNode.requestFocus();
        },
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _controller.addListener(_handleTextChange);
  }

  void _handleTextChange() {
    final hasText = _controller.text.trim().isNotEmpty;
    if (_textNotEmpty.value != hasText) {
      _textNotEmpty.value = hasText;
    }
    // Notify intent prediction
    widget.onTextChanged?.call(_controller.text);
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
    _controller.removeListener(_handleTextChange);
    widget.onTextChanged?.call(''); // Notify empty text
    _controller.dispose();
    _focusNode.dispose();
    _textNotEmpty.dispose();
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
    final enterToSend = ref.watch(enterToSendProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final isNarrow = MediaQuery.of(context).size.width < DS.breakpointNarrow;
    final attachmentVisualSize = isNarrow ? 40.0 : DS.touchTargetMinSize;
    final attachmentIconSize = isNarrow ? 20.0 : DS.iconSizeSm;
    final attachmentPadding = isNarrow ? 4.0 : 8.0;

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
                // --- Attachment Button ---
                SizedBox(
                  width: DS.touchTargetMinSize,
                  height: DS.touchTargetMinSize,
                  child: Center(
                    child: SizedBox(
                      width: attachmentVisualSize,
                      height: attachmentVisualSize,
                      child: IconButton(
                        icon: Icon(
                          Icons.add_circle_outline_rounded,
                          color: isDark ? DS.neutral400 : DS.neutral600,
                        ),
                        iconSize: attachmentIconSize,
                        onPressed: widget.enabled ? _showAttachmentSheet : null,
                        padding: EdgeInsets.all(attachmentPadding),
                        constraints: BoxConstraints.tightFor(
                          width: attachmentVisualSize,
                          height: attachmentVisualSize,
                        ),
                      ),
                    ),
                  ),
                ),

                // --- Voice Input Button ---
                VoiceInputButton(
                  onTranscription: (text) {
                    // 将语音识别结果填入文本框
                    _controller.text = text;
                    _focusNode.requestFocus();
                  },
                  onError: (error) {
                    // 显示错误提示
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text(error)),
                    );
                  },
                  onRecordingStarted: _focusNode.unfocus,
                  onRecordingStopped: _focusNode.requestFocus,
                ),

                const SizedBox(width: DS.spacing8),

                Expanded(
                  child: ValueListenableBuilder<bool>(
                    valueListenable: _textNotEmpty,
                    builder: (context, hasText, child) {
                      final canSend = widget.enabled && !_isSending && hasText;
                      return DecoratedBox(
                        decoration: BoxDecoration(
                          color: isDark ? DS.neutral800 : DS.neutral100,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: isDark ? DS.neutral700 : DS.neutral300,
                          ),
                        ),
                        child: TextField(
                          controller: _controller,
                          focusNode: _focusNode,
                          maxLines: 5,
                          minLines: 1,
                          enabled: canSend,
                          textInputAction: enterToSend
                              ? TextInputAction.send
                              : TextInputAction.newline,
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
                          onSubmitted: canSend && enterToSend
                              ? (_) => _handleSend()
                              : null,
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                GestureDetector(
                  onTapDown: (_) => setState(() => _isButtonPressed = true),
                  onTapUp: (_) => setState(() => _isButtonPressed = false),
                  onTapCancel: () => setState(() => _isButtonPressed = false),
                  onTap: () {
                    final hasText = _controller.text.trim().isNotEmpty;
                    final canSend = widget.enabled && !_isSending && hasText;
                    if (canSend) _handleSend();
                  },
                  child: ValueListenableBuilder<bool>(
                    valueListenable: _textNotEmpty,
                    builder: (context, hasText, child) {
                      final canSend = widget.enabled && !_isSending && hasText;
                      return AnimatedScale(
                        scale: _isButtonPressed ? 0.9 : 1.0,
                        duration: const Duration(milliseconds: 100),
                        curve: Curves.easeInOut,
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          width: 48,
                          height: 48,
                          decoration: BoxDecoration(
                            gradient: canSend ? DS.primaryGradient : null,
                            color: canSend
                                ? null
                                : (isDark ? DS.neutral800 : DS.neutral200),
                            shape: BoxShape.circle,
                            boxShadow: canSend
                                ? [
                                    BoxShadow(
                                      color:
                                          DS.brandPrimary.withValues(alpha: 0.3),
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
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: DS.brandPrimary,),
                                  )
                                : Icon(
                                    Icons.arrow_upward_rounded,
                                    color: canSend
                                        ? DS.brandPrimary
                                        : (isDark
                                            ? DS.brandPrimary30
                                            : DS.brandPrimary38),
                                    size: 24,
                                  ),
                          ),
                        ),
                      );
                    },
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
                    maxLines: 2,
                    overflow: TextOverflow.fade,
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
                icon: Icon(
                  Icons.close_rounded,
                  size: DS.iconSizeSm,
                  color: DS.neutral600,
                ),
                onPressed: widget.onCancelQuote,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ),
          ],
        ),
      );
}
