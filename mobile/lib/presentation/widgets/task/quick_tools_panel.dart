import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/tools/calculator_tool.dart';
import 'package:sparkle/presentation/widgets/tools/translator_tool.dart';
import 'package:sparkle/presentation/widgets/tools/notes_tool.dart';

class QuickToolsPanel extends StatelessWidget {
  const QuickToolsPanel({super.key});

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
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _ToolButton(
          icon: Icons.calculate_outlined,
          label: '计算器',
          color: Colors.blue,
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
          color: Colors.orange,
          onTap: () => _showTool(context, const NotesTool()),
        ),
      ],
    );
  }
}

class _ToolButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  const _ToolButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          boxShadow: AppDesignTokens.shadowSm,
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 28),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
          ],
        ),
      ),
    );
  }
}
