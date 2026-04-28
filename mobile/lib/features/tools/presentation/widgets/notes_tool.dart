import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/tools/models/tool_definition.dart';
import 'package:sparkle/features/tools/presentation/widgets/tool_shell.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class NotesTool extends ConsumerStatefulWidget {
  const NotesTool({
    super.key,
    this.taskId,
    this.surface = ToolSurface.page,
  });

  final String? taskId;
  final ToolSurface surface;

  @override
  ConsumerState<NotesTool> createState() => _NotesToolState();
}

class _NotesToolState extends ConsumerState<NotesTool> {
  static const String _notesKey = 'quick_notes_content';
  static const String _notesTimestampKey = 'quick_notes_timestamp';
  static const String _notesSyncedAtKey = 'quick_notes_synced_at';

  final TextEditingController _controller = TextEditingController();
  bool _isLoading = true;
  bool _isSyncing = false;
  DateTime? _savedAt;
  DateTime? _lastSyncedAt;

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
    final syncedAt = prefs.getString(_notesSyncedAtKey);
    if (mounted) {
      setState(() {
        _controller.text = notes;
        _savedAt = timestamp == null ? null : DateTime.tryParse(timestamp);
        _lastSyncedAt = syncedAt == null ? null : DateTime.tryParse(syncedAt);
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
    await prefs.remove(_notesSyncedAtKey);
    if (mounted) {
      setState(() {
        _controller.clear();
        _savedAt = null;
        _lastSyncedAt = null;
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

  Future<void> _syncToPrism() async {
    final content = _controller.text.trim();
    if (content.isEmpty) {
      AppFeedback.info(context, '先写下一点内容，再同步到认知棱镜');
      return;
    }

    if (mounted) {
      setState(() => _isSyncing = true);
    }

    await _saveNotes();
    final fragment = await ref.read(cognitiveProvider.notifier).createFragment(
          content: content,
          sourceType: 'quick_note',
          taskId: widget.taskId,
        );

    if (!mounted) {
      return;
    }

    if (fragment == null) {
      setState(() => _isSyncing = false);
      AppFeedback.error(context, context.l10n.toolsNotesSyncFailed);
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now();
    await prefs.setString(_notesSyncedAtKey, now.toIso8601String());
    if (!mounted) {
      return;
    }
    setState(() {
      _isSyncing = false;
      _lastSyncedAt = now;
    });
    AppFeedback.success(context, '已同步到认知棱镜');
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
      title: context.l10n.toolsNotesTitle,
      subtitle: context.l10n.toolsNotesSubtitle,
      accentColor: accent,
      compactHeader: true,
      heroChips: [
        ToolHeroChip(
          label: _savedAt == null
              ? '自动保存'
              : '已保存 ${_savedAt!.hour.toString().padLeft(2, '0')}:${_savedAt!.minute.toString().padLeft(2, '0')}',
          accentColor: accent,
          icon: Icons.cloud_done_rounded,
        ),
        ToolHeroChip(
          label: _charCount == 0 ? context.l10n.toolsNotesWaiting : '$_charCount 字',
          accentColor: accent,
          icon: Icons.notes_rounded,
        ),
        ToolHeroChip(
          label: _lastSyncedAt == null
              ? '未同步'
              : '已入棱镜 ${_lastSyncedAt!.hour.toString().padLeft(2, '0')}:${_lastSyncedAt!.minute.toString().padLeft(2, '0')}',
          accentColor: accent,
          icon: Icons.psychology_alt_rounded,
        ),
      ],
      body: _isLoading
          ? Center(child: CircularProgressIndicator(color: accent))
          : LayoutBuilder(
              builder: (context, constraints) {
                final editorHeight = (MediaQuery.sizeOf(context).height * 0.3)
                    .clamp(180.0, 360.0);

                return Column(
                  children: [
                    ToolMetricRow(
                      children: [
                        ToolMetricCard(
                          label: context.l10n.toolsNotesCharLabel,
                          value: '$_charCount',
                          accentColor: accent,
                          icon: Icons.text_fields_rounded,
                        ),
                        ToolMetricCard(
                          label: context.l10n.toolsNotesLineLabel,
                          value: '$_lineCount',
                          accentColor: accent,
                          icon: Icons.subject_rounded,
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing16),
                    ToolSectionCard(
                      accentColor: accent,
                      title: context.l10n.toolsNotesContent,
                      subtitle: context.l10n.toolsNotesContentDesc,
                      child: SizedBox(
                        height: editorHeight,
                        child: TextField(
                          controller: _controller,
                          maxLines: null,
                          expands: true,
                          textAlignVertical: TextAlignVertical.top,
                          decoration: const InputDecoration(
                            hintText: context.l10n.toolsNotesHint,
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
              label: context.l10n.toolsNotesClear,
              variant: ButtonVariant.ghost,
              onPressed: _clearNotes,
              icon: const Icon(Icons.delete_outline_rounded),
              expand: true,
            ),
            SparkleButton(
              label: context.l10n.toolsNotesCopy,
              variant: ButtonVariant.ghost,
              onPressed: _copyNotes,
              icon: const Icon(Icons.copy_rounded),
              expand: true,
            ),
            SparkleButton(
              label: context.l10n.toolsNotesSaveNow,
              onPressed: _saveNotes,
              icon: const Icon(Icons.check_rounded),
              expand: true,
            ),
            SparkleButton(
              label: _isSyncing ? context.l10n.toolsNotesSyncing : context.l10n.toolsNotesSyncToPrism,
              onPressed: _isSyncing ? null : _syncToPrism,
              icon: const Icon(Icons.psychology_alt_rounded),
              loading: _isSyncing,
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
