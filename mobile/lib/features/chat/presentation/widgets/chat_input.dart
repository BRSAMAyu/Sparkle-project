import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/attachment_picker_sheet.dart';
import 'package:sparkle/features/chat/presentation/widgets/voice_input_button.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/document/document.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/presentation/widgets/file_picker_with_presigned.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

/// AI 对话输入组件（原始设计）
/// 左侧：附件 + 语音按钮，中间：输入框，右侧：发送按钮
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
  bool _isAttachmentBursting = false;
  bool _isButtonPressed = false;
  bool _isFocusChanging = false;

  void _showAttachmentSheet() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
    _pulseAttachmentButton();
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (sheetContext) => AttachmentPickerSheet(
          onDirectUpload: _openFileUpload,
          onDocumentClean: _openDocumentCleaner,
        ),
      ),
    );
  }

  void _pulseAttachmentButton() {
    if (!mounted) {
      return;
    }
    setState(() {
      _isAttachmentBursting = true;
    });
    Future.delayed(const Duration(milliseconds: 180), () {
      if (!mounted) {
        return;
      }
      setState(() {
        _isAttachmentBursting = false;
      });
    });
  }

  void _openFileUpload() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => FilePickerWithPresignedUpload(
          groupId: widget.fileUploadGroupId,
          onUploaded: (file) {
            Navigator.pop(context);
            widget.onFileUploaded?.call(file);
          },
          onError: (message) => AppFeedback.error(context, message),
        ),
      ),
    );
  }

  void _openDocumentCleaner() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (context) => DocumentCleanerSheet(
          onResult: (result) {
            if (mounted) {
              setState(() {
                _controller.text = result;
              });
              if (!_isFocusChanging) {
                _isFocusChanging = true;
                Future.delayed(const Duration(milliseconds: 150), () {
                  if (mounted && _focusNode.canRequestFocus) {
                    _focusNode.requestFocus();
                  }
                  _isFocusChanging = false;
                });
              }
            }
          },
        ),
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
    _controller
      ..removeListener(_handleTextChange)
      ..dispose();
    _focusNode.dispose();
    _textNotEmpty.dispose();
    super.dispose();
  }

  Future<void> _handleSend() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSending) return;

    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.messageSend));

    if (widget.onSend != null) {
      widget.onSend!(text, replyToId: widget.quotedMessage?.id);
      _controller.clear();
      widget.onCancelQuote?.call();

      _restoreFocus();
      return;
    }

    setState(() => _isSending = true);
    try {
      _controller.clear();
      _restoreFocus();
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  void _restoreFocus() {
    if (_isFocusChanging) {
      return;
    }
    _isFocusChanging = true;
    Future.delayed(const Duration(milliseconds: 100), () {
      if (mounted && _focusNode.canRequestFocus) {
        _focusNode.requestFocus();
      }
      _isFocusChanging = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final enterToSend = ref.watch(enterToSendProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final reduceMotion = context.reduceMotion;
    final isNarrow = ResponsiveSystem.isMobile(context);
    final attachmentVisualSize = isNarrow ? 40.0 : DS.touchTargetMinSize;
    final attachmentIconSize = isNarrow ? 20.0 : DS.iconSizeSm;
    final attachmentPadding = isNarrow ? 4.0 : 8.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
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
                      child: AnimatedScale(
                        duration: DS.durationFast,
                        curve: Curves.easeOutBack,
                        scale: _isAttachmentBursting ? 1.08 : 1,
                        child: IconButton(
                          icon: Icon(
                            Icons.add_circle_outline_rounded,
                            color: DS.textSecondary,
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
                ),

                // --- Voice Input Button ---
                VoiceInputButton(
                  onTranscription: (text) {
                    _controller.text = text;
                    if (!_isFocusChanging) {
                      _isFocusChanging = true;
                      Future.delayed(const Duration(milliseconds: 150), () {
                        if (mounted && _focusNode.canRequestFocus) {
                          _focusNode.requestFocus();
                        }
                        _isFocusChanging = false;
                      });
                    }
                  },
                  onError: (error) {
                    AppFeedback.error(context, error);
                  },
                  onRecordingStarted: () {
                    _isFocusChanging = true;
                    _focusNode.unfocus();
                    Future.delayed(const Duration(milliseconds: 100), () {
                      if (mounted) {
                        _isFocusChanging = false;
                      }
                    });
                  },
                ),

                const SizedBox(width: DS.spacing8),

                Expanded(
                  child: ValueListenableBuilder<bool>(
                    valueListenable: _textNotEmpty,
                    builder: (context, hasText, child) {
                      final canSend = widget.enabled && !_isSending && hasText;
                      return DecoratedBox(
                        decoration: BoxDecoration(
                          color: DS.surfaceTertiary,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: DS.surfaceTertiary),
                        ),
                        child: TextField(
                          controller: _controller,
                          focusNode: _focusNode,
                          maxLines: 4,
                          minLines: 1,
                          enabled: widget.enabled && !_isSending,
                          textInputAction: enterToSend
                              ? TextInputAction.send
                              : TextInputAction.newline,
                          keyboardType: TextInputType.multiline,
                          decoration: InputDecoration(
                            hintText: widget.hintText ?? 'Type a message...',
                            hintStyle: TextStyle(color: DS.textSecondary),
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
                _buildSendButton(reduceMotion),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSendButton(bool reduceMotion) => ValueListenableBuilder<bool>(
      valueListenable: _textNotEmpty,
      builder: (context, hasText, child) {
        final canSend = widget.enabled && !_isSending && hasText;
        return Semantics(
          button: true,
          enabled: canSend,
          label: 'Send message',
          child: AnimatedScale(
            scale: _isButtonPressed ? 0.9 : 1.0,
            duration: reduceMotion ? Duration.zero : DS.quick,
            curve: Curves.easeInOut,
            child: AnimatedContainer(
              duration: reduceMotion ? Duration.zero : DS.normal,
              width: DS.touchTargetMinSize,
              height: DS.touchTargetMinSize,
              decoration: BoxDecoration(
                gradient: canSend ? DS.primaryGradient : null,
                color: canSend ? null : DS.surfaceTertiary,
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
              child: Material(
                color: Colors.transparent,
                shape: const CircleBorder(),
                child: InkWell(
                  customBorder: const CircleBorder(),
                  onTap: canSend ? _handleSend : null,
                  onHighlightChanged: (pressed) {
                    if (!mounted) return;
                    setState(() => _isButtonPressed = pressed);
                  },
                  child: Center(
                    child: _isSending
                        ? SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: DS.textOnPrimary,
                            ),
                          )
                        : Icon(
                            Icons.arrow_upward_rounded,
                            color:
                                canSend ? DS.textOnPrimary : DS.textSecondary,
                            size: DS.iconSizeBase,
                          ),
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );

  Widget _buildQuotePreview(bool isDark) => Container(
        width: double.infinity,
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: isDark
              ? DS.surfaceSecondary
              : DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border(
            left: BorderSide(color: DS.brandPrimaryConst, width: 4),
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
                      color: DS.brandPrimaryConst,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    widget.quotedMessage!.content ?? '',
                    maxLines: 2,
                    overflow: TextOverflow.fade,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.textSecondary,
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
                  color: DS.textSecondary,
                ),
                onPressed: widget.onCancelQuote,
                padding: const EdgeInsets.all(12),
              ),
            ),
          ],
        ),
      );
}
