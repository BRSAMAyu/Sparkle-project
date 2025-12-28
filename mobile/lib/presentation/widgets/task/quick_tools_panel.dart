import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/tools/breathing_tool.dart';
import 'package:sparkle/presentation/widgets/tools/calculator_tool.dart';
import 'package:sparkle/presentation/widgets/tools/flash_capsule_tool.dart';
import 'package:sparkle/presentation/widgets/tools/focus_stats_tool.dart';
import 'package:sparkle/presentation/widgets/tools/notes_tool.dart';
import 'package:sparkle/presentation/widgets/tools/translator_tool.dart';
import 'package:sparkle/presentation/widgets/tools/vocabulary_lookup_tool.dart';
import 'package:sparkle/presentation/widgets/tools/wordbook_tool.dart';

class QuickToolsPanel extends StatelessWidget { // 当前任务ID，用于关联

  const QuickToolsPanel({super.key, this.taskId});
  final String? taskId;

  void _showTool(BuildContext context, Widget tool) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
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
          onTap: () => _showTool(context, VocabularyLookupTool(taskId: taskId)),
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
  Widget build(BuildContext context) => InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: DS.brandPrimaryConst,
          borderRadius: BorderRadius.circular(12),
          boxShadow: AppDesignTokens.shadowSm,
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: DS.xs),
            Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
    );
}
