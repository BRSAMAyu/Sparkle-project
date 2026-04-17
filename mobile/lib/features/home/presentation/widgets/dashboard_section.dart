import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

enum DashboardSurfaceTone { hero, summary, workspace }

class DashboardSectionShell extends StatelessWidget {
  const DashboardSectionShell({
    required this.child,
    super.key,
    this.tone = DashboardSurfaceTone.workspace,
    this.padding = const EdgeInsets.all(DS.spacing16),
    this.borderRadius = DS.borderRadius20,
    this.onTap,
  });

  final Widget child;
  final DashboardSurfaceTone tone;
  final EdgeInsetsGeometry padding;
  final BorderRadius borderRadius;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final content = MaterialStyler(
      material: _resolveMaterial(context),
      borderRadius: borderRadius,
      padding: padding,
      child: child,
    );

    if (onTap == null) {
      return content;
    }

    return InkWell(
      onTap: onTap,
      borderRadius: borderRadius,
      child: content,
    );
  }

  SparkleMaterial _resolveMaterial(BuildContext context) {
    final base = AppMaterials.ceramic(context);

    return switch (tone) {
      DashboardSurfaceTone.hero => base.copyWith(
          backgroundGradient: LinearGradient(
            colors: [
              DS.brandPrimary.withValues(alpha: 0.13),
              DS.info.withValues(alpha: 0.06),
              DS.surfacePrimaryElevated,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderColor: DS.brandPrimary.withValues(alpha: 0.18),
          borderWidth: 1,
          shadows: [
            BoxShadow(
              color: DS.brandPrimary.withValues(alpha: 0.06),
              blurRadius: 24,
              offset: const Offset(0, 12),
            ),
          ],
        ),
      DashboardSurfaceTone.summary => base.copyWith(
          backgroundGradient: LinearGradient(
            colors: [
              DS.surfacePrimaryElevated,
              DS.surfaceSecondary,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderColor: DS.borderSubtle,
          borderWidth: 1,
        ),
      DashboardSurfaceTone.workspace => base.copyWith(
          borderColor: DS.borderSubtle,
          borderWidth: 1,
        ),
    };
  }
}

class DashboardSectionHeader extends StatelessWidget {
  const DashboardSectionHeader({
    required this.icon,
    required this.title,
    super.key,
    this.summary,
    this.trailing,
    this.accentColor,
    this.iconSize = 36,
  });

  final IconData icon;
  final String title;
  final String? summary;
  final Widget? trailing;
  final Color? accentColor;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    final resolvedAccent = accentColor ?? DS.brandPrimary;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: iconSize,
          height: iconSize,
          decoration: BoxDecoration(
            color: resolvedAccent.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: resolvedAccent.withValues(alpha: 0.14),
            ),
          ),
          child: Icon(
            icon,
            size: 18,
            color: resolvedAccent,
          ),
        ),
        const SizedBox(width: DS.spacing10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: context.sparkleTypography.labelLarge.copyWith(
                  fontWeight: DS.fontWeightBold,
                  color: DS.textPrimary,
                ),
              ),
              if (summary != null && summary!.trim().isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  summary!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textSecondary,
                    height: 1.35,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: DS.spacing10),
          trailing!,
        ],
      ],
    );
  }
}
