import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sensory_modals.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/attachment_picker_sheet.dart';
import 'package:sparkle/features/chat/presentation/widgets/voice_input_button.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/presentation/widgets/quick_share_picker_sheet.dart';
import 'package:sparkle/features/file/file.dart';
import 'package:sparkle/features/file/presentation/widgets/file_picker_with_presigned.dart';
import 'package:sparkle/features/tools/tools.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

/// 社群专用输入组件
/// 布局：左侧 + 按钮，点击展开上方工具栏，支持左右滑动切换模式
enum InputMode { text, voice, share }

enum _CommunityVoiceMode { tapToggle, holdToTalk }

class CommunityChatInput extends ConsumerStatefulWidget {
  const CommunityChatInput({
    super.key,
    this.enabled = true,
    this.hintText,
    this.controller,
    this.focusNode,
    this.onSend,
    this.quotedMessage,
    this.onCancelQuote,
    this.onFileUploaded,
    this.fileUploadGroupId,
    this.onTextChanged,
    this.onQuickShare,
  });
  final bool enabled;
  final String? hintText;
  final TextEditingController? controller;
  final FocusNode? focusNode;
  final void Function(String text, {String? replyToId})? onSend;
  final PrivateMessageInfo? quotedMessage;
  final VoidCallback? onCancelQuote;
  final void Function(StoredFile file)? onFileUploaded;
  final String? fileUploadGroupId;
  final void Function(String text)? onTextChanged;
  final void Function(UniversalSharePayload payload)? onQuickShare;

  @override
  ConsumerState<CommunityChatInput> createState() => _CommunityChatInputState();
}

class _CommunityChatInputState extends ConsumerState<CommunityChatInput> {
  late TextEditingController _controller;
  late FocusNode _focusNode;
  late bool _ownsController;
  late bool _ownsFocusNode;
  final ValueNotifier<bool> _textNotEmpty = ValueNotifier<bool>(false);
  bool _isSending = false;
  bool _isButtonPressed = false;
  bool _isFocusChanging = false;
  bool _voiceAutoStart = false;
  bool _isVoiceRecording = false;
  String _voiceDraftText = '';
  _CommunityVoiceMode _voiceMode = _CommunityVoiceMode.holdToTalk;
  // 输入模式状态
  InputMode _inputMode = InputMode.text;
  // 工具栏是否展开
  bool _toolbarExpanded = false;

  void _showAttachmentSheet() {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (sheetContext) => AttachmentPickerSheet(
          title: context.l10n.chatCommunityShareMaterial,
          primaryTitle: context.l10n.chatCommunityShareDesc,
          primarySubtitle: context.l10n.chatCommunityShareUploadHint,
          onDirectUpload: _openFileUpload,
          onDocumentClean: _openDocumentCleaner,
        ),
      ),
    );
  }

  void _openFileUpload() {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
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
    unawaited(
      launchTool(
        context,
        ref,
        'document_cleaner',
        launchContext: ToolLaunchContext.chatInput,
        preference: ToolOpenPreference.sheet,
        onTextResult: (result) {
          if (!mounted) return;
          setState(() => _controller.text = result);
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
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _ownsFocusNode = widget.focusNode == null;
    _controller = widget.controller ?? TextEditingController();
    _focusNode = widget.focusNode ?? FocusNode();
    _controller.addListener(_handleTextChange);
  }

  @override
  void didUpdateWidget(CommunityChatInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      _controller.removeListener(_handleTextChange);
      if (_ownsController) {
        _controller.dispose();
      }
      _ownsController = widget.controller == null;
      _controller = widget.controller ?? TextEditingController();
      _controller.addListener(_handleTextChange);
    }
    if (oldWidget.focusNode != widget.focusNode) {
      if (_ownsFocusNode) {
        _focusNode.dispose();
      }
      _ownsFocusNode = widget.focusNode == null;
      _focusNode = widget.focusNode ?? FocusNode();
    }
    if (widget.quotedMessage != null && oldWidget.quotedMessage == null) {
      _focusNode.requestFocus();
    }
  }

  void _handleTextChange() {
    final hasText = _controller.text.trim().isNotEmpty;
    if (_textNotEmpty.value != hasText) {
      _textNotEmpty.value = hasText;
    }
    widget.onTextChanged?.call(_controller.text);
  }

  @override
  void dispose() {
    _controller.removeListener(_handleTextChange);
    if (_ownsController) {
      _controller.dispose();
    }
    if (_ownsFocusNode) {
      _focusNode.dispose();
    }
    _textNotEmpty.dispose();
    super.dispose();
  }

  Future<void> _handleSend() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSending) return;

    if (widget.onSend != null) {
      widget.onSend!(text, replyToId: widget.quotedMessage?.id);
      _controller.clear();
      widget.onCancelQuote?.call();

      if (!_isFocusChanging) {
        _isFocusChanging = true;
        Future.delayed(const Duration(milliseconds: 100), () {
          if (mounted && _focusNode.canRequestFocus) {
            _focusNode.requestFocus();
          }
          _isFocusChanging = false;
        });
      }
      return;
    }

    setState(() => _isSending = true);
    try {
      _controller.clear();
      if (!_isFocusChanging) {
        _isFocusChanging = true;
        Future.delayed(const Duration(milliseconds: 100), () {
          if (mounted && _focusNode.canRequestFocus) {
            _focusNode.requestFocus();
          }
          _isFocusChanging = false;
        });
      }
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  void _showQuickShare() {
    unawaited(
      showSensoryModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
        builder: (context) => QuickSharePickerSheet(
          onShare: (payload) {
            widget.onQuickShare?.call(payload);
          },
        ),
      ),
    );
  }

  void _toggleToolbar() {
    setState(() => _toolbarExpanded = !_toolbarExpanded);
  }

  void _switchToTextMode() {
    setState(() {
      _inputMode = InputMode.text;
      _voiceAutoStart = false;
      _isVoiceRecording = false;
    });
  }

  void _startToolbarVoiceRecording() {
    if (!widget.enabled) return;
    setState(() {
      _inputMode = InputMode.voice;
      _toolbarExpanded = false;
      _voiceMode = _CommunityVoiceMode.tapToggle;
      _voiceAutoStart = true;
      _voiceDraftText = '';
    });
    _focusNode.unfocus();
  }

  void _appendVoiceTextToComposer(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty) {
      _switchToTextMode();
      return;
    }
    final current = _controller.text.trim();
    final merged = current.isEmpty ? trimmed : '$current\n$trimmed';
    setState(() {
      _controller.text = merged;
      _controller.selection = TextSelection.collapsed(
        offset: _controller.text.length,
      );
      _voiceDraftText = '';
      _voiceAutoStart = false;
      _isVoiceRecording = false;
      _inputMode = InputMode.text;
    });
    widget.onTextChanged?.call(_controller.text);
    if (!_isFocusChanging) {
      _isFocusChanging = true;
      Future.delayed(const Duration(milliseconds: 120), () {
        if (mounted && _focusNode.canRequestFocus) {
          _focusNode.requestFocus();
        }
        _isFocusChanging = false;
      });
    }
  }

  void _sendVoiceTextDirectly(String text) {
    final trimmed = text.trim();
    setState(() {
      _voiceDraftText = '';
      _voiceAutoStart = false;
      _isVoiceRecording = false;
      _inputMode = InputMode.text;
    });
    if (trimmed.isEmpty) return;
    widget.onSend?.call(trimmed, replyToId: widget.quotedMessage?.id);
    widget.onCancelQuote?.call();
  }

  @override
  Widget build(BuildContext context) {
    final enterToSend = ref.watch(enterToSendProvider);
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final reduceMotion = context.reduceMotion;

    return Padding(
      padding: const EdgeInsets.only(bottom: DS.spacing8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // 引用预览
          if (widget.quotedMessage != null) _buildQuotePreview(isDark),
          if (_inputMode == InputMode.voice &&
              (_isVoiceRecording || _voiceDraftText.trim().isNotEmpty))
            _buildVoicePreview(context, isDark),

          // === 可展开的工具栏 ===
          if (_toolbarExpanded) _buildToolbar(context, isDark),

          // === 可滑动的输入区域 ===
          _buildSwipeableInputArea(
            context,
            isDark: isDark,
            enterToSend: enterToSend,
            reduceMotion: reduceMotion,
          ),
        ],
      ),
    );
  }

  /// 构建上方工具栏（可展开）
  Widget _buildToolbar(BuildContext context, bool isDark) => Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing4,
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: BorderRadius.circular(12),
            boxShadow: DS.shadowSm,
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // 附件按钮
                _ToolbarButton(
                  icon: Icons.attach_file_rounded,
                  label: context.l10n.chatInputAttachment,
                  onPressed: widget.enabled ? _showAttachmentSheet : null,
                  isDark: isDark,
                ),
                const SizedBox(width: DS.spacing24),
                // 语音按钮
                _ToolbarButton(
                  icon: Icons.mic_none,
                  label: context.l10n.chatInputVoice,
                  onPressed:
                      widget.enabled ? _startToolbarVoiceRecording : null,
                  isDark: isDark,
                ),
                // 分享按钮（仅当有分享回调时显示）
                if (widget.onQuickShare != null) ...[
                  const SizedBox(width: DS.spacing24),
                  _ToolbarButton(
                    icon: Icons.share_rounded,
                    label: context.l10n.chatInputShare,
                    onPressed: widget.enabled ? _showQuickShare : null,
                    isDark: isDark,
                  ),
                ],
              ],
            ),
          ),
        ),
      );

  /// 构建输入区域（滑动只作用于中间区域）
  Widget _buildSwipeableInputArea(
    BuildContext context, {
    required bool isDark,
    required bool enterToSend,
    required bool reduceMotion,
  }) =>
      AnimatedSwitcher(
        duration: const Duration(milliseconds: 200),
        switchInCurve: Curves.easeInOut,
        switchOutCurve: Curves.easeInOut,
        child: _buildInputContentForMode(
          isDark: isDark,
          enterToSend: enterToSend,
          reduceMotion: reduceMotion,
        ),
      );

  /// 处理左滑（向左方向滑）：text -> voice -> share -> text
  void _handleSwipeLeft() {
    if (!widget.enabled) return;
    setState(() {
      switch (_inputMode) {
        case InputMode.text:
          _inputMode = InputMode.voice;
          _toolbarExpanded = false;
          _focusNode.unfocus();
        case InputMode.voice:
          _inputMode =
              widget.onQuickShare != null ? InputMode.share : InputMode.text;
        case InputMode.share:
          _inputMode = InputMode.text;
      }
    });
  }

  /// 处理右滑（向右方向滑）：text -> share -> voice -> text
  void _handleSwipeRight() {
    if (!widget.enabled) return;
    setState(() {
      switch (_inputMode) {
        case InputMode.text:
          if (widget.onQuickShare != null) {
            _inputMode = InputMode.share;
            _toolbarExpanded = false;
            _focusNode.unfocus();
          } else {
            _inputMode = InputMode.voice;
            _toolbarExpanded = false;
            _focusNode.unfocus();
          }
        case InputMode.voice:
          _inputMode = InputMode.text;
        case InputMode.share:
          _inputMode = InputMode.voice;
      }
    });
  }

  /// 根据模式构建输入内容
  Widget _buildInputContentForMode({
    required bool isDark,
    required bool enterToSend,
    required bool reduceMotion,
  }) {
    switch (_inputMode) {
      case InputMode.voice:
        return _buildVoiceInputMode(isDark);
      case InputMode.share:
        return _buildShareInputMode(isDark);
      case InputMode.text:
        return _buildTextInputMode(
          isDark: isDark,
          enterToSend: enterToSend,
          reduceMotion: reduceMotion,
        );
    }
  }

  /// 文字输入模式
  Widget _buildTextInputMode({
    required bool isDark,
    required bool enterToSend,
    required bool reduceMotion,
  }) =>
      Padding(
        key: const ValueKey('text-mode'),
        padding: const EdgeInsets.all(DS.spacing8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            // 左侧 + 按钮（展开工具栏）- 固定不动
            SizedBox(
              width: DS.touchTargetMinSize,
              height: DS.touchTargetMinSize,
              child: Center(
                child: Semantics(
                  button: true,
                  label: 'Open message tools',
                  child: IconButton(
                    icon: Icon(
                      Icons.add_circle_outline_rounded,
                      color: DS.textSecondary,
                    ),
                    iconSize: DS.iconSizeSm,
                    onPressed: widget.enabled ? _toggleToolbar : null,
                    padding: const EdgeInsets.all(12),
                    constraints: const BoxConstraints.tightFor(
                      width: DS.touchTargetMinSize,
                      height: DS.touchTargetMinSize,
                    ),
                  ),
                ),
              ),
            ),

            // 输入框（居中，全宽）- 可滑动区域
            Expanded(
              child: Semantics(
                button: true,
                label: 'Swipe text input to switch input modes',
                child: GestureDetector(
                  onHorizontalDragEnd: (details) {
                    if (details.primaryVelocity == null) return;
                    // 左滑 (velocity > 0) -> 语音模式
                    if (details.primaryVelocity! > 300) {
                      _handleSwipeLeft();
                    }
                    // 右滑 (velocity < 0) -> 分享模式
                    else if (details.primaryVelocity! < -300) {
                      _handleSwipeRight();
                    }
                  },
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
              ),
            ),
            const SizedBox(width: DS.spacing12),
            // 发送按钮 - 固定不动
            _buildSendButton(reduceMotion: reduceMotion),
          ],
        ),
      );

  /// 语音输入模式
  Widget _buildVoiceInputMode(bool isDark) => Padding(
        key: const ValueKey('voice-mode'),
        padding: const EdgeInsets.all(DS.spacing8),
        child: Row(
          children: [
            // 取消按钮 - 固定不动
            SizedBox(
              width: DS.touchTargetMinSize,
              height: DS.touchTargetMinSize,
              child: Semantics(
                button: true,
                label: 'Return to text input',
                child: IconButton(
                  icon: Icon(
                    Icons.close,
                    color: DS.textSecondary,
                    size: DS.iconSizeMd,
                  ),
                  onPressed: _switchToTextMode,
                  padding: const EdgeInsets.all(12),
                ),
              ),
            ),
            // 放大的语音按钮（居中）- 可滑动区域
            Expanded(
              child: Semantics(
                button: true,
                label: 'Swipe voice input to switch input modes',
                child: GestureDetector(
                  onHorizontalDragEnd: (details) {
                    if (details.primaryVelocity == null) return;
                    // 左滑 (velocity > 0) -> 分享模式（如果有）或文字模式
                    if (details.primaryVelocity! > 300) {
                      _handleSwipeLeft();
                    }
                    // 右滑 (velocity < 0) -> 文字模式
                    else if (details.primaryVelocity! < -300) {
                      _handleSwipeRight();
                    }
                  },
                  child: Center(
                    child: VoiceInputButton(
                      size:
                          _voiceMode == _CommunityVoiceMode.tapToggle ? 56 : 72,
                      interactionMode:
                          _voiceMode == _CommunityVoiceMode.tapToggle
                              ? VoiceInputInteractionMode.tapToggle
                              : VoiceInputInteractionMode.holdToTalk,
                      autoStart: _voiceAutoStart,
                      showGestureHints: true,
                      onTranscription: (_) {},
                      onLiveTranscription: (text) {
                        if (!mounted) return;
                        setState(() {
                          _voiceDraftText = text;
                        });
                      },
                      onRecordingFinished: (text, action) {
                        switch (action) {
                          case VoiceReleaseAction.cancel:
                            setState(() {
                              _voiceDraftText = '';
                            });
                            _switchToTextMode();
                          case VoiceReleaseAction.send:
                            _sendVoiceTextDirectly(text);
                          case VoiceReleaseAction.commit:
                            _appendVoiceTextToComposer(text);
                        }
                      },
                      onDraftCancelled: () {
                        if (!mounted) return;
                        setState(() {
                          _voiceDraftText = '';
                          _voiceAutoStart = false;
                          _isVoiceRecording = false;
                        });
                      },
                      onError: (error) => AppFeedback.error(context, error),
                      onRecordingStarted: () {
                        if (!mounted) return;
                        setState(() {
                          _isVoiceRecording = true;
                          _voiceAutoStart = false;
                        });
                      },
                      onRecordingStopped: () {
                        if (!mounted) return;
                        setState(() {
                          _isVoiceRecording = false;
                          _voiceAutoStart = false;
                        });
                      },
                    ),
                  ),
                ),
              ),
            ),
            // 占位保持对称 - 固定不动
            const SizedBox(width: DS.touchTargetMinSize),
          ],
        ),
      );

  /// 分享输入模式
  Widget _buildShareInputMode(bool isDark) => Padding(
        key: const ValueKey('share-mode'),
        padding: const EdgeInsets.all(DS.spacing8),
        child: Row(
          children: [
            // 取消按钮 - 固定不动
            SizedBox(
              width: DS.touchTargetMinSize,
              height: DS.touchTargetMinSize,
              child: Semantics(
                button: true,
                label: 'Return to text input',
                child: IconButton(
                  icon: Icon(
                    Icons.close,
                    color: DS.textSecondary,
                    size: DS.iconSizeMd,
                  ),
                  onPressed: _switchToTextMode,
                  padding: const EdgeInsets.all(12),
                ),
              ),
            ),
            // 分享提示区域（居中）- 可滑动区域
            Expanded(
              child: Semantics(
                button: true,
                label: 'Open quick share options',
                child: GestureDetector(
                  onHorizontalDragEnd: (details) {
                    if (details.primaryVelocity == null) return;
                    // 左滑 (velocity > 0) -> 文字模式
                    if (details.primaryVelocity! > 300) {
                      _handleSwipeLeft();
                    }
                    // 右滑 (velocity < 0) -> 语音模式
                    else if (details.primaryVelocity! < -300) {
                      _handleSwipeRight();
                    }
                  },
                  child: InkWell(
                    onTap: () {
                      _showQuickShare();
                      _switchToTextMode();
                    },
                    borderRadius: BorderRadius.circular(16),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing16,
                        vertical: DS.spacing12,
                      ),
                      decoration: BoxDecoration(
                        color: DS.surfaceTertiary,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.share_rounded,
                            color: DS.brandPrimary,
                            size: DS.iconSizeMd,
                          ),
                          const SizedBox(width: DS.spacing8),
                          Text(
                            context.l10n.chatInputTapToShare,
                            style: TextStyle(
                              color: DS.textSecondary,
                              fontSize: DS.fontSizeBase,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
            // 占位保持对称 - 固定不动
            const SizedBox(width: DS.touchTargetMinSize),
          ],
        ),
      );

  Widget _buildVoicePreview(BuildContext context, bool isDark) {
    final text = _voiceDraftText.trim();
    final helper = _voiceMode == _CommunityVoiceMode.tapToggle
        ? (_isVoiceRecording
            ? context.l10n.chatVoiceTapToEnd
            : context.l10n.chatVoiceEndToInput)
        : (_isVoiceRecording
            ? context.l10n.chatVoiceHoldHint
            : context.l10n.chatVoiceLongPressStart);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        DS.spacing12,
        DS.spacing4,
        DS.spacing12,
        DS.spacing4,
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: isDark ? DS.surfaceSecondary : DS.surfacePanel,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.18),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _isVoiceRecording
                      ? Icons.graphic_eq_rounded
                      : Icons.notes_rounded,
                  size: DS.iconSizeSm,
                  color: DS.brandPrimary,
                ),
                const SizedBox(width: DS.spacing8),
                Expanded(
                  child: Text(
                    helper,
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                ),
              ],
            ),
            if (text.isNotEmpty) ...[
              const SizedBox(height: DS.spacing8),
              Text(
                text,
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: DS.fontSizeSm,
                  height: 1.45,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  /// 构建发送按钮
  Widget _buildSendButton({required bool reduceMotion}) =>
      ValueListenableBuilder<bool>(
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
                    label: 'Send community message',
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
        margin: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing4,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing8,
        ),
        decoration: BoxDecoration(
          color: isDark ? DS.surfaceSecondary : DS.surfacePanel,
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
                    context.l10n.chatQuotePrefix(
                      widget.quotedMessage!.sender.displayName,
                    ),
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
                      color: isDark ? DS.textSecondary : DS.textPrimary,
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

/// 工具栏按钮组件
class _ToolbarButton extends StatelessWidget {
  const _ToolbarButton({
    required this.icon,
    required this.label,
    required this.isDark,
    this.onPressed,
  });

  final IconData icon;
  final String label;
  final bool isDark;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final isEnabled = onPressed != null;

    return Semantics(
      button: true,
      label: label,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: DS.iconSizeMd,
                color: isEnabled
                    ? (isDark ? DS.neutral300 : DS.neutral600)
                    : DS.neutral400,
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                label,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: isEnabled ? DS.textSecondary : DS.neutral400,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
