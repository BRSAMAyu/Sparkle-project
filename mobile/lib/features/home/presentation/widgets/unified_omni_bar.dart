import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/chat/data/models/chat_mode.dart';
import 'package:sparkle/features/chat/data/models/expert_catalog_model.dart';
import 'package:sparkle/features/chat/data/services/audio_recording_service.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_mode_provider.dart';
import 'package:sparkle/features/chat/presentation/providers/expert_catalog_provider.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/home/data/repositories/omnibar_repository.dart';
import 'package:sparkle/features/home/domain/services/enhanced_intent_classifier.dart';
import 'package:sparkle/features/home/domain/services/intent_classifier.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';
import 'package:sparkle/features/home/presentation/providers/intent_prediction_provider.dart';
import 'package:sparkle/features/task/task.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

const double _kUnifiedOmniInputHeight = 52;
const double _kUnifiedPredictionHeight = 36;
const double _kUnifiedAgentPanelHeight = 44;

class UnifiedOmniBar extends ConsumerStatefulWidget {
  const UnifiedOmniBar({
    super.key,
    this.hintText,
    this.onHeightChanged,
  });

  final String? hintText;
  final ValueChanged<double>? onHeightChanged;

  @override
  ConsumerState<UnifiedOmniBar> createState() => _UnifiedOmniBarState();
}

class _UnifiedOmniBarState extends ConsumerState<UnifiedOmniBar>
    with TickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final AudioRecordingService _recordingService = AudioRecordingService();

  bool _agentPanelExpanded = false;
  bool _hasText = false;
  bool _isListening = false;
  bool _isLoading = false;
  double? _lastReportedHeight;
  EnhancedIntentType? _intentType;

  late final AnimationController _glowController;
  late final Animation<double> _glowAnimation;
  late final AnimationController _panelController;
  late final Animation<double> _panelSizeFactor;
  late final Animation<Offset> _panelSlideAnimation;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _glowAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );
    _panelController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
    );
    final panelCurve = CurvedAnimation(
      parent: _panelController,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
    _panelSizeFactor = Tween<double>(begin: 0, end: 1).animate(panelCurve);
    _panelSlideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.15),
      end: Offset.zero,
    ).animate(panelCurve);
    _panelController.addListener(() {
      if (mounted) {
        setState(() {});
      }
    });
    _controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    _glowController.dispose();
    _panelController.dispose();
    unawaited(_recordingService.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currentMode = ref.watch(chatModeProvider);
    final predictions = ref.watch(visiblePredictionsProvider);
    final catalog = ref.watch(multiAgentCatalogProvider);
    final entryModes = _buildEntryModes(catalog);
    final hasPredictions = predictions.isNotEmpty;
    final agentPanelHeight = _kUnifiedAgentPanelHeight * _panelSizeFactor.value;
    final showAgentPanel = _agentPanelExpanded || _panelController.value > 0;
    final totalHeight = _kUnifiedOmniInputHeight +
        (hasPredictions ? _kUnifiedPredictionHeight : 0) +
        agentPanelHeight;

    _reportHeight(totalHeight);

    return LayoutBuilder(
      builder: (context, constraints) {
        final isNarrow = constraints.maxWidth < DS.breakpointNarrow;
        final rowHorizontalPadding = isNarrow ? 8.0 : 12.0;
        final inputPadding = isNarrow ? 2.0 : 4.0;
        final iconSize = isNarrow ? 20.0 : 22.0;
        final accentColor = _getIntentAccentColor();

        return AnimatedSize(
          duration: DS.quick,
          curve: DS.curveEaseOut,
          alignment: Alignment.bottomCenter,
          child: AnimatedBuilder(
            animation: _glowAnimation,
            builder: (context, child) {
              final glowColor = _intentType == null
                  ? DS.textSecondary.withValues(alpha: 0.12)
                  : _getIntentGlowColor();
              final glowValue = _shouldReduceMotion
                  ? (_intentType == null ? 0 : 1)
                  : _glowAnimation.value;
              final material = AppMaterials.neoGlass.copyWith(
                backgroundColor: context.sparkleColors.surfacePrimary
                    .withValues(alpha: 0.14),
                borderColor: glowColor.withValues(alpha: 0.3 + glowValue * 0.4),
                borderWidth: 1.5,
                shadows: [
                  BoxShadow(
                    color: glowColor.withValues(alpha: 0.2 * glowValue),
                    blurRadius: isNarrow ? 8 : 12,
                    spreadRadius: isNarrow ? 1 : 2,
                  ),
                  ...context.sparkleShadows.medium,
                ],
              );

              return MaterialStyler(
                material: material,
                borderRadius: BorderRadius.circular(28),
                padding: EdgeInsets.zero,
                child: child!,
              );
            },
            child: ClipRRect(
              borderRadius: BorderRadius.circular(28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (showAgentPanel)
                    _buildAgentPanelSection(
                      context: context,
                      currentMode: currentMode,
                      entryModes: entryModes,
                    ),
                  if (hasPredictions)
                    _buildPredictionSection(
                      context: context,
                      predictions: predictions,
                    ),
                  _buildInputRow(
                    context: context,
                    currentMode: currentMode,
                    accentColor: accentColor,
                    rowHorizontalPadding: rowHorizontalPadding,
                    inputPadding: inputPadding,
                    iconSize: iconSize,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  List<ChatMode> _buildEntryModes(AsyncValue<MultiAgentCatalog> catalog) {
    final multiAgentModes =
        ChatMode.values.where((mode) => mode.isMultiAgent).toList();
    final expertModes = catalog.when(
      data: (value) => value.experts
          .where((ExpertCatalogExpert expert) => expert.enabled)
          .take(6)
          .map(
            (ExpertCatalogExpert expert) => ChatModeExpert(
              expertId: expert.id,
              expertName: expert.displayName,
            ),
          )
          .toList(),
      loading: () => <ChatMode>[],
      error: (_, __) => <ChatMode>[],
    );
    return [...multiAgentModes, ...expertModes];
  }

  void _reportHeight(double totalHeight) {
    if (widget.onHeightChanged == null || totalHeight == _lastReportedHeight) {
      return;
    }
    _lastReportedHeight = totalHeight;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        widget.onHeightChanged!(totalHeight);
      }
    });
  }

  Widget _buildAgentPanelSection({
    required BuildContext context,
    required ChatMode currentMode,
    required List<ChatMode> entryModes,
  }) =>
      ClipRect(
        child: SizeTransition(
          sizeFactor: _panelSizeFactor,
          axisAlignment: -1,
          child: SlideTransition(
            position: _panelSlideAnimation,
            child: Container(
              height: _kUnifiedAgentPanelHeight,
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(color: DS.borderSubtle),
                ),
              ),
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing6,
                ),
                scrollDirection: Axis.horizontal,
                itemCount: entryModes.length,
                separatorBuilder: (_, __) => const SizedBox(width: DS.spacing8),
                itemBuilder: (context, index) {
                  final mode = entryModes[index];
                  return _AgentModeChip(
                    mode: mode,
                    isSelected: currentMode.apiValue == mode.apiValue,
                    onTap: () => _selectMode(mode),
                  );
                },
              ),
            ),
          ),
        ),
      );

  Widget _buildPredictionSection({
    required BuildContext context,
    required List<PredictedAction> predictions,
  }) =>
      AnimatedSwitcher(
        duration: DS.durationFast,
        switchInCurve: DS.curveEaseOut,
        switchOutCurve: DS.curveEaseOut,
        child: Container(
          key: ValueKey('prediction_section_${predictions.length}'),
          height: _kUnifiedPredictionHeight,
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(color: DS.borderSubtle),
            ),
          ),
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing10,
              vertical: DS.spacing4,
            ),
            scrollDirection: Axis.horizontal,
            itemCount: predictions.length,
            separatorBuilder: (_, __) => const SizedBox(width: DS.spacing8),
            itemBuilder: (context, index) => _IntentChip(
              prediction: predictions[index],
            ),
          ),
        ),
      );

  Widget _buildInputRow({
    required BuildContext context,
    required ChatMode currentMode,
    required Color accentColor,
    required double rowHorizontalPadding,
    required double inputPadding,
    required double iconSize,
  }) {
    final enterToSend = ref.watch(enterToSendProvider);
    final canSubmit = _hasText && !_isLoading;

    return SizedBox(
      height: _kUnifiedOmniInputHeight,
      child: Padding(
        padding: EdgeInsets.symmetric(
          horizontal: rowHorizontalPadding,
          vertical: inputPadding,
        ),
        child: Row(
          children: [
            Tooltip(
              message: _isListening ? '停止录音' : '语音输入',
              child: SparkleIconButton(
                icon: Icon(
                  _isListening ? Icons.stop_circle_outlined : Icons.mic,
                  color: _isListening ? DS.error : DS.brandPrimaryConst,
                  size: iconSize,
                ),
                onPressed: _toggleListening,
                variant: ButtonVariant.ghost,
                semanticLabel: _isListening ? '停止录音' : '语音输入',
              ),
            ),
            const SizedBox(width: DS.spacing4),
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
                      ? 'Listening...'
                      : (widget.hintText ?? 'Tell me what you think...'),
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
            const SizedBox(width: DS.spacing4),
            _AgentToggleButton(
              currentMode: currentMode,
              expanded: _agentPanelExpanded,
              onTap: _toggleAgentPanel,
            ),
            const SizedBox(width: DS.spacing4),
            if (_isLoading)
              const SizedBox(
                width: DS.touchTargetMinSize,
                height: DS.touchTargetMinSize,
                child: Center(
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
              )
            else
              SparkleIconButton(
                icon: Icon(
                  _intentType == EnhancedIntentType.chat
                      ? Icons.auto_awesome
                      : Icons.arrow_upward_rounded,
                  color: canSubmit
                      ? accentColor
                      : DS.textSecondary.withValues(alpha: 0.45),
                  size: iconSize,
                ),
                onPressed: canSubmit ? _submit : null,
                disabled: !canSubmit,
                variant: ButtonVariant.ghost,
                semanticLabel: '发送',
              ),
          ],
        ),
      ),
    );
  }

  void _onTextChanged() {
    final text = _controller.text;
    final result = IntentClassifier.classify(text);
    final newIntent = result?.type;
    final hasText = text.isNotEmpty;

    ref.read(intentPredictionProvider.notifier).onInputChanged(text);

    if (newIntent != _intentType || hasText != _hasText) {
      setState(() {
        _intentType = newIntent;
        _hasText = hasText;
      });
    }

    if (_shouldReduceMotion) {
      return;
    }
    if (newIntent != null) {
      unawaited(_glowController.forward(from: 0));
    } else {
      unawaited(_glowController.reverse());
    }
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() => _isLoading = true);

    try {
      final result = await ref.read(omniBarRepositoryProvider).dispatch(text);
      if (!mounted) return;

      await _handleResult(result);
      _controller.clear();
      _focusNode.unfocus();
      setState(() {
        _hasText = false;
        _intentType = null;
      });
      ref.read(intentPredictionProvider.notifier).onInputCleared();
    } catch (e) {
      if (mounted) {
        AppFeedback.error(context, '发送失败: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _handleResult(Map<String, dynamic> result) async {
    final type = result['action_type'] as String?;
    switch (type) {
      case 'CHAT':
        if (mounted) {
          unawaited(context.push('/chat'));
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

  Future<void> _toggleListening() async {
    if (_isListening) {
      await _recordingService.stopRecording();
      setState(() {
        _isListening = false;
      });
      _glowController
        ..stop()
        ..reset();
      return;
    }

    final hasPermission = await _checkPermissions();
    if (!hasPermission) return;

    final authToken = await ref.read(authRepositoryProvider).getAccessToken();
    if (authToken == null) {
      if (mounted) {
        AppFeedback.error(context, '未登录，请先登录');
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
          if (!mounted) return;
          setState(() {
            _controller.text = text;
          });
          _onTextChanged();
        },
        onError: (error) {
          if (!mounted) return;
          setState(() {
            _isListening = false;
          });
          _glowController
            ..stop()
            ..reset();
          AppFeedback.error(context, '语音识别失败: $error');
        },
        onCompleted: () {
          if (!mounted) return;
          setState(() {
            _isListening = false;
          });
          _glowController
            ..stop()
            ..reset();
        },
        maxDuration: const Duration(seconds: 30),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isListening = false;
      });
      _glowController
        ..stop()
        ..reset();
      AppFeedback.error(context, '启动录音失败: $e');
    }
  }

  Future<bool> _checkPermissions() async {
    final status = await Permission.microphone.request();
    if (!status.isGranted) {
      if (mounted) {
        AppFeedback.error(context, '需要麦克风权限才能使用语音输入');
      }
      return false;
    }
    return true;
  }

  void _toggleAgentPanel() {
    unawaited(HapticFeedback.lightImpact());
    setState(() {
      _agentPanelExpanded = !_agentPanelExpanded;
    });
    if (_agentPanelExpanded) {
      unawaited(_panelController.forward());
    } else {
      unawaited(_panelController.reverse());
    }
  }

  Future<void> _selectMode(ChatMode mode) async {
    unawaited(HapticFeedback.lightImpact());
    ref.read(chatModeNotifierProvider.notifier).setMode(mode);
    ref.read(lastMultiAgentModeProvider.notifier).setMode(mode);

    if (_agentPanelExpanded) {
      setState(() {
        _agentPanelExpanded = false;
      });
      unawaited(_panelController.reverse());
    }

    if (mounted) {
      unawaited(context.push('/chat'));
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

  bool get _shouldReduceMotion {
    final mediaQuery = MediaQuery.maybeOf(context);
    if (mediaQuery == null) return false;
    return mediaQuery.disableAnimations || mediaQuery.accessibleNavigation;
  }

  void _submitIfNotComposing() {
    final composing = _controller.value.composing;
    if (composing.isValid && !composing.isCollapsed) {
      return;
    }
    unawaited(_submit());
  }
}

class _IntentChip extends StatelessWidget {
  const _IntentChip({required this.prediction});

  final PredictedAction prediction;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: prediction.action,
        borderRadius: DS.borderRadiusFull,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing4,
          ),
          decoration: BoxDecoration(
            color: prediction.color?.withValues(alpha: 0.15) ??
                DS.brandPrimary.withValues(alpha: 0.1),
            borderRadius: DS.borderRadiusFull,
            border: Border.all(
              color: prediction.color?.withValues(alpha: 0.3) ??
                  DS.brandPrimary.withValues(alpha: 0.2),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                prediction.icon,
                size: DS.iconSizeXs,
                color: prediction.color ?? DS.brandPrimary,
              ),
              const SizedBox(width: DS.spacing6),
              Text(
                prediction.label,
                style: context.sparkleTypography.labelSmall.copyWith(
                  color: prediction.color ?? DS.brandPrimary,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      );
}

class _AgentToggleButton extends StatelessWidget {
  const _AgentToggleButton({
    required this.currentMode,
    required this.expanded,
    required this.onTap,
  });

  final ChatMode currentMode;
  final bool expanded;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isStandard = !currentMode.isMultiAgent;
    final accentColor = isStandard ? DS.textSecondary : currentMode.color;
    final icon = isStandard ? Icons.person_outline_rounded : currentMode.icon;

    return Semantics(
      button: true,
      label: '切换 Agent 模式',
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: DS.quick,
          curve: DS.curveEaseOut,
          width: DS.touchTargetMinSize,
          height: DS.touchTargetMinSize,
          decoration: BoxDecoration(
            color: accentColor.withValues(alpha: expanded ? 0.18 : 0.1),
            shape: BoxShape.circle,
            border: Border.all(
              color: accentColor.withValues(alpha: expanded ? 0.45 : 0.2),
            ),
          ),
          child: Icon(
            icon,
            size: 20,
            color: accentColor,
          ),
        ),
      ),
    );
  }
}

class _AgentModeChip extends StatelessWidget {
  const _AgentModeChip({
    required this.mode,
    required this.isSelected,
    required this.onTap,
  });

  final ChatMode mode;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final foregroundColor = isDark ? const Color(0xFFF1E7DA) : DS.neutral900;

    return InkWell(
      onTap: onTap,
      borderRadius: DS.borderRadiusFull,
      child: AnimatedContainer(
        duration: DS.quick,
        curve: DS.curveEaseOut,
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: mode.color.withValues(alpha: isSelected ? 0.24 : 0.14),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(
            color: mode.color.withValues(alpha: isSelected ? 0.5 : 0.25),
            width: isSelected ? 1.4 : 1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              mode.icon,
              size: DS.iconSizeXs,
              color: foregroundColor,
            ),
            const SizedBox(width: DS.spacing4),
            Text(
              mode.label,
              style: TextStyle(
                color: foregroundColor,
                fontSize: DS.fontSizeXs,
                fontWeight:
                    isSelected ? DS.fontWeightBold : DS.fontWeightMedium,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
