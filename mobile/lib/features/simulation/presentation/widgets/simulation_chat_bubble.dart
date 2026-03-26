import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart' hide AnimatedSlide;

class SimulationChatBubble extends StatefulWidget {
  const SimulationChatBubble({
    required this.speaker,
    required this.message,
    required this.round,
    super.key,
  });

  final String speaker;
  final String message;
  final int round;

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
    final revealed = widget.message.substring(
      0,
      _visibleLength.clamp(0, widget.message.length),
    );

    return AnimatedSlide(
      duration: DS.durationNormal,
      curve: Curves.easeOutCubic,
      offset: _entered
          ? Offset.zero
          : Offset(isLeftAligned ? -0.08 : 0.08, 0),
      child: AnimatedOpacity(
        duration: DS.durationNormal,
        opacity: _entered ? 1 : 0,
        child: Align(
          alignment: isLeftAligned ? Alignment.centerLeft : Alignment.centerRight,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 340),
            child: Container(
              margin: const EdgeInsets.only(bottom: 12),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: scheme.surfaceContainerHighest.withValues(alpha: 0.86),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(20),
                  topRight: const Radius.circular(20),
                  bottomLeft: Radius.circular(isLeftAligned ? 8 : 20),
                  bottomRight: Radius.circular(isLeftAligned ? 20 : 8),
                ),
                border: Border.all(color: accent.withValues(alpha: 0.16)),
                boxShadow: [
                  BoxShadow(
                    color: accent.withValues(alpha: 0.08),
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircleAvatar(
                        radius: 14,
                        backgroundColor: accent.withValues(alpha: 0.14),
                        child: Text(
                          widget.speaker.isEmpty ? '?' : widget.speaker[0],
                          style: TextStyle(
                            color: accent,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Flexible(
                        child: Text(
                          widget.speaker,
                          style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                fontWeight: FontWeight.w700,
                                color: accent,
                              ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    revealed,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          height: 1.5,
                        ),
                  ),
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
}
