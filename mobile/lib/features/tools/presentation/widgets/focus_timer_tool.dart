import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/task/presentation/widgets/timer_widget.dart';

enum FocusTimerPreset {
  stopwatch,
  pomodoro,
}

class FocusTimerTool extends StatefulWidget {
  const FocusTimerTool({
    required this.preset,
    super.key,
  });

  final FocusTimerPreset preset;

  @override
  State<FocusTimerTool> createState() => _FocusTimerToolState();
}

class _FocusTimerToolState extends State<FocusTimerTool> {
  static const List<int> _countdownOptions = [15, 25, 45, 60];

  late TimerMode _mode;
  late int _selectedMinutes;

  @override
  void initState() {
    super.initState();
    _mode = widget.preset == FocusTimerPreset.pomodoro
        ? TimerMode.countDown
        : TimerMode.countUp;
    _selectedMinutes =
        widget.preset == FocusTimerPreset.pomodoro ? 25 : _countdownOptions[0];
  }

  @override
  Widget build(BuildContext context) {
    final title = widget.preset == FocusTimerPreset.pomodoro ? '番茄钟' : '专注计时';
    final subtitle = widget.preset == FocusTimerPreset.pomodoro
        ? '默认 25 分钟工作周期，可一键重置。'
        : '正计时与倒计时都可直接开始。';
    final initialSeconds =
        _mode == TimerMode.countDown ? _selectedMinutes * 60 : 0;
    final maxSeconds =
        _mode == TimerMode.countDown ? _selectedMinutes * 60 : 60 * 60;

    return Container(
      padding: const EdgeInsets.all(DS.spacing24),
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(color: DS.borderSubtle),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.spacing10),
                decoration: BoxDecoration(
                  color: DS.primaryBase.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  widget.preset == FocusTimerPreset.pomodoro
                      ? Icons.timer_rounded
                      : Icons.hourglass_bottom_rounded,
                  color: DS.primaryBase,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: DS.fontWeightBold,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing20),
          if (widget.preset == FocusTimerPreset.stopwatch) ...[
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: [
                _buildModeChip(
                  label: '正计时',
                  selected: _mode == TimerMode.countUp,
                  onTap: () => setState(() => _mode = TimerMode.countUp),
                ),
                _buildModeChip(
                  label: '倒计时',
                  selected: _mode == TimerMode.countDown,
                  onTap: () => setState(() => _mode = TimerMode.countDown),
                ),
              ],
            ),
            if (_mode == TimerMode.countDown) ...[
              const SizedBox(height: DS.spacing12),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: _countdownOptions
                    .map(
                      (minutes) => _buildModeChip(
                        label: '$minutes 分钟',
                        selected: _selectedMinutes == minutes,
                        onTap: () => setState(() => _selectedMinutes = minutes),
                      ),
                    )
                    .toList(),
              ),
            ],
            const SizedBox(height: DS.spacing24),
          ] else ...[
            Row(
              children: [
                Text(
                  '工作时长',
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: DS.textSecondary,
                      ),
                ),
                const SizedBox(width: DS.spacing12),
                _buildModeChip(
                  label: '25 分钟',
                  selected: _selectedMinutes == 25,
                  onTap: () => setState(() => _selectedMinutes = 25),
                ),
                const SizedBox(width: DS.spacing8),
                _buildModeChip(
                  label: '50 分钟',
                  selected: _selectedMinutes == 50,
                  onTap: () => setState(() => _selectedMinutes = 50),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing24),
          ],
          Center(
            child: TimerWidget(
              key: ValueKey(
                  '${widget.preset.name}_${_mode.name}_$initialSeconds'),
              mode: _mode,
              initialSeconds: initialSeconds,
              maxSeconds: maxSeconds,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModeChip({
    required String label,
    required bool selected,
    required VoidCallback onTap,
  }) =>
      InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(999),
        child: AnimatedContainer(
          duration: DS.durationFast,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing8,
          ),
          decoration: BoxDecoration(
            color: selected
                ? DS.primaryBase
                : DS.primaryBase.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: selected ? DS.brandPrimaryConst : DS.textPrimary,
                  fontWeight: DS.fontWeightSemiBold,
                ),
          ),
        ),
      );
}
