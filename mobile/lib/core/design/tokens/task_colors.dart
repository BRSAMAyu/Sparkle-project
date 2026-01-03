import 'package:flutter/material.dart';
import 'package:sparkle/data/models/task_model.dart' show TaskType;

export 'package:sparkle/data/models/task_model.dart' show TaskType;

/// Single source of truth for task colors.
///
/// DO NOT define task colors elsewhere in the UI layer.
@immutable
class TaskColors {
  const TaskColors({required this.brightness});

  final Brightness brightness;

  bool get _isDark => brightness == Brightness.dark;

  Color getColor(TaskType type) {
    switch (type) {
      case TaskType.learning:
        return _isDark ? _RawTaskColors.learningDark : _RawTaskColors.learningLight;
      case TaskType.training:
        return _isDark ? _RawTaskColors.trainingDark : _RawTaskColors.trainingLight;
      case TaskType.errorFix:
        return _isDark ? _RawTaskColors.errorFixDark : _RawTaskColors.errorFixLight;
      case TaskType.reflection:
        return _isDark ? _RawTaskColors.reflectionDark : _RawTaskColors.reflectionLight;
      case TaskType.social:
        return _RawTaskColors.social;
      case TaskType.planning:
        return _isDark ? _RawTaskColors.planningDark : _RawTaskColors.planningLight;
    }
  }

  Color getTint(TaskType type) => getColor(type).withValues(alpha: 0.1);
  Color getBorder(TaskType type) => getColor(type).withValues(alpha: 0.3);
  Color getIcon(TaskType type) => getColor(type);
  Color getLabel(TaskType type) => getColor(type);
}

class _RawTaskColors {
  _RawTaskColors._();

  static const Color learningLight = Color(0xFF64B5F6);
  static const Color learningDark = Color(0xFF4CC9F0);

  static const Color trainingLight = Color(0xFFFF9800);
  static const Color trainingDark = Color(0xFFFFB74D);

  static const Color errorFixLight = Color(0xFFEF5350);
  static const Color errorFixDark = Color(0xFFFF6B6B);

  static const Color reflectionLight = Color(0xFF9C27B0);
  static const Color reflectionDark = Color(0xFFBA68C8);

  // Social must always be amber.
  static const Color social = Color(0xFFFFB703);

  static const Color planningLight = Color(0xFF009688);
  static const Color planningDark = Color(0xFF4DB6AC);
}
