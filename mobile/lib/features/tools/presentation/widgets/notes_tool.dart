import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/custom_button.dart';

class NotesTool extends StatefulWidget {
  const NotesTool({super.key});

  @override
  State<NotesTool> createState() => _NotesToolState();
}

class _NotesToolState extends State<NotesTool> {
  final TextEditingController _controller = TextEditingController();
  bool _isLoading = true;
  static const String _notesKey = 'quick_notes_content';
  static const String _notesTimestampKey = 'quick_notes_timestamp';

  @override
  void initState() {
    super.initState();
    _loadNotes();
  }

  Future<void> _loadNotes() async {
    final prefs = await SharedPreferences.getInstance();
    final notes = prefs.getString(_notesKey) ?? '';
    if (mounted) {
      setState(() {
        _controller.text = notes;
        _isLoading = false;
      });
    }
  }

  Future<void> _saveNotes() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_notesKey, _controller.text);
    await prefs.setString(_notesTimestampKey, DateTime.now().toIso8601String());
  }

  Future<void> _clearNotes() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_notesKey);
    await prefs.remove(_notesTimestampKey);
    if (mounted) {
      setState(_controller.clear);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('笔记已清空')),
      );
    }
  }

  @override
  void dispose() {
    // Auto-save on dispose
    if (_controller.text.isNotEmpty) {
      _saveNotes();
    }
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(DS.xl),
      height: 600,
      decoration: BoxDecoration(
        color: isDark ? DS.neutral900 : DS.surfacePrimaryElevated,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Drag Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: DS.neutral300,
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
                  Icon(Icons.note_alt_outlined, color: DS.brandPrimary),
                  const SizedBox(width: DS.sm),
                  Text(
                    '随手记',
                    style: Theme.of(context)
                        .textTheme
                        .titleLarge
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              TextButton(
                onPressed: _clearNotes,
                child: Text('清空', style: TextStyle(color: DS.error)),
              ),
            ],
          ),
          const SizedBox(height: DS.lg),

          // Last saved indicator
          if (!_isLoading && _controller.text.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: DS.sm),
              child: Text(
                '内容会自动保存',
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? DS.neutral400 : DS.neutral500,
                ),
              ),
            ),

          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : Container(
                    padding: const EdgeInsets.all(DS.lg),
                    decoration: BoxDecoration(
                      color: isDark
                          ? DS.neutral800
                          : DS.warning.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isDark
                            ? DS.neutral700
                            : DS.brandPrimary.withValues(alpha: 0.2),
                      ),
                    ),
                    child: TextField(
                      controller: _controller,
                      maxLines: null,
                      expands: true,
                      decoration: const InputDecoration(
                        hintText: '在这里记录想法...',
                        border: InputBorder.none,
                      ),
                      style: TextStyle(
                        fontSize: 16,
                        height: 1.5,
                        color: isDark ? DS.neutral100 : DS.neutral900,
                      ),
                      onChanged: (_) => _saveNotes(),
                    ),
                  ),
            ),
          const SizedBox(height: DS.lg),
          CustomButton.primary(
            text: '完成',
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('笔记已保存'),
                  duration: Duration(seconds: 1),
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
