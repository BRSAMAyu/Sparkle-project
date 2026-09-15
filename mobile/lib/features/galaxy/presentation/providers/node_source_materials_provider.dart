import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/knowledge/data/models/knowledge_detail_model.dart';

class NodeSourceExcerptViewData {
  const NodeSourceExcerptViewData({
    required this.chunkId,
    required this.preview,
    this.pageNumbers = const [],
    this.sectionTitle,
    this.fallbackOrdinal = 1,
  });

  final String chunkId;
  final String preview;
  final List<int> pageNumbers;
  final String? sectionTitle;
  final int fallbackOrdinal;
}

class NodeSourceDocumentViewData {
  const NodeSourceDocumentViewData({
    required this.document,
    required this.excerpts,
  });

  final NodeSourceDocumentRef document;
  final List<NodeSourceExcerptViewData> excerpts;
}

class NodeSourceMaterialsViewData {
  const NodeSourceMaterialsViewData({
    required this.nodeDetail,
    required this.documents,
  });

  final KnowledgeDetailResponse nodeDetail;
  final List<NodeSourceDocumentViewData> documents;

  NodeKnowledgeStats get knowledgeStats => nodeDetail.knowledgeStats;
  bool get hasPersonalUploads => knowledgeStats.hasPersonalUploads;
}

final nodeSourceMaterialsProvider =
    FutureProvider.family<NodeSourceMaterialsViewData, String>((
  ref,
  nodeId,
) async {
  final repository = ref.watch(enhancedGalaxyRepositoryProvider);

  final detailResult = await repository.getNodeDetail(nodeId);
  if (detailResult.isFailure) {
    throw StateError(
      detailResult.error?.toString() ?? 'Failed to load node source materials',
    );
  }

  final detail = detailResult.value;
  final chunksResult = await repository.getNodeSourceChunks(nodeId);
  final chunks = chunksResult.valueOrNull?.chunks ?? const <NodeSourceChunk>[];
  final chunksByFileId = <String, List<NodeSourceChunk>>{};

  for (final chunk in chunks) {
    chunksByFileId.putIfAbsent(chunk.fileId, () => <NodeSourceChunk>[]).add(
          chunk,
        );
  }

  final documents = detail.sourceDocuments.map((document) {
    final matchedChunks =
        chunksByFileId[document.fileId] ?? const <NodeSourceChunk>[];
    final excerpts = matchedChunks
        .take(3)
        .map(
          (chunk) => NodeSourceExcerptViewData(
            chunkId: chunk.chunkId,
            preview: chunk.displayPreview,
            pageNumbers: chunk.pageNumbers,
            sectionTitle: chunk.sectionTitle,
            fallbackOrdinal: chunk.chunkIndex + 1,
          ),
        )
        .toList(growable: false);

    if (excerpts.isNotEmpty) {
      return NodeSourceDocumentViewData(document: document, excerpts: excerpts);
    }

    return NodeSourceDocumentViewData(
      document: document,
      excerpts: document.previewChunks
          .take(3)
          .toList(growable: false)
          .asMap()
          .entries
          .map(
            (entry) => NodeSourceExcerptViewData(
              chunkId: '${document.fileId}_${entry.key}',
              preview: entry.value,
              fallbackOrdinal: entry.key + 1,
            ),
          )
          .toList(growable: false),
    );
  }).toList(growable: false);

  return NodeSourceMaterialsViewData(
    nodeDetail: detail,
    documents: documents,
  );
});
