import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/chat/data/models/chat_stream_events.dart' as chat;
import 'package:sparkle/features/focus/presentation/providers/focus_statistics_provider.dart'
    as focus_stats;
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

enum FocusTimerPreset {
  stopwatch,
  pomodoro,
}

class FocusTimerTool extends ConsumerStatefulWidget {
  const FocusTimerTool({
    required this.preset,
    super.key,
    this.surface = ToolSurface.page,
  });

  final FocusTimerPreset preset;
  final ToolSurface surface;

  @override
  ConsumerState<FocusTimerTool> createState() => _FocusTimerToolState();
}

class _FocusTimerToolState extends ConsumerState<FocusTimerTool> {
  static const List<int> _countdownOptions = [10, 15, 25, 45, 60, 90];
  static const List<int> _pomodoroOptions = [25, 50, 90];
  static const String _prefsModePrefix = 'focus_timer.mode.';
  static const String _prefsMinutesPrefix = 'focus_timer.minutes.';

  late TimerMode _mode;
  late int _selectedMinutes;
  int _sessionSeed = 0;
  bool _isRunning = false;
  AmbientScene _ambientScene = AmbientScene.none;
  int _elapsedSeconds = 0;
  DateTime? _sessionStartedAt;

  @override
  void initState() {
    super.initState();
    _mode = widget.preset == FocusTimerPreset.pomodoro
        ? TimerMode.countDown
        : TimerMode.countUp;
    _selectedMinutes =
        widget.preset == FocusTimerPreset.pomodoro ? 25 : _countdownOptions[1];
    unawaited(_loadSavedPreferences());
    unawaited(_loadSavedAmbient());
  }

  String get _prefsScope => widget.preset.name;

  Future<void> _loadSavedPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    final savedMode = prefs.getString('$_prefsModePrefix$_prefsScope');
    final savedMinutes = prefs.getInt('$_prefsMinutesPrefix$_prefsScope');

    final nextMode = savedMode == TimerMode.countDown.name
        ? TimerMode.countDown
        : TimerMode.countUp;
    final allowedMinutes = widget.preset == FocusTimerPreset.pomodoro
        ? _pomodoroOptions
        : _countdownOptions;
    final nextMinutes = allowedMinutes.contains(savedMinutes)
        ? savedMinutes!
        : _selectedMinutes;

    if (!mounted) {
      return;
    }
    setState(() {
      _mode = widget.preset == FocusTimerPreset.pomodoro
          ? TimerMode.countDown
          : nextMode;
      _selectedMinutes = nextMinutes;
    });
  }

  Future<void> _persistPreferences() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      '$_prefsModePrefix$_prefsScope',
      _mode.name,
    );
    await prefs.setInt(
      '$_prefsMinutesPrefix$_prefsScope',
      _selectedMinutes,
    );
  }

  Future<void> _loadSavedAmbient() async {
    final saved = await SensoryFeedbackService.getSavedAmbientScene();
    if (mounted) setState(() => _ambientScene = saved);
  }

  @override
  void dispose() {
    // Stop ambient when tool unmounts
    unawaited(SensoryFeedbackService.stopAmbient());
    super.dispose();
  }

  void _resetTimer() {
    setState(() {
      _sessionSeed++;
      _isRunning = false;
      _elapsedSeconds = 0;
      _sessionStartedAt = null;
    });
  }

  Future<void> _updateMode(TimerMode mode) async {
    setState(() {
      _mode = mode;
    });
    await _persistPreferences();
  }

  Future<void> _updateMinutes(int minutes) async {
    setState(() {
      _selectedMinutes = minutes;
    });
    await _persistPreferences();
  }

  Future<void> _selectAmbient(AmbientScene scene) async {
    setState(() => _ambientScene = scene);
    if (scene == AmbientScene.none) {
      await SensoryFeedbackService.stopAmbient();
    } else {
      await SensoryFeedbackService.playAmbient(scene);
    }
  }

  Future<void> _handleSessionComplete({required bool isPomodoro}) async {
    final completedSeconds =
        _mode == TimerMode.countDown ? _selectedMinutes * 60 : _elapsedSeconds;
    final durationMinutes = (completedSeconds / 60).round();
    final endTime = DateTime.now();
    final startTime = _sessionStartedAt ?? endTime.subtract(Duration(seconds: completedSeconds));

    if (durationMinutes <= 0) {
      return;
    }

    final response =
        await ref.read(focus_stats.focusStatisticsProvider.notifier).saveSession(
          startTime: startTime,
          endTime: endTime,
          durationMinutes: durationMinutes,
          focusType: isPomodoro ? 'pomodoro' : 'stopwatch',
          whiteNoiseType:
              _ambientScene == AmbientScene.none ? null : _ambientScene.name,
        );
    final notificationService = ref.read(notificationServiceProvider);
    await notificationService.showSmartPush(
      title: isPomodoro ? '番茄完成' : '专注完成',
      body:
          response == null
              ? '本次专注 ${durationMinutes} 分钟，已记录到本地专注统计。'
              : '本次专注 ${durationMinutes} 分钟，获得 ${response.response.rewards.flameEarned} 点火苗奖励。',
      payload: <String, dynamic>{
        'type': 'focus_complete',
        'session_id': response?.response.id,
        'duration_minutes': durationMinutes,
      },
    );

    if (response == null) {
      return;
    }

    if (response.unlockedAchievements.isNotEmpty) {
      for (final achievement in response.unlockedAchievements) {
        final wsEvent = chat.AchievementUnlockEvent(achievementData: achievement);
        final result = ref
            .read(achievementProvider.notifier)
            .handleAchievementUnlock(wsEvent);
        if (result != null) {
          ref.read(pendingAchievementUnlockProvider.notifier).setPending(
                event: result.event,
                comboCount: result.comboCount,
              );
        }
      }
      await ref.read(achievementProvider.notifier).refreshAchievements();
      await ref.read(achievementProvider.notifier).refreshStats();
      await ref.read(achievementProvider.notifier).refreshStreakStats();
    }
  }

  @override
  Widget build(BuildContext context) {
    final isPomodoro = widget.preset == FocusTimerPreset.pomodoro;
    final accent = isPomodoro ? DS.warning : DS.brandPrimary;
    final title = isPomodoro ? '番茄钟' : '专注计时';
    final subtitle = isPomodoro
        ? '把单次专注收束成稳定节奏。适合复习块、冲刺块和长时深潜。'
        : '正计时和倒计时同台使用，适合任务推进、自由练习和时间校准。';
    final initialSeconds =
        _mode == TimerMode.countDown ? _selectedMinutes * 60 : 0;
    final maxSeconds =
        _mode == TimerMode.countDown ? _selectedMinutes * 60 : 2 * 60 * 60;
    final estimatedEnd = _mode == TimerMode.countDown
        ? DateTime.now().add(Duration(minutes: _selectedMinutes))
        : null;

    return ToolShell(
      surface: widget.surface,
      icon: isPomodoro ? Icons.timer_rounded : Icons.hourglass_bottom_rounded,
      title: title,
      subtitle: subtitle,
      accentColor: accent,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: _mode == TimerMode.countDown ? '倒计时模式' : '正计时模式',
          accentColor: accent,
          icon: _mode == TimerMode.countDown ? Icons.timelapse : Icons.schedule,
        ),
        ToolHeroChip(
          label: _isRunning ? '进行中' : '待开始',
          accentColor: accent,
          icon: _isRunning ? Icons.play_circle_fill_rounded : Icons.pause,
        ),
      ],
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          ToolSectionCard(
            accentColor: accent,
            title: '主计时盘',
            subtitle: '直接开始、暂停或重置。计时完成后会给出本地提示。',
            child: LayoutBuilder(
              builder: (context, constraints) => Center(
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    maxWidth: constraints.maxWidth.clamp(0, 320),
                  ),
                  child: TimerWidget(
                    key: ValueKey(
                      '${widget.preset.name}_${_mode.name}_$initialSeconds$_sessionSeed',
                    ),
                    mode: _mode,
                    initialSeconds: initialSeconds,
                    maxSeconds: maxSeconds,
                    onStateChange: (isRunning) {
                      setState(() {
                        _isRunning = isRunning;
                        if (isRunning) {
                          _sessionStartedAt ??= DateTime.now().subtract(
                            Duration(seconds: _elapsedSeconds),
                          );
                        }
                      });
                      if (isRunning && _ambientScene != AmbientScene.none) {
                        unawaited(
                          SensoryFeedbackService.playAmbient(_ambientScene),
                        );
                      } else if (!isRunning) {
                        unawaited(SensoryFeedbackService.pauseAmbient());
                      }
                    },
                    onTick: (seconds) {
                      if (!mounted) {
                        return;
                      }
                      setState(() {
                        _elapsedSeconds = _mode == TimerMode.countDown
                            ? (_selectedMinutes * 60 - seconds)
                            : seconds;
                      });
                    },
                    onComplete: () {
                      unawaited(_onComplete(isPomodoro: isPomodoro));
                    },
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ToolMetricRow(
            children: [
              ToolMetricCard(
                label: '当前时长',
                value:
                    _mode == TimerMode.countDown ? '$_selectedMinutes 分' : '开放',
                accentColor: accent,
                icon: Icons.flag_rounded,
                caption: _mode == TimerMode.countDown ? '单次目标时长' : '适合追踪投入长度',
              ),
              ToolMetricCard(
                label: '预计结束',
                value: estimatedEnd == null
                    ? '不限'
                    : '${estimatedEnd.hour.toString().padLeft(2, '0')}:${estimatedEnd.minute.toString().padLeft(2, '0')}',
                accentColor: accent,
                icon: Icons.event_available_rounded,
                caption: estimatedEnd == null ? '由你主动暂停' : '方便衔接下一段计划',
              ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: '背景音',
            subtitle: '计时期间播放，有助于进入专注状态。',
            child: _AmbientSelector(
              selected: _ambientScene,
              accentColor: accent,
              onSelect: _selectAmbient,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          ToolSectionCard(
            accentColor: accent,
            title: '计时设置',
            subtitle: '先选模式，再选时长。',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (!isPomodoro) ...[
                  Wrap(
                    spacing: DS.spacing10,
                    runSpacing: DS.spacing10,
                    children: [
                      ToolChoiceChip(
                        label: '正计时',
                        selected: _mode == TimerMode.countUp,
                        onTap: () => unawaited(_updateMode(TimerMode.countUp)),
                        accentColor: accent,
                        icon: Icons.schedule_rounded,
                      ),
                      ToolChoiceChip(
                        label: '倒计时',
                        selected: _mode == TimerMode.countDown,
                        onTap: () =>
                            unawaited(_updateMode(TimerMode.countDown)),
                        accentColor: accent,
                        icon: Icons.timelapse_rounded,
                      ),
                    ],
                  ),
                  if (_mode == TimerMode.countDown) ...[
                    const SizedBox(height: DS.spacing16),
                    Wrap(
                      spacing: DS.spacing10,
                      runSpacing: DS.spacing10,
                      children: _countdownOptions
                          .map(
                        (minutes) => ToolChoiceChip(
                              label: '$minutes 分钟',
                              selected: _selectedMinutes == minutes,
                              onTap: () => unawaited(_updateMinutes(minutes)),
                              accentColor: accent,
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ] else
                  Wrap(
                    spacing: DS.spacing10,
                    runSpacing: DS.spacing10,
                    children: _pomodoroOptions
                        .map(
                        (minutes) => ToolChoiceChip(
                            label: '$minutes 分钟',
                            selected: _selectedMinutes == minutes,
                            onTap: () => unawaited(_updateMinutes(minutes)),
                            accentColor: accent,
                            icon: minutes == 25
                                ? Icons.local_fire_department_rounded
                                : Icons.bolt_rounded,
                          ),
                        )
                        .toList(),
                  ),
              ],
            ),
          ),
        ],
      ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 560;
          final resetButton = SparkleButton(
            label: '重置',
            variant: ButtonVariant.ghost,
            onPressed: _resetTimer,
            icon: const Icon(Icons.refresh_rounded),
            expand: true,
          );
          final switchButton = SparkleButton(
            label: _mode == TimerMode.countUp ? '切到倒计时' : '切到正计时',
            onPressed: () {
              final nextMode = _mode == TimerMode.countUp
                  ? TimerMode.countDown
                  : TimerMode.countUp;
              setState(() {
                _sessionSeed++;
              });
              unawaited(_updateMode(nextMode));
            },
            icon: const Icon(Icons.swap_horiz_rounded),
            expand: true,
          );

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                resetButton,
                const SizedBox(height: DS.spacing12),
                switchButton,
              ],
            );
          }

          return Row(
            children: [
              Expanded(child: resetButton),
              const SizedBox(width: DS.spacing12),
              Expanded(child: switchButton),
            ],
          );
        },
      ),
    );
  }

  Future<void> _onComplete({required bool isPomodoro}) async {
    await SensoryFeedbackService.emit(
      SensoryFeedbackEvent.focusComplete,
    );
    await SensoryFeedbackService.stopAmbient();
    await _handleSessionComplete(isPomodoro: isPomodoro);
    if (!mounted) {
      return;
    }
    AppFeedback.success(
      context,
      isPomodoro ? '番茄时段已完成 🎉' : '倒计时已结束',
    );
    setState(() {
      _isRunning = false;
      _elapsedSeconds = 0;
      _sessionStartedAt = null;
    });
  }
}

// ---------------------------------------------------------------------------
// Ambient scene selector
// ---------------------------------------------------------------------------

class _AmbientSelector extends StatelessWidget {
  const _AmbientSelector({
    required this.selected,
    required this.accentColor,
    required this.onSelect,
  });

  final AmbientScene selected;
  final Color accentColor;
  final Future<void> Function(AmbientScene) onSelect;

  static const _scenes = AmbientScene.values;

  static IconData _icon(AmbientScene scene) => switch (scene) {
        AmbientScene.none => Icons.volume_off_rounded,
        AmbientScene.rain => Icons.water_drop_outlined,
        AmbientScene.ocean => Icons.waves_outlined,
        AmbientScene.whiteNoise => Icons.waves_rounded,
        AmbientScene.cafe => Icons.local_cafe_outlined,
        AmbientScene.piano => Icons.piano_outlined,
      };

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: DS.spacing8,
        runSpacing: DS.spacing8,
        children: _scenes.map((scene) {
          final isSelected = selected == scene;
          return ToolChoiceChip(
            label: scene.label,
            selected: isSelected,
            accentColor: accentColor,
            icon: _icon(scene),
            onTap: () => unawaited(onSelect(scene)),
          );
        }).toList(),
      );
}
