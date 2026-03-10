import 'package:flutter/material.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

enum ToolCategory {
  input,
  study,
  efficiency,
  cognition,
}

enum ToolLaunchContext {
  home,
  taskExecution,
  chatInput,
  toolLibrary,
}

enum ToolSurface {
  page,
  sheet,
}

class ToolLaunchRequest {
  const ToolLaunchRequest({
    required this.context,
    required this.surface,
    this.taskId,
    this.onTextResult,
  });

  final ToolLaunchContext context;
  final ToolSurface surface;
  final String? taskId;
  final ValueChanged<String>? onTextResult;

  ToolLaunchRequest copyWith({
    ToolLaunchContext? context,
    ToolSurface? surface,
    String? taskId,
    ValueChanged<String>? onTextResult,
  }) =>
      ToolLaunchRequest(
        context: context ?? this.context,
        surface: surface ?? this.surface,
        taskId: taskId ?? this.taskId,
        onTextResult: onTextResult ?? this.onTextResult,
      );
}

typedef EmbeddedToolBuilder = Widget Function(ToolLaunchRequest request);
typedef ToolRouteBuilder = String Function(ToolLaunchRequest request);

class ToolDefinition {
  const ToolDefinition({
    required this.id,
    required this.title,
    required this.icon,
    required this.category,
    required this.defaultOrder,
    required this.supportedContexts,
    this.description,
    this.searchTerms = const <String>[],
    this.searchTermsEn = const <String>[],
    this.canPin = true,
    this.supportsStandalone = true,
    this.supportsSheet = false,
    this.showInTaskQuickPanel = false,
    this.routeBuilder,
    this.embeddedBuilder,
  });

  final String id;
  final String title;
  final String? description;
  final IconData icon;
  final ToolCategory category;
  final int defaultOrder;
  final List<String> searchTerms;
  /// English search terms for localization support
  final List<String> searchTermsEn;
  final bool canPin;
  final bool supportsStandalone;
  final bool supportsSheet;
  final bool showInTaskQuickPanel;
  final Set<ToolLaunchContext> supportedContexts;
  final ToolRouteBuilder? routeBuilder;
  final EmbeddedToolBuilder? embeddedBuilder;

  bool get isRouteBased => routeBuilder != null && embeddedBuilder == null;

  bool supportsContext(ToolLaunchContext context) =>
      supportedContexts.contains(context);

  /// Get localized title using the l10n key pattern.
  /// Falls back to the static title if key not found.
  String getLocalizedTitle({AppLocalizations? l10n}) {
    final loc = l10n ?? S;
    // Try to get localized title via key pattern: tools.{id}_title
    final key = 'tools${_toCamelCase(id)}Title';
    try {
      final localized = _getLocalizedString(loc, key);
      return localized ?? title;
    } catch (_) {
      return title;
    }
  }

  /// Get localized description using the l10n key pattern.
  /// Falls back to the static description if key not found.
  String? getLocalizedDescription({AppLocalizations? l10n}) {
    if (description == null) return null;
    final loc = l10n ?? S;
    // Try to get localized description via key pattern: tools.{id}_desc
    final key = 'tools${_toCamelCase(id)}Desc';
    try {
      final localized = _getLocalizedString(loc, key);
      return localized ?? description;
    } catch (_) {
      return description;
    }
  }

  /// Get search terms based on current locale
  List<String> getLocalizedSearchTerms() {
    return I18nService.instance.isEnglish && searchTermsEn.isNotEmpty
        ? searchTermsEn
        : searchTerms;
  }

  /// Convert snake_case or kebab-case to CamelCase for key lookup
  String _toCamelCase(String input) {
    return input
        .split(RegExp(r'[_\-]'))
        .map((part) =>
            part.isEmpty ? '' : '${part[0].toUpperCase()}${part.substring(1)}')
        .join();
  }

  /// Helper to get localized string from AppLocalizations via dynamic key
  String? _getLocalizedString(AppLocalizations l10n, String key) {
    // Map of known tool keys to their getter methods
    switch (key) {
      case 'toolsSpeechToTextTitle':
        return l10n.toolsSpeechToTextTitle;
      case 'toolsSpeechToTextDesc':
        return l10n.toolsSpeechToTextDesc;
      case 'toolsCalculatorTitle':
        return l10n.toolsCalculatorTitle;
      case 'toolsCalculatorDesc':
        return l10n.toolsCalculatorDesc;
      case 'toolsFocusTimerTitle':
        return l10n.toolsFocusTimerTitle;
      case 'toolsFocusTimerDesc':
        return l10n.toolsFocusTimerDesc;
      case 'toolsNotesTitle':
        return l10n.toolsNotesTitle;
      case 'toolsNotesDesc':
        return l10n.toolsNotesDesc;
      case 'toolsTranslatorTitle':
        return l10n.toolsTranslatorTitle;
      case 'toolsTranslatorDesc':
        return l10n.toolsTranslatorDesc;
      case 'toolsFlashCapsuleTitle':
        return l10n.toolsFlashCapsuleTitle;
      case 'toolsFlashCapsuleDesc':
        return l10n.toolsFlashCapsuleDesc;
      case 'toolsFocusStatsTitle':
        return l10n.toolsFocusStatsTitle;
      case 'toolsFocusStatsDesc':
        return l10n.toolsFocusStatsDesc;
      case 'toolsVocabularyLookupTitle':
        return l10n.toolsVocabularyLookupTitle;
      case 'toolsVocabularyLookupDesc':
        return l10n.toolsVocabularyLookupDesc;
      case 'toolsWordbookTitle':
        return l10n.toolsWordbookTitle;
      case 'toolsWordbookDesc':
        return l10n.toolsWordbookDesc;
      case 'toolsBreathingTitle':
        return l10n.toolsBreathingTitle;
      case 'toolsBreathingDesc':
        return l10n.toolsBreathingDesc;
      case 'toolsDocumentCleanerTitle':
        return l10n.toolsDocumentCleanerTitle;
      case 'toolsDocumentCleanerDesc':
        return l10n.toolsDocumentCleanerDesc;
      case 'toolsPatternListTitle':
        return l10n.toolsPatternListTitle;
      case 'toolsPatternListDesc':
        return l10n.toolsPatternListDesc;
      case 'toolsCuriosityCapsuleTitle':
        return l10n.toolsCuriosityCapsuleTitle;
      case 'toolsCuriosityCapsuleDesc':
        return l10n.toolsCuriosityCapsuleDesc;
      case 'toolsCognitiveHubTitle':
        return l10n.toolsCognitiveHubTitle;
      case 'toolsCognitiveHubDesc':
        return l10n.toolsCognitiveHubDesc;
      default:
        return null;
    }
  }
}
