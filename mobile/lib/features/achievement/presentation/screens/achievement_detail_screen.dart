import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_share_bottom_sheet.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
import 'package:sparkle/features/visual_elements/presentation/providers/visual_elements_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/achievement_model.dart';

/// 成就详情页面
class AchievementDetailScreen extends ConsumerStatefulWidget {
  const AchievementDetailScreen({
    required this.achievementId,
    super.key,
  });

  final String achievementId;

  @override
  ConsumerState<AchievementDetailScreen> createState() =>
      _AchievementDetailScreenState();
}

class _AchievementDetailScreenState
    extends ConsumerState<AchievementDetailScreen>
    with TickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _glowAnimation;

  late AnimationController _particleController;

  late AnimationController _entranceController;
  late Animation<double> _iconScaleAnimation;

  bool _requestedVisualElements = false;

  @override
  void initState() {
    super.initState();

    // Existing glow controller - made more subtle (0.95 to 1.05)
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _glowAnimation = Tween<double>(begin: 0.95, end: 1.05).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );
    unawaited(_controller.repeat(reverse: true));

    // Particle animation controller - continuous loop
    _particleController = AnimationController(
      duration: const Duration(seconds: 6),
      vsync: this,
    );
    unawaited(_particleController.repeat());

    // Entrance animation controller - one-shot
    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _iconScaleAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _entranceController,
        curve: Curves.elasticOut,
      ),
    );
    unawaited(_entranceController.forward());

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _requestAchievementDetail();
    });
  }

  @override
  void didUpdateWidget(covariant AchievementDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.achievementId != widget.achievementId) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _requestAchievementDetail();
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _particleController.dispose();
    _entranceController.dispose();
    super.dispose();
  }

  void _requestAchievementDetail() {
    if (!mounted) return;
    unawaited(
      ref
          .read(achievementProvider.notifier)
          .loadAchievementDetail(widget.achievementId),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(achievementProvider);
    final l10n = context.l10n;

    if (state.isLoading) {
      return SparklePageScaffold(
        role: SparklePageRole.immersive,
        appBar: AppBar(),
        child: const Center(child: CircularProgressIndicator()),
      );
    }

    final achievement = state.achievements
        .where((a) => a.achievement.id == widget.achievementId)
        .firstOrNull;

    if (achievement == null) {
      return SparklePageScaffold(
        role: SparklePageRole.immersive,
        appBar: AppBar(),
        child: _buildNotFoundView(l10n),
      );
    }

    return SparklePageScaffold(
      role: SparklePageRole.immersive,
      safeArea: false,
      child: ContentConstraint(
        child: CustomScrollView(
          slivers: [
            // 自定义顶部
            _buildHeader(context, achievement),

            // 内容区域
            SliverToBoxAdapter(
              child: _buildContent(achievement, l10n),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(
    BuildContext context,
    AchievementWithProgress achievement,
  ) {
    final rarity = achievement.achievement.rarity;
    final rarityColor = RarityColorProvider.getColor(rarity);

    return SliverAppBar(
      expandedHeight: 200,
      pinned: true,
      backgroundColor: Color.alphaBlend(
        rarityColor.withValues(alpha: 0.06),
        DS.surfacePrimary,
      ),
      flexibleSpace: FlexibleSpaceBar(
        background: Stack(
          fit: StackFit.expand,
          children: [
            // 背景渐变
            _buildHeaderBackground(rarityColor),

            // Rotating energy field for epic+ rarity
            if (rarity.index >= AchievementRarity.epic.index)
              AnimatedBuilder(
                animation: _particleController,
                builder: (context, child) => CustomPaint(
                  painter: _EnergyFieldPainter(
                    color: rarityColor,
                    rotation: _particleController.value * 2 * math.pi,
                  ),
                  size: Size.infinite,
                ),
              ),

            // 粒子效果（仅稀有+成就）— now animated
            if (rarity.index >= AchievementRarity.rare.index)
              _buildHeaderParticles(rarity),

            // 中心内容
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Icon with entrance scale + subtle glow
                  AnimatedBuilder(
                    animation: Listenable.merge([
                      _glowAnimation,
                      _iconScaleAnimation,
                    ]),
                    builder: (context, child) => Transform.scale(
                      scale: _glowAnimation.value * _iconScaleAnimation.value,
                      child: _buildLargeIcon(achievement),
                    ),
                  ),
                  const SizedBox(height: DS.spacing16),
                  RarityBadge(rarity: rarity),
                ],
              ),
            ),
          ],
        ),
      ),
      leading: Container(
        margin: const EdgeInsets.all(DS.spacing8),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.9),
          shape: BoxShape.circle,
        ),
        child: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
      ),
      actions: [
        Container(
          margin: const EdgeInsets.all(DS.spacing8),
          decoration: BoxDecoration(
            color: DS.surfacePrimary.withValues(alpha: 0.9),
            shape: BoxShape.circle,
          ),
          child: SparkleIconButton(
            icon: const Icon(Icons.share_outlined),
            onPressed: () => _shareAchievement(achievement),
            variant: ButtonVariant.ghost,
          ),
        ),
      ],
    );
  }

  Widget _buildHeaderBackground(Color rarityColor) => Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              rarityColor.withValues(alpha: 0.26),
              rarityColor.withValues(alpha: 0.05),
              DS.surfacePrimary,
            ],
          ),
        ),
      );

  Widget _buildHeaderParticles(AchievementRarity rarity) => AnimatedBuilder(
        animation: _particleController,
        builder: (context, child) => CustomPaint(
          painter: _HeaderParticlePainter(
            rarity,
            animationValue: _particleController.value,
          ),
          size: Size.infinite,
        ),
      );

  Widget _buildLargeIcon(AchievementWithProgress achievement) {
    final rarity = achievement.achievement.rarity;
    final rarityColor = RarityColorProvider.getColor(rarity);

    return Hero(
      tag: 'achievement-${achievement.achievement.id}',
      child: Material(
        color: Colors.transparent,
        child: Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: achievement.isUnlocked
                  ? [
                      rarityColor,
                      rarityColor.withValues(alpha: 0.6),
                    ]
                  : [
                      DS.neutral300,
                      DS.neutral400,
                    ],
            ),
            boxShadow: achievement.isUnlocked
                ? [
                    BoxShadow(
                      color: rarityColor.withValues(alpha: 0.34),
                      blurRadius: 28,
                      spreadRadius: 5,
                    ),
                  ]
                : null,
          ),
          child: Icon(
            _getIconForAchievement(achievement),
            color: achievement.isUnlocked ? DS.textOnPrimary : DS.neutral600,
            size: 50,
          ),
        ),
      ),
    );
  }

  Widget _buildContent(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) {
    var sectionIndex = 0;
    final contextStory = _achievementContextStory(achievement);

    return Container(
      padding: const EdgeInsets.all(DS.spacing20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            Colors.transparent,
            Color.alphaBlend(
              RarityColorProvider.getColor(achievement.achievement.rarity)
                  .withValues(alpha: 0.015),
              DS.surfacePrimary,
            ),
          ],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 名称和解锁状态
          _AnimatedSection(
            index: sectionIndex++,
            child: _buildTitleSection(achievement, l10n),
          ),
          const SizedBox(height: DS.spacing24),

          // 描述
          if (achievement.achievement.description != null) ...[
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildSectionTitle(l10n.achievementDescription),
            ),
            const SizedBox(height: DS.spacing8),
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildDescription(achievement, l10n),
            ),
            const SizedBox(height: DS.spacing24),
          ],

          if (achievement.isUnlocked && contextStory != null) ...[
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildSectionTitle(context.l10n.achievementDetailUnlockMoment),
            ),
            const SizedBox(height: DS.spacing12),
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildContextStoryCard(achievement, contextStory),
            ),
            const SizedBox(height: DS.spacing24),
          ],

          if (_hasEventWindow(achievement.achievement)) ...[
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildSectionTitle(l10n.achievementEventWindow),
            ),
            const SizedBox(height: DS.spacing12),
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildEventWindow(achievement.achievement, l10n),
            ),
            const SizedBox(height: DS.spacing24),
          ],

          // 进度（未解锁时）
          if (!achievement.isUnlocked) ...[
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildSectionTitle(l10n.achievementProgress),
            ),
            const SizedBox(height: DS.spacing12),
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildProgressCard(achievement, l10n),
            ),
            const SizedBox(height: DS.spacing24),
          ],

          // 前置成就
          if (achievement.achievement.prerequisites?.isNotEmpty ?? false) ...[
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildSectionTitle(l10n.achievementPrerequisites),
            ),
            const SizedBox(height: DS.spacing12),
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildPrerequisites(achievement, l10n),
            ),
            const SizedBox(height: DS.spacing24),
          ],

          // 奖励
          if (achievement.achievement.rewardConfig?.isNotEmpty ?? false) ...[
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildSectionTitle(l10n.achievementRewards),
            ),
            const SizedBox(height: DS.spacing12),
            _AnimatedSection(
              index: sectionIndex++,
              child: _buildRewards(achievement, l10n),
            ),
            const SizedBox(height: DS.spacing24),
          ],

          // 统计信息
          _AnimatedSection(
            index: sectionIndex++,
            child: _buildStats(achievement, l10n),
          ),

          const SizedBox(height: DS.spacing40),
        ],
      ),
    );
  }

  Widget _buildTitleSection(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) =>
      LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 420;
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      achievement.achievement.name,
                      maxLines: compact ? 3 : 4,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: compact ? DS.fontSizeXl : DS.fontSize2xl,
                        fontWeight: DS.fontWeightBold,
                        color: DS.textPrimary,
                      ),
                    ),
                    const SizedBox(height: DS.spacing8),
                    Wrap(
                      spacing: DS.spacing12,
                      runSpacing: DS.spacing8,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        if (achievement.isUnlocked) ...[
                          Icon(
                            Icons.check_circle,
                            size: DS.iconSizeSm,
                            color: DS.semanticSuccess,
                          ),
                          Text(
                            l10n.achievementStatusUnlocked,
                            style: TextStyle(
                              fontSize: DS.fontSizeSm,
                              color: DS.semanticSuccess,
                              fontWeight: DS.fontWeightMedium,
                            ),
                          ),
                        ] else ...[
                          Icon(
                            Icons.lock_outline,
                            size: DS.iconSizeSm,
                            color: DS.textTertiary,
                          ),
                          Text(
                            l10n.achievementStatusLocked,
                            style: TextStyle(
                              fontSize: DS.fontSizeSm,
                              color: DS.textTertiary,
                            ),
                          ),
                        ],
                        Text(
                          _getTypeName(achievement.achievement.type, l10n),
                          style: TextStyle(
                            fontSize: DS.fontSizeSm,
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing8),
              SparkleIconButton(
                icon: Icon(
                  achievement.userProgress?.isPinned ?? false
                      ? Icons.push_pin
                      : Icons.push_pin_outlined,
                  color: (achievement.userProgress?.isPinned ?? false)
                      ? DS.semanticWarning
                      : DS.textSecondary,
                ),
                onPressed: () => _togglePin(achievement),
                variant: ButtonVariant.ghost,
              ),
            ],
          );
        },
      );

  Widget _buildSectionTitle(String title) => Text(
        title,
        style: TextStyle(
          fontSize: DS.fontSizeBase,
          fontWeight: DS.fontWeightBold,
          color: DS.textPrimary,
        ),
      );

  Widget _buildDescription(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) =>
      Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              DS.surfaceSecondary,
              Color.alphaBlend(
                RarityColorProvider.getColor(achievement.achievement.rarity)
                    .withValues(alpha: 0.03),
                DS.surfacePrimary,
              ),
            ],
          ),
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.border.withValues(alpha: 0.55)),
          boxShadow: [
            BoxShadow(
              color: DS.textPrimary.withValues(alpha: 0.04),
              blurRadius: 14,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Text(
          achievement.achievement.description ?? l10n.achievementNoDescription,
          style: TextStyle(
            fontSize: DS.fontSizeBase,
            color: DS.textPrimary,
            height: 1.5,
          ),
        ),
      );

  Widget _buildContextStoryCard(
    AchievementWithProgress achievement,
    String story,
  ) {
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);
    final chips = _contextStoryChips(achievement);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.surfaceSecondary,
            Color.alphaBlend(
              rarityColor.withValues(alpha: 0.045),
              DS.surfacePrimary,
            ),
          ],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: rarityColor.withValues(alpha: 0.22)),
        boxShadow: [
          BoxShadow(
            color: rarityColor.withValues(alpha: 0.08),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: rarityColor.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  Icons.history_edu_rounded,
                  color: rarityColor,
                  size: 18,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Text(
                  story,
                  style: TextStyle(
                    fontSize: DS.fontSizeBase,
                    color: DS.textPrimary,
                    height: 1.5,
                    fontWeight: DS.fontWeightMedium,
                  ),
                ),
              ),
            ],
          ),
          if (chips.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: chips,
            ),
          ],
        ],
      ),
    );
  }

  String? _achievementContextStory(AchievementWithProgress achievement) {
    if (!achievement.isUnlocked) return null;
    final progress = achievement.userProgress;
    final explicit = progress?.contextStory?.trim();
    if (explicit != null && explicit.isNotEmpty) {
      return explicit;
    }

    final snapshot = progress?.contextSnapshot ?? const <String, dynamic>{};
    final snapshotStory = snapshot['story']?.toString().trim();
    if (snapshotStory != null && snapshotStory.isNotEmpty) {
      return snapshotStory;
    }

    final unlockedAt = progress?.unlockedAt;
    if (unlockedAt == null) return null;
    return context.l10n.achievementDetailUnlockStory(_formatDate(unlockedAt), achievement.achievement.name);
  }

  List<Widget> _contextStoryChips(AchievementWithProgress achievement) {
    final snapshot =
        achievement.userProgress?.contextSnapshot ?? const <String, dynamic>{};
    final plan = _asStringMap(snapshot['current_plan']);
    final task = _asStringMap(snapshot['task']);
    final progress = _asStringMap(snapshot['progress']);
    final chips = <Widget>[];

    final planName = _cleanSnapshotText(plan['name']);
    final daysToTarget = _asInt(plan['days_to_target']);
    if (planName != null) {
      final label = daysToTarget == null
          ? planName
          : daysToTarget >= 0
              ? context.l10n.achievementDetailDaysBeforeTarget(planName, daysToTarget)
              : context.l10n.achievementDetailDaysAfterTarget(planName, daysToTarget.abs());
      chips.add(_ContextChip(icon: Icons.flag_rounded, label: label));
    }

    final taskTitle = _cleanSnapshotText(task['title']);
    if (taskTitle != null) {
      chips.add(_ContextChip(icon: Icons.task_alt_rounded, label: taskTitle));
    }

    final value = _asInt(progress['value']);
    final target = _asInt(progress['target']);
    if (value != null && target != null && target > 0) {
      chips.add(
        _ContextChip(
          icon: Icons.stacked_line_chart_rounded,
          label: '$value / $target',
        ),
      );
    }

    return chips;
  }

  Map<String, dynamic> _asStringMap(Object? value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) {
      return Map<String, dynamic>.from(value);
    }
    return const <String, dynamic>{};
  }

  String? _cleanSnapshotText(Object? value) {
    final text = value?.toString().trim();
    if (text == null || text.isEmpty || text == 'null') return null;
    return text;
  }

  int? _asInt(Object? value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '');
  }

  bool _hasEventWindow(AchievementModel achievement) =>
      achievement.isLimited ||
      achievement.activeFrom != null ||
      achievement.activeTo != null ||
      achievement.eventTag != null;

  Widget _buildEventWindow(
    AchievementModel achievement,
    AppLocalizations l10n,
  ) {
    final now = DateTime.now();
    final start = achievement.activeFrom?.toLocal();
    final end = achievement.activeTo?.toLocal();

    String statusLabel;
    Color statusColor;
    String windowText;

    if (start != null && now.isBefore(start)) {
      statusLabel = l10n.achievementEventStatusUpcoming;
      statusColor = DS.semanticWarning;
      windowText = l10n.achievementEventStartsAt(
        Formatters.formatDateTime(start),
      );
    } else if (end != null && now.isAfter(end)) {
      statusLabel = l10n.achievementEventStatusEnded;
      statusColor = DS.textTertiary;
      windowText = l10n.achievementEventEnded;
    } else {
      statusLabel = l10n.achievementEventStatusLive;
      statusColor = DS.semanticSuccess;
      if (end != null) {
        windowText = l10n.achievementEventEndsAt(
          Formatters.formatDateTime(end),
        );
      } else if (start != null) {
        windowText = l10n.achievementEventStartsAt(
          Formatters.formatDateTime(start),
        );
      } else {
        windowText = l10n.achievementLimitedSubtitle;
      }
    }

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.surfaceSecondary,
            Color.alphaBlend(
              statusColor.withValues(alpha: 0.04),
              DS.surfacePrimary,
            ),
          ],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadiusFull,
                ),
                child: Text(
                  statusLabel,
                  style: TextStyle(
                    fontSize: DS.fontSizeXs,
                    color: statusColor,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              if (achievement.eventTag != null) ...[
                const SizedBox(width: DS.spacing8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing8,
                    vertical: DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.brandPrimary.withValues(alpha: 0.12),
                    borderRadius: DS.borderRadiusFull,
                  ),
                  child: Text(
                    achievement.eventTag!,
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.brandPrimary,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            windowText,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressCard(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) {
    final userProgress = achievement.userProgress;
    final progress = achievement.progressPercentage / 100;
    final rarityColor =
        RarityColorProvider.getColor(achievement.achievement.rarity);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.surfaceSecondary,
            Color.alphaBlend(
              rarityColor.withValues(alpha: 0.04),
              DS.surfacePrimary,
            ),
          ],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Animated percentage text that counts up
          TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0.0, end: progress),
            duration: const Duration(milliseconds: 800),
            curve: Curves.easeOutCubic,
            builder: (context, animatedProgress, child) {
              final displayPercent =
                  (animatedProgress * 100).round().clamp(0, 100);
              return Wrap(
                alignment: WrapAlignment.spaceBetween,
                runSpacing: DS.spacing8,
                children: [
                  Text(
                    l10n.completionProgress,
                    style: TextStyle(
                      fontSize: DS.fontSizeBase,
                      fontWeight: DS.fontWeightSemibold,
                      color: DS.textPrimary,
                    ),
                  ),
                  Text(
                    '$displayPercent%',
                    style: TextStyle(
                      fontSize: DS.fontSizeLg,
                      fontWeight: DS.fontWeightBold,
                      color: rarityColor,
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: DS.spacing12),
          // Animated progress bar
          TweenAnimationBuilder<double>(
            tween: Tween<double>(begin: 0.0, end: progress.clamp(0.0, 1.0)),
            duration: const Duration(milliseconds: 800),
            curve: Curves.easeOutCubic,
            builder: (context, animatedProgress, child) => Container(
              height: 12,
              decoration: BoxDecoration(
                color: DS.neutral200,
                borderRadius: DS.borderRadiusFull,
              ),
              child: Stack(
                children: [
                  FractionallySizedBox(
                    alignment: Alignment.centerLeft,
                    widthFactor: animatedProgress,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [
                            rarityColor,
                            rarityColor.withValues(alpha: 0.7),
                          ],
                        ),
                        borderRadius: DS.borderRadiusFull,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: DS.spacing12),
          if (userProgress != null)
            Wrap(
              alignment: WrapAlignment.spaceBetween,
              runSpacing: DS.spacing4,
              children: [
                Text(
                  '${userProgress.progressValue}',
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    color: DS.textSecondary,
                  ),
                ),
                Text(
                  '/ ${userProgress.progressTarget}',
                  style: TextStyle(
                    fontSize: DS.fontSizeSm,
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }

  Widget _buildPrerequisites(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) {
    final prerequisites = achievement.achievement.prerequisites ?? [];
    final state = ref.watch(achievementProvider);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            DS.surfaceSecondary,
            Color.alphaBlend(
              DS.info.withValues(alpha: 0.025),
              DS.surfacePrimary,
            ),
          ],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border.withValues(alpha: 0.55)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l10n.achievementPrerequisitesHint,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          ...prerequisites.map((id) {
            final prereq = state.achievements
                .where((a) => a.achievement.id == id)
                .firstOrNull;
            if (prereq == null) return const SizedBox.shrink();

            return Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: Row(
                children: [
                  Icon(
                    prereq.isUnlocked
                        ? Icons.check_circle
                        : Icons.radio_button_unchecked,
                    size: DS.iconSizeSm,
                    color: prereq.isUnlocked
                        ? DS.semanticSuccess
                        : DS.textTertiary,
                  ),
                  const SizedBox(width: DS.spacing12),
                  Expanded(
                    child: Text(
                      prereq.achievement.name,
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        color: prereq.isUnlocked
                            ? DS.textPrimary
                            : DS.textTertiary,
                        decoration: prereq.isUnlocked
                            ? null
                            : TextDecoration.lineThrough,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildRewards(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) {
    final rewards = achievement.achievement.rewardConfig ?? [];
    _ensureVisualElementsLoaded(rewards);
    final titles = ref.watch(titlesProvider);
    final skins = ref.watch(galaxySkinsProvider);

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            DS.semanticSuccess.withValues(alpha: 0.1),
            DS.semanticSuccess.withValues(alpha: 0.05),
          ],
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: DS.semanticSuccess.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.card_giftcard,
                color: DS.semanticSuccess,
                size: DS.iconSizeSm,
              ),
              const SizedBox(width: DS.spacing8),
              Text(
                l10n.achievementUnlockRewards,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.semanticSuccess,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          ...rewards.map(
            (reward) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: _buildRewardItem(
                reward,
                l10n,
                achievement,
                titles,
                skins,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRewardItem(
    Map<String, dynamic> reward,
    AppLocalizations l10n,
    AchievementWithProgress achievement,
    List<UserTitle> titles,
    List<GalaxySkin> skins,
  ) {
    final type = reward['type'] as String? ?? 'unknown';
    final rawAmount = reward['amount'] ?? reward['quantity'] ?? 0;
    final amount = rawAmount is num ? rawAmount.toInt() : 0;
    final displayName =
        reward['name'] as String? ?? reward['display'] as String?;

    String icon;
    String label;

    switch (type) {
      case 'photon':
      case 'photons':
        icon = '💎';
        label = l10n.achievementRewardPhotons(amount);
      case 'title':
        icon = '🏅';
        label = displayName ?? l10n.achievementRewardTitle;
      case 'galaxy_skin':
      case 'skin':
        icon = '🎨';
        label = displayName ?? l10n.achievementRewardSkin;
      case 'xp':
        icon = '⭐';
        label = l10n.achievementRewardXp(amount);
      case 'freeze_charge':
        icon = '🧊';
        label = amount > 0
            ? '${l10n.streakFreezeCharges} x$amount'
            : l10n.streakFreezeCharges;
      case 'visual_element':
        icon = '✨';
        label = displayName ?? l10n.achievementRewardVisualElement;
      default:
        icon = '🎁';
        label = l10n.achievementRewardMystery;
    }

    final action = _buildRewardAction(
      type,
      reward,
      achievement,
      l10n,
      titles,
      skins,
    );

    return Row(
      children: [
        Text(icon, style: const TextStyle(fontSize: 20)),
        const SizedBox(width: DS.spacing12),
        Expanded(
          child: Text(
            label,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textPrimary,
            ),
          ),
        ),
        if (action != null) ...[
          const SizedBox(width: DS.spacing8),
          action,
        ],
      ],
    );
  }

  void _ensureVisualElementsLoaded(List<Map<String, dynamic>> rewards) {
    if (_requestedVisualElements) return;
    final hasVisualElement = rewards.any(
      (reward) => reward['type'] == 'visual_element',
    );
    if (hasVisualElement) {
      _requestedVisualElements = true;
      unawaited(ref.read(visualElementsNotifierProvider.notifier).loadAll());
    }
  }

  Widget? _buildRewardAction(
    String type,
    Map<String, dynamic> reward,
    AchievementWithProgress achievement,
    AppLocalizations l10n,
    List<UserTitle> titles,
    List<GalaxySkin> skins,
  ) {
    final isUnlocked = achievement.isUnlocked;

    if (!isUnlocked) {
      return Text(
        l10n.achievementUnlockToEquip,
        style: TextStyle(
          fontSize: DS.fontSizeXs,
          color: DS.textTertiary,
        ),
      );
    }

    switch (type) {
      case 'title':
        final titleId =
            reward['value']?.toString() ?? reward['title_id']?.toString();
        if (titleId == null) return null;
        final isEquipped =
            titles.any((title) => title.titleId == titleId && title.isEquipped);
        return _buildEquipAction(
          l10n,
          isEquipped: isEquipped,
          onEquip: () => _equipTitle(titleId),
        );
      case 'galaxy_skin':
      case 'skin':
        final skinId =
            reward['skin_id']?.toString() ?? reward['id']?.toString();
        if (skinId == null) return null;
        final isEquipped =
            skins.any((skin) => skin.id == skinId && skin.isEquipped);
        return _buildEquipAction(
          l10n,
          isEquipped: isEquipped,
          onEquip: () => _equipSkin(skinId),
        );
      case 'visual_element':
        final elementId =
            reward['element_id']?.toString() ?? reward['id']?.toString();
        if (elementId == null) return null;
        final isEquipped = ref.watch(isElementEquippedProvider(elementId));
        return _buildEquipAction(
          l10n,
          isEquipped: isEquipped,
          onEquip: () => _equipVisualElement(elementId),
        );
      default:
        return null;
    }
  }

  Widget _buildEquipAction(
    AppLocalizations l10n, {
    required bool isEquipped,
    required VoidCallback onEquip,
  }) {
    if (isEquipped) {
      return Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.semanticSuccess.withValues(alpha: 0.15),
          borderRadius: DS.borderRadiusFull,
        ),
        child: Text(
          l10n.achievementEquipped,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.semanticSuccess,
            fontWeight: DS.fontWeightSemibold,
          ),
        ),
      );
    }

    return SparkleButton(
      label: l10n.achievementEquipAction,
      onPressed: onEquip,
      variant: ButtonVariant.outline,
      size: ButtonSize.small,
    );
  }

  Future<void> _equipTitle(String titleId) async {
    await ref.read(achievementProvider.notifier).equipTitle(titleId);
  }

  Future<void> _equipSkin(String skinId) async {
    await ref.read(achievementProvider.notifier).equipSkin(skinId);
  }

  Future<void> _equipVisualElement(String elementId) async {
    await ref
        .read(visualElementsNotifierProvider.notifier)
        .equipElement(elementId);
  }

  Widget _buildStats(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) {
    final userProgress = achievement.userProgress;

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildStatRow(
            l10n.achievementStatType,
            _getTypeName(achievement.achievement.type, l10n),
          ),
          _buildStatRow(
            l10n.achievementRarity,
            _getRarityName(achievement.achievement.rarity, l10n),
          ),
          if (achievement.achievement.category != null)
            _buildStatRow(
              l10n.achievementCategory,
              _getCategoryLocalizedName(
                achievement.achievement.category!,
                l10n,
              ),
            ),
          if (userProgress?.unlockedAt != null)
            _buildStatRow(
              l10n.achievementUnlockedAt,
              _formatDate(userProgress!.unlockedAt!),
            ),
          if (userProgress?.shareCount != null && userProgress!.shareCount > 0)
            _buildStatRow(
              l10n.achievementShareCount,
              '${userProgress.shareCount}',
            ),
          if (userProgress?.isFirstUnlocker ?? false)
            _buildStatRow(
              l10n.achievementUnlockRank,
              l10n.achievementFirstUnlocker,
              highlight: true,
            ),
        ],
      ),
    );
  }

  Widget _buildStatRow(String label, String value, {bool highlight = false}) =>
      Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing6),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: DS.fontSizeSm,
                color: DS.textSecondary,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Text(
                value,
                textAlign: TextAlign.right,
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight:
                      highlight ? DS.fontWeightBold : DS.fontWeightMedium,
                  color: highlight ? DS.semanticWarning : DS.textPrimary,
                ),
              ),
            ),
          ],
        ),
      );

  Widget _buildNotFoundView(AppLocalizations l10n) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: DS.semanticError,
            ),
            const SizedBox(height: DS.spacing16),
            Text(
              l10n.achievementNotFound,
              style: const TextStyle(
                fontSize: DS.fontSizeLg,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ],
        ),
      );

  IconData _getIconForAchievement(AchievementWithProgress achievement) {
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

  String _getTypeName(AchievementType type, AppLocalizations l10n) {
    switch (type) {
      case AchievementType.streak:
        return l10n.achievementTypeStreak;
      case AchievementType.mastery:
        return l10n.achievementTypeMastery;
      case AchievementType.taskComplete:
        return l10n.achievementTypeTaskComplete;
      case AchievementType.nodeExplore:
        return l10n.achievementTypeNodeExplore;
      case AchievementType.studyTime:
        return l10n.achievementTypeStudyTime;
      case AchievementType.hidden:
        return l10n.achievementTypeHidden;
      case AchievementType.milestone:
        return l10n.achievementTypeMilestone;
      case AchievementType.social:
        return l10n.achievementTypeSocial;
      case AchievementType.contract:
        return l10n.achievementTypeContract;
      case AchievementType.sprint:
        return l10n.achievementTypeSprint;
    }
  }

  String _getRarityName(AchievementRarity rarity, AppLocalizations l10n) {
    switch (rarity) {
      case AchievementRarity.common:
        return l10n.achievementRarityCommon;
      case AchievementRarity.rare:
        return l10n.achievementRarityRare;
      case AchievementRarity.epic:
        return l10n.achievementRarityEpic;
      case AchievementRarity.legendary:
        return l10n.achievementRarityLegendary;
    }
  }

  String _getCategoryLocalizedName(String category, AppLocalizations l10n) {
    switch (category) {
      case 'milestone':
        return l10n.achievementCategoryMilestone;
      case 'streak':
        return l10n.achievementCategoryStreak;
      case 'mastery':
        return l10n.achievementCategoryMastery;
      case 'exploration':
      case 'node_explore':
        return l10n.achievementCategoryExploration;
      case 'tasks':
      case 'task':
      case 'task_complete':
        return l10n.achievementCategoryTask;
      case 'study_time':
        return l10n.achievementTypeStudyTime;
      case 'sprint':
        return l10n.achievementTypeSprint;
      case 'hidden':
        return l10n.achievementTypeHidden;
      default:
        return category;
    }
  }

  String _formatDate(DateTime date) => Formatters.formatDateMedium(date);

  void _togglePin(AchievementWithProgress achievement) {
    final isPinned = achievement.userProgress?.isPinned ?? false;
    unawaited(
      ref
          .read(achievementProvider.notifier)
          .pinAchievement(achievement.achievement.id, !isPinned),
    );
  }

  void _shareAchievement(AchievementWithProgress achievement) {
    if (!achievement.isUnlocked) {
      AppFeedback.info(context, context.l10n.achievementShareLocked);
      return;
    }

    showAchievementShareSheet(
      context,
      achievementId: achievement.achievement.id,
      achievementName: achievement.achievement.name,
    );
  }
}

class _ContextChip extends StatelessWidget {
  const _ContextChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 320),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfacePrimary.withValues(alpha: 0.72),
          borderRadius: DS.borderRadiusFull,
          border: Border.all(color: DS.border.withValues(alpha: 0.55)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: DS.textSecondary,
            ),
            const SizedBox(width: DS.spacing6),
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textSecondary,
                  fontWeight: DS.fontWeightMedium,
                ),
              ),
            ),
          ],
        ),
      );
}

/// Staggered entrance animation wrapper for content sections.
/// Each section fades + slides in with a stagger delay based on its index.
class _AnimatedSection extends StatelessWidget {
  const _AnimatedSection({
    required this.index,
    required this.child,
  });

  final int index;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final delayMs = index * 80;
    final totalDurationMs = delayMs + 400;

    return TweenAnimationBuilder<double>(
      tween: Tween<double>(begin: 0.0, end: 1.0),
      duration: Duration(milliseconds: totalDurationMs),
      builder: (context, rawValue, _) {
        // Map the raw linear 0..1 to account for the stagger delay.
        // During the delay portion, progress stays at 0.
        // After the delay, progress eases from 0 to 1 over 400ms.
        final delayFraction =
            totalDurationMs > 0 ? delayMs / totalDurationMs : 0.0;
        double progress;
        if (rawValue <= delayFraction) {
          progress = 0.0;
        } else {
          final localT = (rawValue - delayFraction) / (1.0 - delayFraction);
          // Apply easeOutCubic curve
          progress = 1.0 - math.pow(1.0 - localT, 3).toDouble();
        }

        return Opacity(
          opacity: progress.clamp(0.0, 1.0),
          child: Transform.translate(
            offset: Offset(0, 20 * (1.0 - progress)),
            child: child,
          ),
        );
      },
    );
  }
}

/// Animated header particle painter.
/// Particles orbit gently and twinkle based on the animation value.
/// Particle count scales by rarity: rare=15, epic=25, legendary=40.
class _HeaderParticlePainter extends CustomPainter {
  _HeaderParticlePainter(
    this.rarity, {
    required this.animationValue,
  });

  final AchievementRarity rarity;
  final double animationValue;

  int get _particleCount {
    switch (rarity) {
      case AchievementRarity.common:
        return 10;
      case AchievementRarity.rare:
        return 15;
      case AchievementRarity.epic:
        return 25;
      case AchievementRarity.legendary:
        return 40;
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    final color = RarityColorProvider.getColor(rarity);
    final random = math.Random(42);

    for (var i = 0; i < _particleCount; i++) {
      // Base position from deterministic random
      final baseX = random.nextDouble() * size.width;
      final baseY = random.nextDouble() * size.height;
      final baseRadius = 1.0 + random.nextDouble() * 3.0;

      // Each particle gets a unique phase offset
      final phase = random.nextDouble() * 2 * math.pi;
      final orbitRadius = 3.0 + random.nextDouble() * 8.0;
      final speed = 0.5 + random.nextDouble() * 1.5;

      // Gentle orbit using sin/cos
      final angle = animationValue * 2 * math.pi * speed + phase;
      final x = baseX + math.cos(angle) * orbitRadius;
      final y = baseY + math.sin(angle) * orbitRadius;

      // Twinkle effect: vary opacity with sin
      final twinklePhase = random.nextDouble() * 2 * math.pi;
      final twinkle = 0.2 +
          0.6 *
              ((math.sin(animationValue * 2 * math.pi * 2 + twinklePhase) + 1) /
                  2);

      // Outer glow
      final glowPaint = Paint()
        ..color = color.withValues(alpha: twinkle * 0.15)
        ..style = PaintingStyle.fill
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4);
      canvas.drawCircle(Offset(x, y), baseRadius * 2.5, glowPaint);

      // Core particle
      final paint = Paint()
        ..color = color.withValues(alpha: twinkle)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(Offset(x, y), baseRadius, paint);
    }
  }

  @override
  bool shouldRepaint(_HeaderParticlePainter oldDelegate) =>
      oldDelegate.rarity != rarity ||
      oldDelegate.animationValue != animationValue;
}

/// Slow-rotating radial gradient overlay for epic+ rarity.
/// Creates a subtle "energy field" effect behind the header icon.
class _EnergyFieldPainter extends CustomPainter {
  _EnergyFieldPainter({
    required this.color,
    required this.rotation,
  });

  final Color color;
  final double rotation;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.shortestSide * 0.45;

    canvas.save();
    canvas.translate(center.dx, center.dy);
    canvas.rotate(rotation);
    canvas.translate(-center.dx, -center.dy);

    // Draw a swept gradient that rotates slowly
    final sweepGradient = SweepGradient(
      colors: [
        color.withValues(alpha: 0.0),
        color.withValues(alpha: 0.08),
        color.withValues(alpha: 0.0),
        color.withValues(alpha: 0.06),
        color.withValues(alpha: 0.0),
      ],
      stops: const [0.0, 0.25, 0.5, 0.75, 1.0],
    );

    final rect = Rect.fromCircle(center: center, radius: radius);
    final paint = Paint()
      ..shader = sweepGradient.createShader(rect)
      ..style = PaintingStyle.fill;

    canvas.drawCircle(center, radius, paint);
    canvas.restore();
  }

  @override
  bool shouldRepaint(_EnergyFieldPainter oldDelegate) =>
      oldDelegate.color != color || oldDelegate.rotation != rotation;
}
