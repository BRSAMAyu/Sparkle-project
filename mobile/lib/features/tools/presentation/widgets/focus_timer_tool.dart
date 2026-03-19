import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

enum FocusTimerPreset {
  stopwatch,
  pomodoro,
}

class FocusTimerTool extends StatefulWidget {
  const FocusTimerTool({
    required this.preset,
    super.key,
    this.surface = ToolSurface.page,
  });

  final FocusTimerPreset preset;
  final ToolSurface surface;

  @override
  State<FocusTimerTool> createState() => _FocusTimerToolState();
}

class _FocusTimerToolState extends State<FocusTimerTool> {
  static const List<int> _countdownOptions = [10, 15, 25, 45, 60, 90];
  static const List<int> _pomodoroOptions = [25, 50, 90];

  late TimerMode _mode;
  late int _selectedMinutes;
  int _sessionSeed = 0;
  bool _isRunning = false;

  @override
  void initState() {
    super.initState();
    _mode = widget.preset == FocusTimerPreset.pomodoro
        ? TimerMode.countDown
        : TimerMode.countUp;
    _selectedMinutes =
        widget.preset == FocusTimerPreset.pomodoro ? 25 : _countdownOptions[1];
  }

  void _resetTimer() {
    setState(() {
      _sessionSeed++;
      _isRunning = false;
    });
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
                      });
                    },
                    onComplete: () {
                      unawaited(HapticFeedback.heavyImpact());
                      AppFeedback.success(
                        context,
                        isPomodoro ? '番茄时段已完成' : '倒计时已结束',
                      );
                      setState(() {
                        _isRunning = false;
                      });
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
                        onTap: () => setState(() => _mode = TimerMode.countUp),
                        accentColor: accent,
                        icon: Icons.schedule_rounded,
                      ),
                      ToolChoiceChip(
                        label: '倒计时',
                        selected: _mode == TimerMode.countDown,
                        onTap: () =>
                            setState(() => _mode = TimerMode.countDown),
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
                              onTap: () =>
                                  setState(() => _selectedMinutes = minutes),
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
                            onTap: () =>
                                setState(() => _selectedMinutes = minutes),
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
            onPressed: () => setState(() {
              _mode = _mode == TimerMode.countUp
                  ? TimerMode.countDown
                  : TimerMode.countUp;
              _sessionSeed++;
            }),
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
}
