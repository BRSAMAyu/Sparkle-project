import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/tools/data/repositories/tool_history_repository.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_context_effect_feedback.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

class _BreathingPattern {
  const _BreathingPattern({
    required this.label,
    required this.description,
    required this.inhale,
    required this.hold,
    required this.exhale,
    required this.rest,
  });

  final String label;
  final String description;
  final int inhale;
  final int hold;
  final int exhale;
  final int rest;

  int get cycleSeconds => inhale + hold + exhale + rest;
}

enum _BreathingPhaseKind {
  inhale,
  holdExpanded,
  exhale,
  holdCollapsed,
}

class _BreathingPhase {
  const _BreathingPhase({
    required this.label,
    required this.seconds,
    required this.kind,
  });

  final String label;
  final int seconds;
  final _BreathingPhaseKind kind;
}

class _BreathingSnapshot {
  const _BreathingSnapshot({
    required this.instruction,
    required this.completedRounds,
    required this.totalRounds,
    required this.controllerValue,
    required this.isComplete,
    this.announcementKey,
  });

  final String instruction;
  final int completedRounds;
  final int totalRounds;
  final double controllerValue;
  final bool isComplete;
  final String? announcementKey;
}

class BreathingTool extends ConsumerStatefulWidget {
  const BreathingTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

  @override
  ConsumerState<BreathingTool> createState() => _BreathingToolState();
}

class _BreathingToolState extends ConsumerState<BreathingTool>
    with SingleTickerProviderStateMixin, WidgetsBindingObserver {
  static const List<int> _durations = [1, 3, 5, 8];
  static List<_BreathingPattern> _patternsFor(BuildContext context) => [
        _BreathingPattern(
          label: '4-7-8',
          description: context.l10n.toolsBreathQuickDesc,
          inhale: 4,
          hold: 7,
          exhale: 8,
          rest: 0,
        ),
        _BreathingPattern(
          label: context.l10n.toolsBreathBox,
          description: context.l10n.toolsBreathBoxDesc,
          inhale: 4,
          hold: 4,
          exhale: 4,
          rest: 4,
        ),
        _BreathingPattern(
          label: context.l10n.toolsBreathRelax,
          description: context.l10n.toolsBreathRelaxDesc,
          inhale: 4,
          hold: 2,
          exhale: 6,
          rest: 2,
        ),
      ];
  static const String _prefsPatternKey = 'breathing.pattern_index';
  static const String _prefsDurationKey = 'breathing.duration_index';
  static const String _prefsSessionKey = 'breathing.active_session';
  static const int _completionNotificationId = 94200;

  late final AnimationController _controller;
  late final FlutterTts _tts;
  Timer? _ticker;

  int _selectedDurationIndex = 1;
  int _selectedPatternIndex = 0;
  bool _isPlaying = false;
  bool _isPaused = false;
  bool _isCompletingSession = false;
  bool _backgroundCompletionScheduled = false;
  bool _completedFromBackgroundRecovery = false;
  int _completedRounds = 0;
  int _totalRounds = 0;
  int _elapsedBeforePauseSeconds = 0;
  String _instruction = I18nService.instance.isChinese ? '准备' : 'Ready';
  String? _lastAnnouncementKey;
  DateTime? _sessionAnchorAt;

  _BreathingPattern get _pattern =>
      _patternsFor(context)[_selectedPatternIndex];
  int get _selectedDurationMinutes => _durations[_selectedDurationIndex];
  int get _targetSessionSeconds => _selectedDurationMinutes * 60;

  List<_BreathingPhase> get _phases => <_BreathingPhase>[
        _BreathingPhase(
          label: context.l10n.toolsBreathInhale,
          seconds: _pattern.inhale,
          kind: _BreathingPhaseKind.inhale,
        ),
        _BreathingPhase(
          label: context.l10n.toolsBreathHold,
          seconds: _pattern.hold,
          kind: _BreathingPhaseKind.holdExpanded,
        ),
        _BreathingPhase(
          label: context.l10n.toolsBreathExhale,
          seconds: _pattern.exhale,
          kind: _BreathingPhaseKind.exhale,
        ),
        _BreathingPhase(
          label: context.l10n.toolsBreathHold,
          seconds: _pattern.rest,
          kind: _BreathingPhaseKind.holdCollapsed,
        ),
      ].where((phase) => phase.seconds > 0).toList(growable: false);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _tts = FlutterTts();
    _controller = AnimationController(
      vsync: this,
      duration: Duration.zero,
      value: 0.0,
    );
    _updateTotalRounds();
    unawaited(_configureTts());
    unawaited(_restoreState());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ticker?.cancel();
    unawaited(_tts.stop());
    if (_isPlaying) {
      unawaited(_persistSession());
      if (_isPaused) {
        unawaited(_cancelCompletionNotification());
      } else {
        unawaited(_scheduleCompletionNotification());
      }
    } else {
      unawaited(_clearPersistedSession());
      unawaited(_cancelCompletionNotification());
    }
    _controller.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.inactive ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.paused) {
      if (_isPlaying) {
        _syncFromClock(allowVoiceGuidance: false);
        _ticker?.cancel();
        unawaited(_persistSession());
        if (_isPaused) {
          unawaited(_cancelCompletionNotification());
        } else {
          unawaited(_scheduleCompletionNotification());
        }
      }
      return;
    }

    if (state == AppLifecycleState.resumed) {
      final didCompleteWhileBackground = _isPlaying &&
          _elapsedSessionSecondsAt(DateTime.now()) >= _targetSessionSeconds;
      _completedFromBackgroundRecovery = didCompleteWhileBackground;
      unawaited(_cancelCompletionNotification());
      if (_isPlaying) {
        _syncFromClock(allowVoiceGuidance: false);
        if (!_isPaused) {
          _startTicker();
        }
      }
    }
  }

  Future<void> _restoreState() async {
    final prefs = await SharedPreferences.getInstance();
    final savedPatternIndex =
        (prefs.getInt(_prefsPatternKey) ?? _selectedPatternIndex)
            .clamp(0, _patternsFor(context).length - 1);
    final savedDurationIndex =
        (prefs.getInt(_prefsDurationKey) ?? _selectedDurationIndex)
            .clamp(0, _durations.length - 1);

    if (mounted) {
      setState(() {
        _selectedPatternIndex = savedPatternIndex;
        _selectedDurationIndex = savedDurationIndex;
        _updateTotalRounds();
      });
    }

    final rawSession = prefs.getString(_prefsSessionKey);
    if (rawSession == null || rawSession.isEmpty) {
      return;
    }

    try {
      final json = jsonDecode(rawSession);
      if (json is! Map<String, dynamic>) {
        await prefs.remove(_prefsSessionKey);
        return;
      }

      final restoredAnchorAt = DateTime.tryParse(
        json['sessionAnchorAt'] as String? ??
            json['sessionStartedAt'] as String? ??
            '',
      );
      final isPaused = json['isPaused'] as bool? ?? false;
      final elapsedBeforePauseSeconds =
          (json['elapsedBeforePauseSeconds'] as num?)?.toInt() ?? 0;
      if (restoredAnchorAt == null && !isPaused) {
        await prefs.remove(_prefsSessionKey);
        return;
      }

      final patternIndex =
          ((json['selectedPatternIndex'] as num?)?.toInt() ?? savedPatternIndex)
              .clamp(0, _patternsFor(context).length - 1);
      final durationIndex = ((json['selectedDurationIndex'] as num?)?.toInt() ??
              savedDurationIndex)
          .clamp(0, _durations.length - 1);

      if (!mounted) {
        return;
      }

      setState(() {
        _selectedPatternIndex = patternIndex;
        _selectedDurationIndex = durationIndex;
        _sessionAnchorAt = isPaused ? null : restoredAnchorAt;
        _isPlaying = true;
        _isPaused = isPaused;
        _elapsedBeforePauseSeconds = elapsedBeforePauseSeconds;
        _lastAnnouncementKey = null;
        _updateTotalRounds();
      });

      final snapshot = _snapshotFor(DateTime.now());
      if (snapshot.isComplete) {
        await _clearPersistedSession();
        if (!mounted) {
          return;
        }
        _controller.value = 0.0;
        setState(() {
          _isPlaying = false;
          _isPaused = false;
          _completedRounds = _totalRounds;
          _instruction =
              I18nService.instance.isChinese ? '练习完成' : 'Practice Complete';
          _elapsedBeforePauseSeconds = 0;
          _sessionAnchorAt = null;
        });
      } else {
        _syncFromClock(allowVoiceGuidance: false);
        if (!isPaused) {
          _startTicker();
        }
      }
    } catch (_) {
      await prefs.remove(_prefsSessionKey);
    }
  }

  Future<void> _configureTts() async {
    try {
      await _tts.setLanguage('zh-CN');
      await _tts.setSpeechRate(0.42);
      await _tts.setPitch(1.0);
      await _tts.awaitSpeakCompletion(false);
    } catch (_) {
      // TTS is optional enhancement. Fail silently on unsupported devices.
    }
  }

  int _elapsedSessionSecondsAt(DateTime now) {
    final anchorElapsed = _sessionAnchorAt == null
        ? 0
        : now.difference(_sessionAnchorAt!).inSeconds;
    return (_elapsedBeforePauseSeconds + anchorElapsed).clamp(
      0,
      _targetSessionSeconds,
    );
  }

  Future<void> _persistPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_prefsPatternKey, _selectedPatternIndex);
    await prefs.setInt(_prefsDurationKey, _selectedDurationIndex);
  }

  Future<void> _persistSession() async {
    final prefs = await SharedPreferences.getInstance();
    if (!_isPlaying) {
      await prefs.remove(_prefsSessionKey);
      return;
    }

    final payload = <String, dynamic>{
      'sessionAnchorAt': _sessionAnchorAt?.toIso8601String(),
      'elapsedBeforePauseSeconds': _elapsedBeforePauseSeconds,
      'isPaused': _isPaused,
      'selectedPatternIndex': _selectedPatternIndex,
      'selectedDurationIndex': _selectedDurationIndex,
    };
    await prefs.setString(_prefsSessionKey, jsonEncode(payload));
  }

  Future<void> _clearPersistedSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_prefsSessionKey);
  }

  Future<void> _scheduleCompletionNotification() async {
    if (!_isPlaying || _isPaused) {
      return;
    }

    final remainingRawSeconds =
        _targetSessionSeconds - _elapsedSessionSecondsAt(DateTime.now());
    if (remainingRawSeconds <= 0) {
      return;
    }
    final remainingSeconds =
        remainingRawSeconds.clamp(1, _targetSessionSeconds);
    final notificationService = ref.read(notificationServiceProvider);
    await notificationService.scheduleNotification(
      id: _completionNotificationId,
      title: context.l10n.toolsBreathComplete,
      body: I18nService.instance.isChinese
          ? '本轮呼吸练习已经结束，回来感受一下身体状态。'
          : 'This breathing session has ended. Return and feel your body state.',
      scheduledDate: DateTime.now().add(Duration(seconds: remainingSeconds)),
      payload: <String, dynamic>{
        'type': 'breathing_complete',
        'pattern': _pattern.label,
        'duration_minutes': _selectedDurationMinutes,
      },
    );
    _backgroundCompletionScheduled = true;
  }

  Future<void> _cancelCompletionNotification() async {
    final notificationService = ref.read(notificationServiceProvider);
    await notificationService.cancelNotification(_completionNotificationId);
    _backgroundCompletionScheduled = false;
  }

  void _updateTotalRounds() {
    final cycleSeconds = _pattern.cycleSeconds == 0 ? 1 : _pattern.cycleSeconds;
    _totalRounds = (_targetSessionSeconds / cycleSeconds).ceil();
  }

  void _startTicker() {
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(milliseconds: 200), (_) {
      _syncFromClock();
    });
  }

  _BreathingSnapshot _snapshotFor(DateTime now) {
    final totalRounds = _totalRounds;
    if (!_isPlaying) {
      return _BreathingSnapshot(
        instruction: I18nService.instance.isChinese ? '准备' : 'Ready',
        completedRounds: 0,
        totalRounds: totalRounds,
        controllerValue: 0.0,
        isComplete: false,
      );
    }

    final elapsedSeconds = _elapsedSessionSecondsAt(now);
    if (elapsedSeconds >= _targetSessionSeconds) {
      return _BreathingSnapshot(
        instruction:
            I18nService.instance.isChinese ? '练习完成' : 'Practice Complete',
        completedRounds: totalRounds,
        totalRounds: totalRounds,
        controllerValue: 0.0,
        isComplete: true,
      );
    }

    final cycleSeconds = _pattern.cycleSeconds == 0 ? 1 : _pattern.cycleSeconds;
    final completedRounds = elapsedSeconds ~/ cycleSeconds;
    final secondsIntoCycle = elapsedSeconds % cycleSeconds;

    var cursor = 0;
    for (final phase in _phases) {
      final nextCursor = cursor + phase.seconds;
      if (secondsIntoCycle < nextCursor) {
        final phaseElapsed = secondsIntoCycle - cursor;
        final progress =
            phase.seconds == 0 ? 1.0 : phaseElapsed / phase.seconds;
        final controllerValue = switch (phase.kind) {
          _BreathingPhaseKind.inhale => progress.clamp(0.0, 1.0),
          _BreathingPhaseKind.holdExpanded => 1.0,
          _BreathingPhaseKind.exhale => (1.0 - progress).clamp(0.0, 1.0),
          _BreathingPhaseKind.holdCollapsed => 0.0,
        };
        return _BreathingSnapshot(
          instruction: phase.label,
          completedRounds: completedRounds,
          totalRounds: totalRounds,
          controllerValue: controllerValue,
          isComplete: false,
          announcementKey: '${completedRounds}_${phase.kind.name}',
        );
      }
      cursor = nextCursor;
    }

    return _BreathingSnapshot(
      instruction: I18nService.instance.isChinese ? '准备' : 'Ready',
      completedRounds: completedRounds,
      totalRounds: totalRounds,
      controllerValue: 0.0,
      isComplete: false,
    );
  }

  Future<void> _announceInstruction(String instruction) async {
    try {
      await _tts.stop();
      await _tts.speak(instruction);
    } catch (_) {
      // Ignore unsupported TTS failures.
    }
  }

  void _syncFromClock({
    bool allowVoiceGuidance = true,
  }) {
    if (!_isPlaying) {
      return;
    }

    final snapshot = _snapshotFor(DateTime.now());
    if (snapshot.isComplete) {
      if (!_isCompletingSession) {
        unawaited(
          _handleCompletion(
            completedFromBackground: _backgroundCompletionScheduled ||
                _completedFromBackgroundRecovery,
          ),
        );
      }
      return;
    }

    final announcementKey = snapshot.announcementKey;
    final shouldAnnounce = allowVoiceGuidance &&
        !_isPaused &&
        announcementKey != null &&
        announcementKey != _lastAnnouncementKey;
    _lastAnnouncementKey = announcementKey ?? _lastAnnouncementKey;

    if (!mounted) {
      return;
    }

    _controller.value = snapshot.controllerValue;
    setState(() {
      _instruction = snapshot.instruction;
      _completedRounds = snapshot.completedRounds;
      _totalRounds = snapshot.totalRounds;
    });
    if (shouldAnnounce) {
      unawaited(_announceInstruction(snapshot.instruction));
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    }
  }

  void _startBreathing() {
    _ticker?.cancel();
    _isCompletingSession = false;
    _completedFromBackgroundRecovery = false;
    _backgroundCompletionScheduled = false;
    setState(() {
      _updateTotalRounds();
      _isPlaying = true;
      _isPaused = false;
      _completedRounds = 0;
      _instruction = I18nService.instance.isChinese ? '准备' : 'Ready';
      _elapsedBeforePauseSeconds = 0;
      _lastAnnouncementKey = null;
      _sessionAnchorAt = DateTime.now();
    });
    unawaited(_persistPreferences());
    unawaited(_persistSession());
    unawaited(_cancelCompletionNotification());
    _syncFromClock();
    _startTicker();
  }

  void _pauseBreathing() {
    if (!_isPlaying || _isPaused) {
      return;
    }
    _ticker?.cancel();
    final now = DateTime.now();
    final snapshot = _snapshotFor(now);
    _elapsedBeforePauseSeconds = _elapsedSessionSecondsAt(now);
    _lastAnnouncementKey = snapshot.announcementKey ?? _lastAnnouncementKey;
    _controller.value = snapshot.controllerValue;
    setState(() {
      _isPaused = true;
      _instruction = snapshot.instruction;
      _completedRounds = snapshot.completedRounds;
      _totalRounds = snapshot.totalRounds;
      _sessionAnchorAt = null;
    });
    unawaited(_tts.stop());
    unawaited(_persistSession());
    unawaited(_cancelCompletionNotification());
  }

  void _resumeBreathing() {
    if (!_isPlaying || !_isPaused) {
      return;
    }
    setState(() {
      _isPaused = false;
      _lastAnnouncementKey = null;
      _sessionAnchorAt = DateTime.now();
    });
    unawaited(_persistSession());
    _syncFromClock();
    _startTicker();
  }

  Future<void> _handleCompletion({
    required bool completedFromBackground,
  }) async {
    if (_isCompletingSession) {
      return;
    }
    _isCompletingSession = true;
    _ticker?.cancel();
    _completedFromBackgroundRecovery = false;
    await _tts.stop();
    await _cancelCompletionNotification();
    await _clearPersistedSession();
    await SensoryFeedbackService.emit(SensoryFeedbackEvent.focusComplete);
    final contextEventId =
        await ref.read(toolHistoryRepositoryProvider).recordBreathingCompleted(
              pattern: _pattern.label,
              durationMinutes: _selectedDurationMinutes,
              roundsCompleted: _totalRounds,
              surface: widget.surface.name,
              completedFromBackground: completedFromBackground,
            );

    if (!mounted) {
      return;
    }

    _controller.value = 0.0;
    setState(() {
      _isPlaying = false;
      _isPaused = false;
      _completedRounds = _totalRounds;
      _instruction =
          I18nService.instance.isChinese ? '练习完成' : 'Practice Complete';
      _elapsedBeforePauseSeconds = 0;
      _lastAnnouncementKey = null;
      _sessionAnchorAt = null;
    });

    unawaited(_announceInstruction(
        I18nService.instance.isChinese ? '练习完成' : 'Practice Complete'));
    if (!completedFromBackground) {
      if (contextEventId == null) {
        AppFeedback.success(context, context.l10n.toolsBreathComplete);
      } else {
        ToolContextEffectFeedback.show(
          context: context,
          ref: ref,
          toolLabel: context.l10n.toolsBreathTitle,
          eventId: contextEventId,
        );
      }
    }
    _isCompletingSession = false;
  }

  void _stopBreathing() {
    _ticker?.cancel();
    _isCompletingSession = false;
    _completedFromBackgroundRecovery = false;
    unawaited(_tts.stop());
    _controller
      ..stop()
      ..value = 0;
    setState(() {
      _isPlaying = false;
      _isPaused = false;
      _completedRounds = 0;
      _instruction = I18nService.instance.isChinese ? '准备' : 'Ready';
      _elapsedBeforePauseSeconds = 0;
      _lastAnnouncementKey = null;
      _sessionAnchorAt = null;
    });
    unawaited(_clearPersistedSession());
    unawaited(_cancelCompletionNotification());
  }

  Future<void> _updatePattern(int index) async {
    if (_isPlaying) {
      return;
    }
    setState(() {
      _selectedPatternIndex = index;
      _updateTotalRounds();
    });
    await _persistPreferences();
  }

  Future<void> _updateDuration(int index) async {
    if (_isPlaying) {
      return;
    }
    setState(() {
      _selectedDurationIndex = index;
      _updateTotalRounds();
    });
    await _persistPreferences();
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.prismBlue;
    return ToolShell(
      surface: widget.surface,
      icon: Icons.air_rounded,
      title: context.l10n.toolsBreathTitle,
      subtitle: context.l10n.toolsBreathSubtitle,
      accentColor: accent,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: _pattern.label,
          accentColor: accent,
          icon: Icons.bubble_chart_rounded,
        ),
        ToolHeroChip(
          label: _isPlaying
              ? (_isPaused
                  ? I18nService.instance.isChinese
                      ? '已暂停 · $_completedRounds / $_totalRounds 轮'
                      : 'Paused · $_completedRounds / $_totalRounds rounds'
                  : I18nService.instance.isChinese
                      ? '$_completedRounds / $_totalRounds 轮'
                      : '$_completedRounds / $_totalRounds rounds')
              : I18nService.instance.isChinese
                  ? '${_durations[_selectedDurationIndex]} 分钟'
                  : '${_durations[_selectedDurationIndex]} min',
          accentColor: accent,
          icon: Icons.self_improvement_rounded,
        ),
      ],
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsBreathStage,
            subtitle: _isPaused
                ? I18nService.instance.isChinese
                    ? '练习已暂停，恢复后会从当前阶段继续，并继续语音提示。'
                    : 'Practice paused, will resume from current phase with voice guidance.'
                : I18nService.instance.isChinese
                    ? '跟着中央指令吸气、停留和呼气。'
                    : 'Follow the central instruction to inhale, hold, and exhale.',
            child: LayoutBuilder(
              builder: (context, constraints) {
                final stageSize = constraints.maxWidth.clamp(180.0, 300.0);
                return Center(
                  child: SizedBox(
                    width: stageSize,
                    height: stageSize,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        Container(
                          width: stageSize,
                          height: stageSize,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: accent.withValues(alpha: 0.16),
                              width: 2,
                            ),
                          ),
                        ),
                        AnimatedBuilder(
                          animation: _controller,
                          builder: (context, child) {
                            final scale = 0.42 + (_controller.value * 0.58);
                            return Transform.scale(
                              scale: scale,
                              child: Container(
                                width: stageSize,
                                height: stageSize,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: RadialGradient(
                                    colors: [
                                      accent.withValues(alpha: 0.30),
                                      accent.withValues(alpha: 0.06),
                                    ],
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _instruction,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.spacing8),
                            Text(
                              _pattern.description,
                              textAlign: TextAlign.center,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.4,
                                  ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ToolMetricRow(
            children: [
              ToolMetricCard(
                label: context.l10n.toolsBreathCurrentRhythm,
                value:
                    '${_pattern.inhale}-${_pattern.hold}-${_pattern.exhale}-${_pattern.rest}',
                accentColor: accent,
                icon: Icons.tonality_rounded,
                caption: I18nService.instance.isChinese
                    ? '吸 / 停 / 呼 / 停'
                    : 'Inhale / Hold / Exhale / Hold',
              ),
              ToolMetricCard(
                label: context.l10n.toolsBreathTargetRounds,
                value: '$_totalRounds',
                accentColor: accent,
                icon: Icons.repeat_rounded,
                caption: I18nService.instance.isChinese
                    ? '按当前时长自动估算'
                    : 'Auto-estimated by duration',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: context.l10n.toolsBreathConfig,
            subtitle: _isPlaying
                ? (_isPaused
                    ? I18nService.instance.isChinese
                        ? '练习已暂停，恢复后会从当前阶段继续。'
                        : 'Practice paused, will resume from current phase.'
                    : I18nService.instance.isChinese
                        ? '练习进行中，配置会在本轮结束后可调整。'
                        : 'Practice in progress, config adjustable after current round.')
                : I18nService.instance.isChinese
                    ? '先选模式，再选练习时长。'
                    : 'Select pattern, then duration.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: DS.spacing10,
                  runSpacing: DS.spacing10,
                  children: List.generate(
                    _patternsFor(context).length,
                    (index) => ToolChoiceChip(
                      label: _patternsFor(context)[index].label,
                      selected: _selectedPatternIndex == index,
                      onTap: () => unawaited(_updatePattern(index)),
                      accentColor: accent,
                    ),
                  ),
                ),
                const SizedBox(height: DS.spacing16),
                Wrap(
                  spacing: DS.spacing10,
                  runSpacing: DS.spacing10,
                  children: List.generate(
                    _durations.length,
                    (index) => ToolChoiceChip(
                      label: context.l10n
                          .toolsBreathDurationMin(_durations[index]),
                      selected: _selectedDurationIndex == index,
                      onTap: () => unawaited(_updateDuration(index)),
                      accentColor: accent,
                      icon: Icons.timer_outlined,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 560;
          final primaryButton = SparkleButton(
            label: _isPlaying
                ? (_isPaused
                    ? context.l10n.toolsBreathContinue
                    : context.l10n.toolsBreathPause)
                : context.l10n.toolsBreathStart,
            onPressed: _isPlaying
                ? (_isPaused ? _resumeBreathing : _pauseBreathing)
                : _startBreathing,
            icon: Icon(
              _isPlaying
                  ? (_isPaused ? Icons.play_arrow_rounded : Icons.pause_rounded)
                  : Icons.play_arrow_rounded,
            ),
            expand: true,
          );
          final secondaryButton = SparkleButton(
            label: _isPlaying
                ? context.l10n.toolsBreathStop
                : context.l10n.toolsBreathReset,
            variant: ButtonVariant.ghost,
            onPressed: _stopBreathing,
            icon: Icon(
              _isPlaying ? Icons.stop_rounded : Icons.refresh_rounded,
            ),
            expand: true,
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                primaryButton,
                const SizedBox(height: DS.spacing12),
                secondaryButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: primaryButton),
              const SizedBox(width: DS.spacing12),
              Expanded(child: secondaryButton),
            ],
          );
        },
      ),
    );
  }
}
