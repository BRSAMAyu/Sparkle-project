import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';
import 'package:sparkle/features/documents/presentation/providers/document_library_provider.dart';

class StudyMaterialsSheet extends ConsumerWidget {
  const StudyMaterialsSheet({
    required this.retrievalEnabled,
    super.key,
  });

  final bool retrievalEnabled;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(documentLibraryProvider);
    final readyDocs = (state.documents.valueOrNull ??
            const <DocumentLibraryItem>[])
        .where((doc) => doc.effectiveStatus == DocumentStatus.ready)
        .toList()
      ..sort((a, b) => b.uploadedAt.compareTo(a.uploadedAt));

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
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: retrievalEnabled
                        ? DS.primaryBase.withValues(alpha: 0.12)
                        : DS.surfaceSecondary,
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Icon(
                    retrievalEnabled
                        ? Icons.menu_book_rounded
                        : Icons.menu_book_outlined,
                    color: retrievalEnabled ? DS.primaryBase : DS.textSecondary,
                  ),
                ),
                const SizedBox(width: DS.spacing12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.chatStudyMaterialsLabel,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  color: DS.textPrimary,
                                  fontWeight: DS.fontWeightSemibold,
                                ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        retrievalEnabled
                            ? context.l10n.chatStudyMaterialsAvailable(
                                readyDocs.length,
                              )
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
            ),
            const SizedBox(height: DS.spacing16),
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
                      return _StudyMaterialRow(document: doc);
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
}

class _StudyMaterialRow extends StatelessWidget {
  const _StudyMaterialRow({required this.document});

  final DocumentLibraryItem document;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing12),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius16,
          border: Border.all(color: DS.borderSubtle),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: DS.primaryBase.withValues(alpha: 0.1),
                borderRadius: DS.borderRadius12,
              ),
              child: Icon(
                _iconForType(document.fileType),
                color: DS.primaryBase,
                size: 18,
              ),
            ),
            const SizedBox(width: DS.spacing12),
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
                  const SizedBox(height: DS.spacing4),
                  Text(
                    document.knowledgeStarCount > 0
                        ? context.l10n.chatStudyMaterialsKnowledgeNodes(
                            document.knowledgeStarCount,
                          )
                        : context.l10n.chatStudyMaterialsReady,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: DS.textSecondary,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

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
