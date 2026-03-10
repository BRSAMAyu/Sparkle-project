import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';

class NotesTool extends StatefulWidget {
  const NotesTool({
    super.key,
    this.surface = ToolSurface.page,
  });

  final ToolSurface surface;

  @override
  State<NotesTool> createState() => _NotesToolState();
}

class _NotesToolState extends State<NotesTool> {
  static const String _notesKey = 'quick_notes_content';
  static const String _notesTimestampKey = 'quick_notes_timestamp';

  final TextEditingController _controller = TextEditingController();
  bool _isLoading = true;
  DateTime? _savedAt;

  int get _charCount => _controller.text.trim().length;
  int get _lineCount => _controller.text.trim().isEmpty
      ? 0
      : '\n'.allMatches(_controller.text).length + 1;

  @override
  void initState() {
    super.initState();
    unawaited(_loadNotes());
  }

  Future<void> _loadNotes() async {
    final prefs = await SharedPreferences.getInstance();
    final notes = prefs.getString(_notesKey) ?? '';
    final timestamp = prefs.getString(_notesTimestampKey);
    if (mounted) {
      setState(() {
        _controller.text = notes;
        _savedAt = timestamp == null ? null : DateTime.tryParse(timestamp);
        _isLoading = false;
      });
    }
  }

  Future<void> _saveNotes() async {
    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now();
    await prefs.setString(_notesKey, _controller.text);
    await prefs.setString(_notesTimestampKey, now.toIso8601String());
    if (mounted) {
      setState(() {
        _savedAt = now;
      });
    }
  }

  Future<void> _clearNotes() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_notesKey);
    await prefs.remove(_notesTimestampKey);
    if (mounted) {
      setState(() {
        _controller.clear();
        _savedAt = null;
      });
      AppFeedback.info(context, '笔记已清空');
    }
  }

  Future<void> _copyNotes() async {
    if (_controller.text.trim().isEmpty) {
      return;
    }
    await Clipboard.setData(ClipboardData(text: _controller.text.trim()));
    if (mounted) {
      AppFeedback.success(context, '笔记已复制');
    }
  }

  @override
  void dispose() {
    if (_controller.text.isNotEmpty) {
      unawaited(_saveNotes());
    }
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final accent = DS.prismBlue;
    return ToolShell(
      surface: widget.surface,
      icon: Icons.edit_note_rounded,
      title: '闪念笔记',
      subtitle: '用于快速承接灵感、会议碎片和任务切片。内容会自动保存，适合做短时外脑。',
      accentColor: accent,
      compactHeader: true,
      fillHeight: false,
      heroChips: [
        ToolHeroChip(
          label: _savedAt == null
              ? '自动保存'
              : '已保存 ${_savedAt!.hour.toString().padLeft(2, '0')}:${_savedAt!.minute.toString().padLeft(2, '0')}',
          accentColor: accent,
          icon: Icons.cloud_done_rounded,
        ),
        ToolHeroChip(
          label: _charCount == 0 ? '等待记录' : '$_charCount 字',
          accentColor: accent,
          icon: Icons.notes_rounded,
        ),
      ],
      body: _isLoading
          ? Center(child: CircularProgressIndicator(color: accent))
          : LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 620;
                final editorHeight = compact ? 260.0 : 320.0;

                return Column(
                  children: [
                    Wrap(
                      spacing: DS.spacing12,
                      runSpacing: DS.spacing12,
                      children: [
                        ToolMetricCard(
                          label: '字数',
                          value: '$_charCount',
                          accentColor: accent,
                          icon: Icons.text_fields_rounded,
                        ),
                        ToolMetricCard(
                          label: '行数',
                          value: '$_lineCount',
                          accentColor: accent,
                          icon: Icons.subject_rounded,
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing16),
                    ToolSectionCard(
                      accentColor: accent,
                      title: '笔记内容',
                      subtitle: '输入时会自动保存，不需要手动提交。',
                      child: SizedBox(
                        height: editorHeight,
                        child: TextField(
                          controller: _controller,
                          maxLines: null,
                          expands: true,
                          textAlignVertical: TextAlignVertical.top,
                          decoration: const InputDecoration(
                            hintText: '把刚刚闪过的想法先放进来...',
                            border: InputBorder.none,
                          ),
                          style:
                              Theme.of(context).textTheme.bodyLarge?.copyWith(
                                    color: DS.textPrimary,
                                    height: 1.65,
                                  ),
                          onChanged: (_) => _saveNotes(),
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
      footer: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 620;
          final actions = <Widget>[
            SparkleButton(
              label: '清空',
              variant: ButtonVariant.ghost,
              onPressed: _clearNotes,
              icon: const Icon(Icons.delete_outline_rounded),
              expand: true,
            ),
            SparkleButton(
              label: '复制内容',
              variant: ButtonVariant.ghost,
              onPressed: _copyNotes,
              icon: const Icon(Icons.copy_rounded),
              expand: true,
            ),
            SparkleButton(
              label: '立即保存',
              onPressed: _saveNotes,
              icon: const Icon(Icons.check_rounded),
              expand: true,
            ),
          ];

          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var index = 0; index < actions.length; index++) ...[
                  if (index > 0) const SizedBox(height: DS.spacing12),
                  actions[index],
                ],
              ],
            );
          }

          return Row(
            children: [
              for (var index = 0; index < actions.length; index++) ...[
                if (index > 0) const SizedBox(width: DS.spacing12),
                Expanded(child: actions[index]),
              ],
            ],
          );
        },
      ),
    );
  }
}
