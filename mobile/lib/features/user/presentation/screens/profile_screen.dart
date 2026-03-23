import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/achievement/achievement_routes.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/visual_elements/visual_elements_routes.dart';
import 'package:sparkle/features/user/presentation/widgets/statistics_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final achievementState = ref.watch(achievementProvider);
    final visualState = ref.watch(visualElementProvider);
    final l10n = AppLocalizations.of(context)!;
    final screenHeight = MediaQuery.of(context).size.height;
    final headerHeight = screenHeight < 720 ? 196.0 : 244.0;

    if (user == null) return const SizedBox.shrink();

    return GraphiteScaffold(
      role: SparklePageRole.settings,
      safeArea: false,
      child: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            _buildHeader(context, user, headerHeight: headerHeight),
            ContentConstraint(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
                child: Column(
                  children: [
                    const SizedBox(height: DS.spacing4),
                    const StatisticsCard(),
                    const SizedBox(height: DS.spacing20),
                    _buildPrestigeShowcase(
                      context,
                      achievementState,
                      visualState,
                    ),
                    const SizedBox(height: DS.spacing24),
                    _buildSettingsSection(context, ref, l10n, user),
                    const SizedBox(height: 100), // Bottom padding
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPrestigeShowcase(
    BuildContext context,
    AchievementState achievementState,
    VisualElementState visualState,
  ) {
    final unlockedAchievements = achievementState.achievements
        .where((item) => item.isUnlocked)
        .toList()
      ..sort((a, b) {
        final rarityCompare =
            b.achievement.rarity.index.compareTo(a.achievement.rarity.index);
        if (rarityCompare != 0) return rarityCompare;
        final aTime = a.userProgress?.unlockedAt;
        final bTime = b.userProgress?.unlockedAt;
        if (aTime == null || bTime == null) return 0;
        return bTime.compareTo(aTime);
      });

    final featured = unlockedAchievements.take(3).toList();
    final equippedTitle =
        achievementState.titles.where((title) => title.isEquipped).firstOrNull;
    final equippedBackground = visualState.config?.equippedBackground;
    final equippedEffect = visualState.config?.equippedEffect;
    final equippedParticle = visualState.config?.equippedParticle;
    final prestigeColor = equippedBackground != null
        ? _colorFromElement(equippedBackground)
        : DS.brandPrimary;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(DS.spacing18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Color.alphaBlend(
              prestigeColor.withValues(alpha: 0.12),
              DS.surfaceSecondary,
            ),
            DS.surfacePrimaryElevated,
          ],
        ),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: prestigeColor.withValues(alpha: 0.2)),
        boxShadow: [
          BoxShadow(
            color: prestigeColor.withValues(alpha: 0.08),
            blurRadius: 22,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.workspace_premium_rounded, color: prestigeColor),
              const SizedBox(width: DS.spacing8),
              Text(
                '荣耀身份',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: DS.fontWeightBold,
                          color: DS.textPrimary,
                        ) ??
                    TextStyle(
                      fontSize: DS.fontSizeBase,
                      fontWeight: DS.fontWeightBold,
                      color: DS.textPrimary,
                    ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: [
              _buildIdentityChip(
                label: equippedTitle?.titleDisplay ?? '未装备称号',
                color: prestigeColor,
              ),
              if (equippedBackground != null)
                _buildIdentityChip(
                  label: equippedBackground.prestigeLabel ??
                      equippedBackground.name,
                  color: _colorFromElement(equippedBackground),
                ),
              if (equippedEffect != null)
                _buildIdentityChip(
                  label: equippedEffect.prestigeLabel ?? equippedEffect.name,
                  color: _colorFromElement(equippedEffect),
                ),
              if (equippedParticle != null)
                _buildIdentityChip(
                  label:
                      equippedParticle.prestigeLabel ?? equippedParticle.name,
                  color: _colorFromElement(equippedParticle),
                ),
            ],
          ),
          const SizedBox(height: DS.spacing16),
          Text(
            '近期高光成就',
            style: DS.labelLarge.copyWith(
              fontWeight: DS.fontWeightSemibold,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(height: DS.spacing10),
          if (featured.isEmpty)
            Text(
              '继续完成学习与冲刺，你的荣耀陈列柜会在这里逐步点亮。',
              style: DS.bodySmall.copyWith(color: DS.textSecondary),
            )
          else
            ...featured.map(
              (item) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing8),
                child: Container(
                  padding: const EdgeInsets.all(DS.spacing12),
                  decoration: BoxDecoration(
                    color: Color.alphaBlend(
                      _rarityColor(item.achievement.rarity)
                          .withValues(alpha: 0.06),
                      DS.surfacePrimary.withValues(alpha: 0.9),
                    ),
                    borderRadius: DS.borderRadius16,
                    border: Border.all(
                      color: _rarityColor(item.achievement.rarity)
                          .withValues(alpha: 0.14),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.auto_awesome,
                        size: 16,
                        color: _rarityColor(item.achievement.rarity),
                      ),
                      const SizedBox(width: DS.spacing8),
                      Expanded(
                        child: Text(
                          item.achievement.name,
                          style: DS.bodySmall.copyWith(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightSemibold,
                          ),
                        ),
                      ),
                      Text(
                        _rarityLabel(item.achievement.rarity),
                        style: DS.labelSmall.copyWith(
                          color: _rarityColor(item.achievement.rarity),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildIdentityChip({
    required String label,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing10,
        vertical: DS.spacing6,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: DS.borderRadius12,
      ),
      child: Text(
        label,
        style: DS.labelSmall.copyWith(
          color: color,
          fontWeight: DS.fontWeightMedium,
        ),
      ),
    );
  }

  Color _colorFromElement(dynamic element) {
    final colors = (element.config['colors'] as List<dynamic>?) ??
        (element.config['gradient'] as List<dynamic>?);
    if (colors != null && colors.isNotEmpty) {
      final value = colors.first.toString().replaceFirst('#', '');
      final hex = value.length == 6 ? 'FF$value' : value;
      final parsed = int.tryParse(hex, radix: 16);
      if (parsed != null) {
        return Color(parsed);
      }
    }
    return DS.brandPrimary;
  }

  Color _rarityColor(dynamic rarity) {
    final key = rarity.toString().split('.').last;
    switch (key) {
      case 'legendary':
        return const Color(0xFFFFA726);
      case 'epic':
        return const Color(0xFFAB47BC);
      case 'rare':
        return const Color(0xFF42A5F5);
      default:
        return const Color(0xFFB0BEC5);
    }
  }

  String _rarityLabel(dynamic rarity) {
    final key = rarity.toString().split('.').last;
    switch (key) {
      case 'legendary':
        return '传奇';
      case 'epic':
        return '史诗';
      case 'rare':
        return '稀有';
      default:
        return '普通';
    }
  }

  Widget _buildHeader(
    BuildContext context,
    UserModel user, {
    required double headerHeight,
  }) {
    final l10n = AppLocalizations.of(context)!;

    return SizedBox(
      height: headerHeight,
      child: Stack(
        children: [
          // Wave Background
          Positioned.fill(
            child: CustomPaint(
              painter: _WaveHeaderPainter(
                startColor: Color.lerp(
                  DS.surfacePrimaryElevated,
                  DS.brandPrimary,
                  0.04,
                )!,
                middleColor:
                    Color.lerp(DS.surfaceCanvas, DS.surfaceSecondary, 0.54)!,
                endColor:
                    Color.lerp(DS.surfaceCanvas, DS.brandSecondary, 0.06)!,
              ),
            ),
          ),
          // Content
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(DS.spacing24),
              child: Column(
                children: [
                  const SizedBox(height: DS.spacing6),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // Avatar Area
                      DecoratedBox(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: DS.borderStrong,
                            width: 3,
                          ),
                          boxShadow: DS.shadowMd,
                        ),
                        child: SparkleAvatar(
                          radius: 40,
                          backgroundColor: DS.avatarFallbackBackground,
                          url: user.avatarStatus == AvatarStatus.pending
                              ? (user.pendingAvatarUrl ?? user.avatarUrl)
                              : user.avatarUrl,
                          fallbackText: user.nickname ?? user.username,
                          status: user.avatarStatus,
                        ),
                      ),
                      const SizedBox(width: DS.spacing20),
                      // Info Area
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user.nickname ?? user.username,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.sm),
                            Wrap(
                              spacing: DS.spacing8,
                              runSpacing: DS.spacing8,
                              children: [
                                _buildHeaderPill(
                                  icon: Icons.local_fire_department_rounded,
                                  label:
                                      '${l10n.levelPrefix}${user.flameLevel}',
                                  accent: DS.brandPrimaryConst,
                                ),
                                _buildHeaderPill(
                                  icon: Icons.bolt_rounded,
                                  label:
                                      '${l10n.brightness} ${(user.flameBrightness * 100).toInt()}%',
                                  accent: DS.info,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderPill({
    required IconData icon,
    required String label,
    required Color accent,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: Color.alphaBlend(
            accent.withValues(alpha: 0.1),
            DS.surfaceOverlay,
          ),
          borderRadius: DS.borderRadius20,
          border: Border.all(
            color: accent.withValues(alpha: 0.14),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: accent, size: 16),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: DS.labelSmall.copyWith(
                color: DS.textPrimary,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ],
        ),
      );

  Widget _buildSettingsSection(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
    UserModel user,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Guest upgrade (conditional)
          if (user.registrationSource == 'guest') ...[
            GraphiteCardSurface(
              child: _buildSettingsTile(
                context,
                icon: Icons.upgrade_rounded,
                title: l10n.profileUpgradeGuest,
                accentColor: const Color(0xFFC37D3A),
                onTap: () => context.push(UserRoutes.guestUpgrade),
              ),
            ),
            const SizedBox(height: DS.spacing16),
          ],

          // Personal Growth
          _buildSectionLabel(context, l10n.personalGrowth),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.emoji_events_outlined,
                  title: l10n.achievementTitle,
                  accentColor: const Color(0xFFFFD700),
                  onTap: () => context.push(AchievementRoutes.basePath),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.photo_library_outlined,
                  title: '海报工坊',
                  subtitle: '把成长、计划与灵感做成高质感分享海报',
                  accentColor: const Color(0xFF6E8EF7),
                  onTap: () => context.push(UserRoutes.posterStudio),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.palette_outlined,
                  title: l10n.visualElementsTitle,
                  accentColor: const Color(0xFF7B68EE),
                  onTap: () => context.push(VisualElementsRoutes.basePath),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.psychology_alt_outlined,
                  title: l10n.myPersona,
                  accentColor: const Color(0xFF8877A6),
                  onTap: () => context.push(UserRoutes.persona),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // Settings
          _buildSectionLabel(context, l10n.settings),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.person_outline_rounded,
                  title: l10n.profilePersonalInfo,
                  accentColor: const Color(0xFF9B7A72),
                  onTap: () => context.push(UserRoutes.editProfile),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.tune_rounded,
                  title: l10n.schedulePreferences,
                  accentColor: const Color(0xFF7087A6),
                  onTap: () => context.push(UserRoutes.settings),
                ),
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // Account
          _buildSectionLabel(context, l10n.account),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.manage_accounts_outlined,
                  title: l10n.accountSecurity,
                  accentColor: const Color(0xFF6E8FAE),
                  onTap: () => context.push(UserRoutes.accountSecurity),
                ),
                if (AppFeatureFlags.enableUserMemoryControls) ...[
                  const Divider(height: 1, indent: 60),
                  _buildSettingsTile(
                    context,
                    icon: Icons.memory_rounded,
                    title: l10n.memoryControl,
                    accentColor: const Color(0xFF6D9282),
                    onTap: () => context.push(UserRoutes.memorySettings),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: DS.spacing16),

          // Sign Out
          _buildSectionLabel(context, l10n.logout),
          const SizedBox(height: DS.spacing8),
          GraphiteCardSurface(
            child: Column(
              children: [
                _buildSettingsTile(
                  context,
                  icon: Icons.logout_rounded,
                  title: l10n.logout,
                  accentColor: const Color(0xFFB06F67),
                  isDestructive: true,
                  onTap: () => _showLogoutDialog(context, ref, l10n),
                ),
                const Divider(height: 1, indent: 60),
                _buildSettingsTile(
                  context,
                  icon: Icons.delete_forever_rounded,
                  title: l10n.profileDeleteAccount,
                  accentColor: const Color(0xFFB84F45),
                  isDestructive: true,
                  onTap: () => context.push(UserRoutes.deleteAccount),
                ),
              ],
            ),
          ),
        ],
      );

  void _showLogoutDialog(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
  ) {
    showDialog<void>(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: GraphiteModalSurface(
          title: l10n.logout,
          showHandle: false,
          borderRadius: BorderRadius.circular(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.confirmLogout,
                style: DS.bodyMedium.copyWith(color: DS.textSecondary),
              ),
              const SizedBox(height: DS.lg),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      onPressed: () => Navigator.pop(context),
                      label: l10n.cancel,
                    ),
                  ),
                  const SizedBox(width: DS.sm),
                  Expanded(
                    child: SparkleButton.destructive(
                      onPressed: () {
                        Navigator.pop(context);
                        ref.read(authProvider.notifier).logout();
                      },
                      label: l10n.confirm,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionLabel(BuildContext context, String title) => Padding(
        padding: const EdgeInsets.only(left: DS.spacing4),
        child: Text(
          title,
          style: DS.labelLarge.copyWith(
            letterSpacing: 0.2,
            color: DS.textSecondary,
          ),
        ),
      );

  Widget _buildSettingsTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    String? subtitle,
    required Color accentColor,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing6,
      ),
      leading: Container(
        padding: const EdgeInsets.all(DS.sm),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              accentColor.withValues(alpha: isDark ? 0.28 : 0.20),
              Color.lerp(accentColor, DS.surfacePrimaryElevated, 0.68)!,
            ],
          ),
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: accentColor.withValues(alpha: isDark ? 0.36 : 0.18),
          ),
        ),
        child: Icon(icon, color: accentColor, size: 20),
      ),
      title: Row(
        children: [
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: isDestructive ? DS.error : DS.textPrimary,
                fontWeight: DS.fontWeightMedium,
              ),
            ),
          ),
          const SizedBox(width: DS.spacing8),
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: accentColor.withValues(alpha: 0.7),
              shape: BoxShape.circle,
            ),
          ),
        ],
      ),
      subtitle: Padding(
        padding: const EdgeInsets.only(top: DS.spacing4),
        child: Text(
          subtitle ?? _settingsSubtitle(title),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: DS.bodySmall.copyWith(
            color: DS.textSecondary,
          ),
        ),
      ),
      trailing: Icon(
        Icons.arrow_forward_ios_rounded,
        size: 16,
        color: DS.neutral400,
      ),
    );
  }

  String _settingsSubtitle(String title) {
    switch (title) {
      case '成就':
      case '成就系统':
        return '查看已解锁的里程碑与荣誉进度';
      case '视觉元素':
        return '管理背景、粒子和视觉奖励';
      case '我的画像':
      case '我的人格画像':
        return '查看系统理解到的学习特征与偏好';
      case '个人资料':
        return '编辑头像、昵称和基础资料';
      case '偏好设置':
      case '日程偏好':
        return '管理感官反馈、学习模式与推送偏好';
      case '账号安全':
        return '查看安全信息、设备与隐私控制';
      case '记忆管理':
        return '调整长期记忆与上下文保留策略';
      case '退出登录':
        return '安全退出当前账号';
      case '删除账号':
        return '永久移除账号与相关数据';
      default:
        return '进入此页面继续调整详细设置';
    }
  }
}

class _WaveHeaderPainter extends CustomPainter {
  const _WaveHeaderPainter({
    required this.startColor,
    required this.middleColor,
    required this.endColor,
  });

  final Color startColor;
  final Color middleColor;
  final Color endColor;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [
          startColor,
          middleColor,
          endColor,
        ],
      ).createShader(
        Rect.fromLTWH(0, 0, size.width, size.height),
      );

    final path = Path();
    path.lineTo(0, size.height - 60);

    // First curve
    path.quadraticBezierTo(
      size.width * 0.25,
      size.height,
      size.width * 0.5,
      size.height - 40,
    );

    // Second curve
    path.quadraticBezierTo(
      size.width * 0.75,
      size.height - 80,
      size.width,
      size.height - 20,
    );

    path.lineTo(size.width, 0);
    path.close();

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _WaveHeaderPainter oldDelegate) =>
      oldDelegate.startColor != startColor ||
      oldDelegate.middleColor != middleColor ||
      oldDelegate.endColor != endColor;
}
