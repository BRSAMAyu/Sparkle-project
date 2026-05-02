import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';
import 'package:sparkle/features/documents/data/repositories/document_library_repository.dart';

class DocumentLibraryState {
  const DocumentLibraryState({
    this.documents = const AsyncValue.loading(),
    this.searchQuery = '',
    this.statusFilter,
    this.dateFilter = DocumentDateFilter.all,
    this.highlyCitedOnly = false,
    this.subjectFilter,
    this.nodeFilterId,
    this.nodeFilterName,
    this.expandedDocumentIds = const <String>{},
  });

  final AsyncValue<List<DocumentLibraryItem>> documents;
  final String searchQuery;
  final DocumentStatus? statusFilter;
  final DocumentDateFilter dateFilter;
  final bool highlyCitedOnly;
  final String? subjectFilter;
  final String? nodeFilterId;
  final String? nodeFilterName;
  final Set<String> expandedDocumentIds;

  DocumentLibraryState copyWith({
    AsyncValue<List<DocumentLibraryItem>>? documents,
    String? searchQuery,
    DocumentStatus? Function()? statusFilter,
    DocumentDateFilter? dateFilter,
    bool? highlyCitedOnly,
    String? Function()? subjectFilter,
    String? Function()? nodeFilterId,
    String? Function()? nodeFilterName,
    Set<String>? expandedDocumentIds,
  }) {
    return DocumentLibraryState(
      documents: documents ?? this.documents,
      searchQuery: searchQuery ?? this.searchQuery,
      statusFilter: statusFilter != null ? statusFilter() : this.statusFilter,
      dateFilter: dateFilter ?? this.dateFilter,
      highlyCitedOnly: highlyCitedOnly ?? this.highlyCitedOnly,
      subjectFilter:
          subjectFilter != null ? subjectFilter() : this.subjectFilter,
      nodeFilterId: nodeFilterId != null ? nodeFilterId() : this.nodeFilterId,
      nodeFilterName:
          nodeFilterName != null ? nodeFilterName() : this.nodeFilterName,
      expandedDocumentIds: expandedDocumentIds ?? this.expandedDocumentIds,
    );
  }

  List<DocumentLibraryItem> get allDocuments =>
      documents.valueOrNull ?? const <DocumentLibraryItem>[];

  List<DocumentLibraryItem> get filtered {
    final now = DateTime.now();
    final visible = allDocuments.where((doc) {
      final matchesQuery = doc.matchesQuery(searchQuery);
      final matchesStatus =
          statusFilter == null || doc.effectiveStatus == statusFilter;
      final matchesDate = dateFilter.matches(doc.uploadedAt, now);
      final matchesCitation = !highlyCitedOnly || doc.isHighlyCited;
      final matchesSubject = subjectFilter == null ||
          (doc.subjectArea ?? '').toUpperCase() == subjectFilter;
      final matchesNode = nodeFilterId == null ||
          doc.attachedNodes.any((node) => node.nodeId == nodeFilterId);
      final matchesLifecycle =
          doc.lifecycleStatus != SourceLifecycleStatus.revoked;
      return matchesQuery &&
          matchesStatus &&
          matchesDate &&
          matchesCitation &&
          matchesSubject &&
          matchesNode &&
          matchesLifecycle;
    }).toList()
      ..sort((left, right) {
        final statusCompare = _statusRank(left.effectiveStatus)
            .compareTo(_statusRank(right.effectiveStatus));
        if (statusCompare != 0) return statusCompare;
        final citationCompare = right.citationInsight.referencesThisWeek
            .compareTo(left.citationInsight.referencesThisWeek);
        if (citationCompare != 0) return citationCompare;
        return right.uploadedAt.compareTo(left.uploadedAt);
      });
    return visible;
  }

  List<String> get availableSubjectFilters {
    final values = allDocuments
        .map((doc) => (doc.subjectArea ?? '').trim().toUpperCase())
        .where((value) => value.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    return values;
  }

  static int _statusRank(DocumentStatus status) {
    switch (status) {
      case DocumentStatus.processing:
        return 0;
      case DocumentStatus.ready:
        return 1;
      case DocumentStatus.failed:
        return 2;
    }
  }
}

class DocumentLibraryNotifier extends StateNotifier<DocumentLibraryState> {
  DocumentLibraryNotifier(this._repository)
      : super(const DocumentLibraryState()) {
    _load();
  }

  final DocumentLibraryRepository _repository;

  Future<void> _load() async {
    state = state.copyWith(
      documents: const AsyncValue.loading(),
    );
    try {
      final docs = await _repository.listDocuments();
      final citationInsights = await _repository.loadCitationInsights();
      final nodeSectorCodes = await _repository.loadNodeSectorCodes();

      final enriched = await Future.wait(
        docs.map((doc) async {
          final status = await _repository.getDocumentStatus(doc.fileId);
          final nodes = await _repository.listDocumentNodes(doc.fileId);
          final subjectCode = _inferSubjectCode(nodes, nodeSectorCodes);
          return doc.copyWith(
            processingStatus: status,
            attachedNodes: nodes,
            citationInsight:
                citationInsights[doc.fileId] ?? const DocumentCitationInsight(),
            subjectArea: subjectCode,
            errorMessage: status?.error ?? doc.errorMessage,
          );
        }),
      );

      state = state.copyWith(
        documents: AsyncValue.data(enriched),
      );
    } on Exception catch (error, stackTrace) {
      state = state.copyWith(
        documents: AsyncValue.error(error, stackTrace),
      );
    }
  }

  Future<void> refresh() => _load();

  void setSearchQuery(String query) {
    state = state.copyWith(searchQuery: query);
  }

  void setStatusFilter(DocumentStatus? status) {
    state = state.copyWith(statusFilter: () => status);
  }

  void setDateFilter(DocumentDateFilter filter) {
    state = state.copyWith(dateFilter: filter);
  }

  void toggleHighlyCitedOnly() {
    state = state.copyWith(highlyCitedOnly: !state.highlyCitedOnly);
  }

  void setSubjectFilter(String? subjectCode) {
    state = state.copyWith(subjectFilter: () => subjectCode);
  }

  void setNodeFilter({
    required String nodeId,
    required String nodeName,
  }) {
    state = state.copyWith(
      nodeFilterId: () => nodeId,
      nodeFilterName: () => nodeName,
    );
  }

  void clearNodeFilter() {
    state = state.copyWith(
      nodeFilterId: () => null,
      nodeFilterName: () => null,
    );
  }

  void toggleExpanded(String fileId) {
    final nextExpanded = Set<String>.from(state.expandedDocumentIds);
    if (!nextExpanded.add(fileId)) {
      nextExpanded.remove(fileId);
    }
    state = state.copyWith(expandedDocumentIds: nextExpanded);
  }

  Future<void> deleteDocument(String fileId) async {
    final previous =
        state.documents.valueOrNull ?? const <DocumentLibraryItem>[];
    final updated = previous.where((doc) => doc.fileId != fileId).toList();
    final nextExpanded = Set<String>.from(state.expandedDocumentIds)
      ..remove(fileId);

    state = state.copyWith(
      documents: AsyncValue.data(updated),
      expandedDocumentIds: nextExpanded,
    );

    try {
      await _repository.deleteDocument(fileId);
    } on Exception {
      state = state.copyWith(
        documents: AsyncValue.data(previous),
      );
      rethrow;
    }
  }

  Future<void> archiveDocument(String fileId) async {
    await _applyLifecycleAction(
      fileId,
      nextStatus: SourceLifecycleStatus.archived,
      action: () => _repository.archiveDocument(fileId),
    );
  }

  Future<void> restoreDocument(String fileId) async {
    await _applyLifecycleAction(
      fileId,
      nextStatus: SourceLifecycleStatus.active,
      action: () => _repository.restoreDocument(fileId),
    );
  }

  Future<void> revokeDocument(String fileId) async {
    await _applyLifecycleAction(
      fileId,
      nextStatus: SourceLifecycleStatus.revoked,
      action: () => _repository.revokeDocument(fileId),
    );
  }

  Future<void> _applyLifecycleAction(
    String fileId, {
    required SourceLifecycleStatus nextStatus,
    required Future<void> Function() action,
  }) async {
    final previous =
        state.documents.valueOrNull ?? const <DocumentLibraryItem>[];
    final updated = previous
        .map(
          (doc) => doc.fileId == fileId
              ? doc.copyWith(lifecycleStatus: nextStatus)
              : doc,
        )
        .toList();
    state = state.copyWith(documents: AsyncValue.data(updated));

    try {
      await action();
    } on Exception {
      state = state.copyWith(documents: AsyncValue.data(previous));
      rethrow;
    }
  }

  Future<void> shareToGroup({
    required String fileId,
    required String groupId,
  }) {
    return _repository.shareDocumentToGroup(
      fileId: fileId,
      groupId: groupId,
    );
  }

  static String? _inferSubjectCode(
    List<DocumentGalaxyNode> nodes,
    Map<String, String> nodeSectorCodes,
  ) {
    if (nodes.isEmpty) return null;

    final counts = <String, int>{};
    for (final node in nodes) {
      final sectorCode =
          (nodeSectorCodes[node.nodeId] ?? 'VOID').trim().toUpperCase();
      if (sectorCode.isEmpty) continue;
      counts.update(sectorCode, (value) => value + 1, ifAbsent: () => 1);
    }

    if (counts.isEmpty) return 'VOID';

    final sorted = counts.entries.toList()
      ..sort((left, right) => right.value.compareTo(left.value));
    return sorted.first.key;
  }
}

final documentLibraryProvider =
    StateNotifierProvider<DocumentLibraryNotifier, DocumentLibraryState>(
  (ref) => DocumentLibraryNotifier(
    ref.watch(documentLibraryRepositoryProvider),
  ),
);
