import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Semantic tone for AI status indicators.
enum AiStatusTone { info, success, warning, brand, neutral }

/// Centralized mapping for AI status strings to labels and tones.
///
/// This mapper avoids hardcoded colors (0xFF...) and outputs semantic tones
/// that can be resolved to colors via design tokens.
class AiStatusMapper {
  /// Get display label for AI status.
  ///
  /// If [l10n] is provided, returns localized string.
  /// Otherwise, uses the global [I18nService].
  static String label(String rawStatus, {AppLocalizations? l10n}) {
    final loc = l10n ?? S;
    switch (rawStatus) {
      case 'THINKING':
        return loc.aiStatusThinking;
      case 'GENERATING':
        return loc.aiStatusGenerating;
      case 'EXECUTING_TOOL':
        return loc.aiStatusExecutingTool;
      case 'SEARCHING':
        return loc.aiStatusSearching;
      case 'ANALYZING':
        return loc.aiStatusAnalyzing;
      case 'PLANNING':
        return loc.aiStatusPlanning;
      case 'REVIEWING':
        return loc.aiStatusReviewing;
      case 'WAITING':
        return loc.aiStatusWaiting;
      case 'READY':
        return loc.aiStatusReady;
      case 'ERROR':
        return loc.aiStatusError;
      case 'IDLE':
        return loc.aiStatusIdle;
      case 'CONNECTING':
        return loc.aiStatusConnecting;
      case 'RECONNECTING':
        return loc.aiStatusReconnecting;
      case 'DISCONNECTED':
        return loc.aiStatusDisconnected;
      default:
        return loc.aiStatusProcessing;
    }
  }

  /// Get compact label for AI status (used in bubbles).
  ///
  /// If [l10n] is provided, returns localized string.
  /// Otherwise, uses the global [I18nService].
  static String compactLabel(String rawStatus, {AppLocalizations? l10n}) {
    final loc = l10n ?? S;
    // Compact labels are the same as full labels since they're already short
    return label(rawStatus, l10n: loc);
  }

  /// Get semantic tone for AI status.
  static AiStatusTone tone(String rawStatus) {
    switch (rawStatus) {
      case 'THINKING':
        return AiStatusTone.info;
      case 'GENERATING':
        return AiStatusTone.success;
      case 'EXECUTING_TOOL':
        return AiStatusTone.warning;
      case 'SEARCHING':
        return AiStatusTone.brand;
      default:
        return AiStatusTone.neutral;
    }
  }

  /// Convert tone to color using design tokens.
  static Color toneToColor(AiStatusTone tone, BuildContext context) {
    switch (tone) {
      case AiStatusTone.info:
        return DS.info;
      case AiStatusTone.success:
        return DS.success;
      case AiStatusTone.warning:
        return DS.warning;
      case AiStatusTone.brand:
        return DS.brandPrimary;
      case AiStatusTone.neutral:
        return DS.textSecondary;
    }
  }

  /// Convert tone to background color with alpha using design tokens.
  static Color toneToBackgroundColor(AiStatusTone tone, BuildContext context) =>
      toneToColor(tone, context).withValues(alpha: 0.1);

  /// Convert tone to border color with alpha using design tokens.
  static Color toneToBorderColor(AiStatusTone tone, BuildContext context) =>
      toneToColor(tone, context).withValues(alpha: 0.3);
}
