import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/user/user_routes.dart';
import 'package:sparkle/l10n/app_localizations.dart';

class AccountSecurityScreen extends StatelessWidget {
  const AccountSecurityScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.accountSecurity),
        centerTitle: true,
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.spacing16),
          children: [
            SparkleStaggerItem(
              index: 0,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.panel,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: [
                        _buildInfoChip(
                          context,
                          icon: Icons.shield_outlined,
                          label: l10n.accountSecurity,
                        ),
                        _buildInfoChip(
                          context,
                          icon: Icons.lock_clock_outlined,
                          label: l10n.profileSessionManagement,
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing12),
                    Text(
                      l10n.accountSecurityIntro,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                            height: 1.45,
                          ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            SparkleStaggerItem(
              index: 1,
              child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.accountSecurity,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: DS.spacing4),
                    Text(
                      '把登录入口、设备状态和关键操作记录收在一起，方便你按风险等级快速查看。',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: DS.textSecondary,
                            height: 1.4,
                          ),
                    ),
                    const SizedBox(height: DS.spacing16),
                    _buildTile(
                      context,
                      icon: Icons.link_rounded,
                      title: l10n.profileLinkedAccounts,
                      subtitle: '统一管理 Google、Apple、微信等绑定方式。',
                      accentColor: const Color(0xFF7A8C64),
                      onTap: () => context.push(UserRoutes.socialAccounts),
                    ),
                    const Divider(height: 1, indent: 64),
                    _buildTile(
                      context,
                      icon: Icons.devices_rounded,
                      title: l10n.profileSessionManagement,
                      subtitle: '查看当前设备、最近活跃时间和远程退出状态。',
                      accentColor: const Color(0xFF5E8197),
                      onTap: () => context.push(UserRoutes.sessionManagement),
                    ),
                    const Divider(height: 1, indent: 64),
                    _buildTile(
                      context,
                      icon: Icons.shield_outlined,
                      title: l10n.profileSecurityLog,
                      subtitle: '保留登录、解绑、密码修改等安全轨迹。',
                      accentColor: const Color(0xFF8A7AAE),
                      onTap: () => context.push(UserRoutes.securityLog),
                    ),
                    const Divider(height: 1, indent: 64),
                    _buildTile(
                      context,
                      icon: Icons.history_rounded,
                      title: l10n.systemActivity,
                      subtitle: '回顾近期系统更新和重要账号行为变化。',
                      accentColor: const Color(0xFF7B948E),
                      onTap: () => context.push(UserRoutes.systemUpdates),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoChip(
    BuildContext context, {
    required IconData icon,
    required String label,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: DS.textSecondary),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: DS.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ],
        ),
      );

  Widget _buildTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required Color accentColor,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      onTap: onTap,
      borderRadius: DS.borderRadius16,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing4,
          vertical: DS.spacing10,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
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
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: DS.textPrimary,
                          fontWeight: DS.fontWeightMedium,
                        ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    subtitle,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                          height: 1.4,
                        ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: DS.surfaceSecondary,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: DS.borderSubtle),
              ),
              child: Icon(
                Icons.arrow_forward_ios_rounded,
                size: 14,
                color: DS.neutral400,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
