import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/navigation/shell_navigation.dart';

/// Wraps a scrollable child and scrolls it to top when the active tab is
/// re-tapped (via [scrollToTopSignalProvider]).
class TapToTopListener extends ConsumerWidget {
  const TapToTopListener({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.listen(scrollToTopSignalProvider, (prev, next) {
      final position = PrimaryScrollController.maybeOf(context);
      if (position != null && position.hasListeners) {
        position.animateTo(
          0,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
        );
      }
    });
    return child;
  }
}
