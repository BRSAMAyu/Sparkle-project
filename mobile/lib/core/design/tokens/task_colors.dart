import 'package:flutter/material.dart';
import 'package:sparkle/shared/entities/task_model.dart' show TaskType;

export 'package:sparkle/shared/entities/task_model.dart' show TaskType;

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
        return _isDark
            ? _RawTaskColors.learningDark
            : _RawTaskColors.learningLight;
      case TaskType.training:
        return _isDark
            ? _RawTaskColors.trainingDark
            : _RawTaskColors.trainingLight;
      case TaskType.errorFix:
        return _isDark
            ? _RawTaskColors.errorFixDark
            : _RawTaskColors.errorFixLight;
      case TaskType.reflection:
        return _isDark
            ? _RawTaskColors.reflectionDark
            : _RawTaskColors.reflectionLight;
      case TaskType.social:
        return _isDark ? _RawTaskColors.socialDark : _RawTaskColors.socialLight;
      case TaskType.planning:
        return _isDark
            ? _RawTaskColors.planningDark
            : _RawTaskColors.planningLight;
      case TaskType.ocr:
        return _isDark ? _RawTaskColors.ocrDark : _RawTaskColors.ocrLight;
    }
  }

  Color getTint(TaskType type) => getColor(type).withValues(alpha: 0.1);
  Color getBorder(TaskType type) => getColor(type).withValues(alpha: 0.3);
  Color getIcon(TaskType type) => getColor(type);
  Color getLabel(TaskType type) => getColor(type);
}

class _RawTaskColors {
  _RawTaskColors._();

  // Light values are WCAG AA calibrated (UIUX round1 batch1): each passes
  // >=4.5:1 as pill label text on the 10% tint over white/ambient/primary.
  // Dark values are untouched by that calibration.
  static const Color learningLight = Color(0xFF175FB0); // was 64B5F6 (2.21:1 on white) -> 6.36:1
  static const Color learningDark = Color(0xFF4CC9F0);

  static const Color trainingLight = Color(0xFF8E4E00); // was FF9800 (2.16:1) -> 6.48:1
  static const Color trainingDark = Color(0xFFFFB74D);

  static const Color errorFixLight = Color(0xFFB0312A); // was EF5350 (3.49:1) -> 6.33:1
  static const Color errorFixDark = Color(0xFFFF6B6B);

  static const Color reflectionLight = Color(0xFF9C27B0); // already 6.30:1, kept

  static const Color reflectionDark = Color(0xFFBA68C8);

  // Social must always be amber.
  static const Color socialLight = Color(0xFF755F00); // was shared FFB703 (1.75:1) -> 6.19:1
  static const Color socialDark = Color(0xFFFFB703); // dark keeps the bright amber

  static const Color planningLight = Color(0xFF00695C); // was 009688 (3.67:1) -> 6.61:1
  static const Color planningDark = Color(0xFF4DB6AC);

  // OCR is gray.
  static const Color ocrLight = Color(0xFF4F6572); // was shared 78909C (3.35:1) -> 6.11:1
  static const Color ocrDark = Color(0xFF78909C); // dark keeps the lighter gray
}
