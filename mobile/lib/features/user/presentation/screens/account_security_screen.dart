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
            GraphiteCardSurface(
              child: Text(
                l10n.accountSecurityIntro,
                style: Theme.of(context)
                    .textTheme
                    .bodyMedium
                    ?.copyWith(color: DS.textSecondary),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            GraphiteCardSurface(
              child: Column(
                children: [
                  _buildTile(
                    context,
                    icon: Icons.link_rounded,
                    title: l10n.profileLinkedAccounts,
                    accentColor: const Color(0xFF7A8C64),
                    onTap: () => context.push(UserRoutes.socialAccounts),
                  ),
                  const Divider(height: 1, indent: 60),
                  _buildTile(
                    context,
                    icon: Icons.devices_rounded,
                    title: l10n.profileSessionManagement,
                    accentColor: const Color(0xFF5E8197),
                    onTap: () => context.push(UserRoutes.sessionManagement),
                  ),
                  const Divider(height: 1, indent: 60),
                  _buildTile(
                    context,
                    icon: Icons.shield_outlined,
                    title: l10n.profileSecurityLog,
                    accentColor: const Color(0xFF8A7AAE),
                    onTap: () => context.push(UserRoutes.securityLog),
                  ),
                  const Divider(height: 1, indent: 60),
                  _buildTile(
                    context,
                    icon: Icons.history_rounded,
                    title: l10n.systemActivity,
                    accentColor: const Color(0xFF7B948E),
                    onTap: () => context.push(UserRoutes.systemUpdates),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required Color accentColor,
    required VoidCallback onTap,
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
          color: DS.textPrimary,
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
