import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/data/models/expert_catalog_model.dart';

const String expertChatModePrefix = 'expert::';

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
    this.descriptionText,
  });

  /// API value sent to the backend
  final String apiValue;

  /// Display label shown in the UI
  final String label;

  /// Icon displayed for this mode
  final IconData icon;

  /// Primary color associated with this mode
  final Color color;

  /// Optional server-driven description
  final String? descriptionText;

  /// Get ChatMode from API value
  static ChatMode fromApiValue(String value) {
    if (value.startsWith(expertChatModePrefix)) {
      final expertId = value.substring(expertChatModePrefix.length);
      final expertName = expertId
          .split('_')
          .where((part) => part.isNotEmpty)
          .map((part) => part[0].toUpperCase() + part.substring(1))
          .join(' ');
      return ChatModeExpert(
        expertId: expertId,
        expertName: expertName.isEmpty ? expertId : expertName,
      );
    }
    return chatModeValues.firstWhere(
      (mode) => mode.apiValue == value,
      orElse: ChatModeStandard.new,
    );
  }

  static ChatMode fromCatalogMode(ExpertCatalogMode mode) => ChatModeCatalog(
        apiValue: mode.entryChatMode,
        label: mode.label.isEmpty ? mode.id : mode.label,
        descriptionText: mode.description,
        icon: _iconForMode(mode.id, mode.entryChatMode),
        color: _colorForMode(mode.id, mode.entryChatMode),
      );

  static List<ChatMode> catalogToModes(List<ExpertCatalogMode> modes) {
    final mapped = <String, ChatMode>{
      standard.apiValue: standard,
    };
    for (final mode in modes) {
      if (!mode.enabled) {
        continue;
      }
      final chatMode = ChatMode.fromCatalogMode(mode);
      mapped[chatMode.apiValue] = chatMode;
    }
    return mapped.values.toList();
  }

  /// Check if this is a multi-agent mode (not standard)
  bool get isMultiAgent => apiValue != 'standard';

  /// Get description text for the mode
  String get description {
    if (descriptionText != null && descriptionText!.isNotEmpty) {
      return descriptionText!;
    }
    switch (apiValue) {
      case 'standard':
        return '使用标准 AI 对话模式';
      case 'deep_analysis':
        return '多专家协作深度解析问题';
      case 'study_plan':
        return '任务分解与学习计划协作';
      case 'error_diagnosis':
        return '错题诊断与分析循环';
      case 'expert_auto':
        return '自动选择最合适专家并协作';
      default:
        if (apiValue.startsWith(expertChatModePrefix)) {
          return '专家直达模式';
        }
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
      other is ChatMode &&
          runtimeType == other.runtimeType &&
          apiValue == other.apiValue;

  @override
  int get hashCode => apiValue.hashCode;
}

class ChatModeStandard extends ChatMode {
  ChatModeStandard()
      : super(
          apiValue: 'standard',
          label: '标准对话',
          icon: Icons.chat_bubble_outline,
          color: DS.brandPrimaryConst,
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

class ChatModeExpertAuto extends ChatMode {
  ChatModeExpertAuto()
      : super(
          apiValue: 'expert_auto',
          label: '专家自动',
          icon: Icons.auto_awesome_mosaic,
          color: const Color(0xFF00897B),
        );
}

class ChatModeExpert extends ChatMode {
  ChatModeExpert({
    required this.expertId,
    required this.expertName,
  }) : super(
          apiValue: '$expertChatModePrefix$expertId',
          label: expertName,
          icon: Icons.person_search,
          color: const Color(0xFF1565C0),
        );

  final String expertId;
  final String expertName;
}

class ChatModeCatalog extends ChatMode {
  ChatModeCatalog({
    required super.apiValue,
    required super.label,
    required super.icon,
    required super.color,
    super.descriptionText,
  });
}

IconData _iconForMode(String modeId, String chatMode) {
  switch (modeId) {
    case 'standard':
      return Icons.chat_bubble_outline;
    case 'deep_analysis':
      return Icons.psychology;
    case 'study_plan':
      return Icons.calendar_month;
    case 'error_diagnosis':
      return Icons.quiz;
    case 'expert_auto':
      return Icons.auto_awesome_mosaic;
    default:
      if (chatMode.startsWith(expertChatModePrefix)) {
        return Icons.person_search;
      }
      return Icons.hub;
  }
}

Color _colorForMode(String modeId, String chatMode) {
  switch (modeId) {
    case 'standard':
      return DS.brandPrimaryConst;
    case 'deep_analysis':
      return const Color(0xFF9C27B0);
    case 'study_plan':
      return DS.successAccent;
    case 'error_diagnosis':
      return DS.errorAccent;
    case 'expert_auto':
      return const Color(0xFF00897B);
    default:
      if (chatMode.startsWith(expertChatModePrefix)) {
        return const Color(0xFF1565C0);
      }
      return DS.brandPrimaryConst;
  }
}

/// All available chat modes (offline fallback)
final List<ChatMode> chatModeValues = [
  ChatModeStandard(),
  ChatModeDeepAnalysis(),
  ChatModeStudyPlan(),
  ChatModeErrorDiagnosis(),
  ChatModeExpertAuto(),
];

/// Convenience accessors for common modes (for backward compatibility)
final ChatMode standard = ChatModeStandard();
final ChatMode deepAnalysis = ChatModeDeepAnalysis();
final ChatMode studyPlan = ChatModeStudyPlan();
final ChatMode errorDiagnosis = ChatModeErrorDiagnosis();
final ChatMode expertAuto = ChatModeExpertAuto();
