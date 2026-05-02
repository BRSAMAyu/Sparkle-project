import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_state.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';
import 'package:sparkle/features/documents/presentation/providers/document_library_provider.dart';
import 'package:sparkle/core/services/i18n_service.dart';

/// Source Tray — full-featured material selection sheet.
///
/// Vision demo point #5: Shows source relevance, allows toggling, supports
/// retrieval mode selection (auto/user-selected/task/goal/off), and displays
/// knowledge node coverage per source.
class StudyMaterialsSheet extends ConsumerStatefulWidget {
  const StudyMaterialsSheet({
    required this.retrievalEnabled,
    this.documentContextMode = DocumentContextMode.auto,
    this.onModeChanged,
    super.key,
  });

  final bool retrievalEnabled;
  final DocumentContextMode documentContextMode;
  final ValueChanged<DocumentContextMode>? onModeChanged;

  @override
  ConsumerState<StudyMaterialsSheet> createState() =>
      _StudyMaterialsSheetState();
}

class _StudyMaterialsSheetState extends ConsumerState<StudyMaterialsSheet> {
  final Set<String> _toggledOff = {};

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(documentLibraryProvider);
    final readyDocs = (state.documents.valueOrNull ??
            const <DocumentLibraryItem>[])
        .where((doc) => doc.effectiveStatus == DocumentStatus.ready)
        .toList()
      ..sort((a, b) => _relevanceOf(b).index.compareTo(_relevanceOf(a).index));

    return SafeArea(
      top: false,
      child: Container(
        decoration: BoxDecoration(
          color: DS.surfacePrimary,
          borderRadius: const BorderRadius.vertical(
            top: Radius.circular(24),
          ),
        ),
        padding: const EdgeInsets.fromLTRB(
          DS.spacing20,
          DS.spacing16,
          DS.spacing20,
          DS.spacing20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 44,
                height: 4,
                decoration: BoxDecoration(
                  color: DS.borderSubtle,
                  borderRadius: DS.borderRadiusFull,
                ),
              ),
            ),
            const SizedBox(height: DS.spacing16),
            _Header(
              mode: widget.documentContextMode,
              docCount: readyDocs.length,
              onModeChanged: (mode) {
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                widget.onModeChanged?.call(mode);
              },
            ),
            const SizedBox(height: DS.spacing12),
            _ModeSelector(
              currentMode: widget.documentContextMode,
              onModeChanged: (mode) {
                SensoryFeedbackService.emit(SensoryFeedbackEvent.selection);
                widget.onModeChanged?.call(mode);
              },
            ),
            const SizedBox(height: DS.spacing16),
            if (widget.documentContextMode != DocumentContextMode.off)
              _RelevanceLegend(),
            if (widget.documentContextMode != DocumentContextMode.off)
              const SizedBox(height: DS.spacing8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 320),
              child: state.documents.when(
                loading: () => const Center(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: DS.spacing32),
                    child: CircularProgressIndicator(),
                  ),
                ),
                error: (error, _) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: DS.spacing12),
                  child: Text(
                    error.toString(),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.error,
                        ),
                  ),
                ),
                data: (_) {
                  if (readyDocs.isEmpty) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(
                        vertical: DS.spacing20,
                      ),
                      child: Text(
                        context.l10n.chatStudyMaterialsEmptySubtitle,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                              height: 1.5,
                            ),
                      ),
                    );
                  }
                  return ListView.separated(
                    shrinkWrap: true,
                    itemCount: readyDocs.length,
                    separatorBuilder: (_, __) =>
                        const SizedBox(height: DS.spacing10),
                    itemBuilder: (context, index) {
                      final doc = readyDocs[index];
                      final relevance = _relevanceOf(doc);
                      final isToggledOff = _toggledOff.contains(doc.fileId);
                      return _SourceRow(
                        document: doc,
                        relevance: relevance,
                        isEnabled: !isToggledOff &&
                            widget.documentContextMode !=
                                DocumentContextMode.off,
                        canToggle: widget.documentContextMode ==
                            DocumentContextMode.userSelected,
                        onToggle: () {
                          SensoryFeedbackService.emit(SensoryFeedbackEvent.tap);
                          setState(() {
                            if (isToggledOff) {
                              _toggledOff.remove(doc.fileId);
                            } else {
                              _toggledOff.add(doc.fileId);
                            }
                          });
                        },
                      );
                    },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  _SourceRelevance _relevanceOf(DocumentLibraryItem doc) {
    if (doc.citationInsight.totalReferences > 3) {
      return _SourceRelevance.high;
    }
    if (doc.knowledgeStarCount > 0 ||
        doc.qualityScore != null && doc.qualityScore! > 0.5) {
      return _SourceRelevance.medium;
    }
    return _SourceRelevance.low;
  }
}

enum _SourceRelevance { high, medium, low }

class _Header extends StatelessWidget {
  const _Header({
    required this.mode,
    required this.docCount,
    required this.onModeChanged,
  });

  final DocumentContextMode mode;
  final int docCount;
  final ValueChanged<DocumentContextMode> onModeChanged;

  @override
  Widget build(BuildContext context) {
    final isActive = mode != DocumentContextMode.off;
    return Row(
      children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: isActive
                ? DS.primaryBase.withValues(alpha: 0.12)
                : DS.surfaceSecondary,
            borderRadius: DS.borderRadius12,
          ),
          child: Icon(
            isActive
                ? Icons.auto_awesome_outlined
                : Icons.auto_awesome_outlined,
            color: isActive ? DS.primaryBase : DS.textSecondary,
            size: 20,
          ),
        ),
        const SizedBox(width: DS.spacing12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                context.l10n.chatStudyMaterialsLabel,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightSemibold,
                    ),
              ),
              const SizedBox(height: DS.spacing4),
              Text(
                isActive
                    ? context.l10n.chatStudyMaterialsAvailable(docCount)
                    : context.l10n.chatStudyMaterialsPausedDescription,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                      height: 1.4,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ModeSelector extends StatelessWidget {
  const _ModeSelector({
    required this.currentMode,
    required this.onModeChanged,
  });

  final DocumentContextMode currentMode;
  final ValueChanged<DocumentContextMode> onModeChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: DS.borderRadius8,
      ),
      child: Row(
        children: [
          _ModeChip(
            label: I18nService.instance.isChinese ? '自动' : 'Auto',
            selected: currentMode == DocumentContextMode.auto,
            onTap: () => onModeChanged(DocumentContextMode.auto),
          ),
          _ModeChip(
            label: context.l10n.chatStudyMySelection,
            selected: currentMode == DocumentContextMode.userSelected,
            onTap: () => onModeChanged(DocumentContextMode.userSelected),
          ),
          _ModeChip(
            label: I18nService.instance.isChinese ? '任务' : 'Task',
            selected: currentMode == DocumentContextMode.taskScope,
            onTap: () => onModeChanged(DocumentContextMode.taskScope),
          ),
          _ModeChip(
            label: context.l10n.chatStudyNoMaterial,
            selected: currentMode == DocumentContextMode.off,
            onTap: () => onModeChanged(DocumentContextMode.off),
          ),
        ],
      ),
    );
  }
}

class _ModeChip extends StatelessWidget {
  const _ModeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Semantics(
        button: true,
        label: 'Chat study materials sheet control 1',
        child: GestureDetector(
          onTap: onTap,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              color: selected ? DS.surfacePrimary : Colors.transparent,
              borderRadius: DS.borderRadius8,
              boxShadow: selected
                  ? [
                      BoxShadow(
                        color: DS.borderSubtle.withValues(alpha: 0.3),
                        blurRadius: 4,
                        offset: const Offset(0, 1),
                      ),
                    ]
                  : null,
            ),
            child: Center(
              child: Text(
                label,
                style: DS.labelSmall.copyWith(
                  color: selected ? DS.textPrimary : DS.textTertiary,
                  fontWeight: selected ? FontWeight.w500 : FontWeight.normal,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RelevanceLegend extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Row(
        children: [
          _LegendDot(
              color: DS.success, label: context.l10n.chatStudyHighRelevance),
          const SizedBox(width: 12),
          _LegendDot(
              color: DS.warning, label: context.l10n.chatStudyMediumRelevance),
          const SizedBox(width: 12),
          _LegendDot(
              color: DS.textTertiary, label: context.l10n.chatStudyNotAnalyzed),
        ],
      );
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: DS.labelSmall.copyWith(color: DS.textTertiary, fontSize: 11),
          ),
        ],
      );
}

class _SourceRow extends StatelessWidget {
  const _SourceRow({
    required this.document,
    required this.relevance,
    required this.isEnabled,
    required this.canToggle,
    required this.onToggle,
  });

  final DocumentLibraryItem document;
  final _SourceRelevance relevance;
  final bool isEnabled;
  final bool canToggle;
  final VoidCallback onToggle;

  Color get _relevanceColor {
    if (!isEnabled) return DS.textTertiary;
    switch (relevance) {
      case _SourceRelevance.high:
        return DS.success;
      case _SourceRelevance.medium:
        return DS.warning;
      case _SourceRelevance.low:
        return DS.textTertiary;
    }
  }

  String get _relevanceLabel {
    if (!isEnabled) return S.chatStudyClosed;
    switch (relevance) {
      case _SourceRelevance.high:
        return S.chatStudyHighRelevance;
      case _SourceRelevance.medium:
        return S.chatStudyMediumRelevance;
      case _SourceRelevance.low:
        return S.chatStudyNotAnalyzed;
    }
  }

  @override
  Widget build(BuildContext context) {
    final nodeCount = document.knowledgeStarCount;
    return Semantics(
      button: true,
      label: 'Chat study materials sheet control 2',
      child: GestureDetector(
        onTap: canToggle ? onToggle : null,
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: isEnabled ? 1.0 : 0.45,
          child: Container(
            padding: const EdgeInsets.all(DS.spacing12),
            decoration: BoxDecoration(
              color: DS.surfaceSecondary,
              borderRadius: DS.borderRadius16,
              border: Border.all(
                color: isEnabled
                    ? _relevanceColor.withValues(alpha: 0.25)
                    : DS.borderSubtle,
              ),
            ),
            child: Row(
              children: [
                // Relevance indicator dot
                Container(
                  width: 8,
                  height: 8,
                  margin: const EdgeInsets.only(right: 10),
                  decoration: BoxDecoration(
                    color: _relevanceColor,
                    shape: BoxShape.circle,
                  ),
                ),
                // File icon
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: DS.primaryBase.withValues(alpha: 0.08),
                    borderRadius: DS.borderRadius8,
                  ),
                  child: Icon(
                    _iconForType(document.fileType),
                    color: DS.primaryBase,
                    size: 16,
                  ),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        document.filename,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textPrimary,
                              fontWeight: DS.fontWeightSemibold,
                            ),
                      ),
                      const SizedBox(height: 3),
                      Row(
                        children: [
                          Text(
                            _relevanceLabel,
                            style: DS.labelSmall.copyWith(
                              color: _relevanceColor,
                              fontSize: 11,
                            ),
                          ),
                          if (nodeCount > 0) ...[
                            const SizedBox(width: 8),
                            Text(
                              context.l10n.chatStudyNodeCount(nodeCount),
                              style: DS.labelSmall.copyWith(
                                color: DS.textTertiary,
                                fontSize: 11,
                              ),
                            ),
                          ],
                          if (document.citationInsight.totalReferences > 0) ...[
                            const SizedBox(width: 8),
                            Text(
                              context.l10n.chatStudyCitationCount(
                                  document.citationInsight.totalReferences),
                              style: DS.labelSmall.copyWith(
                                color: DS.textTertiary,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                if (canToggle)
                  Icon(
                    isEnabled
                        ? Icons.check_circle
                        : Icons.remove_circle_outline,
                    size: 18,
                    color: isEnabled ? DS.success : DS.textTertiary,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  static IconData _iconForType(String fileType) {
    switch (fileType) {
      case 'pdf':
        return Icons.picture_as_pdf_outlined;
      case 'docx':
        return Icons.description_outlined;
      case 'pptx':
        return Icons.slideshow_outlined;
      case 'md':
        return Icons.notes_rounded;
      case 'image':
        return Icons.image_outlined;
      default:
        return Icons.insert_drive_file_outlined;
    }
  }
}
