import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

/// Expanded toolbar section - Quick action tools
class ExpandedToolbarSection extends ConsumerWidget {
  const ExpandedToolbarSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final size = MediaQuery.of(context).size;
    final category = ResponsiveSystem.getCategory(context);

    // Responsive column count: 3 for narrow mobile, 4 for standard, 5 for tablet/desktop
    final crossAxisCount = switch (category) {
      DeviceCategory.tablet => 5,
      DeviceCategory.desktop => 5,
      DeviceCategory.tv => 5,
      DeviceCategory.watch => size.width < 400 ? 3 : 4,
      DeviceCategory.phone => size.width < 400 ? 3 : 4,
      DeviceCategory.phablet => size.width < 400 ? 3 : 4,
    };

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: DS.spacing16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '快捷工具',
            style: context.sparkleTypography.labelLarge.copyWith(
              color: DS.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: DS.spacing12),
          GridView.count(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            crossAxisCount: crossAxisCount,
            mainAxisSpacing: DS.spacing12,
            crossAxisSpacing: DS.spacing12,
            children: const [
              _ToolButton(
                icon: Icons.center_focus_strong_rounded,
                label: '专注模式',
                route: '/focus',
              ),
              _ToolButton(
                icon: Icons.timer_rounded,
                label: '番茄钟',
                route: '/focus?mode=pomodoro',
              ),
              _ToolButton(
                icon: Icons.note_add_rounded,
                label: '快速笔记',
                route: '/memory/new',
              ),
              _ToolButton(
                icon: Icons.casino_rounded,
                label: '随机任务',
                route: '/tasks/random',
              ),
              _ToolButton(
                icon: Icons.lightbulb_rounded,
                label: '好奇心胶囊',
                route: '/cognitive',
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
  });

  final IconData icon;
  final String label;
  final String route;

  @override
  Widget build(BuildContext context) => InkWell(
      onTap: () => context.push(route),
      borderRadius: DS.borderRadius16,
      child: MaterialStyler(
        material: AppMaterials.ceramic,
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
                fontWeight: FontWeight.w500,
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
