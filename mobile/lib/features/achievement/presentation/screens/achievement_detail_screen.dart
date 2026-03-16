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
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _glowAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );
    unawaited(_controller.repeat(reverse: true));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
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
      backgroundColor: rarityColor.withValues(alpha: 0.1),
      flexibleSpace: FlexibleSpaceBar(
        background: Stack(
          fit: StackFit.expand,
          children: [
            // 背景渐变
            _buildHeaderBackground(rarityColor),

            // 粒子效果（仅稀有+成就）
            if (rarity.index >= AchievementRarity.rare.index)
              _buildHeaderParticles(rarity),

            // 中心内容
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  AnimatedBuilder(
                    animation: _glowAnimation,
                    builder: (context, child) => Transform.scale(
                      scale: _glowAnimation.value,
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
              rarityColor.withValues(alpha: 0.3),
              rarityColor.withValues(alpha: 0.05),
              DS.surfacePrimary,
            ],
          ),
        ),
      );

  Widget _buildHeaderParticles(AchievementRarity rarity) => CustomPaint(
        painter: _HeaderParticlePainter(rarity),
        size: Size.infinite,
      );

  Widget _buildLargeIcon(AchievementWithProgress achievement) {
    final rarity = achievement.achievement.rarity;
    final rarityColor = RarityColorProvider.getColor(rarity);

    return Container(
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
                  color: rarityColor.withValues(alpha: 0.5),
                  blurRadius: 32,
                  spreadRadius: 8,
                ),
              ]
            : null,
      ),
      child: Icon(
        _getIconForAchievement(achievement),
        color: achievement.isUnlocked ? DS.textOnPrimary : DS.neutral600,
        size: 50,
      ),
    );
  }

  Widget _buildContent(
    AchievementWithProgress achievement,
    AppLocalizations l10n,
  ) =>
      Container(
        padding: const EdgeInsets.all(DS.spacing20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 名称和解锁状态
            _buildTitleSection(achievement, l10n),
            const SizedBox(height: DS.spacing24),

            // 描述
            if (achievement.achievement.description != null) ...[
              _buildSectionTitle(l10n.achievementDescription),
              const SizedBox(height: DS.spacing8),
              _buildDescription(achievement, l10n),
              const SizedBox(height: DS.spacing24),
            ],

            // 进度（未解锁时）
            if (!achievement.isUnlocked) ...[
              _buildSectionTitle(l10n.achievementProgress),
              const SizedBox(height: DS.spacing12),
              _buildProgressCard(achievement, l10n),
              const SizedBox(height: DS.spacing24),
            ],

            // 前置成就
            if (achievement.achievement.prerequisites?.isNotEmpty ?? false) ...[
              _buildSectionTitle(l10n.achievementPrerequisites),
              const SizedBox(height: DS.spacing12),
              _buildPrerequisites(achievement, l10n),
              const SizedBox(height: DS.spacing24),
            ],

            // 奖励
            if (achievement.achievement.rewardConfig?.isNotEmpty ?? false) ...[
              _buildSectionTitle(l10n.achievementRewards),
              const SizedBox(height: DS.spacing12),
              _buildRewards(achievement, l10n),
              const SizedBox(height: DS.spacing24),
            ],

            // 统计信息
            _buildStats(achievement, l10n),

            const SizedBox(height: DS.spacing40),
          ],
        ),
      );

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
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.border),
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
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
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
                '${achievement.progressPercentage}%',
                style: TextStyle(
                  fontSize: DS.fontSizeLg,
                  fontWeight: DS.fontWeightBold,
                  color: rarityColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Container(
            height: 12,
            decoration: BoxDecoration(
              color: DS.neutral200,
              borderRadius: DS.borderRadiusFull,
            ),
            child: Stack(
              children: [
                FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: progress.clamp(0.0, 1.0),
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
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border),
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
              child: _buildRewardItem(reward, l10n),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRewardItem(
    Map<String, dynamic> reward,
    AppLocalizations l10n,
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
      default:
        icon = '🎁';
        label = l10n.achievementRewardMystery;
    }

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
      ],
    );
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

/// 头部粒子效果绘制器
class _HeaderParticlePainter extends CustomPainter {
  _HeaderParticlePainter(this.rarity);

  final AchievementRarity rarity;

  @override
  void paint(Canvas canvas, Size size) {
    final color = RarityColorProvider.getColor(rarity);
    final random = math.Random(42);

    for (var i = 0; i < 20; i++) {
      final x = random.nextDouble() * size.width;
      final y = random.nextDouble() * size.height;
      final radius = 1 + random.nextDouble() * 3;

      final paint = Paint()
        ..color = color.withValues(alpha: 0.3)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(x, y), radius, paint);
    }
  }

  @override
  bool shouldRepaint(_HeaderParticlePainter oldDelegate) =>
      oldDelegate.rarity != rarity;
}
