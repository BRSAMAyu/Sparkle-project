import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/chat/data/services/audio_recording_service.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/home/data/repositories/omnibar_repository.dart';
import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';
import 'package:sparkle/features/home/domain/services/intent_classifier.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

/// OmniBar - Project Cockpit Floating Dock
class OmniBar extends ConsumerStatefulWidget {
  const OmniBar({super.key, this.hintText});
  final String? hintText;

  @override
  ConsumerState<OmniBar> createState() => _OmniBarState();
}

class _OmniBarState extends ConsumerState<OmniBar>
    with SingleTickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final AudioRecordingService _recordingService = AudioRecordingService();
  bool _isLoading = false;
  EnhancedIntentType? _intentType;

  late AnimationController _glowController;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _glowAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );

    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final text = _controller.text;
    final result = IntentClassifier.classify(text);
    final newIntent = result?.type;

    // Notify intent prediction provider
    ref.read(intentPredictionProvider.notifier).onInputChanged(text);

    if (newIntent != _intentType) {
      setState(() => _intentType = newIntent);
      if (!_shouldReduceMotion) {
        if (newIntent != null) {
          unawaited(_glowController.forward(from: 0));
        } else {
          unawaited(_glowController.reverse());
        }
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _glowController.dispose();
    unawaited(_recordingService.dispose());
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() => _isLoading = true);

    try {
      final result = await ref.read(omniBarRepositoryProvider).dispatch(text);
      if (mounted) {
        await _handleResult(result);
        _controller.clear();
        _focusNode.unfocus();
        setState(() => _intentType = null);
        // Clear intent prediction
        ref.read(intentPredictionProvider.notifier).onInputCleared();
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.sendFailedWithError(e));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleResult(Map<String, dynamic> result) async {
    final type = result['action_type'] as String?;
    switch (type) {
      case 'CHAT':
        if (mounted) {
          context.go('/chat');
        }
        return;
      case 'TASK':
        await ref.read(taskListProvider.notifier).refreshTasks();
        await ref.read(dashboardProvider.notifier).refresh();
        return;
      case 'CAPSULE':
        await ref.read(cognitiveProvider.notifier).loadFragments();
        await ref.read(dashboardProvider.notifier).refresh();
        return;
      default:
        return;
    }
  }

  Color _getIntentAccentColor() {
    switch (_intentType) {
      case EnhancedIntentType.chat:
        return DS.info;
      case EnhancedIntentType.task:
        return DS.success;
      case EnhancedIntentType.capsule:
        return DS.prismPurple;
      case EnhancedIntentType.translation:
        return DS.info;
      case EnhancedIntentType.prism:
        return DS.prismPurple;
      case EnhancedIntentType.sprint:
        return DS.warning;
      case EnhancedIntentType.learn:
        return DS.taskReflection;
      case EnhancedIntentType.review:
        return DS.brandSecondary;
      default:
        return DS.textSecondary;
    }
  }

  Color _getIntentGlowColor() =>
      _getIntentAccentColor().withValues(alpha: 0.22);

  void _submitIfNotComposing() {
    final composing = _controller.value.composing;
    if (composing.isValid && !composing.isCollapsed) {
      return;
    }
    unawaited(_submit());
  }

  bool get _shouldReduceMotion {
    final mediaQuery = MediaQuery.maybeOf(context);
    if (mediaQuery == null) return false;
    return mediaQuery.disableAnimations || mediaQuery.accessibleNavigation;
  }

  @override
  Widget build(BuildContext context) {
    final enterToSend = ref.watch(enterToSendProvider);
    final l10n = context.l10n;

    return LayoutBuilder(
      builder: (context, constraints) {
        final isNarrow = constraints.maxWidth < DS.breakpointNarrow;
        final horizontalPadding = isNarrow ? 8.0 : 12.0;
        final verticalPadding = isNarrow ? 2.0 : 4.0;
        final iconSize = isNarrow ? 20.0 : 24.0;
        final accentColor = _getIntentAccentColor();

        return AnimatedBuilder(
          animation: _glowAnimation,
          builder: (context, child) {
            final glowColor = _intentType == null
                ? DS.textSecondary.withValues(alpha: 0.12)
                : _getIntentGlowColor();
            final glowValue = _shouldReduceMotion
                ? (_intentType == null ? 0.0 : 1.0)
                : _glowAnimation.value;
            final glowBlur = isNarrow ? 8.0 : 12.0;
            final glowSpread = isNarrow ? 1.0 : 2.0;

            // Base neoGlass material
            final material = AppMaterials.neoGlass.copyWith(
              // Higher opacity for floating dock
              backgroundColor:
                  context.sparkleColors.surfacePrimary.withValues(alpha: 0.1),
              // Dynamic border based on glow
              borderColor: glowColor.withValues(alpha: 0.3 + glowValue * 0.4),
              borderWidth: 1.5,
              // Dynamic shadow/glow
              shadows: [
                BoxShadow(
                  color: glowColor.withValues(alpha: 0.2 * glowValue),
                  blurRadius: glowBlur,
                  spreadRadius: glowSpread,
                ),
                ...context.sparkleShadows.medium,
              ],
            );

            return MaterialStyler(
              material: material,
              borderRadius: BorderRadius.circular(32),
              padding: EdgeInsets.symmetric(
                horizontal: horizontalPadding,
                vertical: verticalPadding,
              ),
              child: child!,
            );
          },
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  focusNode: _focusNode,
                  textInputAction: enterToSend
                      ? TextInputAction.send
                      : TextInputAction.newline,
                  onSubmitted:
                      enterToSend ? (_) => _submitIfNotComposing() : null,
                  keyboardType: TextInputType.text,
                  style: context.sparkleTypography.bodyLarge.copyWith(
                    color: DS.textPrimary,
                  ),
                  decoration: InputDecoration(
                    hintText: _isListening
                        ? l10n.omnibarListeningHint
                        : (widget.hintText ?? l10n.omnibarDefaultHint),
                    hintStyle: context.sparkleTypography.bodyLarge.copyWith(
                      color: _isListening
                          ? accentColor
                          : DS.textSecondary.withValues(alpha: 0.5),
                    ),
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.zero,
                  ),
                  cursorColor: DS.brandPrimary,
                ),
              ),
              if (_isLoading)
                Padding(
                  padding: const EdgeInsets.all(DS.spacing8),
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor:
                          AlwaysStoppedAnimation<Color>(DS.brandPrimary),
                    ),
                  ),
                )
              else if (_controller.text.isEmpty && !_isListening)
                Tooltip(
                  message: l10n.voiceInputAction,
                  child: SparkleIconButton(
                    icon: Icon(
                      Icons.mic,
                      color: DS.brandPrimaryConst,
                      size: iconSize,
                    ),
                    onPressed: _toggleListening,
                    variant: ButtonVariant.ghost,
                    semanticLabel: l10n.voiceInputAction,
                  ),
                )
              else
                SparkleIconButton(
                  icon: Icon(
                    _isListening
                        ? Icons.stop_circle_outlined
                        : (_intentType == EnhancedIntentType.chat
                            ? Icons.auto_awesome
                            : Icons.arrow_upward_rounded),
                    color: _isListening
                        ? DS.error
                        : (_intentType != null
                            ? accentColor
                            : DS.textSecondary.withValues(alpha: 0.7)),
                    size: iconSize,
                  ),
                  onPressed: _isListening ? _toggleListening : _submit,
                  variant: ButtonVariant.ghost,
                  semanticLabel:
                      _isListening ? l10n.voiceInputStopAction : l10n.send,
                ),
            ],
          ),
        );
      },
    );
  }

  bool _isListening = false;

  Future<bool> _checkPermissions() async {
    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.voiceInputNoPermission);
      }
      return false;
    }
    return true;
  }

  Future<void> _toggleListening() async {
    if (_isListening) {
      // Stop listening
      await _recordingService.stopRecording();
      setState(() {
        _isListening = false;
      });
      _glowController
        ..stop()
        ..reset();
      return;
    }

    // Start listening
    final hasPermission = await _checkPermissions();
    if (!hasPermission) {
      return;
    }

    // Get auth token
    final authToken = await ref.read(authRepositoryProvider).getAccessToken();
    if (authToken == null) {
      if (mounted) {
        AppFeedback.error(context, context.l10n.voiceInputLoginRequired);
      }
      return;
    }

    setState(() {
      _isListening = true;
    });
    if (!_shouldReduceMotion) {
      unawaited(_glowController.repeat(reverse: true));
    }

    final wsUrl = '${ApiConstants.wsBaseUrl}${ApiConstants.wsStt}';

    try {
      await _recordingService.startRecording(
        wsUrl: wsUrl,
        authToken: authToken,
        onTranscription: (text) {
          if (mounted) {
            setState(() {
              _controller.text = text;
            });
            _onTextChanged();
          }
        },
        onError: (error) {
          if (mounted) {
            setState(() {
              _isListening = false;
            });
            _glowController
              ..stop()
              ..reset();
            AppFeedback.error(
              context,
              context.l10n.voiceInputSpeechFailed(error),
            );
          }
        },
        onCompleted: () {
          if (mounted) {
            setState(() {
              _isListening = false;
            });
            _glowController
              ..stop()
              ..reset();
          }
        },
        maxDuration: const Duration(seconds: 30),
      );
    } catch (e) {
      if (mounted) {
        setState(() {
          _isListening = false;
        });
        _glowController
          ..stop()
          ..reset();
        AppFeedback.error(context, context.l10n.voiceInputStartFailed(e));
      }
    }
  }
}
