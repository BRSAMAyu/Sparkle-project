import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';
import 'package:sparkle/presentation/widgets/profile/statistics_card.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);

    if (user == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    return Scaffold(
      body: SingleChildScrollView(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            _UserInfoCard(user: user),
            const SizedBox(height: AppDesignTokens.spacing24),
            _buildWeeklyActivityChart(context),
            _buildTaskTypeDistribution(context),
            const SizedBox(height: AppDesignTokens.spacing16),
            _SettingsList(),
            const SizedBox(height: AppDesignTokens.spacing32),
          ],
        ),
      ),
    );
  }

  Widget _buildWeeklyActivityChart(BuildContext context) {
    return StatisticsCard(
      title: 'Weekly Activity',
      subtitle: 'Tasks Completed',
      chart: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: 10,
          barTouchData: BarTouchData(enabled: false),
          titlesData: FlTitlesData(
            show: true,
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
                  if (value.toInt() < 0 || value.toInt() >= days.length) return const SizedBox();
                  return Padding(
                    padding: const EdgeInsets.only(top: 8.0),
                    child: Text(days[value.toInt()], style: const TextStyle(fontSize: 10)),
                  );
                },
              ),
            ),
            leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          ),
          gridData: const FlGridData(show: false),
          borderData: FlBorderData(show: false),
          barGroups: [
            // Mock Data
            _makeBarGroup(0, 3),
            _makeBarGroup(1, 5),
            _makeBarGroup(2, 2),
            _makeBarGroup(3, 8),
            _makeBarGroup(4, 4),
            _makeBarGroup(5, 6),
            _makeBarGroup(6, 3),
          ],
        ),
      ),
    );
  }

  BarChartGroupData _makeBarGroup(int x, double y) {
    return BarChartGroupData(
      x: x,
      barRods: [
        BarChartRodData(
          toY: y,
          gradient: AppDesignTokens.primaryGradient,
          width: 12,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
          backDrawRodData: BackgroundBarChartRodData(
            show: true,
            toY: 10,
            color: AppDesignTokens.neutral100,
          ),
        ),
      ],
    );
  }

  Widget _buildTaskTypeDistribution(BuildContext context) {
    return StatisticsCard(
      title: 'Focus Areas',
      subtitle: 'Last 30 Days',
      chart: PieChart(
        PieChartData(
          sectionsSpace: 2,
          centerSpaceRadius: 40,
          sections: [
            PieChartSectionData(
              value: 40,
              color: AppDesignTokens.primaryBase,
              title: 'Learn',
              radius: 50,
              titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
            ),
            PieChartSectionData(
              value: 30,
              color: AppDesignTokens.secondaryBase,
              title: 'Work',
              radius: 50,
              titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
            ),
            PieChartSectionData(
              value: 15,
              color: AppDesignTokens.accent,
              title: 'Other',
              radius: 50,
              titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
            ),
            PieChartSectionData(
              value: 15,
              color: AppDesignTokens.success,
              title: 'Health',
              radius: 50,
              titleStyle: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}

class _UserInfoCard extends StatelessWidget {
  final dynamic user;
  const _UserInfoCard({required this.user});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 240,
      decoration: const BoxDecoration(
        gradient: AppDesignTokens.primaryGradient,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
      ),
      child: Stack(
        children: [
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: CustomPaint(
              size: const Size(double.infinity, 60),
              painter: _WavePainter(color: Theme.of(context).scaffoldBackgroundColor),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(AppDesignTokens.spacing24),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.3),
                      shape: BoxShape.circle,
                    ),
                    child: const CircleAvatar(
                      radius: 40,
                      backgroundColor: Colors.white,
                      child: Icon(Icons.person, size: 40, color: AppDesignTokens.primaryBase),
                    ),
                  ),
                  const SizedBox(width: AppDesignTokens.spacing16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          user.nickname ?? user.username,
                          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          user.email,
                          style: TextStyle(color: Colors.white.withOpacity(0.9)),
                        ),
                        const SizedBox(height: AppDesignTokens.spacing8),
                        Row(
                          children: [
                            const Icon(Icons.local_fire_department, color: AppDesignTokens.accent, size: 20),
                            const SizedBox(width: 4),
                            Text(
                              'Level ${user.flameLevel}',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _WavePainter extends CustomPainter {
  final Color color;
  _WavePainter({required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color..style = PaintingStyle.fill;
    final path = Path();
    path.moveTo(0, size.height * 0.5);
    path.quadraticBezierTo(size.width * 0.25, size.height * 0.8, size.width * 0.5, size.height * 0.5);
    path.quadraticBezierTo(size.width * 0.75, size.height * 0.2, size.width, size.height * 0.5);
    path.lineTo(size.width, size.height);
    path.lineTo(0, size.height);
    path.close();
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _SettingsList extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: AppDesignTokens.spacing16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: AppDesignTokens.borderRadius12,
        boxShadow: AppDesignTokens.shadowSm,
      ),
      child: Column(
        children: [
          _buildSettingTile(
            icon: Icons.edit_outlined,
            gradient: AppDesignTokens.primaryGradient,
            title: 'Edit Profile',
            onTap: () {},
          ),
          const Divider(height: 1, indent: 56),
          _buildSettingTile(
            icon: Icons.tune,
            gradient: AppDesignTokens.secondaryGradient,
            title: 'Preferences',
            onTap: () {},
          ),
          const Divider(height: 1, indent: 56),
          _buildSettingTile(
            icon: Icons.notifications_outlined,
            gradient: AppDesignTokens.infoGradient,
            title: 'Notifications',
            onTap: () {},
          ),
          const Divider(height: 1, indent: 56),
          _buildSettingTile(
            icon: Icons.info_outline,
            gradient: AppDesignTokens.successGradient,
            title: 'About',
            onTap: () {},
          ),
          const Divider(height: 1, indent: 56),
          ListTile(
            leading: const Icon(Icons.logout, color: AppDesignTokens.error),
            title: const Text('Logout', style: TextStyle(color: AppDesignTokens.error)),
            onTap: () {
              ref.read(authProvider.notifier).logout();
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSettingTile({
    required IconData icon,
    required LinearGradient gradient,
    required String title,
    VoidCallback? onTap,
  }) {
    return ListTile(
      leading: Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          gradient: gradient,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
      title: Text(title),
      trailing: const Icon(Icons.chevron_right, color: AppDesignTokens.neutral400),
      onTap: onTap,
    );
  }
}