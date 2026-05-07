import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/universal_share_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Widget for displaying a knowledge node share card preview
///
/// Used in chat bubbles and quick share pickers
class NodeShareCard extends StatelessWidget {
  const NodeShareCard({
    required this.nodeId,
    required this.nodeName,
    this.nodeDescription,
    this.masteryLevel,
    this.category,
    this.parentPath,
    this.connections,
    this.learningTime,
    this.isCompact = false,
    this.onTap,
    super.key,
  });

  final String nodeId;
  final String nodeName;
  final String? nodeDescription;
  final double? masteryLevel; // 0.0 - 1.0
  final String? category;
  final String? parentPath;
  final int? connections;
  final int? learningTime; // in minutes
  final bool isCompact;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactCard(context);
    }
    return _buildFullCard(context);
  }

  Widget _buildCompactCard(BuildContext context) => SparklePressable(
        onTap: onTap,
        padding: EdgeInsets.zero,
        borderRadius: DS.borderRadius8,
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
                  color: DS.brandSecondary.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Icon(
                  Icons.school,
                  color: DS.brandSecondary,
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
                      nodeName,
                      style: TextStyle(
                        fontWeight: DS.fontWeightMedium,
                        fontSize: DS.fontSizeSm,
                        color: DS.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (masteryLevel != null)
                      Text(
                        '掌握度 ${(_masteryPercent!)}%',
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

  Widget _buildFullCard(BuildContext context) => SparklePressable(
        onTap: onTap,
        padding: EdgeInsets.zero,
        borderRadius: DS.borderRadius12,
        child: Builder(
          builder: (context) {
            final isDarkMode = Theme.of(context).brightness == Brightness.dark;
            return Container(
              constraints: const BoxConstraints(maxWidth: 280),
          decoration: BoxDecoration(
            gradient: isDarkMode
                ? LinearGradient(
                    colors: [
                      DS.brandSecondary.withValues(alpha: 0.1),
                      DS.brandPrimary.withValues(alpha: 0.05),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  )
                : null,
            color: isDarkMode ? null : DS.surfacePanel,
            borderRadius: DS.borderRadius12,
            border: Border.all(
              color: isDarkMode
                  ? DS.brandSecondary.withValues(alpha: 0.3)
                  : DS.borderSubtle,
            ),
            boxShadow: DS.shadowSm,
          ),
          child: Stack(
            children: [
              // Star background decoration
              Positioned(
                right: -10,
                bottom: -10,
                child: Icon(
                  Icons.star,
                  size: 80,
                  color: DS.brandSecondary.withValues(alpha: 0.1),
                ),
              ),
              // Small stars
              Positioned(
                left: 20,
                top: 30,
                child: Icon(
                  Icons.star,
                  size: 12,
                  color: DS.warning.withValues(alpha: 0.3),
                ),
              ),
              Positioned(
                right: 40,
                top: 50,
                child: Icon(
                  Icons.star,
                  size: 8,
                  color: DS.warning.withValues(alpha: 0.2),
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
                            color: DS.brandSecondary.withValues(alpha: 0.15),
                            borderRadius: DS.borderRadius8,
                          ),
                          child: Icon(
                            Icons.school,
                            color: DS.brandSecondary,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: DS.sm),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                category ?? context.l10n.communityShareKnowledgeNode,
                                style: TextStyle(
                                  fontSize: DS.fontSizeXs,
                                  color: DS.textTertiary,
                                ),
                              ),
                              Text(
                                nodeName,
                                style: TextStyle(
                                  fontWeight: DS.fontWeightBold,
                                  fontSize: DS.fontSizeBase,
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

                    // Parent path
                    if (parentPath != null && parentPath!.isNotEmpty) ...[
                      const SizedBox(height: DS.xs),
                      Row(
                        children: [
                          Icon(
                            Icons.arrow_right,
                            size: 14,
                            color: DS.textTertiary,
                          ),
                          const SizedBox(width: DS.xs),
                          Expanded(
                            child: Text(
                              parentPath!,
                              style: TextStyle(
                                fontSize: DS.fontSizeXs,
                                color: DS.textTertiary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],

                    // Mastery indicator
                    if (masteryLevel != null) ...[
                      const SizedBox(height: DS.md),
                      Row(
                        children: [
                          Expanded(
                            child: ClipRRect(
                              borderRadius: DS.borderRadius4,
                              child: LinearProgressIndicator(
                                value: masteryLevel!,
                                backgroundColor: DS.neutral200,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  _getMasteryColor(),
                                ),
                                minHeight: 8,
                              ),
                            ),
                          ),
                          const SizedBox(width: DS.sm),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: DS.sm,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: _getMasteryColor().withValues(alpha: 0.15),
                              borderRadius: DS.borderRadius4,
                            ),
                            child: Text(
                              _getMasteryLabel(),
                              style: TextStyle(
                                fontSize: DS.fontSizeXs,
                                fontWeight: DS.fontWeightBold,
                                color: _getMasteryColor(),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],

                    const SizedBox(height: DS.md),

                    // Stats row
                    Row(
                      children: [
                        if (learningTime != null)
                          _buildStat(
                            context.l10n.communityShareLearning,
                            '${learningTime}分钟',
                            Icons.timer_outlined,
                          ),
                        if (connections != null && connections! > 0) ...[
                          const SizedBox(width: DS.md),
                          _buildStat(
                            context.l10n.communityShareConnections,
                            '$connections个',
                            Icons.hub,
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
            );
          },
        ),
      );

  String? get _masteryPercent =>
      masteryLevel != null ? (masteryLevel! * 100).toStringAsFixed(0) : null;

  Color _getMasteryColor() {
    if (masteryLevel == null) return DS.brandSecondary;
    if (masteryLevel! >= 0.9) return DS.success;
    if (masteryLevel! >= 0.7) return DS.info;
    if (masteryLevel! >= 0.4) return DS.warning;
    return DS.neutral400;
  }

  String _getMasteryLabel() {
    if (masteryLevel == null) return '';
    if (masteryLevel! >= 0.9) return S.communityShareMastered;
    if (masteryLevel! >= 0.7) return S.communityShareProficient;
    if (masteryLevel! >= 0.4) return S.communityShareLearningStatus;
    return S.communityShareBeginner;
  }

  Widget _buildStat(String label, String value, IconData icon) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: DS.textTertiary,
          ),
          const SizedBox(width: DS.xs),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textTertiary,
                ),
              ),
              Text(
                value,
                style: TextStyle(
                  fontWeight: DS.fontWeightBold,
                  fontSize: DS.fontSizeSm,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
        ],
      );
}

/// Factory for creating node share cards from payload
class NodeShareCardFactory {
  /// Create a NodeShareCard from a UniversalSharePayload
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
  }) {
    final metadata = payload.metadata ?? {};
    final mastery = metadata['mastery'] as double? ??
        (payload.subtitle != null && payload.subtitle!.contains('%')
            ? _parseMasteryFromSubtitle(payload.subtitle!)
            : null);

    return NodeShareCard(
      nodeId: payload.resourceId,
      nodeName: payload.title,
      nodeDescription: payload.description,
      masteryLevel: mastery,
      category: metadata['category'] as String?,
      parentPath: metadata['parent_path'] as String?,
      connections: metadata['connections'] as int?,
      learningTime: metadata['learning_time'] as int?,
      isCompact: isCompact,
      onTap: onTap,
    );
  }

  static double? _parseMasteryFromSubtitle(String subtitle) {
    final match = RegExp(r'(\d+)%').firstMatch(subtitle);
    if (match != null) {
      return int.parse(match.group(1)!) / 100.0;
    }
    return null;
  }
}
