import 'package:flutter/material.dart';

/// Global slot limiter for attention-drawing pulse animations.
///
/// Wrap this near the root of the widget tree (e.g. in MaterialApp.builder).
/// SparkleAttentionPulse will request a slot before animating; when all slots
/// are taken, excess pulses degrade to static display.
class PulseScope extends InheritedWidget {
  PulseScope({
    required super.child,
    super.key,
  });

  /// Maximum concurrent active pulses across the app.
  static const int _maxActiveSlots = 2;

  final ValueNotifier<int> _activeCount = ValueNotifier<int>(0);

  /// Request an animation slot. Returns true if granted.
  bool requestSlot() {
    if (_activeCount.value >= _maxActiveSlots) return false;
    _activeCount.value++;
    return true;
  }

  /// Release a previously acquired slot.
  void releaseSlot() {
    if (_activeCount.value > 0) _activeCount.value--;
  }

  static PulseScope? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<PulseScope>();

  @override
  bool updateShouldNotify(PulseScope oldWidget) => false;
}
