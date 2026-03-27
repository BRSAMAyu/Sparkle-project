import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;
import 'package:sparkle/features/simulation/data/models/simulation_models.dart';

class SimulationChatBubble extends StatefulWidget {
  const SimulationChatBubble({
    required this.speaker,
    required this.message,
    required this.round,
    super.key,
    this.participant,
    this.replyToSpeaker,
    this.turnGoal,
    this.isSpotlighted = false,
  });

  final String speaker;
  final String message;
  final int round;
  final SimulationParticipantModel? participant;
  final String? replyToSpeaker;
  final String? turnGoal;
  final bool isSpotlighted;

  @override
  State<SimulationChatBubble> createState() => _SimulationChatBubbleState();
}

class _SimulationChatBubbleState extends State<SimulationChatBubble> {
  Timer? _timer;
  int _visibleLength = 0;
  bool _entered = false;

  @override
  void initState() {
    super.initState();
    _startReveal();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      setState(() => _entered = true);
    });
  }

  @override
  void didUpdateWidget(covariant SimulationChatBubble oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.message != widget.message) {
      _startReveal();
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startReveal() {
    _timer?.cancel();
    _visibleLength = 0;
    final message = widget.message;
    if (message.isEmpty) {
      return;
    }
    final totalLength = message.length;
    final step = totalLength <= 40 ? 1 : 2;
    _timer = Timer.periodic(const Duration(milliseconds: 16), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _visibleLength = (_visibleLength + step).clamp(0, totalLength);
      });
      if (_visibleLength >= totalLength) {
        timer.cancel();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final accent = _accentForSpeaker(widget.speaker);
    final isLeftAligned = widget.speaker.hashCode.isEven;
    final participant = widget.participant;
    final revealed = widget.message.substring(
      0,
      _visibleLength.clamp(0, widget.message.length),
    );

    return AnimatedSlide(
      duration: DS.durationNormal,
      curve: Curves.easeOutCubic,
      offset: _entered ? Offset.zero : Offset(isLeftAligned ? -0.08 : 0.08, 0),
      child: AnimatedOpacity(
        duration: DS.durationNormal,
        opacity: _entered ? 1 : 0,
        child: Align(
          alignment:
              isLeftAligned ? Alignment.centerLeft : Alignment.centerRight,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 340),
            child: Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: isLeftAligned ? Alignment.topLeft : Alignment.topRight,
                  end: Alignment.bottomCenter,
                  colors: [
                    accent.withValues(
                      alpha: widget.isSpotlighted ? 0.22 : 0.14,
                    ),
                    scheme.surfaceContainerHighest.withValues(alpha: 0.92),
                  ],
                ),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(20),
                  topRight: const Radius.circular(20),
                  bottomLeft: Radius.circular(isLeftAligned ? 8 : 20),
                  bottomRight: Radius.circular(isLeftAligned ? 20 : 8),
                ),
                border: Border.all(
                  color: accent.withValues(
                    alpha: widget.isSpotlighted ? 0.32 : 0.16,
                  ),
                  width: widget.isSpotlighted ? 1.4 : 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: accent.withValues(
                      alpha: widget.isSpotlighted ? 0.16 : 0.08,
                    ),
                    blurRadius: widget.isSpotlighted ? 28 : 20,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (widget.isSpotlighted) ...[
                    Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.mic_rounded,
                            size: 14,
                            color: accent,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            '当前焦点发言',
                            style: Theme.of(context)
                                .textTheme
                                .labelMedium
                                ?.copyWith(
                                  color: accent,
                                  fontWeight: FontWeight.w700,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  if (widget.replyToSpeaker?.isNotEmpty ?? false) ...[
                    Container(
                      margin: const EdgeInsets.only(bottom: 10),
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: scheme.surface.withValues(alpha: 0.72),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.reply_rounded,
                            size: 14,
                            color: accent,
                          ),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              '承接 ${widget.replyToSpeaker} 的观点',
                              style: Theme.of(context)
                                  .textTheme
                                  .labelMedium
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        width: 34,
                        height: 34,
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [
                              accent.withValues(alpha: 0.96),
                              accent.withValues(alpha: 0.68),
                            ],
                          ),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Center(
                          child: Icon(
                            _speakerIcon(participant),
                            color: Colors.white,
                            size: 18,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.speaker,
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(
                                    fontWeight: FontWeight.w800,
                                    color: accent,
                                  ),
                            ),
                            if ((participant?.roleHint.isNotEmpty ?? false) ||
                                (participant?.stance?.isNotEmpty ?? false)) ...[
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: [
                                  if (participant?.roleHint.isNotEmpty ?? false)
                                    _MetaPill(
                                      label: participant!.roleHint,
                                      foreground: accent,
                                      background:
                                          accent.withValues(alpha: 0.12),
                                    ),
                                  if (participant?.stance?.isNotEmpty ?? false)
                                    _MetaPill(
                                      label: '立场 ${participant!.stance!}',
                                      foreground: DS.textSecondary,
                                      background:
                                          scheme.surface.withValues(alpha: 0.9),
                                    ),
                                ],
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                  if ((participant?.sourceNodeName?.isNotEmpty ?? false) ||
                      (participant?.source?.isNotEmpty ?? false)) ...[
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        if (participant?.sourceNodeName?.isNotEmpty ?? false)
                          _MetaPill(
                            icon: Icons.hub_rounded,
                            label: participant!.sourceNodeName!,
                            foreground: DS.info,
                            background: DS.info.withValues(alpha: 0.12),
                          ),
                        if (participant?.source?.isNotEmpty ?? false)
                          _MetaPill(
                            icon: Icons.dataset_linked_rounded,
                            label: _sourceLabel(participant!.source!),
                            foreground: DS.textSecondary,
                            background: scheme.surfaceContainerHigh
                                .withValues(alpha: 0.9),
                          ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 8),
                  Text(
                    revealed,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          height: 1.5,
                        ),
                  ),
                  if (participant?.contextAnchor?.isNotEmpty ?? false) ...[
                    const SizedBox(height: 10),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: scheme.surface.withValues(alpha: 0.72),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: accent.withValues(alpha: 0.14),
                        ),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.anchor_rounded,
                            size: 16,
                            color: accent,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              participant!.contextAnchor!,
                              style: Theme.of(context)
                                  .textTheme
                                  .bodySmall
                                  ?.copyWith(
                                    color: DS.textSecondary,
                                    height: 1.4,
                                  ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  if ((widget.replyToSpeaker?.isNotEmpty ?? false) ||
                      (widget.turnGoal?.isNotEmpty ?? false)) ...[
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: [
                        if (widget.replyToSpeaker?.isNotEmpty ?? false)
                          _MetaPill(label: '回应 ${widget.replyToSpeaker}'),
                        if (widget.turnGoal?.isNotEmpty ?? false)
                          _MetaPill(
                            icon: Icons.flag_rounded,
                            label: _turnGoalLabel(widget.turnGoal!),
                          ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 8),
                  Text(
                    '第 ${widget.round} 轮',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Color _accentForSpeaker(String speaker) {
    final palette = <Color>[
      DS.info,
      DS.success,
      DS.warning,
      DS.brandPrimary,
      DS.accent,
    ];
    return palette[speaker.hashCode.abs() % palette.length];
  }

  String _sourceLabel(String source) {
    switch (source) {
      case 'galaxy':
        return '知识星图';
      case 'tasks':
        return '任务记录';
      case 'plan':
        return '学习计划';
      case 'starter_graph':
        return '起步图谱';
      default:
        return source;
    }
  }

  IconData _speakerIcon(SimulationParticipantModel? participant) {
    final role = participant?.roleHint.toLowerCase() ?? '';
    final stance = participant?.stance?.toLowerCase() ?? '';
    if (role.contains('质疑') || stance.contains('反')) {
      return Icons.gavel_rounded;
    }
    if (role.contains('联想') || role.contains('创意')) {
      return Icons.auto_awesome_rounded;
    }
    if (role.contains('导航') || role.contains('教练')) {
      return Icons.explore_rounded;
    }
    if (role.contains('分析') || role.contains('专家')) {
      return Icons.psychology_alt_rounded;
    }
    return Icons.person_rounded;
  }

  String _turnGoalLabel(String turnGoal) {
    switch (turnGoal) {
      case 'challenge':
        return '提出质疑';
      case 'synthesize':
        return '整合观点';
      case 'open':
        return '打开话题';
      case 'guide_user':
        return '邀请用户作答';
      default:
        return '目标 $turnGoal';
    }
  }
}

class _MetaPill extends StatelessWidget {
  const _MetaPill({
    required this.label,
    this.icon,
    this.foreground,
    this.background,
  });

  final String label;
  final IconData? icon;
  final Color? foreground;
  final Color? background;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: background ?? DS.surfaceTertiary,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(
                icon,
                size: 12,
                color: foreground ?? DS.textSecondary,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              label,
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: foreground ?? DS.textSecondary,
                  ),
            ),
          ],
        ),
      );
}
