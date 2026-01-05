import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/domain/entities/user_model.dart';
import 'package:sparkle/features/user/presentation/screens/edit_profile_screen.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/presentation/providers/locale_provider.dart';
import 'package:sparkle/presentation/widgets/common/sparkle_avatar.dart';
import 'package:sparkle/presentation/widgets/profile/statistics_card.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final l10n = AppLocalizations.of(context)!;

    if (user == null) return const SizedBox.shrink();

    return Scaffold(
      backgroundColor: DS.neutral50,
      body: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            _buildHeader(context, user),
            Padding(
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
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, UserModel user) => SizedBox(
        height: 320,
        child: Stack(
          children: [
            // Wave Background
            Positioned.fill(
              child: CustomPaint(
                painter: _WaveHeaderPainter(),
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
                                color: DS.brandPrimary.withValues(alpha: 0.3),
                                width: 4,),
                            boxShadow: [
                              BoxShadow(
                                color: DS.brandPrimary.withValues(alpha: 0.2),
                                blurRadius: 20,
                                spreadRadius: 5,
                              ),
                            ],
                          ),
                          child: SparkleAvatar(
                            radius: 40,
                            backgroundColor: DS.brandPrimary,
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
                                    horizontal: 12, vertical: 6,),
                                decoration: BoxDecoration(
                                  color: DS.brandPrimary.withValues(alpha: 0.2),
                                  borderRadius: DS.borderRadius20,
                                ),
                                child: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.local_fire_department_rounded,
                                        color: DS.brandPrimary, size: 16,),
                                    const SizedBox(width: DS.xs),
                                    Text(
                                      'Lv.${user.flameLevel}',
                                      style: TextStyle(
                                        color: DS.brandPrimary,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    const SizedBox(width: DS.sm),
                                    Text(
                                      'Brightness ${(user.flameBrightness * 100).toInt()}%',
                                      style: TextStyle(
                                        color: DS.textSecondary,
                                        fontSize: 12,
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
          BuildContext context, WidgetRef ref, AppLocalizations l10n,) =>
      DecoratedBox(
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          boxShadow: DS.shadowSm,
        ),
        child: Column(
          children: [
            _buildSettingsTile(
              context,
              icon: Icons.person_outline_rounded,
              title: l10n.nickname,
              gradient: DS.primaryGradient,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const EditProfileScreen(),
                  ),
                );
              },
            ),
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.tune_rounded,
              title: l10n.schedulePreferences,
              gradient: DS.secondaryGradient,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const UnifiedSettingsScreen(),
                  ),
                );
              },
            ),
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.language_rounded,
              title: l10n.language,
              gradient: DS.infoGradient,
              onTap: () {
                _showLanguageDialog(context, ref);
              },
            ),
            const Divider(height: 1, indent: 60),
            _buildSettingsTile(
              context,
              icon: Icons.logout_rounded,
              title: l10n.logout,
              gradient: DS.errorGradient,
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

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.language),
        shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius16),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: Text(l10n.languageChinese),
              trailing: currentLocale.languageCode == 'zh'
                  ? Icon(Icons.check, color: DS.primaryBase)
                  : null,
              onTap: () {
                ref.read(localeProvider.notifier).setLocale(const Locale('zh'));
                Navigator.pop(context);
              },
            ),
            ListTile(
              title: Text(l10n.languageEnglish),
              trailing: currentLocale.languageCode == 'en'
                  ? Icon(Icons.check, color: DS.primaryBase)
                  : null,
              onTap: () {
                ref.read(localeProvider.notifier).setLocale(const Locale('en'));
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _showLogoutDialog(
      BuildContext context, WidgetRef ref, AppLocalizations l10n,) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.logout),
        content: Text(l10n.confirmLogout),
        shape: const RoundedRectangleBorder(borderRadius: DS.borderRadius16),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              ref.read(authProvider.notifier).logout();
            },
            child: Text(l10n.confirm, style: TextStyle(color: DS.error)),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required LinearGradient gradient,
    required VoidCallback onTap,
    bool isDestructive = false,
  }) =>
      ListTile(
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing4,
        ),
        leading: Container(
          padding: const EdgeInsets.all(DS.sm),
          decoration: BoxDecoration(
            gradient: gradient,
            borderRadius: DS.borderRadius8,
          ),
          child: Icon(icon, color: Colors.white, size: 20),
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

class _WaveHeaderPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = DS.primaryGradient.createShader(
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
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
