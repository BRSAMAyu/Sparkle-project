import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/tool_launcher.dart';
import 'package:sparkle/features/tools/tool_registry.dart';

class QuickToolsPanel extends ConsumerWidget {
  const QuickToolsPanel({super.key, this.taskId});

  final String? taskId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tools = ToolRegistry.taskQuickTools();
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      alignment: WrapAlignment.center,
      children: tools
          .map(
            (tool) => _ToolButton(
              icon: tool.icon,
              label: tool.title,
              onTap: () => launchTool(
                context,
                ref,
                tool.id,
                launchContext: ToolLaunchContext.taskExecution,
                taskId: taskId,
                preference: ToolOpenPreference.sheet,
              ),
            ),
          )
          .toList(),
    );
  }
}

class _ToolButton extends StatelessWidget {
  const _ToolButton({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tone =
        isDark ? DS.primaryBase.withValues(alpha: 0.12) : DS.neutral100;

    return Semantics(
      button: true,
      label: label,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: 92,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 12),
          decoration: BoxDecoration(
            color: DS.surfaceOverlay,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: DS.borderSubtle,
            ),
          ),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: tone,
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, color: DS.primaryBase, size: 20),
              ),
              const SizedBox(height: DS.xs),
              Text(
                label,
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: DS.fontWeightMedium,
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
