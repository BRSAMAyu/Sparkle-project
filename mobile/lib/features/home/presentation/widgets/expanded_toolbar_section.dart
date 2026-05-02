import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/reviews/reviews_routes.dart';

/// Expanded toolbar section - Quick action tools
class ExpandedToolbarSection extends ConsumerWidget {
  const ExpandedToolbarSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final category = ResponsiveSystem.getCategory(context);

    // Responsive column count: 3 for watch, 4 for mobile, 5 for tablet/desktop
    final crossAxisCount = switch (category) {
      DeviceCategory.tablet => 5,
      DeviceCategory.desktop => 5,
      DeviceCategory.tv => 5,
      DeviceCategory.watch => 3,
      DeviceCategory.phone => 4,
      DeviceCategory.phablet => 4,
    };

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            I18nService.instance.isChinese ? '快捷工具' : 'Quick Tools',
            style: context.sparkleTypography.labelLarge.copyWith(
              color: DS.textSecondary,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: crossAxisCount,
            mainAxisSpacing: DS.spacing12,
            crossAxisSpacing: DS.spacing12,
            children: [
              _ToolButton(
                key: const ValueKey('tool_focus_mode'),
                icon: Icons.center_focus_strong_rounded,
                label: I18nService.instance.isChinese ? '专注模式' : 'Focus Mode',
                route: '/focus',
              ),
              _ToolButton(
                key: const ValueKey('tool_pomodoro'),
                icon: Icons.timer_rounded,
                label: I18nService.instance.isChinese ? '番茄钟' : 'Pomodoro',
                route: '/focus',
              ),
              _ToolButton(
                key: const ValueKey('tool_quick_note'),
                icon: Icons.edit_note_rounded,
                label: I18nService.instance.isChinese ? '闪念笔记' : 'Quick Note',
                route: '/memory',
              ),
              _ToolButton(
                key: const ValueKey('tool_error_book'),
                icon: Icons.assignment_late_rounded,
                label: I18nService.instance.isChinese ? '错题本' : 'Error Book',
                route: '/errors',
              ),
              _ToolButton(
                key: const ValueKey('tool_cognitive'),
                icon: Icons.psychology_rounded,
                label: I18nService.instance.isChinese ? '认知模式' : 'Cognitive Mode',
                route: '/cognitive/patterns',
              ),
              _ToolButton(
                key: const ValueKey('tool_curiosity'),
                icon: Icons.lightbulb_rounded,
                label: I18nService.instance.isChinese ? '好奇心胶囊' : 'Curiosity Capsule',
                route: '/curiosity-capsule',
              ),
              _ToolButton(
                key: const ValueKey('tool_review'),
                icon: Icons.event_note_rounded,
                label: I18nService.instance.isChinese ? '复习计划' : 'Review Plan',
                route: ReviewRoutes.planHub,
              ),
              _ToolButton(
                key: const ValueKey('tool_forecast'),
                icon: Icons.show_chart_rounded,
                label: I18nService.instance.isChinese ? '学习预测' : 'Learning Forecast',
                route: '/learning/forecast',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ToolButton extends StatelessWidget {
  const _ToolButton({
    required this.icon,
    required this.label,
    required this.route,
    super.key,
  });

  final IconData icon;
  final String label;
  final String route;

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return InkWell(
      onTap: () => context.push(route),
      borderRadius: DS.borderRadius16,
      child: MaterialStyler(
        key: ValueKey('tool_button_${label}_$brightness'),
        material: AppMaterials.ceramic(context),
        borderRadius: DS.borderRadius16,
        padding: const EdgeInsets.all(DS.spacing12),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing8),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.12),
                borderRadius: DS.borderRadius12,
              ),
              child: Icon(
                icon,
                color: DS.brandPrimaryConst,
                size: DS.iconSizeSm,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            Text(
              label,
              style: context.sparkleTypography.labelSmall.copyWith(
                fontSize: 10,
                color: DS.textPrimary,
                fontWeight: DS.fontWeightMedium,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
