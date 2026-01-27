import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Chat Mode Class
///
/// Defines the different AI collaboration modes available in the app.
/// Each mode has a unique API value, display label, icon, and associated color.
abstract class ChatMode {

  ChatMode({
    required this.apiValue,
    required this.label,
    required this.icon,
    required this.color,
  });
  /// API value sent to the backend
  final String apiValue;

  /// Display label shown in the UI
  final String label;

  /// Icon displayed for this mode
  final IconData icon;

  /// Primary color associated with this mode
  final Color color;

  /// Get ChatMode from API value
  static ChatMode fromApiValue(String value) => chatModeValues.firstWhere(
      (mode) => mode.apiValue == value,
      orElse: () => ChatModeStandard(),
    );

  /// Check if this is a multi-agent mode (not standard)
  bool get isMultiAgent => apiValue != 'standard';

  /// Get description text for the mode
  String get description {
    switch (apiValue) {
      case 'standard':
        return '使用标准 AI 对话模式';
      case 'deep_analysis':
        return '多专家协作深度解析问题';
      case 'study_plan':
        return '任务分解与学习计划协作';
      case 'error_diagnosis':
        return '错题诊断与分析循环';
      default:
        return '';
    }
  }

  /// Get the gradient for this mode
  LinearGradient get gradient => LinearGradient(
        colors: [
          color.withValues(alpha: 0.18),
          color.withValues(alpha: 0.08),
        ],
      );

  /// All available chat modes
  static List<ChatMode> get values => chatModeValues;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ChatMode && runtimeType == other.runtimeType && apiValue == other.apiValue;

  @override
  int get hashCode => apiValue.hashCode;
}

class ChatModeStandard extends ChatMode {
  ChatModeStandard() : super(
        apiValue: 'standard',
        label: '标准对话',
        icon: Icons.chat_bubble_outline,
        color: DS.brandPrimary,
      );
}

class ChatModeDeepAnalysis extends ChatMode {
  ChatModeDeepAnalysis()
      : super(
          apiValue: 'deep_analysis',
          label: '深度解析',
          icon: Icons.psychology,
          color: const Color(0xFF9C27B0),
        );
}

class ChatModeStudyPlan extends ChatMode {
  ChatModeStudyPlan()
      : super(
          apiValue: 'study_plan',
          label: '学习计划',
          icon: Icons.calendar_month,
          color: DS.successAccent,
      );
}

class ChatModeErrorDiagnosis extends ChatMode {
  ChatModeErrorDiagnosis()
      : super(
          apiValue: 'error_diagnosis',
          label: '错题分析',
          icon: Icons.quiz,
          color: DS.errorAccent,
      );
}

/// All available chat modes
final List<ChatMode> chatModeValues = [
  ChatModeStandard(),
  ChatModeDeepAnalysis(),
  ChatModeStudyPlan(),
  ChatModeErrorDiagnosis(),
];

/// Convenience accessors for common modes (for backward compatibility)
final ChatMode standard = ChatModeStandard();
final ChatMode deepAnalysis = ChatModeDeepAnalysis();
final ChatMode studyPlan = ChatModeStudyPlan();
final ChatMode errorDiagnosis = ChatModeErrorDiagnosis();
