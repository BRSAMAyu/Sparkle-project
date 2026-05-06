import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/chat/presentation/widgets/attachment_picker_sheet.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_accessory_pill.dart';
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
    this.studyMaterialsEnabled = true,
    this.availableStudyMaterialsCount = 0,
    this.documentContextMode = DocumentContextMode.auto,
    this.onToggleStudyMaterials,
    this.onOpenStudyMaterials,
    this.onSetDocumentContextMode,
    this.onFreeformCorrection,
  });
  final bool enabled;
  final String? hintText;
  final void Function(String text, {String? replyToId})? onSend;
  final PrivateMessageInfo? quotedMessage;
  final VoidCallback? onCancelQuote;
  final void Function(StoredFile file)? onFileUploaded;
  final String? fileUploadGroupId;
  final void Function(String text)? onTextChanged;
  final bool studyMaterialsEnabled;
  final int availableStudyMaterialsCount;
  final DocumentContextMode documentContextMode;
  final VoidCallback? onToggleStudyMaterials;
  final VoidCallback? onOpenStudyMaterials;
  final ValueChanged<DocumentContextMode>? onSetDocumentContextMode;
  final FutureOr<void> Function(String text)? onFreeformCorrection;

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
    _focusNode.addListener(() {
      if (mounted) setState(() {});
    });
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

  Future<void> _handleFreeformCorrection() async {
    final callback = widget.onFreeformCorrection;
    if (callback == null) return;

    final text = await _showFreeformCorrectionDialog();
    if (text == null || text.isEmpty) return;
    await Future<void>.sync(() => callback(text));
    if (mounted) {
      AppFeedback.info(context, context.l10n.auroraCorrectionSubmitted);
      _restoreFocus();
    }
  }

  Future<String?> _showFreeformCorrectionDialog() {
    final controller = TextEditingController();
    final focusNode = FocusNode();

    return showDialog<String?>(
      context: context,
      builder: (ctx) {
        String? submittedText() {
          final text = controller.text.trim();
          return text.isEmpty ? null : text;
        }

        return AlertDialog(
          title: Text(context.l10n.auroraCorrectionInputTitle),
          content: TextField(
            controller: controller,
            focusNode: focusNode,
            autofocus: true,
            maxLines: 3,
            minLines: 2,
            decoration: InputDecoration(
              hintText: context.l10n.auroraCorrectionInputHint,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(DS.radius12),
              ),
              contentPadding: const EdgeInsets.all(DS.spacing12),
            ),
            textInputAction: TextInputAction.send,
            onSubmitted: (_) {
              final text = submittedText();
              if (text != null) {
                Navigator.of(ctx).pop(text);
              }
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(null),
              child: Text(context.l10n.auroraCorrectionInputCancel),
            ),
            FilledButton(
              onPressed: () => Navigator.of(ctx).pop(submittedText()),
              child: Text(context.l10n.auroraCorrectionInputSend),
            ),
          ],
        );
      },
    ).whenComplete(() {
      focusNode.dispose();
      controller.dispose();
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
          if (widget.onToggleStudyMaterials != null ||
              widget.onFreeformCorrection != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing8,
                0,
                DS.spacing8,
                DS.spacing6,
              ),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Wrap(
                  spacing: DS.spacing8,
                  runSpacing: DS.spacing8,
                  children: [
                    if (widget.onToggleStudyMaterials != null)
                      _SourceTrayPill(
                        mode: widget.documentContextMode,
                        enabled: widget.enabled,
                        onModeChanged: widget.onSetDocumentContextMode,
                      ),
                    if (widget.onToggleStudyMaterials != null &&
                        widget.documentContextMode != DocumentContextMode.off &&
                        widget.availableStudyMaterialsCount > 0)
                      ChatAccessoryPill(
                        icon: Icons.description_outlined,
                        label: context.l10n.chatStudyMaterialsAvailable(
                          widget.availableStudyMaterialsCount,
                        ),
                        trailing: Icon(
                          Icons.arrow_outward_rounded,
                          size: 12,
                          color: DS.textSecondary,
                        ),
                        onTap:
                            widget.enabled ? widget.onOpenStudyMaterials : null,
                        emphasize: true,
                      ),
                    if (widget.onToggleStudyMaterials != null &&
                        widget.documentContextMode == DocumentContextMode.off)
                      ChatAccessoryPill(
                        icon: Icons.pause_circle_outline_rounded,
                        label: context.l10n.chatStudyMaterialsPausedDescription,
                        onTap: widget.enabled
                            ? widget.onToggleStudyMaterials
                            : null,
                      ),
                    if (widget.onFreeformCorrection != null)
                      ChatAccessoryPill(
                        icon: Icons.edit_note_rounded,
                        label: context.l10n.auroraCorrectionFreeformLabel,
                        onTap:
                            widget.enabled ? _handleFreeformCorrection : null,
                        emphasize: true,
                      ),
                  ],
                ),
              ),
            ),
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
                        child: Semantics(
                          button: true,
                          label: 'Open attachment options',
                          child: IconButton(
                            icon: Icon(
                              Icons.add_circle_outline_rounded,
                              color: DS.textSecondary,
                            ),
                            iconSize: attachmentIconSize,
                            onPressed:
                                widget.enabled ? _showAttachmentSheet : null,
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
                      final isFocused = _focusNode.hasFocus;
                      return AnimatedContainer(
                        duration:
                            reduceMotion ? Duration.zero : DS.durationNormal,
                        curve: Curves.easeOut,
                        decoration: BoxDecoration(
                          color: DS.surfaceTertiary,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: isFocused
                                ? DS.brandPrimary.withValues(alpha: 0.8)
                                : DS.surfaceTertiary,
                            width: isFocused ? 1.5 : 1.0,
                          ),
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
                            hintText: widget.hintText ?? (I18nService.instance.isChinese ? '输入消息...' : 'Type a message...'),
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
                  child: Semantics(
                    button: true,
                    label: 'Send message',
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
                                color: canSend
                                    ? DS.textOnPrimary
                                    : DS.textSecondary,
                                size: DS.iconSizeBase,
                              ),
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
                    context.l10n.chatInputQuoting(
                        widget.quotedMessage!.sender.displayName),
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
              child: Semantics(
                button: true,
                label: 'Cancel quoted message',
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
            ),
          ],
        ),
      );
}

class _SourceTrayPill extends StatelessWidget {
  const _SourceTrayPill({
    required this.mode,
    required this.enabled,
    this.onModeChanged,
  });

  final DocumentContextMode mode;
  final bool enabled;
  final ValueChanged<DocumentContextMode>? onModeChanged;

  @override
  Widget build(BuildContext context) {
    final (icon, label) = switch (mode) {
      DocumentContextMode.auto => (
          Icons.auto_awesome_rounded,
          context.l10n.chatStudyMaterialsLabel,
        ),
      DocumentContextMode.userSelected => (
          Icons.playlist_add_check_rounded,
          I18nService.instance.isChinese ? '我的资料' : 'My Sources',
        ),
      DocumentContextMode.taskScope => (
          Icons.task_alt_rounded,
          I18nService.instance.isChinese ? '任务范围' : 'Task Scope',
        ),
      DocumentContextMode.goalScope => (
          Icons.flag_rounded,
          I18nService.instance.isChinese ? '目标范围' : 'Goal Scope',
        ),
      DocumentContextMode.off => (
          Icons.menu_book_outlined,
          context.l10n.chatStudyMaterialsPaused,
        ),
    };
    return ChatAccessoryPill(
      icon: icon,
      label: label,
      selected: mode != DocumentContextMode.off,
      onTap: enabled
          ? () {
              final next = switch (mode) {
                DocumentContextMode.auto => DocumentContextMode.userSelected,
                DocumentContextMode.userSelected =>
                  DocumentContextMode.taskScope,
                DocumentContextMode.taskScope => DocumentContextMode.goalScope,
                DocumentContextMode.goalScope => DocumentContextMode.off,
                DocumentContextMode.off => DocumentContextMode.auto,
              };
              onModeChanged?.call(next);
            }
          : null,
      accentColor: DS.primaryBase,
    );
  }
}
