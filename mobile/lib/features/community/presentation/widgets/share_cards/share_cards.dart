/// Share cards for different content types
///
/// These widgets are used in:
/// - Chat bubbles for displaying shared resources
/// - Quick share picker for previewing before sharing
/// - Universal share bottom sheet for card preview

export 'task_share_card.dart';
export 'plan_share_card.dart';
export 'capsule_share_card.dart';
export 'node_share_card.dart';
export 'achievement_share_card.dart';
export 'learning_report_share_card.dart';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'task_share_card.dart';
import 'plan_share_card.dart';
import 'capsule_share_card.dart';
import 'node_share_card.dart';
import 'achievement_share_card.dart';
import 'learning_report_share_card.dart';

/// Factory for creating share cards from content type
class ShareCardFactory {
  /// Create a share card widget based on content type
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
    String? sharedResourceId,
    VoidCallback? onAdopt,
  }) {
    return switch (payload.contentType) {
      ShareableContentType.taskCompletion => TaskShareCardFactory.fromPayload(
          payload,
          isCompact: isCompact,
          onTap: onTap,
          sharedResourceId: sharedResourceId,
          onAdopt: onAdopt,
        ),
      ShareableContentType.planProgress => PlanShareCardFactory.fromPayload(
          payload,
          isCompact: isCompact,
          onTap: onTap,
          sharedResourceId: sharedResourceId,
          onAdopt: onAdopt,
        ),
      ShareableContentType.capsule => CapsuleShareCardFactory.fromPayload(
          payload,
          isCompact: isCompact,
          onTap: onTap,
        ),
      ShareableContentType.knowledgeNode => NodeShareCardFactory.fromPayload(
          payload,
          isCompact: isCompact,
          onTap: onTap,
        ),
      ShareableContentType.achievement => AchievementShareCardFactory.fromPayload(
          payload,
          isCompact: isCompact,
          onTap: onTap,
        ),
      ShareableContentType.learningReport => LearningReportShareCardFactory.fromPayload(
          payload,
          isCompact: isCompact,
          onTap: onTap,
        ),
      _ => _buildDefaultCard(payload, isCompact: isCompact, onTap: onTap),
    };
  }

  static Widget _buildDefaultCard(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
  }) =>
      GestureDetector(
        onTap: onTap,
        child: Container(
          padding: EdgeInsets.all(DS.sm),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: DS.borderRadius8,
            border: Border.all(color: DS.border),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Icon(
                  _getIconForType(payload.contentType),
                  color: DS.brandPrimary,
                  size: 18,
                ),
              ),
              SizedBox(width: DS.sm),
              Flexible(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      payload.title,
                      style: TextStyle(
                        fontWeight: DS.fontWeightMedium,
                        fontSize: DS.fontSizeSm,
                        color: DS.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (payload.subtitle != null)
                      Text(
                        payload.subtitle!,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textTertiary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  static IconData _getIconForType(ShareableContentType type) => switch (type) {
        ShareableContentType.achievement => Icons.emoji_events,
        ShareableContentType.taskCompletion => Icons.task_alt,
        ShareableContentType.planProgress => Icons.flag,
        ShareableContentType.capsule => Icons.access_time,
        ShareableContentType.knowledgeNode => Icons.school,
        ShareableContentType.learningReport => Icons.assessment,
        ShareableContentType.cognitivePrism => Icons.psychology,
      };
}
