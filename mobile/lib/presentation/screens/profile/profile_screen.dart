import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/screens/profile/schedule_preferences_screen.dart';
import 'package:sparkle/presentation/widgets/profile/statistics_card.dart';
import 'package:sparkle/presentation/widgets/common/flame_indicator.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);

    if (user == null) return const SizedBox.shrink();

    return Scaffold(
      backgroundColor: AppDesignTokens.neutral50,
      body: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            _buildHeader(context, user),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16),
              child: Column(
                children: [
                  const SizedBox(height: AppDesignTokens.spacing24),
                  const StatisticsCard(),
                  const SizedBox(height: AppDesignTokens.spacing24),
                  _buildSettingsSection(context, ref),
                  const SizedBox(height: 100), // Bottom padding
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context, dynamic user) {
    return SizedBox(
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
              padding: const EdgeInsets.all(AppDesignTokens.spacing24),
              child: Column(
                children: [
                  const SizedBox(height: AppDesignTokens.spacing16),
                  Row(
                    children: [
                      // Avatar Area
                      Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white.withOpacity(0.3), width: 4),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.white.withOpacity(0.2),
                              blurRadius: 20,
                              spreadRadius: 5,
                            ),
                          ],
                        ),
                        child: CircleAvatar(
                          radius: 40,
                          backgroundColor: Colors.white,
                          child: Text(
                            user.username[0].toUpperCase(),
                            style: const TextStyle(
                              fontSize: 32,
                              fontWeight: AppDesignTokens.fontWeightBold,
                              color: AppDesignTokens.primaryBase,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: AppDesignTokens.spacing20),
                      // Info Area
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              user.nickname ?? user.username,
                              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                color: Colors.white,
                                fontWeight: AppDesignTokens.fontWeightBold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.2),
                                borderRadius: AppDesignTokens.borderRadius20,
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  const Icon(Icons.local_fire_department_rounded, color: Colors.white, size: 16),
                                  const SizedBox(width: 4),
                                  Text(
                                    'Lv.${user.flameLevel}',
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    'Brightness ${(user.flameBrightness * 100).toInt()}%',
                                    style: TextStyle(
                                      color: Colors.white.withOpacity(0.9),
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
  }

  Widget _buildSettingsSection(BuildContext context, WidgetRef ref) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: AppDesignTokens.borderRadius16,
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: Column(
        children: [
          _buildSettingsTile(
            context,
            icon: Icons.person_outline_rounded,
            title: '编辑资料',
            gradient: AppDesignTokens.primaryGradient,
            onTap: () {},
          ),
          const Divider(height: 1, indent: 60),
          _buildSettingsTile(
            context,
            icon: Icons.tune_rounded,
            title: '学习偏好',
            gradient: AppDesignTokens.secondaryGradient,
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const SchedulePreferencesScreen(),
                ),
              );
            },
          ),
          const Divider(height: 1, indent: 60),
          _buildSettingsTile(
            context,
            icon: Icons.notifications_none_rounded,
            title: '通知设置',
            gradient: AppDesignTokens.infoGradient,
            onTap: () {},
          ),
          const Divider(height: 1, indent: 60),
          _buildSettingsTile(
            context,
            icon: Icons.logout_rounded,
            title: '退出登录',
            gradient: AppDesignTokens.errorGradient,
            isDestructive: true,
            onTap: () {
              ref.read(authProvider.notifier).logout();
            },
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
  }) {
    return ListTile(
      onTap: onTap,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppDesignTokens.spacing16,
        vertical: AppDesignTokens.spacing4,
      ),
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          gradient: gradient,
          borderRadius: AppDesignTokens.borderRadius8,
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
      title: Text(
        title,
        style: TextStyle(
          color: isDestructive ? AppDesignTokens.error : AppDesignTokens.neutral900,
          fontWeight: AppDesignTokens.fontWeightMedium,
        ),
      ),
      trailing: const Icon(
        Icons.arrow_forward_ios_rounded,
        size: 16,
        color: AppDesignTokens.neutral400,
      ),
    );
  }
}

class _WaveHeaderPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..shader = AppDesignTokens.primaryGradient.createShader(
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
