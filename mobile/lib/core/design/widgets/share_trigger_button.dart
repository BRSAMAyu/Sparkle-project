import 'dart:io';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/universal_share_bottom_sheet.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/universal_share_service.dart';

/// Variant type for the share trigger button
enum ShareButtonVariant {
  /// Icon-only button
  icon,

  /// Chip-style button with icon and label
  chip,

  /// Floating action button
  fab,

  /// Outlined button
  outlined,

  /// Filled button
  filled,
}

/// Size variant for the button
enum ShareButtonSize {
  small,
  medium,
  large,
}

/// Unified share trigger button that can be used across the app
///
/// This widget provides a consistent interface for triggering share operations
/// with different visual variants to fit various UI contexts.
class ShareTriggerButton extends StatelessWidget {
  const ShareTriggerButton({
    required this.payload,
    this.onGenerateCard,
    this.onCommunityShare,
    this.variant = ShareButtonVariant.icon,
    this.size = ShareButtonSize.medium,
    this.label,
    this.icon,
    this.templates = DefaultShareTemplates.all,
    this.showLabel = true,
    super.key,
  });

  /// The share payload containing content info
  final UniversalSharePayload payload;

  /// Callback to generate share card image
  final Future<File?> Function(UniversalSharePayload payload)? onGenerateCard;

  /// Custom callback for community share
  final VoidCallback? onCommunityShare;

  /// Visual variant of the button
  final ShareButtonVariant variant;

  /// Size of the button
  final ShareButtonSize size;

  /// Custom label text (defaults to "分享")
  final String? label;

  /// Custom icon (defaults to share icon)
  final IconData? icon;

  /// Available templates
  final List<ShareTemplate> templates;

  /// Whether to show the label (for chip/filled variants)
  final bool showLabel;

  @override
  Widget build(BuildContext context) => switch (variant) {
      ShareButtonVariant.icon => _buildIconButton(context),
      ShareButtonVariant.chip => _buildChipButton(context),
      ShareButtonVariant.fab => _buildFabButton(context),
      ShareButtonVariant.outlined => _buildOutlinedButton(context),
      ShareButtonVariant.filled => _buildFilledButton(context),
    };

  void _onTap(BuildContext context) {
    showUniversalShareSheet(
      context,
      payload: payload,
      onGenerateCard: onGenerateCard,
      onCommunityShare: onCommunityShare,
      templates: templates,
    );
  }

  Widget _buildIconButton(BuildContext context) {
    final iconSize = _getIconSize();
    final padding = _getPadding();

    return InkWell(
      onTap: () => _onTap(context),
      borderRadius: BorderRadius.circular(iconSize),
      child: Padding(
        padding: EdgeInsets.all(padding),
        child: Icon(
          icon ?? Icons.share,
          size: iconSize,
          color: DS.textSecondary,
        ),
      ),
    );
  }

  Widget _buildChipButton(BuildContext context) {
    final fontSize = _getFontSize();

    return GestureDetector(
      onTap: () => _onTap(context),
      child: Container(
        padding: EdgeInsets.symmetric(
          horizontal: _getPadding() * 1.5,
          vertical: _getPadding() * 0.75,
        ),
        decoration: BoxDecoration(
          color: DS.brandPrimary.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon ?? Icons.share,
              size: fontSize + 2,
              color: DS.brandPrimary,
            ),
            if (showLabel) ...[
              const SizedBox(width: DS.xs),
              Text(
                label ?? '分享',
                style: TextStyle(
                  fontSize: fontSize,
                  fontWeight: DS.fontWeightMedium,
                  color: DS.brandPrimary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildFabButton(BuildContext context) {
    final iconSize = _getIconSize();

    return FloatingActionButton(
      onPressed: () => _onTap(context),
      backgroundColor: DS.brandPrimary,
      heroTag: 'share_${payload.resourceId}',
      mini: size == ShareButtonSize.small,
      child: Icon(
        icon ?? Icons.share,
        size: iconSize,
        color: Colors.white,
      ),
    );
  }

  Widget _buildOutlinedButton(BuildContext context) {
    final fontSize = _getFontSize();
    final padding = _getPadding();

    return OutlinedButton.icon(
      onPressed: () => _onTap(context),
      icon: Icon(
        icon ?? Icons.share,
        size: fontSize + 2,
      ),
      label: showLabel ? Text(label ?? context.l10n.share) : const SizedBox.shrink(),
      style: OutlinedButton.styleFrom(
        foregroundColor: DS.brandPrimary,
        side: BorderSide(color: DS.brandPrimary),
        padding: EdgeInsets.symmetric(
          horizontal: padding * 1.5,
          vertical: padding,
        ),
        textStyle: TextStyle(fontSize: fontSize),
      ),
    );
  }

  Widget _buildFilledButton(BuildContext context) {
    final fontSize = _getFontSize();
    final padding = _getPadding();

    return FilledButton.icon(
      onPressed: () => _onTap(context),
      icon: Icon(
        icon ?? Icons.share,
        size: fontSize + 2,
      ),
      label: showLabel ? Text(label ?? context.l10n.share) : const SizedBox.shrink(),
      style: FilledButton.styleFrom(
        backgroundColor: DS.brandPrimary,
        padding: EdgeInsets.symmetric(
          horizontal: padding * 1.5,
          vertical: padding,
        ),
        textStyle: TextStyle(fontSize: fontSize),
      ),
    );
  }

  double _getIconSize() => switch (size) {
        ShareButtonSize.small => 18,
        ShareButtonSize.medium => 22,
        ShareButtonSize.large => 26,
      };

  double _getPadding() => switch (size) {
        ShareButtonSize.small => DS.xs,
        ShareButtonSize.medium => DS.sm,
        ShareButtonSize.large => DS.md,
      };

  double _getFontSize() => switch (size) {
        ShareButtonSize.small => DS.fontSizeSm,
        ShareButtonSize.medium => DS.fontSizeBase,
        ShareButtonSize.large => DS.fontSizeLg,
      };
}

/// Convenience widget for achievement share trigger
class AchievementShareTrigger extends StatelessWidget {
  const AchievementShareTrigger({
    required this.achievementId,
    required this.achievementName,
    this.shareCardUrl,
    this.variant = ShareButtonVariant.icon,
    this.size = ShareButtonSize.medium,
    this.onGenerateCard,
    super.key,
  });

  final String achievementId;
  final String achievementName;
  final String? shareCardUrl;
  final ShareButtonVariant variant;
  final ShareButtonSize size;
  final Future<File?> Function(UniversalSharePayload payload)? onGenerateCard;

  @override
  Widget build(BuildContext context) => ShareTriggerButton(
      payload: UniversalSharePayload(
        contentType: ShareableContentType.achievement,
        resourceId: achievementId,
        title: achievementName,
        cardImageUrl: shareCardUrl,
      ),
      variant: variant,
      size: size,
      onGenerateCard: onGenerateCard,
    );
}

/// Convenience widget for task completion share trigger
class TaskShareTrigger extends StatelessWidget {
  const TaskShareTrigger({
    required this.taskId,
    required this.taskTitle,
    this.taskDescription,
    this.variant = ShareButtonVariant.icon,
    this.size = ShareButtonSize.medium,
    this.onGenerateCard,
    super.key,
  });

  final String taskId;
  final String taskTitle;
  final String? taskDescription;
  final ShareButtonVariant variant;
  final ShareButtonSize size;
  final Future<File?> Function(UniversalSharePayload payload)? onGenerateCard;

  @override
  Widget build(BuildContext context) => ShareTriggerButton(
      payload: UniversalSharePayload(
        contentType: ShareableContentType.taskCompletion,
        resourceId: taskId,
        title: taskTitle,
        subtitle: taskDescription,
      ),
      variant: variant,
      size: size,
      onGenerateCard: onGenerateCard,
      icon: Icons.task_alt,
    );
}

/// Convenience widget for plan progress share trigger
class PlanShareTrigger extends StatelessWidget {
  const PlanShareTrigger({
    required this.planId,
    required this.planTitle,
    this.progress,
    this.variant = ShareButtonVariant.icon,
    this.size = ShareButtonSize.medium,
    this.onGenerateCard,
    super.key,
  });

  final String planId;
  final String planTitle;
  final double? progress;
  final ShareButtonVariant variant;
  final ShareButtonSize size;
  final Future<File?> Function(UniversalSharePayload payload)? onGenerateCard;

  @override
  Widget build(BuildContext context) => ShareTriggerButton(
      payload: UniversalSharePayload(
        contentType: ShareableContentType.planProgress,
        resourceId: planId,
        title: planTitle,
        subtitle: progress != null
            ? '进度: ${(progress! * 100).toStringAsFixed(0)}%'
            : null,
        metadata: progress != null ? {'progress': progress} : null,
      ),
      variant: variant,
      size: size,
      onGenerateCard: onGenerateCard,
      icon: Icons.flag,
    );
}

/// Convenience widget for capsule share trigger
class CapsuleShareTrigger extends StatelessWidget {
  const CapsuleShareTrigger({
    required this.capsuleId,
    required this.capsuleTitle,
    this.capsuleSummary,
    this.variant = ShareButtonVariant.icon,
    this.size = ShareButtonSize.medium,
    this.onGenerateCard,
    super.key,
  });

  final String capsuleId;
  final String capsuleTitle;
  final String? capsuleSummary;
  final ShareButtonVariant variant;
  final ShareButtonSize size;
  final Future<File?> Function(UniversalSharePayload payload)? onGenerateCard;

  @override
  Widget build(BuildContext context) => ShareTriggerButton(
      payload: UniversalSharePayload(
        contentType: ShareableContentType.capsule,
        resourceId: capsuleId,
        title: capsuleTitle,
        subtitle: capsuleSummary,
      ),
      variant: variant,
      size: size,
      onGenerateCard: onGenerateCard,
      icon: Icons.access_time,
    );
}

/// Convenience widget for knowledge node share trigger
class NodeShareTrigger extends StatelessWidget {
  const NodeShareTrigger({
    required this.nodeId,
    required this.nodeName,
    this.masteryLevel,
    this.variant = ShareButtonVariant.icon,
    this.size = ShareButtonSize.medium,
    this.onGenerateCard,
    super.key,
  });

  final String nodeId;
  final String nodeName;
  final double? masteryLevel;
  final ShareButtonVariant variant;
  final ShareButtonSize size;
  final Future<File?> Function(UniversalSharePayload payload)? onGenerateCard;

  @override
  Widget build(BuildContext context) => ShareTriggerButton(
      payload: UniversalSharePayload(
        contentType: ShareableContentType.knowledgeNode,
        resourceId: nodeId,
        title: nodeName,
        subtitle: masteryLevel != null
            ? '掌握度: ${(masteryLevel! * 100).toStringAsFixed(0)}%'
            : null,
        metadata: masteryLevel != null ? {'mastery': masteryLevel} : null,
      ),
      variant: variant,
      size: size,
      onGenerateCard: onGenerateCard,
      icon: Icons.school,
    );
}
