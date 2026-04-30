import 'dart:async';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/rarity_visual_wrapper.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/design/widgets/sparkle_tappable.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

// ---------------------------------------------------------------------------
// AchievementCardStyle
// ---------------------------------------------------------------------------

/// 成就卡片样式
enum AchievementCardStyle {
  /// 紧凑型 - 用于列表
  compact,

  /// 标准型 - 用于网格
  standard,

  /// 展示型 - 用于高密度小组件网格
  showcase,

  /// 完整型 - 用于详情
  full,
}

// ---------------------------------------------------------------------------
// AnimatedAchievementCard  (entrance animation wrapper)
// ---------------------------------------------------------------------------

/// Wraps any child with a staggered entrance animation:
/// fade + scale (0.95 -> 1.0) + slide up (8px).
///
/// [index] controls stagger delay (index * 50 ms).
class AnimatedAchievementCard extends StatefulWidget {
  const AnimatedAchievementCard({
    required this.child,
    super.key,
    this.index = 0,
    this.rarity = AchievementRarity.common,
  });

  final Widget child;
  final int index;
  final AchievementRarity rarity;

  @override
  State<AnimatedAchievementCard> createState() =>
      _AnimatedAchievementCardState();
}

class _AnimatedAchievementCardState extends State<AnimatedAchievementCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;
  late final Animation<double> _scaleAnimation;
  late final Animation<Offset> _slideAnimation;

  int get _rarityDelayMs => switch (widget.rarity) {
        AchievementRarity.common => 32,
        AchievementRarity.rare => 44,
        AchievementRarity.epic => 56,
        AchievementRarity.legendary => 70,
      };

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AnimationSystem.scene, // 400 ms
    );

    const curve = Curves.easeOutCubic;

    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: curve,
    );
    _scaleAnimation = Tween<double>(begin: 0.95, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: curve),
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 8),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: curve));

    // Stagger: each card delays by index * 50 ms.
    unawaited(
      Future<void>.delayed(
        Duration(milliseconds: widget.index * _rarityDelayMs),
        () {
          if (mounted) _controller.forward();
        },
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _controller,
        builder: (context, child) => Transform.translate(
          offset: _slideAnimation.value,
          child: Transform.scale(
            scale: _scaleAnimation.value,
            child: Opacity(
              opacity: _fadeAnimation.value,
              child: child,
            ),
          ),
        ),
        child: widget.child,
      );
}

// ---------------------------------------------------------------------------
// _AnimatedProgressBar  (fills from 0 -> target on first build)
// ---------------------------------------------------------------------------

class _AnimatedProgressBar extends StatelessWidget {
  const _AnimatedProgressBar({
    required this.progress,
    required this.rarityColor,
    required this.isUnlocked,
    this.height = 6,
  });

  final double progress;
  final Color rarityColor;
  final bool isUnlocked;
  final double height;

  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0, end: progress.clamp(0.0, 1.0)),
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutCubic,
        builder: (context, value, _) => Container(
          height: height,
          decoration: BoxDecoration(
            color: DS.neutral200,
            borderRadius: DS.borderRadiusFull,
          ),
          child: FractionallySizedBox(
            alignment: Alignment.centerLeft,
            widthFactor: value,
            child: Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: isUnlocked
                      ? [
                          DS.semanticSuccess,
                          DS.semanticSuccess.withValues(alpha: 0.8),
                        ]
                      : [
                          rarityColor,
                          rarityColor.withValues(alpha: 0.7),
                        ],
                ),
                borderRadius: DS.borderRadiusFull,
              ),
            ),
          ),
        ),
      );
}

// ---------------------------------------------------------------------------
// _AnimatedCompactProgressBar
// ---------------------------------------------------------------------------

class _AnimatedCompactProgressBar extends StatelessWidget {
  const _AnimatedCompactProgressBar({
    required this.progress,
    required this.rarityColor,
    required this.progressPercentage,
  });

  final double progress;
  final Color rarityColor;
  final int progressPercentage;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Expanded(
            child: TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0, end: progress.clamp(0.0, 1.0)),
              duration: const Duration(milliseconds: 600),
              curve: Curves.easeOutCubic,
              builder: (context, value, _) => Container(
                height: 4,
                decoration: BoxDecoration(
                  color: DS.neutral200,
                  borderRadius: DS.borderRadiusFull,
                ),
                child: FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: value,
                  child: Container(
                    decoration: BoxDecoration(
                      color: rarityColor,
                      borderRadius: DS.borderRadiusFull,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Text(
            '$progressPercentage%',
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              fontWeight: DS.fontWeightMedium,
              color: DS.textSecondary,
            ),
          ),
        ],
      );
}

// ---------------------------------------------------------------------------
// AchievementCard  (core stateless card with 3 layout variants)
// ---------------------------------------------------------------------------

/// 成就卡片组件
///
/// 显示成就图标、名称、进度，支持点击跳转。
/// 动画效果通过内部 stateful 子组件实现，卡片本身保持 StatelessWidget。
class AchievementCard extends StatelessWidget {
  const AchievementCard({
    required this.achievement,
    super.key,
    this.onTap,
    this.style = AchievementCardStyle.standard,
    this.isPinned = false,
    this.showProgress = true,
  });

  final AchievementWithProgress achievement;
  final VoidCallback? onTap;
  final AchievementCardStyle style;
  final bool isPinned;
  final bool showProgress;

  // -- helpers ---------------------------------------------------------------

  bool get _isNewlyUnlocked {
    final unlockedAt = achievement.userProgress?.unlockedAt;
    if (unlockedAt == null) return false;
    return DateTime.now().difference(unlockedAt) < newlyUnlockedWindow;
  }

  bool get _shouldShimmer =>
      achievement.isUnlocked &&
      shimmerRarities.contains(achievement.achievement.rarity);

  BorderRadius get _borderRadiusForStyle {
    switch (style) {
      case AchievementCardStyle.compact:
        return const BorderRadius.all(Radius.circular(12));
      case AchievementCardStyle.standard:
        return const BorderRadius.all(Radius.circular(16));
      case AchievementCardStyle.showcase:
        return const BorderRadius.all(Radius.circular(18));
      case AchievementCardStyle.full:
        return const BorderRadius.all(Radius.circular(20));
    }
  }

  // -- build -----------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    Widget card;
    switch (style) {
      case AchievementCardStyle.compact:
        card = _buildCompact(context);
      case AchievementCardStyle.standard:
        card = _buildStandard(context);
      case AchievementCardStyle.showcase:
        card = _buildShowcase(context);
      case AchievementCardStyle.full:
        card = _buildFull(context);
    }

    // Use RarityVisualWrapper for consistent rarity-based effects
    final shouldWrap = _shouldShimmer || _isNewlyUnlocked;
    if (!shouldWrap) return card;

    return Hero(
      tag: 'achievement-${achievement.achievement.id}',
      child: RarityVisualWrapper(
        rarity: achievement.achievement.rarity,
        borderRadius: _borderRadiusForStyle,
        showShimmer: _shouldShimmer,
        showGlow: _isNewlyUnlocked,
        isNewlyUnlocked: _isNewlyUnlocked,
        unlockedAt: achievement.userProgress?.unlockedAt,
        child: card,
      ),
    );
  }

  // -- compact variant -------------------------------------------------------

  Widget _buildCompact(BuildContext context) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);

    return SparkleTappable(
      onTap: onTap,
      borderRadius: DS.borderRadius12,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing12,
          vertical: DS.spacing10,
        ),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              isUnlocked ? DS.surfacePrimary : DS.surfaceSecondary,
              Color.lerp(
                    DS.surfaceSecondary,
                    rarityColor,
                    isUnlocked ? 0.06 : 0.03,
                  ) ??
                  DS.surfaceSecondary,
            ],
          ),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: isUnlocked
                ? rarityColor.withValues(alpha: 0.72)
                : DS.border.withValues(alpha: 0.72),
            width: isUnlocked ? 1.5 : 1,
          ),
          boxShadow: isUnlocked
              ? [
                  BoxShadow(
                    color: rarityColor.withValues(alpha: 0.12),
                    blurRadius: 14,
                    offset: const Offset(0, 8),
                  ),
                ]
              : [
                  BoxShadow(
                    color: DS.textPrimary.withValues(alpha: 0.04),
                    blurRadius: 10,
                    offset: const Offset(0, 6),
                  ),
                ],
        ),
        child: Row(
          children: [
            _buildIcon(size: 36),
            const SizedBox(width: DS.spacing10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          achievement.achievement.name,
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            fontWeight: DS.fontWeightSemibold,
                            color:
                                isUnlocked ? DS.textPrimary : DS.textSecondary,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (isPinned)
                        Padding(
                          padding: const EdgeInsets.only(left: DS.spacing8),
                          child: Icon(
                            Icons.push_pin,
                            size: DS.iconSizeXs,
                            color: DS.semanticWarning,
                          ),
                        ),
                      if (achievement.achievement.isLimited)
                        Padding(
                          padding: const EdgeInsets.only(left: DS.spacing6),
                          child: _buildLimitedChip(context),
                        ),
                    ],
                  ),
                  if (achievement.achievement.description != null) ...[
                    const SizedBox(height: DS.spacing4),
                    Text(
                      achievement.achievement.description!,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                  if (showProgress && !isUnlocked) ...[
                    const SizedBox(height: DS.spacing4),
                    _buildCompactProgressBar(),
                  ],
                ],
              ),
            ),
            const SizedBox(width: DS.spacing8),
            _buildStatusIcon(),
          ],
        ),
      ),
    );
  }

  // -- standard variant ------------------------------------------------------

  Widget _buildStandard(BuildContext context) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);
    final rarityGradient =
        RarityColorProvider.getGradient(achievement.achievement.rarity);

    return SparkleTappable(
      onTap: onTap,
      borderRadius: DS.borderRadius16,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          gradient: isUnlocked && rarityGradient != null
              ? LinearGradient(
                  colors: [
                    rarityGradient.colors.first.withValues(alpha: 0.1),
                    rarityGradient.colors.last.withValues(alpha: 0.05),
                  ],
                )
              : null,
          color: isUnlocked ? DS.surfacePrimary : DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: isUnlocked ? rarityColor : DS.border,
            width: isUnlocked ? 2 : 1,
          ),
          boxShadow: isUnlocked
              ? [
                  BoxShadow(
                    color: rarityColor.withValues(alpha: 0.2),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ]
              : DS.shadowSm,
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 180;
            final compressed = constraints.maxHeight < 130;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildIcon(size: compact ? 42 : 48),
                    SizedBox(width: compact ? DS.spacing10 : DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(
                                  achievement.achievement.name,
                                  style: TextStyle(
                                    fontSize: compact
                                        ? DS.fontSizeSm
                                        : DS.fontSizeBase,
                                    fontWeight: DS.fontWeightBold,
                                    color: isUnlocked
                                        ? DS.textPrimary
                                        : DS.textSecondary,
                                  ),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              const SizedBox(width: DS.spacing4),
                              _buildStatusIcon(size: compact ? 18 : 20),
                            ],
                          ),
                          const SizedBox(height: DS.spacing4),
                          Row(
                            children: [
                              Flexible(
                                child: RarityBadge(
                                  rarity: achievement.achievement.rarity,
                                  isCompact: true,
                                  showLabel: !(compact || compressed),
                                ),
                              ),
                              if (isPinned) ...[
                                const SizedBox(width: DS.spacing6),
                                Icon(
                                  Icons.push_pin,
                                  size: DS.iconSizeXs,
                                  color: DS.semanticWarning,
                                ),
                              ],
                              if (achievement.achievement.isLimited) ...[
                                const SizedBox(width: DS.spacing6),
                                _buildLimitedChip(context),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (!compressed &&
                    achievement.achievement.description != null) ...[
                  const SizedBox(height: DS.spacing10),
                  Text(
                    achievement.achievement.description!,
                    style: TextStyle(
                      fontSize: compact ? DS.fontSizeXs : DS.fontSizeSm,
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                if (showProgress && !compressed) ...[
                  const SizedBox(height: DS.spacing10),
                  _buildProgressBar(),
                ],
              ],
            );
          },
        ),
      ),
    );
  }

  // -- showcase variant ------------------------------------------------------

  Widget _buildShowcase(BuildContext context) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);
    final rarityGradient =
        RarityColorProvider.getGradient(achievement.achievement.rarity);
    final rewardPreview = _rewardPreviewLabels(context);
    final categoryLabel = _categoryLabel(context);
    final progressValue = achievement.userProgress?.progressValue;
    final progressTarget = achievement.userProgress?.progressTarget;

    return SparkleTappable(
      onTap: onTap,
      borderRadius: const BorderRadius.all(Radius.circular(18)),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact =
              constraints.maxWidth < 185 || constraints.maxHeight < 245;
          final ultraCompact =
              constraints.maxWidth < 168 || constraints.maxHeight < 232;
          final rewardLimit = ultraCompact ? 1 : 2;

          return Container(
            padding: EdgeInsets.all(compact ? DS.spacing12 : DS.spacing16),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: isUnlocked && rarityGradient != null
                    ? [
                        rarityGradient.colors.first.withValues(alpha: 0.18),
                        rarityGradient.colors.last.withValues(alpha: 0.08),
                      ]
                    : [
                        DS.surfacePrimary,
                        Color.lerp(DS.surfaceSecondary, rarityColor, 0.06) ??
                            DS.surfaceSecondary,
                      ],
              ),
              borderRadius: const BorderRadius.all(Radius.circular(18)),
              border: Border.all(
                color: isUnlocked
                    ? rarityColor.withValues(alpha: 0.9)
                    : DS.border.withValues(alpha: 0.85),
                width: isUnlocked ? 1.6 : 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: (isUnlocked ? rarityColor : DS.textPrimary)
                      .withValues(alpha: isUnlocked ? 0.14 : 0.06),
                  blurRadius: isUnlocked ? 18 : 12,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Wrap(
                        spacing: DS.spacing6,
                        runSpacing: DS.spacing6,
                        children: [
                          RarityBadge(
                            rarity: achievement.achievement.rarity,
                            isCompact: true,
                            showLabel: !compact,
                          ),
                          _buildToneChip(
                            label: categoryLabel,
                            color: rarityColor,
                            icon: _categoryIcon(),
                            maxWidth: compact ? 72 : 90,
                          ),
                          if ((achievement.userProgress?.isFirstUnlocker ??
                                  false) &&
                              !ultraCompact)
                            _buildToneChip(
                              label: context.l10n.achievementCardFirstUnlocker,
                              color: DS.semanticWarning,
                              icon: Icons.workspace_premium_rounded,
                              maxWidth: 78,
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    _buildStatusIcon(size: compact ? 18 : 20),
                  ],
                ),
                SizedBox(height: compact ? DS.spacing8 : DS.spacing12),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildIcon(size: compact ? 40 : 46),
                    SizedBox(width: compact ? DS.spacing10 : DS.spacing12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            achievement.achievement.name,
                            style: TextStyle(
                              fontSize:
                                  compact ? DS.fontSizeSm : DS.fontSizeBase,
                              fontWeight: DS.fontWeightBold,
                              color: isUnlocked
                                  ? DS.textPrimary
                                  : DS.textSecondary,
                              height: 1.2,
                            ),
                            maxLines: compact ? 2 : 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                          if (!ultraCompact &&
                              achievement.achievement.description != null) ...[
                            const SizedBox(height: DS.spacing4),
                            Text(
                              achievement.achievement.description!,
                              style: TextStyle(
                                fontSize: DS.fontSizeXs,
                                color: DS.textSecondary,
                                height: 1.3,
                              ),
                              maxLines: compact ? 1 : 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
                SizedBox(height: compact ? DS.spacing8 : DS.spacing10),
                if (rewardPreview.isNotEmpty) ...[
                  if (!compact)
                    Text(
                      context.l10n.achievementCardGloryReward,
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        fontWeight: DS.fontWeightSemibold,
                        color: DS.textSecondary,
                      ),
                    ),
                  if (!compact) const SizedBox(height: DS.spacing6),
                  Wrap(
                    spacing: DS.spacing6,
                    runSpacing: DS.spacing6,
                    children: rewardPreview
                        .take(rewardLimit)
                        .map(
                          (label) => _buildToneChip(
                            label: label,
                            color: rarityColor,
                            icon: Icons.auto_awesome_rounded,
                            maxWidth: compact ? 84 : 112,
                          ),
                        )
                        .toList(),
                  ),
                  SizedBox(height: compact ? DS.spacing8 : DS.spacing10),
                ],
                const Spacer(),
                _buildProgressBar(height: compact ? 6 : 7),
                const SizedBox(height: DS.spacing8),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        isUnlocked
                            ? context.l10n.achievementCardCompleted
                            : progressValue != null && progressTarget != null
                                ? '$progressValue / $progressTarget'
                                : context.l10n.achievementCardKeepPursuing,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textSecondary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: DS.spacing8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: DS.spacing8,
                        vertical: DS.spacing4,
                      ),
                      decoration: BoxDecoration(
                        color: rarityColor.withValues(alpha: 0.12),
                        borderRadius: DS.borderRadiusFull,
                      ),
                      child: Text(
                        isUnlocked
                            ? context.l10n.achievementCardAchieved
                            : '${achievement.progressPercentage}%',
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          fontWeight: DS.fontWeightSemibold,
                          color: rarityColor,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // -- full variant ----------------------------------------------------------

  Widget _buildFull(BuildContext context) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);
    final rarityGradient =
        RarityColorProvider.getGradient(achievement.achievement.rarity);

    return SparkleTappable(
      onTap: onTap,
      borderRadius: DS.borderRadius20,
      child: Container(
        padding: const EdgeInsets.all(DS.spacing20),
        decoration: BoxDecoration(
          gradient: isUnlocked && rarityGradient != null
              ? LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    rarityGradient.colors.first.withValues(alpha: 0.15),
                    rarityGradient.colors.last.withValues(alpha: 0.08),
                  ],
                )
              : null,
          color: isUnlocked ? DS.surfacePrimary : DS.surfaceSecondary,
          borderRadius: DS.borderRadius20,
          border: Border.all(
            color: isUnlocked ? rarityColor : DS.border,
            width: isUnlocked ? 2 : 1,
          ),
          boxShadow: isUnlocked
              ? [
                  BoxShadow(
                    color: rarityColor.withValues(alpha: 0.25),
                    blurRadius: 16,
                    offset: const Offset(0, 6),
                  ),
                ]
              : DS.shadowMd,
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 420;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildIcon(size: compact ? 48 : 56),
                    SizedBox(width: compact ? DS.spacing12 : DS.spacing16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            achievement.achievement.name,
                            maxLines: compact ? 2 : 3,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize:
                                  compact ? DS.fontSizeBase : DS.fontSizeLg,
                              fontWeight: DS.fontWeightBold,
                              color: isUnlocked
                                  ? DS.textPrimary
                                  : DS.textSecondary,
                            ),
                          ),
                          const SizedBox(height: DS.spacing8),
                          Wrap(
                            spacing: DS.spacing8,
                            runSpacing: DS.spacing8,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              RarityBadge(
                                rarity: achievement.achievement.rarity,
                                showLabel: !compact,
                              ),
                              if (isPinned)
                                Icon(
                                  Icons.push_pin,
                                  size: DS.iconSizeSm,
                                  color: DS.semanticWarning,
                                ),
                              _buildStatusIcon(size: compact ? 22 : 28),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                if (achievement.achievement.description != null) ...[
                  const SizedBox(height: DS.spacing16),
                  Text(
                    achievement.achievement.description!,
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      color: DS.textSecondary,
                      height: 1.5,
                    ),
                  ),
                ],
                if (showProgress) ...[
                  const SizedBox(height: DS.spacing16),
                  _buildProgressBar(height: 8),
                  const SizedBox(height: DS.spacing8),
                  _buildProgressText(context),
                ],
              ],
            );
          },
        ),
      ),
    );
  }

  // -- shared sub-widgets ----------------------------------------------------

  Widget _buildIcon({double size = 48}) {
    final isUnlocked = achievement.isUnlocked;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isUnlocked
              ? [
                  rarityColor.withValues(alpha: 0.9),
                  rarityColor.withValues(alpha: 0.6),
                ]
              : [
                  DS.neutral300,
                  DS.neutral400,
                ],
        ),
        boxShadow: isUnlocked
            ? [
                BoxShadow(
                  color: rarityColor.withValues(alpha: 0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ]
            : null,
      ),
      child: Icon(
        _getIconForAchievement(),
        color: isUnlocked ? Colors.white : DS.neutral600,
        size: size * 0.5,
      ),
    );
  }

  Widget _buildStatusIcon({double size = 20}) {
    if (achievement.isUnlocked) {
      return Icon(
        Icons.check_circle,
        color: DS.semanticSuccess,
        size: size,
      );
    }
    return Icon(
      Icons.lock_outline,
      color: DS.textTertiary,
      size: size,
    );
  }

  Widget _buildLimitedChip(BuildContext context) {
    final l10n = context.l10n;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing6,
        vertical: 2,
      ),
      decoration: BoxDecoration(
        color: DS.semanticWarning.withValues(alpha: 0.15),
        borderRadius: DS.borderRadiusFull,
        border: Border.all(color: DS.semanticWarning.withValues(alpha: 0.6)),
      ),
      child: Text(
        l10n.achievementLimitedTime,
        style: TextStyle(
          fontSize: DS.fontSizeXs,
          color: DS.semanticWarning,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }

  Widget _buildProgressBar({double height = 6}) {
    final progress = achievement.progressPercentage / 100;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);

    return _AnimatedProgressBar(
      progress: progress,
      rarityColor: rarityColor,
      isUnlocked: achievement.isUnlocked,
      height: height,
    );
  }

  Widget _buildCompactProgressBar() {
    final progress = achievement.progressPercentage / 100;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);

    return _AnimatedCompactProgressBar(
      progress: progress,
      rarityColor: rarityColor,
      progressPercentage: achievement.progressPercentage,
    );
  }

  Widget _buildProgressText(BuildContext context) {
    final userProgress = achievement.userProgress;

    if (userProgress == null) {
      return const SizedBox.shrink();
    }

    return Wrap(
      alignment: WrapAlignment.spaceBetween,
      runSpacing: DS.spacing4,
      children: [
        Text(
          context.l10n.achievementProgress,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.textSecondary,
          ),
        ),
        Text(
          '${userProgress.progressValue} / ${userProgress.progressTarget}',
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            fontWeight: DS.fontWeightMedium,
            color: DS.textPrimary,
          ),
        ),
      ],
    );
  }

  Widget _buildToneChip({
    required String label,
    required Color color,
    required IconData icon,
    double? maxWidth,
  }) =>
      Container(
        constraints: BoxConstraints(maxWidth: maxWidth ?? 120),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: color.withValues(alpha: 0.24)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: color),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                fontWeight: DS.fontWeightSemibold,
                color: color,
              ),
            ),
          ],
        ),
      );

  List<String> _rewardPreviewLabels(BuildContext context) {
    final rewards = achievement.achievement.rewardConfig ?? const [];
    final labels = <String>[];

    for (final reward in rewards) {
      final type = reward['type']?.toString() ?? '';
      switch (type) {
        case 'title':
          labels.add(reward['display']?.toString() ?? context.l10n.achievementCardNewTitle);
        case 'visual_element':
          labels.add(context.l10n.achievementCardVisualElement);
        case 'galaxy_skin':
          labels.add(context.l10n.achievementCardGalaxySkin);
        case 'avatar_border':
          labels.add(context.l10n.achievementCardAvatarBorder);
        case 'profile_badge':
          labels.add(context.l10n.achievementCardProfileBadge);
        case 'banner':
          labels.add(context.l10n.achievementCardBanner);
      }
    }

    return labels.toSet().toList();
  }

  String _categoryLabel(BuildContext context) {
    switch (achievement.achievement.type) {
      case AchievementType.streak:
        return context.l10n.achievementCardCategoryStreak;
      case AchievementType.mastery:
        return context.l10n.achievementCardCategoryMastery;
      case AchievementType.taskComplete:
        return context.l10n.achievementCardCategoryTask;
      case AchievementType.nodeExplore:
        return context.l10n.achievementCardCategoryExploration;
      case AchievementType.studyTime:
        return context.l10n.achievementCardCategoryStudyTime;
      case AchievementType.hidden:
        return context.l10n.achievementCardCategoryHidden;
      case AchievementType.milestone:
        return context.l10n.achievementCardCategoryMilestone;
      case AchievementType.social:
        return context.l10n.achievementCardCategorySocial;
      case AchievementType.contract:
        return context.l10n.achievementCardCategoryContract;
      case AchievementType.sprint:
        return context.l10n.achievementCardCategorySprint;
    }
  }

  IconData _categoryIcon() {
    switch (achievement.achievement.type) {
      case AchievementType.streak:
        return Icons.local_fire_department_rounded;
      case AchievementType.mastery:
        return Icons.military_tech_rounded;
      case AchievementType.taskComplete:
        return Icons.task_alt_rounded;
      case AchievementType.nodeExplore:
        return Icons.explore_rounded;
      case AchievementType.studyTime:
        return Icons.schedule_rounded;
      case AchievementType.hidden:
        return Icons.visibility_off_rounded;
      case AchievementType.milestone:
        return Icons.flag_rounded;
      case AchievementType.social:
        return Icons.groups_rounded;
      case AchievementType.contract:
        return Icons.description_rounded;
      case AchievementType.sprint:
        return Icons.bolt_rounded;
    }
  }

  IconData _getIconForAchievement() {
    // 根据成就类型返回对应图标
    switch (achievement.achievement.type) {
      case AchievementType.streak:
        return Icons.local_fire_department_rounded;
      case AchievementType.mastery:
        return Icons.military_tech;
      case AchievementType.taskComplete:
        return Icons.task_alt;
      case AchievementType.nodeExplore:
        return Icons.explore;
      case AchievementType.studyTime:
        return Icons.schedule;
      case AchievementType.hidden:
        return Icons.help_outline;
      case AchievementType.milestone:
        return Icons.flag;
      case AchievementType.social:
        return Icons.people;
      case AchievementType.contract:
        return Icons.description;
      case AchievementType.sprint:
        return Icons.directions_run;
    }
  }
}

// ---------------------------------------------------------------------------
// AchievementGridCard  (grid layout convenience wrapper)
// ---------------------------------------------------------------------------

/// 成就网格卡片（用于网格布局）
class AchievementGridCard extends StatelessWidget {
  const AchievementGridCard({
    required this.achievement,
    super.key,
    this.onTap,
    this.showProgress = true,
    this.animationIndex,
  });

  final AchievementWithProgress achievement;
  final VoidCallback? onTap;
  final bool showProgress;

  /// When non-null, wraps the card in [AnimatedAchievementCard] with stagger.
  final int? animationIndex;

  @override
  Widget build(BuildContext context) {
    final card = AchievementCard(
      achievement: achievement,
      onTap: onTap,
      showProgress: showProgress,
    );

    if (animationIndex != null) {
      return AnimatedAchievementCard(
        index: animationIndex!,
        rarity: achievement.achievement.rarity,
        child: card,
      );
    }
    return card;
  }
}

// ---------------------------------------------------------------------------
// AchievementListCard  (list layout convenience wrapper)
// ---------------------------------------------------------------------------

/// 成就列表卡片（用于列表布局）
class AchievementListCard extends StatelessWidget {
  const AchievementListCard({
    required this.achievement,
    super.key,
    this.onTap,
    this.showProgress = true,
    this.animationIndex,
  });

  final AchievementWithProgress achievement;
  final VoidCallback? onTap;
  final bool showProgress;

  /// When non-null, wraps the card in [AnimatedAchievementCard] with stagger.
  final int? animationIndex;

  @override
  Widget build(BuildContext context) {
    final card = AchievementCard(
      achievement: achievement,
      onTap: onTap,
      style: AchievementCardStyle.compact,
      showProgress: showProgress,
    );

    if (animationIndex != null) {
      return AnimatedAchievementCard(
        index: animationIndex!,
        rarity: achievement.achievement.rarity,
        child: card,
      );
    }
    return card;
  }
}

// ---------------------------------------------------------------------------
// AchievementDetailCard  (detail page convenience wrapper)
// ---------------------------------------------------------------------------

/// 成就详情卡片（用于详情页）
class AchievementDetailCard extends StatelessWidget {
  const AchievementDetailCard({
    required this.achievement,
    super.key,
    this.showProgress = true,
  });

  final AchievementWithProgress achievement;
  final bool showProgress;

  @override
  Widget build(BuildContext context) => AchievementCard(
        achievement: achievement,
        style: AchievementCardStyle.full,
        showProgress: showProgress,
      );
}
