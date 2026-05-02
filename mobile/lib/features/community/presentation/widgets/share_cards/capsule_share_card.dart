import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/universal_share_service.dart';

/// Purple color constant for capsule cards
const _capsulePurple = Color(0xFF9C27B0);

/// Widget for displaying a capsule (time capsule / thought capsule) share card preview
///
/// Used in chat bubbles and quick share pickers
class CapsuleShareCard extends StatelessWidget {
  const CapsuleShareCard({
    required this.capsuleId,
    required this.capsuleTitle,
    this.capsuleSummary,
    this.capsuleType,
    this.depth,
    this.createdAt,
    this.wordCount,
    this.tags,
    this.isCompact = false,
    this.onTap,
    super.key,
  });

  final String capsuleId;
  final String capsuleTitle;
  final String? capsuleSummary;
  final String? capsuleType;
  final int? depth; // Thinking depth level
  final DateTime? createdAt;
  final int? wordCount;
  final List<String>? tags;
  final bool isCompact;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactCard(context);
    }
    return _buildFullCard(context);
  }

  Widget _buildCompactCard(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(DS.sm),
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
                  color: _capsulePurple.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Icon(
                  _getTypeIcon(),
                  color: _capsulePurple,
                  size: 18,
                ),
              ),
              const SizedBox(width: DS.sm),
              Flexible(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      capsuleTitle,
                      style: TextStyle(
                        fontWeight: DS.fontWeightMedium,
                        fontSize: DS.fontSizeSm,
                        color: DS.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (capsuleType != null)
                      Text(
                        capsuleType!,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textTertiary,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  Widget _buildFullCard(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          width: 280,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                _capsulePurple.withValues(alpha: 0.1),
                DS.brandSecondary.withValues(alpha: 0.05),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: DS.borderRadius12,
            border: Border.all(color: _capsulePurple.withValues(alpha: 0.3)),
            boxShadow: DS.shadowSm,
          ),
          child: Stack(
            children: [
              // Background decoration
              Positioned(
                right: -10,
                bottom: -10,
                child: Icon(
                  Icons.hourglass_empty,
                  size: 80,
                  color: _capsulePurple.withValues(alpha: 0.1),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(DS.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Header
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(DS.sm),
                          decoration: BoxDecoration(
                            color: _capsulePurple.withValues(alpha: 0.15),
                            borderRadius: DS.borderRadius8,
                          ),
                          child: Icon(
                            _getTypeIcon(),
                            color: _capsulePurple,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: DS.sm),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                capsuleType ??
                                    context.l10n.communityShareTimeCapsule,
                                style: TextStyle(
                                  fontSize: DS.fontSizeXs,
                                  color: DS.textTertiary,
                                ),
                              ),
                              Text(
                                capsuleTitle,
                                style: TextStyle(
                                  fontWeight: DS.fontWeightBold,
                                  fontSize: DS.fontSizeLg,
                                  color: DS.textPrimary,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),

                    // Summary
                    if (capsuleSummary != null &&
                        capsuleSummary!.isNotEmpty) ...[
                      const SizedBox(height: DS.sm),
                      Container(
                        padding: const EdgeInsets.all(DS.sm),
                        decoration: BoxDecoration(
                          color: DS.surfacePrimary.withValues(alpha: 0.5),
                          borderRadius: DS.borderRadius8,
                        ),
                        child: Text(
                          capsuleSummary!,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            color: DS.textSecondary,
                            fontStyle: FontStyle.italic,
                          ),
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],

                    const SizedBox(height: DS.md),

                    // Stats row
                    Row(
                      children: [
                        if (depth != null) _buildDepthIndicator(depth!),
                        if (wordCount != null) ...[
                          const SizedBox(width: DS.md),
                          _buildStat(
                            I18nService.instance.isChinese
                                ? '${wordCount}字'
                                : '$wordCount words',
                            Icons.edit_note,
                          ),
                        ],
                        if (createdAt != null) ...[
                          const SizedBox(width: DS.md),
                          _buildStat(
                            _formatDate(createdAt!),
                            Icons.access_time,
                          ),
                        ],
                      ],
                    ),

                    // Tags
                    if (tags != null && tags!.isNotEmpty) ...[
                      const SizedBox(height: DS.sm),
                      Wrap(
                        spacing: DS.xs,
                        runSpacing: DS.xs,
                        children: tags!
                            .take(3)
                            .map(
                              (tag) => Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: DS.sm,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: _capsulePurple.withValues(alpha: 0.1),
                                  borderRadius: DS.borderRadius4,
                                ),
                                child: Text(
                                  '#$tag',
                                  style: const TextStyle(
                                    fontSize: DS.fontSizeXs,
                                    color: _capsulePurple,
                                  ),
                                ),
                              ),
                            )
                            .toList(),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  IconData _getTypeIcon() => switch (capsuleType?.toLowerCase()) {
        'thinking' || '思考' => Icons.psychology,
        'reflection' || '反思' => Icons.auto_stories,
        'inspiration' || '灵感' => Icons.lightbulb,
        'summary' || '总结' => Icons.summarize,
        _ => Icons.hourglass_empty,
      };

  Widget _buildDepthIndicator(int depth) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.sm,
          vertical: DS.xs,
        ),
        decoration: BoxDecoration(
          color: _getDepthColor().withValues(alpha: 0.15),
          borderRadius: DS.borderRadius4,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.layers,
              size: 14,
              color: _getDepthColor(),
            ),
            const SizedBox(width: DS.xs),
            Text(
              I18nService.instance.isChinese
                  ? '深度 Lv.$depth'
                  : 'Depth Lv.$depth',
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightBold,
                color: _getDepthColor(),
              ),
            ),
          ],
        ),
      );

  Color _getDepthColor() {
    if (depth == null) return _capsulePurple;
    if (depth! >= 4) return DS.success;
    if (depth! >= 3) return DS.info;
    if (depth! >= 2) return DS.warning;
    return _capsulePurple;
  }

  Widget _buildStat(String value, IconData icon) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: DS.textTertiary,
          ),
          const SizedBox(width: DS.xs),
          Text(
            value,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: DS.textTertiary,
            ),
          ),
        ],
      );

  String _formatDate(DateTime date) => '${date.month}/${date.day}';
}

/// Factory for creating capsule share cards from payload
class CapsuleShareCardFactory {
  /// Create a CapsuleShareCard from a UniversalSharePayload
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
  }) {
    final metadata = payload.metadata ?? {};

    return CapsuleShareCard(
      capsuleId: payload.resourceId,
      capsuleTitle: payload.title,
      capsuleSummary: payload.subtitle ?? payload.description,
      capsuleType: metadata['type'] as String?,
      depth: metadata['depth'] as int?,
      wordCount: metadata['word_count'] as int?,
      tags: (metadata['tags'] as List<dynamic>?)?.cast<String>(),
      createdAt: metadata['created_at'] != null
          ? DateTime.tryParse(metadata['created_at'] as String)
          : null,
      isCompact: isCompact,
      onTap: onTap,
    );
  }
}
