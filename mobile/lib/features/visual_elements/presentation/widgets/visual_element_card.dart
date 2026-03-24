import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/rarity_visual_wrapper.dart';
import 'package:sparkle/core/design/widgets/sparkle_tappable.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/visual_element_model.dart';

/// 视觉元素卡片组件
class VisualElementCard extends StatefulWidget {
  const VisualElementCard({
    required this.element,
    super.key,
    this.onTap,
    this.onLongPress,
    this.isCompact = false,
    this.showStatus = true,
  });

  final VisualElementModel element;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final bool isCompact;
  final bool showStatus;

  @override
  State<VisualElementCard> createState() => _VisualElementCardState();
}

class _VisualElementCardState extends State<VisualElementCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _breathingController;
  late Animation<double> _breathingAnimation;

  @override
  void initState() {
    super.initState();
    _breathingController = AnimationController(
      duration: const Duration(milliseconds: 1600),
      vsync: this,
    );
    _breathingAnimation = Tween<double>(begin: 0.3, end: 0.7).animate(
      CurvedAnimation(
        parent: _breathingController,
        curve: Curves.easeInOut,
      ),
    );

    // 已装备卡片启动呼吸动画
    if (widget.element.isEquipped) {
      _breathingController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(VisualElementCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    // 装备状态变化时更新动画
    if (widget.element.isEquipped != oldWidget.element.isEquipped) {
      if (widget.element.isEquipped) {
        _breathingController.repeat(reverse: true);
      } else {
        _breathingController.stop();
        _breathingController.reset();
      }
    }
  }

  @override
  void dispose() {
    _breathingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final colors = _getRarityColors(widget.element.rarity);
    final borderRadius =
        widget.isCompact ? DS.borderRadius12 : DS.borderRadius16;

    // Determine if we should show rarity effects
    final shouldShimmer = widget.element.isUnlocked &&
        _shouldShimmerForRarity(widget.element.rarity);
    final isNewlyUnlocked = _isElementNewlyUnlocked;

    return SparkleTappable(
      onTap: widget.onTap,
      onLongPress: widget.onLongPress,
      enableHaptic: widget.element.isUnlocked,
      borderRadius: borderRadius,
      child: RarityVisualWrapper(
        rarity: widget.element.rarity,
        borderRadius: borderRadius,
        showShimmer: shouldShimmer,
        showGlow: isNewlyUnlocked,
        isNewlyUnlocked: isNewlyUnlocked,
        unlockedAt: widget.element.unlockedAt,
        child: Stack(
          children: [
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    DS.surfaceSecondary,
                    DS.surfaceTertiary.withValues(alpha: 0.5),
                  ],
                ),
                borderRadius: borderRadius,
                border: Border.all(
                  color: widget.element.isEquipped
                      ? colors.border
                      : DS.border.withValues(alpha: 0.5),
                  width: widget.element.isEquipped ? 2 : 1,
                ),
                boxShadow: widget.element.isEquipped
                    ? [
                        BoxShadow(
                          color: colors.border.withValues(alpha: 0.3),
                          blurRadius: 8,
                          spreadRadius: 2,
                        ),
                      ]
                    : null,
              ),
              child: ClipRRect(
                borderRadius: borderRadius,
                child: Stack(
                  children: [
                    _buildPreviewBackground(colors),
                    Padding(
                      padding: EdgeInsets.all(
                        widget.isCompact ? DS.spacing8 : DS.spacing12,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              _buildTypeIcon(),
                              _buildRarityBadge(colors, l10n),
                            ],
                          ),
                          const Spacer(),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                widget.element.name,
                                style: TextStyle(
                                  fontSize: widget.isCompact
                                      ? DS.fontSizeSm
                                      : DS.fontSizeBase,
                                  fontWeight: DS.fontWeightSemibold,
                                  color: DS.textPrimary,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              if (widget.element.description != null &&
                                  !widget.isCompact) ...[
                                const SizedBox(height: DS.spacing4),
                                Text(
                                  widget.element.description!,
                                  style: TextStyle(
                                    fontSize: DS.fontSizeXs,
                                    color: DS.textSecondary,
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ],
                              if (widget.showStatus) ...[
                                const SizedBox(height: DS.spacing8),
                                _buildStatusRow(l10n),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                    if (!widget.element.isUnlocked)
                      _buildLockedOverlay(l10n, colors),
                  ],
                ),
              ),
            ),
            if (widget.element.isEquipped)
              Positioned.fill(
                child: AnimatedBuilder(
                  animation: _breathingAnimation,
                  builder: (context, child) => CustomPaint(
                    painter: _BreathingBorderPainter(
                      animation: _breathingAnimation,
                      color: colors.border,
                      borderRadius: borderRadius,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  bool _shouldShimmerForRarity(VisualElementRarity rarity) => rarity == VisualElementRarity.rare ||
        rarity == VisualElementRarity.epic ||
        rarity == VisualElementRarity.legendary;

  bool get _isElementNewlyUnlocked {
    final unlockedAt = widget.element.unlockedAt;
    if (unlockedAt == null) return false;
    return DateTime.now().difference(unlockedAt) < newlyUnlockedWindow;
  }

  Widget _buildPreviewBackground(_RarityColors colors) {
    // 根据元素类型生成预览背景
    return Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: _getPreviewGradientColors(),
          ),
        ),
        child: Stack(
          children: [
            CustomPaint(
              painter: _ElementPreviewPainter(
                elementType: widget.element.elementType,
                config: widget.element.config,
                seed: widget.element.id.hashCode,
                colors: colors,
              ),
            ),
            Positioned.fill(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      colors.border.withValues(alpha: 0.2),
                      Colors.transparent,
                      colors.background.withValues(alpha: 0.16),
                    ],
                    stops: const [0.0, 0.42, 1.0],
                  ),
                ),
              ),
            ),
            Positioned(
              top: -24,
              right: -8,
              child: IgnorePointer(
                child: Container(
                  width: widget.isCompact ? 72 : 92,
                  height: widget.isCompact ? 72 : 92,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        Colors.white.withValues(alpha: 0.18),
                        Colors.white.withValues(alpha: 0.04),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.45, 1.0],
                    ),
                  ),
                ),
              ),
            ),
            Positioned.fill(
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.transparent,
                        DS.surfacePrimary.withValues(alpha: 0.06),
                        DS.surfacePrimary.withValues(alpha: 0.24),
                      ],
                      stops: const [0.0, 0.58, 1.0],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Color> _getPreviewGradientColors() {
    // 从配置中提取渐变颜色，否则使用默认
    final gradientConfig =
        widget.element.config['gradient'] as Map<String, dynamic>?;
    if (gradientConfig != null) {
      final colors = gradientConfig['colors'] as List<dynamic>?;
      if (colors != null && colors.isNotEmpty) {
        return colors.map((c) => _parseColor(c.toString())).toList();
      }
    }
    // 默认渐变
    return [
      DS.surfaceSecondary.withValues(alpha: 0.8),
      DS.surfaceTertiary.withValues(alpha: 0.6),
    ];
  }

  Color _parseColor(String hexColor) {
    try {
      hexColor = hexColor.replaceAll('#', '');
      if (hexColor.length == 6) {
        return Color(int.parse('FF$hexColor', radix: 16));
      } else if (hexColor.length == 8) {
        return Color(int.parse(hexColor, radix: 16));
      }
    } catch (_) {}
    return DS.surfaceSecondary;
  }

  Widget _buildTypeIcon() {
    final icon = _getTypeIcon(widget.element.elementType);
    final rarityColors = _getRarityColors(widget.element.rarity);
    return Container(
      padding: const EdgeInsets.all(DS.spacing6),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.surfacePrimary.withValues(alpha: 0.94),
            rarityColors.background.withValues(alpha: 0.72),
          ],
        ),
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: rarityColors.border.withValues(alpha: 0.26),
        ),
        boxShadow: [
          BoxShadow(
            color: rarityColors.border.withValues(alpha: 0.08),
            blurRadius: 16,
            spreadRadius: 1,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Icon(
        icon,
        size: widget.isCompact ? DS.iconSizeXs : DS.iconSizeSm,
        color: Color.lerp(DS.textSecondary, rarityColors.text, 0.28),
      ),
    );
  }

  IconData _getTypeIcon(VisualElementType type) {
    switch (type) {
      case VisualElementType.background:
        return Icons.gradient;
      case VisualElementType.particle:
        return Icons.auto_awesome;
      case VisualElementType.effect:
        return Icons.blur_on;
      case VisualElementType.bundle:
        return Icons.inventory_2;
    }
  }

  Widget _buildRarityBadge(_RarityColors colors, AppLocalizations l10n) => Container(
      padding: EdgeInsets.symmetric(
        horizontal: widget.isCompact ? DS.spacing6 : DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: DS.borderRadius8,
        border: Border.all(color: colors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _getRarityIcon(widget.element.rarity),
            size: widget.isCompact ? 10 : DS.iconSizeXs,
            color: colors.text,
          ),
          if (!widget.isCompact) ...[
            const SizedBox(width: DS.spacing4),
            Text(
              _getRarityName(widget.element.rarity, l10n),
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightMedium,
                color: colors.text,
              ),
            ),
          ],
        ],
      ),
    );

  IconData _getRarityIcon(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return Icons.circle_outlined;
      case VisualElementRarity.rare:
        return Icons.star_border;
      case VisualElementRarity.epic:
        return Icons.auto_awesome;
      case VisualElementRarity.legendary:
        return Icons.diamond_outlined;
    }
  }

  String _getRarityName(VisualElementRarity rarity, AppLocalizations l10n) {
    switch (rarity) {
      case VisualElementRarity.common:
        return l10n.achievementRarityCommon;
      case VisualElementRarity.rare:
        return l10n.achievementRarityRare;
      case VisualElementRarity.epic:
        return l10n.achievementRarityEpic;
      case VisualElementRarity.legendary:
        return l10n.achievementRarityLegendary;
    }
  }

  Widget _buildStatusRow(AppLocalizations l10n) {
    String statusText;
    Color statusColor;
    IconData statusIcon;

    if (widget.element.isEquipped) {
      statusText = l10n.visualElementEquipped;
      statusColor = DS.success;
      statusIcon = Icons.check_circle;
    } else if (widget.element.isUnlocked) {
      statusText = l10n.visualElementUnlocked;
      statusColor = DS.info;
      statusIcon = Icons.lock_open;
    } else {
      statusText = _getUnlockSourceText(l10n);
      statusColor = DS.textTertiary;
      statusIcon = Icons.lock;
    }

    return Row(
      children: [
        Icon(
          statusIcon,
          size: DS.iconSizeXs,
          color: statusColor,
        ),
        const SizedBox(width: DS.spacing4),
        Expanded(
          child: Text(
            statusText,
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: statusColor,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  String _getUnlockSourceText(AppLocalizations l10n) {
    switch (widget.element.unlockSource) {
      case VisualElementUnlockSource.system:
        return l10n.visualElementUnlockSystem;
      case VisualElementUnlockSource.achievement:
        return l10n.visualElementUnlockAchievement;
      case VisualElementUnlockSource.shop:
        return l10n.visualElementUnlockShop;
      case VisualElementUnlockSource.event:
        return l10n.visualElementUnlockEvent;
      case VisualElementUnlockSource.season:
        return l10n.visualElementUnlockSeason;
    }
  }

  /// 磨砂玻璃锁定遮罩
  Widget _buildLockedOverlay(AppLocalizations l10n, _RarityColors colors) => Positioned.fill(
      child: ClipRRect(
        borderRadius: widget.isCompact ? DS.borderRadius12 : DS.borderRadius16,
        child: Stack(
          children: [
            // 磨砂玻璃背景
            BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 8.0, sigmaY: 8.0),
              child: Container(
                color: DS.surfacePrimary.withValues(alpha: 0.85),
              ),
            ),
            // 内容
            Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.lock_outline,
                    size: widget.isCompact ? DS.iconSizeMd : DS.iconSizeLg,
                    color: DS.textTertiary,
                  ),
                  if (!widget.isCompact) ...[
                    const SizedBox(height: DS.spacing8),
                    Text(
                      _getUnlockConditionSummary(l10n),
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.textTertiary,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );

  String _getUnlockConditionSummary(AppLocalizations l10n) {
    switch (widget.element.unlockSource) {
      case VisualElementUnlockSource.system:
        return l10n.visualElementUnlockHintSystem;
      case VisualElementUnlockSource.achievement:
        final achievementId =
            widget.element.unlockRequirement?['achievement_id'];
        if (achievementId != null) {
          return l10n.visualElementUnlockHintAchievement(
            achievementId.toString(),
          );
        }
        return l10n.visualElementUnlockHintAchievementDefault;
      case VisualElementUnlockSource.shop:
        final price = widget.element.unlockRequirement?['price_photons'];
        if (price != null) {
          return l10n.visualElementUnlockHintShop(price.toString());
        }
        return l10n.visualElementUnlockHintShopDefault;
      case VisualElementUnlockSource.event:
        return l10n.visualElementUnlockHintEvent;
      case VisualElementUnlockSource.season:
        return l10n.visualElementUnlockHintSeason;
    }
  }

  _RarityColors _getRarityColors(VisualElementRarity rarity) {
    switch (rarity) {
      case VisualElementRarity.common:
        return _RarityColors(
          background: DS.rarityCommonBg,
          border: DS.rarityCommon,
          text: DS.rarityCommonText,
        );
      case VisualElementRarity.rare:
        return _RarityColors(
          background: DS.rarityRareBg,
          border: DS.rarityRare,
          text: DS.rarityRareText,
        );
      case VisualElementRarity.epic:
        return _RarityColors(
          background: DS.rarityEpicBg,
          border: DS.rarityEpic,
          text: DS.rarityEpicText,
        );
      case VisualElementRarity.legendary:
        return _RarityColors(
          background: DS.rarityLegendaryBg,
          border: DS.rarityLegendary,
          text: DS.rarityLegendaryText,
        );
    }
  }
}

class _RarityColors {
  _RarityColors({
    required this.background,
    required this.border,
    required this.text,
  });

  final Color background;
  final Color border;
  final Color text;
}

/// 呼吸边框画笔
class _BreathingBorderPainter extends CustomPainter {
  _BreathingBorderPainter({
    required this.animation,
    required this.color,
    required this.borderRadius,
  });

  final Animation<double> animation;
  final Color color;
  final BorderRadius borderRadius;

  @override
  void paint(Canvas canvas, Size size) {
    final opacity = animation.value;
    final paint = Paint()
      ..color = color.withValues(alpha: opacity)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;

    final rrect = borderRadius.toRRect(Offset.zero & size);
    canvas.drawRRect(rrect, paint);
  }

  @override
  bool shouldRepaint(covariant _BreathingBorderPainter oldDelegate) => animation.value != oldDelegate.animation.value;
}

/// 元素预览画笔
class _ElementPreviewPainter extends CustomPainter {
  _ElementPreviewPainter({
    required this.elementType,
    required this.config,
    required this.seed,
    required this.colors,
  });

  final VisualElementType elementType;
  final Map<String, dynamic> config;
  final int seed;
  final _RarityColors colors;

  @override
  void paint(Canvas canvas, Size size) {
    switch (elementType) {
      case VisualElementType.background:
        _drawBackgroundPreview(canvas, size);
        break;
      case VisualElementType.particle:
        _drawParticlePreview(canvas, size);
        break;
      case VisualElementType.effect:
        _drawEffectPreview(canvas, size);
        break;
      case VisualElementType.bundle:
        _drawBundlePreview(canvas, size);
        break;
    }
  }

  void _drawBackgroundPreview(Canvas canvas, Size size) {
    // 绘制渐变背景效果
    final rect = Offset.zero & size;
    final gradient = LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [
        colors.border.withValues(alpha: 0.1),
        colors.border.withValues(alpha: 0.3),
      ],
    );
    final paint = Paint()
      ..shader = gradient.createShader(rect)
      ..style = PaintingStyle.fill;
    canvas.drawRect(rect, paint);
  }

  void _drawParticlePreview(Canvas canvas, Size size) {
    // 绘制粒子点
    final particleColors =
        config['colors'] as List<dynamic>? ?? ['#ffffff', '#ffd700'];
    final count = config['count'] as int? ?? 10;

    final random = _SeededRandom(seed);
    for (var i = 0; i < count.clamp(5, 15); i++) {
      final x = random.nextDouble() * size.width;
      final y = random.nextDouble() * size.height;
      final radius = 1.5 + random.nextDouble() * 2.5;
      final colorIndex = i % particleColors.length;

      final color = _parseColor(particleColors[colorIndex].toString());
      final paint = Paint()
        ..color = color.withValues(alpha: 0.6)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  void _drawEffectPreview(Canvas canvas, Size size) {
    // 绘制特效效果
    final center = Offset(size.width / 2, size.height / 2);
    final effectColor = config['color'] as String? ?? '#ffffff';
    final color = _parseColor(effectColor);

    final paint = Paint()
      ..shader = RadialGradient(
        colors: [
          color.withValues(alpha: 0.4),
          color.withValues(alpha: 0.0),
        ],
      ).createShader(Rect.fromCircle(center: center, radius: size.width / 2))
      ..style = PaintingStyle.fill;

    canvas.drawCircle(center, size.width / 2.5, paint);
  }

  void _drawBundlePreview(Canvas canvas, Size size) {
    // 绘制套装效果
    _drawBackgroundPreview(canvas, size);
    _drawParticlePreview(canvas, size);
  }

  Color _parseColor(String hexColor) {
    try {
      hexColor = hexColor.replaceAll('#', '');
      if (hexColor.length == 6) {
        return Color(int.parse('FF$hexColor', radix: 16));
      } else if (hexColor.length == 8) {
        return Color(int.parse(hexColor, radix: 16));
      }
    } catch (_) {}
    return DS.surfaceSecondary;
  }

  @override
  bool shouldRepaint(covariant _ElementPreviewPainter oldDelegate) => elementType != oldDelegate.elementType ||
        config != oldDelegate.config;
}

/// 确定性随机数生成器（用于预览）
class _SeededRandom {
  _SeededRandom(this.seed);

  final int seed;
  int _current = 0;

  double nextDouble() {
    _current = (_current * 1103515245 + 12345 + seed) & 0x7FFFFFFF;
    return _current / 0x7FFFFFFF;
  }
}
