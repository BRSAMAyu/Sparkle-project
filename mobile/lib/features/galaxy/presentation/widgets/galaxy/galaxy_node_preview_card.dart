import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxyNodePreviewCard extends StatelessWidget {
  const GalaxyNodePreviewCard({
    required this.node,
    required this.onFocus,
    required this.onInspectConnections,
    required this.onViewDetails,
    required this.onStartReview,
    this.onLaunchPrediction,
    super.key,
  });

  final GalaxyNodeModel node;
  final VoidCallback onFocus;
  final VoidCallback onInspectConnections;
  final VoidCallback onViewDetails;
  final VoidCallback onStartReview;

  /// U-07：theater 演练入口（LABS hidden by default）默认不挂在节点
  /// 预览卡上；参数保留为可空以兼容未来 Labs 态按需启用。
  final VoidCallback? onLaunchPrediction;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    // 实例字段不参与流程提升，先落局部变量供判空与传参。
    final launchPrediction = onLaunchPrediction;
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final sectorStyle = SectorConfig.getStyle(node.sector);
    final sectorName = SectorConfig.getLocalizedName(node.sector);
    final sectorColor = sectorStyle.primaryColorFor(isDarkMode: isDarkMode);
    final glowColor = sectorStyle.glowColorFor(isDarkMode: isDarkMode);
    final backgroundColor = isDarkMode
        ? Color.alphaBlend(
            sectorColor.withValues(alpha: 0.08),
            const Color(0xE6151D30),
          )
        : Color.alphaBlend(
            sectorColor.withValues(alpha: 0.05),
            DS.neutral0.withValues(alpha: 0.94),
          );
    final borderColor = isDarkMode
        ? DS.neutral0.withValues(alpha: 0.12)
        : DS.galaxyShadow.withValues(alpha: 0.08);
    final secondaryColor = isDarkMode
        ? DS.neutral0.withValues(alpha: 0.7)
        : DS.neutral900.withValues(alpha: 0.54);
    final masteryProgress = (node.masteryScore / 100).clamp(0.0, 1.0);

    return Material(
      color: Colors.transparent,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 252),
        child: DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                backgroundColor,
                Color.alphaBlend(
                  glowColor.withValues(alpha: isDarkMode ? 0.08 : 0.04),
                  backgroundColor,
                ),
              ],
            ),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: borderColor),
            boxShadow: [
              BoxShadow(
                color: (isDarkMode ? DS.neutral900 : glowColor)
                    .withValues(alpha: isDarkMode ? 0.22 : 0.08),
                blurRadius: 24,
                offset: const Offset(0, 12),
              ),
            ],
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            width: 44,
                            height: 4,
                            decoration: BoxDecoration(
                              color: sectorColor,
                              borderRadius: BorderRadius.circular(999),
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            node.name,
                            style: TextStyle(
                              color: isDarkMode
                                  ? DS.neutral0
                                  : DS.neutral900.withValues(alpha: 0.87),
                              fontSize: 16,
                              fontWeight: DS.fontWeightBold,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 6),
                          Text(
                            l10n.galaxyNodePreviewSubtitle(
                              sectorName,
                              node.importance,
                            ),
                            style: TextStyle(
                              color: secondaryColor,
                              fontSize: 12,
                              fontWeight: DS.fontWeightSemibold,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    SizedBox(
                      width: 46,
                      height: 46,
                      child: CustomPaint(
                        painter: _MasteryRingPainter(
                          color: sectorColor,
                          glowColor: glowColor,
                          progress: masteryProgress,
                          isDarkMode: isDarkMode,
                        ),
                        child: Center(
                          child: Text(
                            '${node.masteryScore}',
                            style: TextStyle(
                              color: isDarkMode
                                  ? DS.neutral0
                                  : DS.neutral900.withValues(alpha: 0.87),
                              fontSize: 11,
                              fontWeight: DS.fontWeightBold,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  node.isUnlocked
                      ? l10n.galaxyNodeUnlocked
                      : l10n.galaxyNodeLocked,
                  style: TextStyle(
                    color: sectorColor,
                    fontSize: 12,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                if (!node.isUnlocked) ...[
                  const SizedBox(height: 6),
                  Text(
                    l10n.galaxyNodeLockedHint,
                    style: TextStyle(
                      color: secondaryColor,
                      fontSize: 12,
                      height: 1.35,
                    ),
                  ),
                ],
                const SizedBox(height: 10),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: masteryProgress,
                    minHeight: 6,
                    backgroundColor: (isDarkMode ? DS.neutral0 : DS.neutral900)
                        .withValues(alpha: 0.08),
                    valueColor: AlwaysStoppedAnimation<Color>(sectorColor),
                  ),
                ),
                const SizedBox(height: 10),
                Divider(
                  height: 1,
                  color: isDarkMode
                      ? DS.neutral0.withValues(alpha: 0.1)
                      : DS.galaxyShadow.withValues(alpha: 0.08),
                ),
                if (node.shouldPulseForReview) ...[
                  const SizedBox(height: 12),
                  _ReviewUrgencyCallout(
                    node: node,
                    sectorColor: sectorColor,
                    glowColor: glowColor,
                    isDarkMode: isDarkMode,
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: _CardActionButton(
                      label: context.l10n.galaxyStartReview,
                      icon: Icons.bolt_rounded,
                      color: glowColor,
                      onPressed: onStartReview,
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _CardActionButton(
                        label: l10n.galaxyNodeFocus,
                        icon: Icons.center_focus_strong_rounded,
                        color: sectorColor,
                        onPressed: onFocus,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: _CardActionButton(
                        label: l10n.galaxyNodeInspectConnections,
                        icon: Icons.hub_rounded,
                        color: glowColor,
                        onPressed: onInspectConnections,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: _CardActionButton(
                    label: l10n.viewDetails,
                    icon: Icons.menu_book_rounded,
                    color: sectorColor,
                    onPressed: onViewDetails,
                  ),
                ),
                if (launchPrediction != null) ...[
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: _CardActionButton(
                      label: l10n.galaxyNodeLaunchPrediction,
                      icon: Icons.auto_graph_rounded,
                      color: sectorColor,
                      onPressed: launchPrediction,
                    ),
                  ),
                ],
                if ((node.description ?? '').trim().isNotEmpty) ...[
                  const SizedBox(height: 10),
                  Text(
                    node.description!,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: secondaryColor,
                      fontSize: 12,
                      height: 1.35,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CardActionButton extends StatelessWidget {
  const _CardActionButton({
    required this.label,
    required this.icon,
    required this.color,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => FilledButton.tonal(
        onPressed: onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: color.withValues(alpha: 0.1),
          foregroundColor: color,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          side: BorderSide(color: color.withValues(alpha: 0.18)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 14),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: DS.fontWeightBold,
                ),
              ),
            ),
          ],
        ),
      );
}

class _ReviewUrgencyCallout extends StatelessWidget {
  const _ReviewUrgencyCallout({
    required this.node,
    required this.sectorColor,
    required this.glowColor,
    required this.isDarkMode,
  });

  final GalaxyNodeModel node;
  final Color sectorColor;
  final Color glowColor;
  final bool isDarkMode;

  @override
  Widget build(BuildContext context) {
    final secondaryColor = isDarkMode
        ? DS.neutral0.withValues(alpha: 0.7)
        : DS.neutral900.withValues(alpha: 0.54);
    final scorePercent = (node.reviewUrgencyScore * 100).round();
    final daysSince = node.daysSinceMasteryUpdate.round();

    return DecoratedBox(
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          glowColor.withValues(alpha: isDarkMode ? 0.12 : 0.08),
          isDarkMode
              ? DS.neutral0.withValues(alpha: 0.03)
              : DS.galaxyShadow.withValues(alpha: 0.02),
        ),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: glowColor.withValues(alpha: isDarkMode ? 0.2 : 0.14),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.auto_awesome_rounded,
                  size: 14,
                  color: glowColor,
                ),
                const SizedBox(width: 6),
                Text(
                  context.l10n.galaxyBestReviewWindow,
                  style: TextStyle(
                    color: sectorColor,
                    fontSize: 12,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
                const Spacer(),
                Text(
                  '$scorePercent%',
                  style: TextStyle(
                    color: secondaryColor,
                    fontSize: 11,
                    fontWeight: DS.fontWeightBold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              _buildReviewMessage(context),
              style: TextStyle(
                color: isDarkMode
                    ? DS.neutral0
                    : DS.neutral900.withValues(alpha: 0.87),
                fontSize: 12,
                height: 1.4,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              _buildReviewHint(daysSince, context),
              style: TextStyle(
                color: secondaryColor,
                fontSize: 11,
                height: 1.35,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _buildReviewMessage(BuildContext context) {
    final l10n = context.l10n;
    return l10n.galaxyReviewHighMasteryEn(node.masteryScore);
  }

  String _buildReviewHint(int daysSince, BuildContext context) {
    final l10n = context.l10n;
    switch (node.reviewUrgencyReason) {
      case 'recent_errors':
        return l10n.galaxyReviewErrorReturnEn;
      case 'review_window':
        return daysSince > 0
            ? l10n.galaxyReviewWindowDaysEn(daysSince)
            : l10n.galaxyReviewWindowReadyEn;
      case 'low_mastery':
        return l10n.galaxyReviewUnstableEn;
      default:
        return l10n.galaxyReviewReLightEn;
    }
  }
}

class _MasteryRingPainter extends CustomPainter {
  const _MasteryRingPainter({
    required this.color,
    required this.glowColor,
    required this.progress,
    required this.isDarkMode,
  });

  final Color color;
  final Color glowColor;
  final double progress;
  final bool isDarkMode;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = size.shortestSide / 2 - 4;
    canvas
      ..drawCircle(
        center,
        radius + 1.5,
        Paint()
          ..color = glowColor.withValues(alpha: isDarkMode ? 0.16 : 0.08)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
      )
      ..drawCircle(
        center,
        radius,
        Paint()
          ..color = (isDarkMode ? DS.neutral0 : DS.neutral900)
              .withValues(alpha: isDarkMode ? 0.08 : 0.05)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 4,
      )
      ..drawArc(
        Rect.fromCircle(center: center, radius: radius),
        -1.5708,
        6.28318 * progress,
        false,
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 4
          ..strokeCap = StrokeCap.round,
      );
  }

  @override
  bool shouldRepaint(covariant _MasteryRingPainter oldDelegate) =>
      oldDelegate.color != color ||
      oldDelegate.glowColor != glowColor ||
      oldDelegate.progress != progress ||
      oldDelegate.isDarkMode != isDarkMode;
}
