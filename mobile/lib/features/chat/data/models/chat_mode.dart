import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Chat Mode Enum
///
/// Defines the different AI collaboration modes available in the app.
/// Each mode has a unique API value, display label, icon, and associated color.
enum ChatMode {
  /// Standard mode - uses the default LangGraph flow
  standard('standard', '标准对话', Icons.chat_bubble_outline, DS.brandPrimary),

  /// Deep Analysis mode - multi-expert progressive exploration
  deepAnalysis(
    'deep_analysis',
    '深度解析',
    Icons.psychology,
    Color(0xFF9C27B0), // Purple
  ),

  /// Study Plan mode - task decomposition collaboration
  studyPlan(
    'study_plan',
    '学习计划',
    Icons.calendar_month,
    DS.successAccent,
  ),

  /// Error Diagnosis mode - error diagnosis loop
  errorDiagnosis(
    'error_diagnosis',
    '错题分析',
    Icons.quiz,
    DS.errorAccent,
  );

  /// API value sent to the backend
  final String apiValue;

  /// Display label shown in the UI
  final String label;

  /// Icon displayed for this mode
  final IconData icon;

  /// Primary color associated with this mode
  final Color color;

  const ChatMode(
    this.apiValue,
    this.label,
    this.icon,
    this.color,
  );

  /// Get ChatMode from API value
  static ChatMode fromApiValue(String value) {
    return ChatMode.values.firstWhere(
      (mode) => mode.apiValue == value,
      orElse: () => ChatMode.standard,
    );
  }

  /// Check if this is a multi-agent mode (not standard)
  bool get isMultiAgent => this != ChatMode.standard;
}

/// Extension for ChatMode utility methods
extension ChatModeExtension on ChatMode {
  /// Get description text for the mode
  String get description {
    switch (this) {
      case ChatMode.standard:
        return '使用标准 AI 对话模式';
      case ChatMode.deepAnalysis:
        return '多专家协作深度解析问题';
      case ChatMode.studyPlan:
        return '任务分解与学习计划协作';
      case ChatMode.errorDiagnosis:
        return '错题诊断与分析循环';
    }
  }

  /// Get the gradient for this mode
  LinearGradient get gradient {
    return LinearGradient(
      colors: [
        color.withValues(alpha: 0.18),
        color.withValues(alpha: 0.08),
      ],
    );
  }
}
