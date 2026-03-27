import 'package:flutter/material.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/sector_config.dart';
import 'package:sparkle/shared/entities/galaxy_model.dart';

class GalaxyNodePreviewCard extends StatelessWidget {
  const GalaxyNodePreviewCard({
    required this.node,
    required this.onFocus,
    required this.onInspectConnections,
    required this.onLaunchPrediction,
    super.key,
  });

  final GalaxyNodeModel node;
  final VoidCallback onFocus;
  final VoidCallback onInspectConnections;
  final VoidCallback onLaunchPrediction;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
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
            Colors.white.withValues(alpha: 0.94),
          );
    final borderColor = isDarkMode
        ? Colors.white.withValues(alpha: 0.12)
        : Colors.black.withValues(alpha: 0.08);
    final secondaryColor = isDarkMode ? Colors.white70 : Colors.black54;
    final masteryProgress = (node.masteryScore / 100).clamp(0.0, 1.0);

    return Material(
      color: Colors.transparent,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 220),
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
                color: (isDarkMode ? Colors.black : glowColor)
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
                              color: isDarkMode ? Colors.white : Colors.black87,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
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
                              fontWeight: FontWeight.w600,
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
                              color: isDarkMode ? Colors.white : Colors.black87,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
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
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 10),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: masteryProgress,
                    minHeight: 6,
                    backgroundColor: (isDarkMode ? Colors.white : Colors.black)
                        .withValues(alpha: 0.08),
                    valueColor: AlwaysStoppedAnimation<Color>(sectorColor),
                  ),
                ),
                const SizedBox(height: 10),
                Divider(
                  height: 1,
                  color: isDarkMode
                      ? Colors.white.withValues(alpha: 0.1)
                      : Colors.black.withValues(alpha: 0.08),
                ),
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
                    label: '推演此节点',
                    icon: Icons.auto_graph_rounded,
                    color: sectorColor,
                    onPressed: onLaunchPrediction,
                  ),
                ),
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
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      );
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
          ..color = (isDarkMode ? Colors.white : Colors.black)
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
