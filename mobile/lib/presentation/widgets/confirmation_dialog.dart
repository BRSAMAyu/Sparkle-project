import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';

/// 确认操作对话框 (用于高风险操作)
class ConfirmationDialog extends StatelessWidget {
  final String title;
  final String content;
  final Map<String, dynamic>? previewData; // 数据预览
  final VoidCallback onConfirm;
  final VoidCallback onCancel;

  const ConfirmationDialog({
    required this.title, required this.content, required this.onConfirm, required this.onCancel, super.key,
    this.previewData,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(title),
      content: SingleChildScrollView(
        child: ListBody(
          children: <Widget>[
            Text(content),
            if (previewData != null && previewData!.isNotEmpty) ...[
              const SizedBox(height: DS.lg),
              Text(
                '操作预览:',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: DS.sm),
              Container(
                padding: const EdgeInsets.all(DS.sm),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _formatPreview(previewData!),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
      actions: <Widget>[
        TextButton(
          onPressed: onCancel,
          child: const Text('取消'),
        ),
        ElevatedButton(
          onPressed: onConfirm,
          child: const Text('确认'),
        ),
      ],
    );
  }

  String _formatPreview(Map<String, dynamic> data, [int indent = 0]) {
    String buffer = '';
    final indentStr = '  ' * indent;
    data.forEach((key, value) {
      if (value is Map) {
        buffer += '$indentStr$key:\n';
        buffer += _formatPreview(value.cast<String, dynamic>(), indent + 1);
      } else if (value is List) {
        buffer += '$indentStr$key: [\n';
        for (var item in value) {
          if (item is Map) {
            buffer += '${'  ' * (indent + 1)}{\n';
            buffer += _formatPreview(item.cast<String, dynamic>(), indent + 2);
            buffer += '${'  ' * (indent + 1)}}\\n';
          } else {
            buffer += '${'  ' * (indent + 1)}$item\n';
          }
        }
        buffer += '$indentStr]\n';
      } else {
        buffer += '$indentStr$key: $value\n';
      }
    });
    return buffer;
  }
}
