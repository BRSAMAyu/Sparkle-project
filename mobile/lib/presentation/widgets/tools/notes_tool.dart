import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/widgets/common/custom_button.dart';

class NotesTool extends StatefulWidget {
  const NotesTool({super.key});

  @override
  State<NotesTool> createState() => _NotesToolState();
}

class _NotesToolState extends State<NotesTool> {
  final TextEditingController _controller = TextEditingController();

  @override
  Widget build(BuildContext context) => Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 600, // Taller for notes
      decoration: const BoxDecoration(
        color: DS.brandPrimary,
        borderRadius: BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppDesignTokens.neutral300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: DS.xl),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.note_alt_outlined, color: DS.brandPrimary),
                  const SizedBox(width: DS.sm),
                  Text(
                    '随手记',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              TextButton(
                onPressed: () {
                  _controller.clear();
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('已清空')));
                },
                child: const Text('清空', style: TextStyle(color: AppDesignTokens.error)),
              ),
            ],
          ),
          const SizedBox(height: DS.lg),
          Expanded(
            child: Container(
              padding: const EdgeInsets.all(DS.lg),
              decoration: BoxDecoration(
                color: DS.warning[50],
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: DS.brandPrimary.withValues(alpha: 0.2)),
              ),
              child: TextField(
                controller: _controller,
                maxLines: null,
                expands: true,
                decoration: const InputDecoration(
                  hintText: '在这里记录想法...',
                  border: InputBorder.none,
                ),
                style: const TextStyle(fontSize: 16, height: 1.5),
              ),
            ),
          ),
          const SizedBox(height: DS.lg),
          CustomButton.primary(
            text: '复制到剪贴板',
            onPressed: () {
               // Clipboard logic if needed, or just close
               Navigator.pop(context);
               ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('笔记已保存 (Mock)')));
            },
            size: ButtonSize.medium,
          ),
        ],
      ),
    );
}
