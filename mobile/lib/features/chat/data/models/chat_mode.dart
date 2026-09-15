import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';

const String expertChatModePrefix = 'expert::';
const String teamChatModePrefix = 'team::';

/// Chat Mode Class
///
/// Defines the different AI collaboration modes available in the app.
/// Each mode has a unique API value, display label, icon, and associated color.
abstract class ChatMode {
  ChatMode({
    required this.apiValue,
    required this.icon,
    required this.color,
  });

  /// API value sent to the backend
  final String apiValue;

  /// Icon displayed for this mode
  final IconData icon;

  /// Primary color associated with this mode
  final Color color;

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
        displayName: expertName.isEmpty ? expertId : expertName,
      );
    }
    if (value.startsWith(teamChatModePrefix)) {
      final raw = value.substring(teamChatModePrefix.length);
      try {
        final decoded = jsonDecode(raw);
        if (decoded is Map<String, dynamic>) {
          final agents = decoded['agents'] is List
              ? (decoded['agents'] as List).map((e) => '$e').toList()
              : const <String>[];
          final excluded = decoded['excluded'] is List
              ? (decoded['excluded'] as List).map((e) => '$e').toList()
              : const <String>[];
          final finalAgents = decoded['final_agents'] is List
              ? (decoded['final_agents'] as List).map((e) => '$e').toList()
              : const <String>[];
          final mode = decoded['mode']?.toString() ?? 'auto';
          return ChatModeTeam(
            selectedAgents: agents,
            excludedAgents: excluded,
            finalAnswerAgents: finalAgents,
            collaborationMode: mode,
            teamLabel: decoded['label']?.toString(),
            teamId: decoded['team_id']?.toString(),
          );
        }
      } catch (_) {}
    }
    return chatModeValues.firstWhere(
      (mode) => mode.apiValue == value,
      orElse: ChatModeStandard.new,
    );
  }

  /// Check if this is a multi-agent mode (not standard)
  bool get isMultiAgent => apiValue != 'standard';

  /// Get description text for the mode
  String get description {
    final l10n = I18nService.instance.l10n;
    switch (apiValue) {
      case 'standard':
        return l10n.chatModeStandardDesc;
      case 'deep_analysis':
        return l10n.chatModeDeepAnalysisDesc;
      case 'study_plan':
        return l10n.chatModeStudyPlanDesc;
      case 'error_diagnosis':
        return l10n.chatModeErrorDiagnosisDesc;
      case 'expert_auto':
        return l10n.chatModeExpertAutoDesc;
      default:
        if (apiValue.startsWith(teamChatModePrefix)) {
          return l10n.chatModeCustomTeamDesc;
        }
        if (apiValue.startsWith(expertChatModePrefix)) {
          return l10n.chatModeExpertDirectDesc;
        }
        return '';
    }
  }

  /// Display label shown in the UI
  String get label {
    final l10n = I18nService.instance.l10n;
    switch (apiValue) {
      case 'standard':
        return l10n.chatModeStandard;
      case 'deep_analysis':
        return l10n.chatModeDeepAnalysis;
      case 'study_plan':
        return l10n.chatModeStudyPlan;
      case 'error_diagnosis':
        return l10n.chatModeErrorDiagnosis;
      case 'expert_auto':
        return l10n.chatModeExpertAuto;
      default:
        if (apiValue.startsWith(teamChatModePrefix)) {
          return l10n.chatModeCustomTeam;
        }
        if (apiValue.startsWith(expertChatModePrefix)) {
          return expertName ?? apiValue.substring(expertChatModePrefix.length);
        }
        return apiValue;
    }
  }

  String? get expertName => null;

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
          icon: Icons.chat_bubble_outline,
          color: DS.brandPrimaryConst,
        );
}

class ChatModeDeepAnalysis extends ChatMode {
  ChatModeDeepAnalysis()
      : super(
          apiValue: 'deep_analysis',
          icon: Icons.psychology,
          color: DS.brandSecondary,
        );
}

class ChatModeStudyPlan extends ChatMode {
  ChatModeStudyPlan()
      : super(
          apiValue: 'study_plan',
          icon: Icons.calendar_month,
          color: DS.successAccent,
        );
}

class ChatModeErrorDiagnosis extends ChatMode {
  ChatModeErrorDiagnosis()
      : super(
          apiValue: 'error_diagnosis',
          icon: Icons.quiz,
          color: DS.errorAccent,
        );
}

class ChatModeExpertAuto extends ChatMode {
  ChatModeExpertAuto()
      : super(
          apiValue: 'expert_auto',
          icon: Icons.auto_awesome_mosaic,
          color: DS.success,
        );
}

class ChatModeExpert extends ChatMode {
  ChatModeExpert({
    required this.expertId,
    required this.displayName,
  }) : super(
          apiValue: '$expertChatModePrefix$expertId',
          icon: Icons.person_search,
          color: DS.info,
        );

  final String expertId;
  final String displayName;

  @override
  String? get expertName => displayName;
}

class ChatModeTeam extends ChatMode {
  ChatModeTeam({
    required this.selectedAgents,
    this.excludedAgents = const [],
    this.finalAnswerAgents = const [],
    this.collaborationMode = 'auto',
    this.teamLabel,
    this.teamId,
  }) : super(
          apiValue: _buildApiValue(
            selectedAgents,
            excludedAgents,
            collaborationMode,
            finalAnswerAgents,
            teamLabel,
            teamId,
          ),
          icon: Icons.groups_rounded,
          color: DS.brandSecondary,
        );

  final List<String> selectedAgents;
  final List<String> excludedAgents;
  final List<String> finalAnswerAgents;
  final String collaborationMode;
  final String? teamLabel;
  final String? teamId;

  static String _buildApiValue(
    List<String> agents,
    List<String> excluded,
    String mode,
    List<String> finalAgents,
    String? label,
    String? teamId,
  ) {
    final spec = <String, dynamic>{
      'agents': agents,
      if (excluded.isNotEmpty) 'excluded': excluded,
      if (finalAgents.isNotEmpty) 'final_agents': finalAgents,
      if (mode != 'auto') 'mode': mode,
      if (label != null && label.isNotEmpty) 'label': label,
      if (teamId != null && teamId.isNotEmpty) 'team_id': teamId,
    };
    return '$teamChatModePrefix${jsonEncode(spec)}';
  }

  @override
  String get label =>
      teamLabel ?? I18nService.instance.l10n.chatTeamExpertsCount(
        selectedAgents.length,
      );

  @override
  bool get isMultiAgent => true;
}

/// All available chat modes
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
