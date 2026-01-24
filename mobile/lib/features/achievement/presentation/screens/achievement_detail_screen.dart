import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/presentation/widgets/achievement_card.dart';
import 'package:sparkle/features/achievement/presentation/widgets/rarity_badge.dart';
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
    _controller.repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(achievementProvider);

    if (state.isLoading) {
      return Scaffold(
        appBar: AppBar(),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final achievement = state.achievements
        .where((a) => a.achievement.id == widget.achievementId)
        .firstOrNull;

    if (achievement == null) {
      return Scaffold(
        appBar: AppBar(),
        body: _buildNotFoundView(),
      );
    }

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          // 自定义顶部
          _buildHeader(context, achievement),

          // 内容区域
          SliverToBoxAdapter(
            child: _buildContent(achievement),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(BuildContext context, AchievementWithProgress achievement) {
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
        child: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      actions: [
        Container(
          margin: const EdgeInsets.all(DS.spacing8),
          decoration: BoxDecoration(
            color: DS.surfacePrimary.withValues(alpha: 0.9),
            shape: BoxShape.circle,
          ),
          child: IconButton(
            icon: const Icon(Icons.share_outlined),
            onPressed: () => _shareAchievement(achievement),
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
        color: achievement.isUnlocked ? Colors.white : DS.neutral600,
        size: 50,
      ),
    );
  }

  Widget _buildContent(AchievementWithProgress achievement) => Container(
      padding: const EdgeInsets.all(DS.spacing20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 名称和解锁状态
          _buildTitleSection(achievement),
          const SizedBox(height: DS.spacing24),

          // 描述
          if (achievement.achievement.description != null) ...[
            _buildSectionTitle('描述'),
            const SizedBox(height: DS.spacing8),
            _buildDescription(achievement),
            const SizedBox(height: DS.spacing24),
          ],

          // 进度（未解锁时）
          if (!achievement.isUnlocked) ...[
            _buildSectionTitle('进度'),
            const SizedBox(height: DS.spacing12),
            _buildProgressCard(achievement),
            const SizedBox(height: DS.spacing24),
          ],

          // 前置成就
          if (achievement.achievement.prerequisites?.isNotEmpty ?? false) ...[
            _buildSectionTitle('前置成就'),
            const SizedBox(height: DS.spacing12),
            _buildPrerequisites(achievement),
            const SizedBox(height: DS.spacing24),
          ],

          // 奖励
          if (achievement.achievement.rewardConfig?.isNotEmpty ?? false) ...[
            _buildSectionTitle('奖励'),
            const SizedBox(height: DS.spacing12),
            _buildRewards(achievement),
            const SizedBox(height: DS.spacing24),
          ],

          // 统计信息
          _buildStats(achievement),

          const SizedBox(height: DS.spacing40),
        ],
      ),
    );

  Widget _buildTitleSection(AchievementWithProgress achievement) => Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                achievement.achievement.name,
                style: TextStyle(
                  fontSize: DS.fontSize2xl,
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
              const SizedBox(height: DS.spacing8),
              Row(
                children: [
                  if (achievement.isUnlocked) ...[
                    Icon(
                      Icons.check_circle,
                      size: DS.iconSizeSm,
                      color: DS.semanticSuccess,
                    ),
                    const SizedBox(width: DS.spacing6),
                    Text(
                      '已解锁',
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
                    const SizedBox(width: DS.spacing6),
                    Text(
                      '未解锁',
                      style: TextStyle(
                        fontSize: DS.fontSizeSm,
                        color: DS.textTertiary,
                      ),
                    ),
                  ],
                  const SizedBox(width: DS.spacing12),
                  Text(
                    _getTypeName(achievement.achievement.type),
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
        // 置顶按钮
        IconButton(
          icon: Icon(
            achievement.userProgress?.isPinned ?? false
                ? Icons.push_pin
                : Icons.push_pin_outlined,
            color: (achievement.userProgress?.isPinned ?? false)
                ? DS.semanticWarning
                : DS.textSecondary,
          ),
          onPressed: () => _togglePin(achievement),
        ),
      ],
    );

  Widget _buildSectionTitle(String title) => Text(
      title,
      style: TextStyle(
        fontSize: DS.fontSizeBase,
        fontWeight: DS.fontWeightBold,
        color: DS.textPrimary,
      ),
    );

  Widget _buildDescription(AchievementWithProgress achievement) => Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.border),
      ),
      child: Text(
        achievement.achievement.description ?? '暂无描述',
        style: TextStyle(
          fontSize: DS.fontSizeBase,
          color: DS.textPrimary,
          height: 1.5,
        ),
      ),
    );

  Widget _buildProgressCard(AchievementWithProgress achievement) {
    final userProgress = achievement.userProgress;
    final progress = achievement.progressPercentage / 100;
    final rarityColor = RarityColorProvider.getColor(achievement.achievement.rarity);

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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '完成进度',
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
                        colors: [rarityColor, rarityColor.withValues(alpha: 0.7)],
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
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
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

  Widget _buildPrerequisites(AchievementWithProgress achievement) {
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
            '需要先完成以下成就：',
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

  Widget _buildRewards(AchievementWithProgress achievement) {
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
                '解锁奖励',
                style: TextStyle(
                  fontSize: DS.fontSizeSm,
                  fontWeight: DS.fontWeightSemibold,
                  color: DS.semanticSuccess,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          ...rewards.map((reward) => Padding(
              padding: const EdgeInsets.only(bottom: DS.spacing8),
              child: _buildRewardItem(reward),
            )),
        ],
      ),
    );
  }

  Widget _buildRewardItem(Map<String, dynamic> reward) {
    final type = reward['type'] as String? ?? 'unknown';
    final amount = reward['amount'] as int? ?? 0;

    String icon;
    String label;

    switch (type) {
      case 'photons':
        icon = '💎';
        label = '$amount 光子';
      case 'title':
        icon = '🏅';
        label = reward['name'] as String? ?? '称号';
      case 'skin':
        icon = '🎨';
        label = reward['name'] as String? ?? '星系皮肤';
      case 'xp':
        icon = '⭐';
        label = '$amount 经验';
      default:
        icon = '🎁';
        label = '神秘奖励';
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

  Widget _buildStats(AchievementWithProgress achievement) {
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
            '类型',
            _getTypeName(achievement.achievement.type),
          ),
          _buildStatRow(
            '稀有度',
            _getRarityName(achievement.achievement.rarity),
          ),
          if (achievement.achievement.category != null)
            _buildStatRow(
              '分类',
              achievement.achievement.category!,
            ),
          if (userProgress?.unlockedAt != null)
            _buildStatRow(
              '解锁时间',
              _formatDate(userProgress!.unlockedAt!),
            ),
          if (userProgress?.shareCount != null && userProgress!.shareCount > 0)
            _buildStatRow(
              '分享次数',
              '${userProgress.shareCount}',
            ),
          if (userProgress?.isFirstUnlocker ?? false)
            _buildStatRow(
              '解锁排名',
              '首位解锁者',
              highlight: true,
            ),
        ],
      ),
    );
  }

  Widget _buildStatRow(String label, String value, {bool highlight = false}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: DS.spacing6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              color: DS.textSecondary,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: DS.fontSizeSm,
              fontWeight: highlight ? DS.fontWeightBold : DS.fontWeightMedium,
              color: highlight ? DS.semanticWarning : DS.textPrimary,
            ),
          ),
        ],
      ),
    );

  Widget _buildNotFoundView() => Center(
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
            '成就未找到',
            style: TextStyle(
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
    }
  }

  String _getTypeName(AchievementType type) {
    switch (type) {
      case AchievementType.streak:
        return '连胜';
      case AchievementType.mastery:
        return '精通';
      case AchievementType.taskComplete:
        return '任务';
      case AchievementType.nodeExplore:
        return '探索';
      case AchievementType.studyTime:
        return '学习';
      case AchievementType.hidden:
        return '隐藏';
      case AchievementType.milestone:
        return '里程碑';
      case AchievementType.social:
        return '社交';
      case AchievementType.contract:
        return '契约';
    }
  }

  String _getRarityName(AchievementRarity rarity) {
    switch (rarity) {
      case AchievementRarity.common:
        return '普通';
      case AchievementRarity.rare:
        return '稀有';
      case AchievementRarity.epic:
        return '史诗';
      case AchievementRarity.legendary:
        return '传说';
    }
  }

  String _formatDate(DateTime date) => '${date.year}年${date.month}月${date.day}日';

  void _togglePin(AchievementWithProgress achievement) {
    final isPinned = achievement.userProgress?.isPinned ?? false;
    ref
        .read(achievementProvider.notifier)
        .pinAchievement(achievement.achievement.id, !isPinned);
  }

  void _shareAchievement(AchievementWithProgress achievement) {
    // TODO: 实现分享功能
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('分享功能开发中'),
        duration: Duration(seconds: 2),
      ),
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
