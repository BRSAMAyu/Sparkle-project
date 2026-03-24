import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
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

class BreathingTool extends StatefulWidget {
  const BreathingTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

  @override
  State<BreathingTool> createState() => _BreathingToolState();
}

class _BreathingToolState extends State<BreathingTool>
    with SingleTickerProviderStateMixin {
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

  late final AnimationController _controller;
  Timer? _timer;

  int _selectedDurationIndex = 1;
  int _selectedPatternIndex = 0;
  bool _isPlaying = false;
  int _completedRounds = 0;
  int _totalRounds = 0;
  String _instruction = '准备';

  _BreathingPattern get _pattern => _patterns[_selectedPatternIndex];

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
      value: 0.0,
    );
    _updateTotalRounds();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _updateTotalRounds() {
    final seconds = _durations[_selectedDurationIndex] * 60;
    _totalRounds = (seconds / _pattern.cycleSeconds).ceil();
  }

  void _startBreathing() {
    setState(() {
      _isPlaying = true;
      _completedRounds = 0;
      _updateTotalRounds();
    });
    _runPhase(0);
  }

  void _stopBreathing() {
    _timer?.cancel();
    _controller.stop();
    _controller.value = 0;
    setState(() {
      _isPlaying = false;
      _instruction = '准备';
    });
  }

  void _runPhase(int phaseIndex) {
    if (!_isPlaying) {
      return;
    }

    final phases = <({
      String label,
      int seconds,
      bool grow,
      bool holdExpanded,
    })>[
      (label: '吸气', seconds: _pattern.inhale, grow: true, holdExpanded: false),
      (label: '停留', seconds: _pattern.hold, grow: false, holdExpanded: true),
      (label: '呼气', seconds: _pattern.exhale, grow: false, holdExpanded: false),
      (label: '停留', seconds: _pattern.rest, grow: false, holdExpanded: false),
    ].where((phase) => phase.seconds > 0).toList();

    if (phaseIndex >= phases.length) {
      final nextRound = _completedRounds + 1;
      if (nextRound >= _totalRounds) {
        _stopBreathing();
        AppFeedback.success(context, '呼吸练习已完成');
        return;
      }

      setState(() {
        _completedRounds = nextRound;
      });
      _runPhase(0);
      return;
    }

    final phase = phases[phaseIndex];
    setState(() {
      _instruction = phase.label;
    });

    if (phase.grow) {
      _controller.duration = Duration(seconds: phase.seconds);
      unawaited(_controller.forward(from: _controller.value));
    } else if (phase.holdExpanded) {
      _controller.stop();
      _controller.value = 1;
    } else {
      _controller.duration = Duration(seconds: phase.seconds);
      unawaited(
        _controller.reverse(
          from: _controller.value == 0 ? 1 : _controller.value,
        ),
      );
    }

    _timer?.cancel();
    _timer = Timer(Duration(seconds: phase.seconds), () {
      if (!mounted) {
        return;
      }
      _runPhase(phaseIndex + 1);
    });
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
            subtitle: '先选模式，再选练习时长。',
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
                      onTap: () {
                        setState(() {
                          _selectedPatternIndex = index;
                          _updateTotalRounds();
                        });
                      },
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
                      onTap: () {
                        setState(() {
                          _selectedDurationIndex = index;
                          _updateTotalRounds();
                        });
                      },
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
