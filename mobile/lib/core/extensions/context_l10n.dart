import 'package:flutter/material.dart';
import '../../l10n/app_localizations.dart';

/// BuildContext extension for easy access to localizations.
///
/// Usage:
/// ```dart
/// // In a widget's build method
/// Text(context.l10n.aiStatusThinking)
///
/// // Get current locale
/// final isEnglish = context.locale.languageCode == 'en';
/// ```
extension ContextL10nExtension on BuildContext {
  /// Get the current AppLocalizations instance.
  ///
  /// Throws if localizations are not configured.
  AppLocalizations get l10n => AppLocalizations.of(this)!;

  /// Get the current locale.
  Locale get locale => Localizations.localeOf(this);

  /// Check if current locale is Chinese.
  bool get isChinese => locale.languageCode == 'zh';

  /// Check if current locale is English.
  bool get isEnglish => locale.languageCode == 'en';
}
