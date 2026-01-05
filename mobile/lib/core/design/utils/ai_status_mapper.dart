import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Semantic tone for AI status indicators.
enum AiStatusTone { info, success, warning, brand, neutral }

/// Centralized mapping for AI status strings to labels and tones.
///
/// This mapper avoids hardcoded colors (0xFF...) and outputs semantic tones
/// that can be resolved to colors via design tokens.
class AiStatusMapper {
  /// Get display label for AI status.
  static String label(String rawStatus) {
    switch (rawStatus) {
      case 'THINKING':
        return '思考中...';
      case 'GENERATING':
        return '正在生成回复...';
      case 'EXECUTING_TOOL':
        return '正在使用工具...';
      case 'SEARCHING':
        return '正在搜索...';
      default:
        return '处理中...';
    }
  }

  /// Get compact label for AI status (used in bubbles).
  static String compactLabel(String rawStatus) {
    switch (rawStatus) {
      case 'THINKING':
        return '思考中';
      case 'GENERATING':
        return '生成中';
      case 'EXECUTING_TOOL':
        return '工具执行中';
      case 'SEARCHING':
        return '搜索中';
      default:
        return '处理中';
    }
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
