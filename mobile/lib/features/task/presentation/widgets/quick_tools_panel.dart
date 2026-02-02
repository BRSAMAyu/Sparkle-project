import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/presentation/widgets/breathing_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/calculator_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/flash_capsule_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/focus_stats_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/notes_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/translator_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/vocabulary_lookup_tool.dart';
import 'package:sparkle/features/tools/presentation/widgets/wordbook_tool.dart';

class QuickToolsPanel extends StatelessWidget {
  // 当前任务ID，用于关联

  const QuickToolsPanel({super.key, this.taskId});
  final String? taskId;

  void _showTool(BuildContext context, Widget tool) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Padding(
        padding:
            EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: tool,
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Wrap(
        spacing: 12,
        runSpacing: 12,
        alignment: WrapAlignment.center,
        children: [
          _ToolButton(
            icon: Icons.calculate_outlined,
            label: '计算器',
            color: DS.brandPrimaryConst,
            onTap: () => _showTool(context, const CalculatorTool()),
          ),
          _ToolButton(
            icon: Icons.translate_outlined,
            label: '翻译',
            color: Colors.purple,
            onTap: () => _showTool(context, const TranslatorTool()),
          ),
          _ToolButton(
            icon: Icons.note_alt_outlined,
            label: '笔记',
            color: DS.brandPrimaryConst,
            onTap: () => _showTool(context, const NotesTool()),
          ),
          _ToolButton(
            icon: Icons.search_rounded,
            label: '查词',
            color: Colors.cyan,
            onTap: () =>
                _showTool(context, VocabularyLookupTool(taskId: taskId)),
          ),
          _ToolButton(
            icon: Icons.lightbulb_outlined,
            label: '闪念胶囊',
            color: Colors.amber,
            onTap: () => _showTool(context, FlashCapsuleTool(taskId: taskId)),
          ),
          _ToolButton(
            icon: Icons.menu_book_rounded,
            label: '生词本',
            color: DS.success,
            onTap: () => _showTool(context, const WordbookTool()),
          ),
          _ToolButton(
            icon: Icons.air,
            label: '呼吸',
            color: Colors.indigo,
            onTap: () => _showTool(context, const BreathingTool()),
          ),
          _ToolButton(
            icon: Icons.bar_chart,
            label: '统计',
            color: Colors.deepPurple,
            onTap: () => _showTool(context, const FocusStatsTool()),
          ),
        ],
      );
}

class _ToolButton extends StatelessWidget {
  const _ToolButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Use appropriate colors based on theme
    final bgColor = isDark
        ? color.withValues(alpha: 0.15)  // Semi-transparent for dark mode
        : color.withValues(alpha: 0.1);   // Lighter for light mode

    final surfaceColor = isDark
        ? DS.neutral800
        : DS.neutral100;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: surfaceColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: bgColor,
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: isDark ? 0.2 : 0.1),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: bgColor,
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 20),
            ),
            const SizedBox(height: DS.xs),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: isDark ? DS.neutral300 : DS.neutral700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
