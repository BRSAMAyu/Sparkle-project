import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/chat/presentation/widgets/working_memory_badge.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class ChatWorkingMemoryPanel extends ConsumerStatefulWidget {
  const ChatWorkingMemoryPanel({
    required this.sessionId,
    required this.onViewSource,
    this.loader,
    this.onForgetEntry,
    this.onMarkCorrectEntry,
    super.key,
  });

  final String? sessionId;
  final ValueChanged<String> onViewSource;
  final Future<WorkingMemorySessionModel> Function(String? sessionId)? loader;
  final Future<void> Function(String entryId, String? sessionId)? onForgetEntry;
  final Future<WorkingMemoryItem> Function(String entryId, String? sessionId)?
      onMarkCorrectEntry;

  @override
  ConsumerState<ChatWorkingMemoryPanel> createState() =>
      _ChatWorkingMemoryPanelState();
}

class _ChatWorkingMemoryPanelState
    extends ConsumerState<ChatWorkingMemoryPanel> {
  bool _loading = false;
  bool _expanded = false;
  bool _dismissed = false;
  String? _error;
  WorkingMemorySessionModel _session =
      WorkingMemorySessionModel(sessionId: null, items: const []);

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void didUpdateWidget(covariant ChatWorkingMemoryPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.sessionId != widget.sessionId) {
      unawaited(_load());
    }
  }

  Future<void> _load() async {
    final sessionId = widget.sessionId?.trim();
    if (!AppFeatureFlags.enableWorkingMemoryDrawer ||
        sessionId == null ||
        sessionId.isEmpty) {
      if (mounted) {
        setState(() {
          _session =
              WorkingMemorySessionModel(sessionId: null, items: const []);
          _loading = false;
          _error = null;
        });
      }
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await (widget.loader != null
          ? widget.loader!(sessionId)
          : ref
              .read(memoryApiServiceProvider)
              .getWorkingMemorySession(sessionId: sessionId));
      if (!mounted) return;
      setState(() {
        _session = data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = '$e';
      });
    }
  }

  Future<void> _forget(String entryId) async {
    final sessionId = _session.sessionId;
    if (widget.onForgetEntry != null) {
      await widget.onForgetEntry!(entryId, sessionId);
    } else {
      await ref.read(memoryApiServiceProvider).forgetWorkingMemoryEntry(
            entryId,
            sessionId: sessionId,
          );
    }
    await _load();
  }

  Future<void> _markCorrect(String entryId) async {
    final sessionId = _session.sessionId;
    if (widget.onMarkCorrectEntry != null) {
      await widget.onMarkCorrectEntry!(entryId, sessionId);
    } else {
      await ref.read(memoryApiServiceProvider).markWorkingMemoryEntryCorrect(
            entryId,
            sessionId: sessionId,
          );
    }
    await _load();
    if (mounted) {
      AppFeedback.success(context, context.l10n.chatMemoryMarkedCorrect);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_dismissed ||
        !AppFeatureFlags.enableWorkingMemoryDrawer ||
        ((widget.sessionId ?? '').isEmpty && _session.items.isEmpty)) {
      return const SizedBox.shrink();
    }

    return Container(
      margin:
          const EdgeInsets.fromLTRB(DS.spacing16, DS.spacing8, DS.spacing16, 0),
      decoration: BoxDecoration(
        color: DS.surfacePanel,
        borderRadius: DS.borderRadius16,
        border: Border.all(color: DS.borderSubtle),
      ),
      child: Column(
        children: [
          Semantics(
            button: true,
            label: _expanded
                ? context.l10n.chatSemanticsCollapseMemory
                : context.l10n.chatSemanticsExpandMemory,
            child: InkWell(
              borderRadius: DS.borderRadius16,
              onTap: () => setState(() => _expanded = !_expanded),
              child: Padding(
                padding: const EdgeInsets.all(DS.spacing12),
                child: Row(
                  children: [
                    Icon(Icons.psychology_alt_outlined,
                        color: DS.info, size: 18),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            context.l10n.chatMemoryAiRemembers,
                            style: TextStyle(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightSemibold,
                              fontSize: DS.fontSizeSm,
                            ),
                          ),
                          Text(
                            _loading
                                ? context.l10n.chatMemorySyncing
                                : _error != null
                                    ? context.l10n.chatMemoryUnavailable
                                    : context.l10n.chatMemorySessionCount(
                                        _session.items.length),
                            style: TextStyle(
                              color: DS.textSecondary,
                              fontSize: DS.fontSizeXs,
                            ),
                          ),
                        ],
                      ),
                    ),
                    GestureDetector(
                      onTap: () => setState(() => _dismissed = true),
                      child: Padding(
                        padding: const EdgeInsets.only(left: DS.spacing4),
                        child: Icon(Icons.close_rounded,
                            color: DS.textTertiary, size: 16),
                      ),
                    ),
                    const SizedBox(width: DS.spacing4),
                    Icon(
                      _expanded ? Icons.expand_less : Icons.expand_more,
                      color: DS.textSecondary,
                    ),
                  ],
                ),
              ),
            ),
          ),
          if (_expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(
                DS.spacing12,
                0,
                DS.spacing12,
                DS.spacing12,
              ),
              child: _buildExpandedBody(),
            ),
        ],
      ),
    );
  }

  Widget _buildExpandedBody() {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: DS.spacing12),
        child: LinearProgressIndicator(),
      );
    }
    if (_error != null) {
      return Text(
        _error!,
        style: TextStyle(color: DS.error, fontSize: DS.fontSizeXs),
      );
    }
    if (_session.items.isEmpty) {
      return Text(
        context.l10n.chatMemoryEmptyHint,
        style: TextStyle(color: DS.textSecondary, fontSize: DS.fontSizeXs),
      );
    }
    return Column(
      children: _session.items
          .take(10)
          .map(
            (item) => Container(
              margin: const EdgeInsets.only(top: DS.spacing8),
              padding: const EdgeInsets.all(DS.spacing12),
              decoration: BoxDecoration(
                color: DS.surfacePrimary,
                borderRadius: DS.borderRadius12,
                border:
                    Border.all(color: DS.borderSubtle.withValues(alpha: 0.8)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          item.summary,
                          style: TextStyle(
                            color: DS.textPrimary,
                            fontWeight: DS.fontWeightMedium,
                          ),
                        ),
                      ),
                      WorkingMemoryBadge(
                        consolidated: item.consolidatedToL1Id != null,
                      ),
                    ],
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    context.l10n.chatMemoryMentionCount(
                        item.mentionCount, item.subjectType),
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: DS.fontSizeXs,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Wrap(
                    spacing: DS.spacing8,
                    runSpacing: DS.spacing8,
                    children: [
                      TextButton(
                        onPressed: item.evidenceToken.isEmpty
                            ? null
                            : () => widget.onViewSource(item.evidenceToken),
                        child: Text(context.l10n.chatMemoryOriginalTurn),
                      ),
                      TextButton(
                        onPressed: () => _forget(item.id),
                        child: Text(context.l10n.chatMemoryManualForget),
                      ),
                      TextButton(
                        onPressed:
                            item.rejected ? null : () => _markCorrect(item.id),
                        child: Text(context.l10n.chatMemoryMarkCorrect),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }
}
