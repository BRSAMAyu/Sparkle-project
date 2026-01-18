import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/intervention_handler_service.dart';

class DebugInterventionTrigger extends ConsumerStatefulWidget {
  final Widget child;

  const DebugInterventionTrigger({
    super.key,
    required this.child,
  });

  @override
  ConsumerState<DebugInterventionTrigger> createState() =>
      _DebugInterventionTriggerState();
}

class _DebugInterventionTriggerState
    extends ConsumerState<DebugInterventionTrigger> {
  int _tapCount = 0;
  DateTime? _firstTapAt;

  void _handleTap() {
    if (!kDebugMode) return;
    final now = DateTime.now();
    _firstTapAt ??= now;
    if (now.difference(_firstTapAt!) > const Duration(seconds: 2)) {
      _tapCount = 0;
      _firstTapAt = now;
    }
    _tapCount += 1;
    if (_tapCount >= 5) {
      _tapCount = 0;
      _firstTapAt = null;
      ref.read(interventionHandlerServiceProvider).debugTrigger();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return widget.child;
    }

    return Stack(
      children: [
        widget.child,
        Positioned(
          top: 0,
          left: 0,
          width: 48,
          height: 48,
          child: GestureDetector(
            behavior: HitTestBehavior.translucent,
            onTap: _handleTap,
          ),
        ),
      ],
    );
  }
}
