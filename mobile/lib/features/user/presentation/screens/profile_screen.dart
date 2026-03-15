import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_avatar.dart';
import 'package:sparkle/core/providers/locale_provider.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/features/user/presentation/widgets/statistics_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final l10n = AppLocalizations.of(context)!;
    final screenHeight = MediaQuery.of(context).size.height;
    final headerHeight = screenHeight < 720 ? 248.0 : 320.0;

    if (user == null) return const SizedBox.shrink();

    return GraphiteScaffold(
      role: SparklePageRole.content,
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
                    const SizedBox(height: DS.spacing24),
                    const StatisticsCard(),
                    const SizedBox(height: DS.spacing24),
                    _buildSettingsSection(context, ref, l10n),
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

  Widget _buildHeader(
    BuildContext context,
    UserModel user, {
    required double headerHeight,
  }) => SizedBox(
      height: headerHeight,
      child: Stack(
        children: [
          // Wave Background
          Positioned.fill(
            child: CustomPaint(
              painter: _WaveHeaderPainter(
                startColor: Color.lerp(
                    DS.surfacePrimaryElevated, DS.brandPrimary, 0.04)!,
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
                  const SizedBox(height: DS.spacing16),
                  Row(
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
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(
                                    color: DS.textPrimary,
                                    fontWeight: DS.fontWeightBold,
                                  ),
                            ),
                            const SizedBox(height: DS.sm),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: DS.surfaceOverlay,
                                borderRadius: DS.borderRadius20,
                                border: Border.all(color: DS.borderSubtle),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.local_fire_department_rounded,
                                    color: DS.brandPrimaryConst,
                                    size: 16,
                                  ),
                                  const SizedBox(width: DS.xs),
                                  Text(
                                    'Lv.${user.flameLevel}',
                                    style: DS.labelLarge.copyWith(
                                      color: DS.textPrimary,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(width: DS.sm),
                                  Text(
                                    'Brightness ${(user.flameBrightness * 100).toInt()}%',
                                    style: DS.labelSmall.copyWith(
                                      color: DS.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
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

  Widget _buildSettingsSection(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
  ) =>
      GraphiteCardSurface(
        child: Column(
          children: [
            _buildSettingsTile(
              context,
              icon: Icons.person_outline_rounded,
              title: '个人资料',
              accentColor: const Color(0xFF9B7A72),
              onTap: () {
                context.push(UserRoutes.editProfile);
              },
            ),
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.tune_rounded,
              title: l10n.schedulePreferences,
              accentColor: const Color(0xFF7087A6),
              onTap: () {
                context.push(UserRoutes.settings);
              },
            ),
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.psychology_alt_outlined,
              title: l10n.myPersona,
              accentColor: const Color(0xFF8877A6),
              onTap: () {
                context.push(UserRoutes.persona);
              },
            ),
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.history_rounded,
              title: l10n.systemActivity,
              accentColor: const Color(0xFF7B948E),
              onTap: () {
                context.push(UserRoutes.systemUpdates);
              },
            ),
            if (AppFeatureFlags.enableUserMemoryControls) ...[
              const Divider(height: 1, indent: 60),
              _buildSettingsTile(
                context,
                icon: Icons.memory_rounded,
                title: l10n.memoryControl,
                accentColor: const Color(0xFF6D9282),
                onTap: () {
                  context.push(UserRoutes.memorySettings);
                },
              ),
            ],
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.language_rounded,
              title: l10n.language,
              accentColor: const Color(0xFF6E8FAE),
              onTap: () {
                _showLanguageDialog(context, ref);
              },
            ),
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.logout_rounded,
              title: l10n.logout,
              accentColor: const Color(0xFFB06F67),
              isDestructive: true,
              onTap: () {
                _showLogoutDialog(context, ref, l10n);
              },
            ),
          ],
        ),
      );

  void _showLanguageDialog(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;
    final currentLocale = ref.read(localeProvider);

    showDialog<void>(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: GraphiteModalSurface(
          title: l10n.language,
          showHandle: false,
          borderRadius: BorderRadius.circular(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                title: Text(l10n.languageChinese),
                trailing: currentLocale.languageCode == 'zh'
                    ? Icon(Icons.check, color: DS.primaryBase)
                    : null,
                onTap: () {
                  ref
                      .read(localeProvider.notifier)
                      .setLocale(const Locale('zh'));
                  Navigator.pop(context);
                },
              ),
              ListTile(
                title: Text(l10n.languageEnglish),
                trailing: currentLocale.languageCode == 'en'
                    ? Icon(Icons.check, color: DS.primaryBase)
                    : null,
                onTap: () {
                  ref
                      .read(localeProvider.notifier)
                      .setLocale(const Locale('en'));
                  Navigator.pop(context);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

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

  Widget _buildSettingsTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required Color accentColor,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: DS.spacing16,
        vertical: DS.spacing4,
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
      title: Text(
        title,
        style: TextStyle(
          color: isDestructive ? DS.error : DS.textPrimary,
          fontWeight: DS.fontWeightMedium,
        ),
      ),
      trailing: Icon(
        Icons.arrow_forward_ios_rounded,
        size: 16,
        color: DS.neutral400,
      ),
    );
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
