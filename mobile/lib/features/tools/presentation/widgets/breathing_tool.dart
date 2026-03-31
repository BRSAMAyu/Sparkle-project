import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
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
  });

  final String instruction;
  final int completedRounds;
  final int totalRounds;
  final double controllerValue;
  final bool isComplete;
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
  static const List<_BreathingPattern> _patterns = [
    _BreathingPattern(
      label: '4-7-8',
      description: '快速降噪，适合焦躁和睡前收束。',
      inhale: 4,
      hold: 7,
      exhale: 8,
      rest: 0,
    ),
    _BreathingPattern(
      label: '方块呼吸',
      description: '均衡稳定，适合进入专注前校准节奏。',
      inhale: 4,
      hold: 4,
      exhale: 4,
      rest: 4,
    ),
    _BreathingPattern(
      label: '舒缓呼吸',
      description: '呼长于吸，适合紧张后的恢复。',
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
  Timer? _ticker;

  int _selectedDurationIndex = 1;
  int _selectedPatternIndex = 0;
  bool _isPlaying = false;
  bool _isCompletingSession = false;
  bool _backgroundCompletionScheduled = false;
  bool _completedFromBackgroundRecovery = false;
  int _completedRounds = 0;
  int _totalRounds = 0;
  String _instruction = '准备';
  DateTime? _sessionStartedAt;

  _BreathingPattern get _pattern => _patterns[_selectedPatternIndex];
  int get _selectedDurationMinutes => _durations[_selectedDurationIndex];
  int get _targetSessionSeconds => _selectedDurationMinutes * 60;

  List<_BreathingPhase> get _phases => <_BreathingPhase>[
        _BreathingPhase(
          label: '吸气',
          seconds: _pattern.inhale,
          kind: _BreathingPhaseKind.inhale,
        ),
        _BreathingPhase(
          label: '停留',
          seconds: _pattern.hold,
          kind: _BreathingPhaseKind.holdExpanded,
        ),
        _BreathingPhase(
          label: '呼气',
          seconds: _pattern.exhale,
          kind: _BreathingPhaseKind.exhale,
        ),
        _BreathingPhase(
          label: '停留',
          seconds: _pattern.rest,
          kind: _BreathingPhaseKind.holdCollapsed,
        ),
      ].where((phase) => phase.seconds > 0).toList(growable: false);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _controller = AnimationController(
      vsync: this,
      duration: Duration.zero,
      value: 0.0,
    );
    _updateTotalRounds();
    unawaited(_restoreState());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _ticker?.cancel();
    if (_isPlaying) {
      unawaited(_persistSession());
      unawaited(_scheduleCompletionNotification());
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
        _syncFromClock();
        _ticker?.cancel();
        unawaited(_persistSession());
        unawaited(_scheduleCompletionNotification());
      }
      return;
    }

    if (state == AppLifecycleState.resumed) {
      final didCompleteWhileBackground = _isPlaying &&
          _sessionStartedAt != null &&
          DateTime.now().difference(_sessionStartedAt!).inSeconds >=
              _targetSessionSeconds;
      _completedFromBackgroundRecovery = didCompleteWhileBackground;
      unawaited(_cancelCompletionNotification());
      if (_isPlaying) {
        _syncFromClock();
        _startTicker();
      }
    }
  }

  Future<void> _restoreState() async {
    final prefs = await SharedPreferences.getInstance();
    final savedPatternIndex =
        (prefs.getInt(_prefsPatternKey) ?? _selectedPatternIndex)
            .clamp(0, _patterns.length - 1);
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

      final restoredStartedAt = DateTime.tryParse(
        json['sessionStartedAt'] as String? ?? '',
      );
      if (restoredStartedAt == null) {
        await prefs.remove(_prefsSessionKey);
        return;
      }

      final patternIndex =
          ((json['selectedPatternIndex'] as num?)?.toInt() ?? savedPatternIndex)
              .clamp(0, _patterns.length - 1);
      final durationIndex = ((json['selectedDurationIndex'] as num?)?.toInt() ??
              savedDurationIndex)
          .clamp(0, _durations.length - 1);

      if (!mounted) {
        return;
      }

      setState(() {
        _selectedPatternIndex = patternIndex;
        _selectedDurationIndex = durationIndex;
        _sessionStartedAt = restoredStartedAt;
        _isPlaying = true;
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
          _completedRounds = _totalRounds;
          _instruction = '练习完成';
          _sessionStartedAt = null;
        });
      } else {
        _syncFromClock();
        _startTicker();
      }
    } catch (_) {
      await prefs.remove(_prefsSessionKey);
    }
  }

  Future<void> _persistPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_prefsPatternKey, _selectedPatternIndex);
    await prefs.setInt(_prefsDurationKey, _selectedDurationIndex);
  }

  Future<void> _persistSession() async {
    final prefs = await SharedPreferences.getInstance();
    if (!_isPlaying || _sessionStartedAt == null) {
      await prefs.remove(_prefsSessionKey);
      return;
    }

    final payload = <String, dynamic>{
      'sessionStartedAt': _sessionStartedAt!.toIso8601String(),
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
    if (!_isPlaying || _sessionStartedAt == null) {
      return;
    }

    final remainingRawSeconds = _targetSessionSeconds -
        DateTime.now().difference(_sessionStartedAt!).inSeconds;
    if (remainingRawSeconds <= 0) {
      return;
    }
    final remainingSeconds =
        remainingRawSeconds.clamp(1, _targetSessionSeconds);
    final notificationService = ref.read(notificationServiceProvider);
    await notificationService.scheduleNotification(
      id: _completionNotificationId,
      title: '呼吸练习完成',
      body: '本轮呼吸练习已经结束，回来感受一下身体状态。',
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
    final startedAt = _sessionStartedAt;
    if (startedAt == null) {
      return _BreathingSnapshot(
        instruction: '准备',
        completedRounds: 0,
        totalRounds: totalRounds,
        controllerValue: 0.0,
        isComplete: false,
      );
    }

    final elapsedSeconds = now.difference(startedAt).inSeconds.clamp(
          0,
          _targetSessionSeconds,
        );
    if (elapsedSeconds >= _targetSessionSeconds) {
      return _BreathingSnapshot(
        instruction: '练习完成',
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
        );
      }
      cursor = nextCursor;
    }

    return _BreathingSnapshot(
      instruction: '准备',
      completedRounds: completedRounds,
      totalRounds: totalRounds,
      controllerValue: 0.0,
      isComplete: false,
    );
  }

  void _syncFromClock() {
    if (!_isPlaying || _sessionStartedAt == null) {
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

    if (!mounted) {
      return;
    }

    _controller.value = snapshot.controllerValue;
    setState(() {
      _instruction = snapshot.instruction;
      _completedRounds = snapshot.completedRounds;
      _totalRounds = snapshot.totalRounds;
    });
  }

  void _startBreathing() {
    _ticker?.cancel();
    _isCompletingSession = false;
    _completedFromBackgroundRecovery = false;
    _backgroundCompletionScheduled = false;
    setState(() {
      _updateTotalRounds();
      _isPlaying = true;
      _completedRounds = 0;
      _instruction = '准备';
      _sessionStartedAt = DateTime.now();
    });
    unawaited(_persistPreferences());
    unawaited(_persistSession());
    unawaited(_cancelCompletionNotification());
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
    await _cancelCompletionNotification();
    await _clearPersistedSession();
    await SensoryFeedbackService.emit(SensoryFeedbackEvent.focusComplete);

    if (!mounted) {
      return;
    }

    _controller.value = 0.0;
    setState(() {
      _isPlaying = false;
      _completedRounds = _totalRounds;
      _instruction = '练习完成';
      _sessionStartedAt = null;
    });

    if (!completedFromBackground) {
      AppFeedback.success(context, '呼吸练习已完成');
    }
    _isCompletingSession = false;
  }

  void _stopBreathing() {
    _ticker?.cancel();
    _isCompletingSession = false;
    _completedFromBackgroundRecovery = false;
    _controller
      ..stop()
      ..value = 0;
    setState(() {
      _isPlaying = false;
      _completedRounds = 0;
      _instruction = '准备';
      _sessionStartedAt = null;
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
      title: '呼吸练习',
      subtitle: '把呼吸节奏做成可执行工具，而不是一次性动画。支持多种模式和不同练习时长，适合在任务间切换状态。',
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
              ? '$_completedRounds / $_totalRounds 轮'
              : '${_durations[_selectedDurationIndex]} 分钟',
          accentColor: accent,
          icon: Icons.self_improvement_rounded,
        ),
      ],
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: '呼吸舞台',
            subtitle: '跟着中央指令吸气、停留和呼气。',
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
                label: '当前节律',
                value:
                    '${_pattern.inhale}-${_pattern.hold}-${_pattern.exhale}-${_pattern.rest}',
                accentColor: accent,
                icon: Icons.tonality_rounded,
                caption: '吸 / 停 / 呼 / 停',
              ),
              ToolMetricCard(
                label: '目标轮数',
                value: '$_totalRounds',
                accentColor: accent,
                icon: Icons.repeat_rounded,
                caption: '按当前时长自动估算',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: '练习配置',
            subtitle: _isPlaying ? '练习进行中，配置会在本轮结束后可调整。' : '先选模式，再选练习时长。',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: DS.spacing10,
                  runSpacing: DS.spacing10,
                  children: List.generate(
                    _patterns.length,
                    (index) => ToolChoiceChip(
                      label: _patterns[index].label,
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
                      label: '${_durations[index]} 分钟',
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
          final startButton = SparkleButton(
            label: _isPlaying ? '停止练习' : '开始练习',
            onPressed: _isPlaying ? _stopBreathing : _startBreathing,
            icon: Icon(
              _isPlaying ? Icons.stop_rounded : Icons.play_arrow_rounded,
            ),
            expand: true,
          );
          final resetButton = SparkleButton(
            label: '重置',
            variant: ButtonVariant.ghost,
            onPressed: _stopBreathing,
            icon: const Icon(Icons.refresh_rounded),
            expand: true,
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                startButton,
                const SizedBox(height: DS.spacing12),
                resetButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: startButton),
              const SizedBox(width: DS.spacing12),
              Expanded(child: resetButton),
            ],
          );
        },
      ),
    );
  }
}
