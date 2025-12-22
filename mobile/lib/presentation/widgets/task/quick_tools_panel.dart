import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_tokens.dart';

class QuickToolsPanel extends StatelessWidget {
  const QuickToolsPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _ToolButton(
          icon: Icons.calculate_outlined,
          label: '计算器',
          color: Colors.blue,
          onTap: () {
            // Show calculator dialog/overlay
            ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('计算器功能开发中')));
          },
        ),
        _ToolButton(
          icon: Icons.translate_outlined,
          label: '翻译',
          color: Colors.purple,
          onTap: () {
             ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('翻译功能开发中')));
          },
        ),
        _ToolButton(
          icon: Icons.note_alt_outlined,
          label: '笔记',
          color: Colors.orange,
          onTap: () {
             ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('笔记功能开发中')));
          },
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
