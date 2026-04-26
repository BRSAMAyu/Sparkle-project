enum DocumentStatus {
  processing,
  ready,
  failed;

  static DocumentStatus fromRaw(String? value) {
    switch ((value ?? '').trim().toLowerCase()) {
      case 'processed':
      case 'done':
      case 'ready':
        return DocumentStatus.ready;
      case 'failed':
      case 'error':
        return DocumentStatus.failed;
      default:
        return DocumentStatus.processing;
    }
  }
}

enum DocumentDateFilter {
  all,
  last7Days,
  last30Days,
  last90Days;

  bool matches(DateTime uploadedAt, DateTime now) {
    switch (this) {
      case DocumentDateFilter.all:
        return true;
      case DocumentDateFilter.last7Days:
        return uploadedAt.isAfter(now.subtract(const Duration(days: 7)));
      case DocumentDateFilter.last30Days:
        return uploadedAt.isAfter(now.subtract(const Duration(days: 30)));
      case DocumentDateFilter.last90Days:
        return uploadedAt.isAfter(now.subtract(const Duration(days: 90)));
    }
  }
}

class DocumentProcessingStatus {
  const DocumentProcessingStatus({
    required this.status,
    required this.progressPercent,
    required this.stage,
    this.nodesFound,
    this.error,
  });

  factory DocumentProcessingStatus.fromJson(Map<String, dynamic> json) {
    final progress = (json['progress_percent'] as num?)?.toInt() ??
        (json['progress'] as num?)?.toInt() ??
        0;
    return DocumentProcessingStatus(
      status: DocumentStatus.fromRaw(json['status']?.toString()),
      progressPercent: progress.clamp(0, 100),
      stage: json['stage']?.toString() ?? '',
      nodesFound: (json['nodes_found'] as num?)?.toInt(),
      error: json['error']?.toString(),
    );
  }

  final DocumentStatus status;
  final int progressPercent;
  final String stage;
  final int? nodesFound;
  final String? error;

  bool get isProcessing => status == DocumentStatus.processing;
  bool get isReady => status == DocumentStatus.ready;
  bool get isFailed => status == DocumentStatus.failed;
}

class DocumentGalaxyNode {
  const DocumentGalaxyNode({
    required this.nodeId,
    required this.fileId,
    required this.name,
    required this.sourceType,
    required this.status,
    required this.isPrimary,
    this.description,
    this.chunkRefs,
    this.attachedAt,
    this.updatedAt,
  });

  factory DocumentGalaxyNode.fromJson(Map<String, dynamic> json) {
    return DocumentGalaxyNode(
      nodeId: json['node_id']?.toString() ?? '',
      fileId: json['file_id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      description: json['description']?.toString(),
      sourceType: json['source_type']?.toString() ?? 'seed',
      status: json['status']?.toString() ?? 'published',
      isPrimary: json['is_primary'] as bool? ?? false,
      chunkRefs: json['chunk_refs'],
      attachedAt: _readDateTime(json['attached_at']),
      updatedAt: _readDateTime(json['updated_at']),
    );
  }

  final String nodeId;
  final String fileId;
  final String name;
  final String? description;
  final String sourceType;
  final String status;
  final bool isPrimary;
  final Object? chunkRefs;
  final DateTime? attachedAt;
  final DateTime? updatedAt;

  int get chunkReferenceCount {
    final refs = chunkRefs;
    if (refs is List) return refs.length;
    if (refs is Map) return refs.length;
    return 0;
  }
}

class DocumentCitationChunk {
  const DocumentCitationChunk({
    required this.label,
    required this.preview,
    required this.hitCount,
    this.chunkIndex,
    this.sectionTitle,
    this.lastReferencedAt,
  });

  final String label;
  final String preview;
  final int hitCount;
  final int? chunkIndex;
  final String? sectionTitle;
  final DateTime? lastReferencedAt;
}

class DocumentCitationInsight {
  const DocumentCitationInsight({
    this.referencesThisWeek = 0,
    this.totalReferences = 0,
    this.conversationCount = 0,
    this.topChunks = const <DocumentCitationChunk>[],
    this.searchSnippets = const <String>[],
  });

  final int referencesThisWeek;
  final int totalReferences;
  final int conversationCount;
  final List<DocumentCitationChunk> topChunks;
  final List<String> searchSnippets;

  bool get isHighlyCited => totalReferences >= 3 || referencesThisWeek >= 2;
}

class DocumentLibraryItem {
  const DocumentLibraryItem({
    required this.fileId,
    required this.filename,
    required this.fileType,
    required this.rawStatus,
    required this.uploadedAt,
    required this.visibility,
    this.fileSizeBytes,
    this.processingStatus,
    this.attachedNodes = const <DocumentGalaxyNode>[],
    this.citationInsight = const DocumentCitationInsight(),
    this.subjectArea,
    this.errorMessage,
  });

  factory DocumentLibraryItem.fromJson(Map<String, dynamic> json) {
    final filename =
        json['file_name']?.toString() ?? json['filename']?.toString() ?? '';
    final mimeType = json['mime_type']?.toString() ?? '';
    return DocumentLibraryItem(
      fileId: json['id']?.toString() ?? json['file_id']?.toString() ?? '',
      filename: filename,
      fileType: inferFileType(mimeType, filename),
      rawStatus: DocumentStatus.fromRaw(json['status']?.toString()),
      uploadedAt: _readDateTime(
            json['created_at'] ?? json['uploaded_at'] ?? json['updated_at'],
          ) ??
          DateTime.now(),
      visibility: json['visibility']?.toString() ?? 'private',
      fileSizeBytes: (json['file_size'] as num?)?.toInt(),
      errorMessage: json['error_message']?.toString(),
    );
  }

  final String fileId;
  final String filename;
  final String fileType;
  final DocumentStatus rawStatus;
  final DateTime uploadedAt;
  final String visibility;
  final int? fileSizeBytes;
  final DocumentProcessingStatus? processingStatus;
  final List<DocumentGalaxyNode> attachedNodes;
  final DocumentCitationInsight citationInsight;
  final String? subjectArea;
  final String? errorMessage;

  DocumentLibraryItem copyWith({
    String? fileId,
    String? filename,
    String? fileType,
    DocumentStatus? rawStatus,
    DateTime? uploadedAt,
    String? visibility,
    int? fileSizeBytes,
    DocumentProcessingStatus? processingStatus,
    List<DocumentGalaxyNode>? attachedNodes,
    DocumentCitationInsight? citationInsight,
    String? subjectArea,
    String? errorMessage,
  }) {
    return DocumentLibraryItem(
      fileId: fileId ?? this.fileId,
      filename: filename ?? this.filename,
      fileType: fileType ?? this.fileType,
      rawStatus: rawStatus ?? this.rawStatus,
      uploadedAt: uploadedAt ?? this.uploadedAt,
      visibility: visibility ?? this.visibility,
      fileSizeBytes: fileSizeBytes ?? this.fileSizeBytes,
      processingStatus: processingStatus ?? this.processingStatus,
      attachedNodes: attachedNodes ?? this.attachedNodes,
      citationInsight: citationInsight ?? this.citationInsight,
      subjectArea: subjectArea ?? this.subjectArea,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }

  DocumentStatus get effectiveStatus => processingStatus?.status ?? rawStatus;

  int get knowledgeStarCount {
    final attachedCount = attachedNodes.length;
    final statusCount = processingStatus?.nodesFound ?? 0;
    return attachedCount > statusCount ? attachedCount : statusCount;
  }

  bool get isHighlyCited => citationInsight.isHighlyCited;

  Iterable<String> get searchCorpus sync* {
    yield filename;
    if ((subjectArea ?? '').trim().isNotEmpty) {
      yield subjectArea!;
    }
    for (final node in attachedNodes) {
      yield node.name;
      if ((node.description ?? '').trim().isNotEmpty) {
        yield node.description!;
      }
    }
    for (final snippet in citationInsight.searchSnippets) {
      if (snippet.trim().isNotEmpty) {
        yield snippet;
      }
    }
  }

  bool matchesQuery(String query) {
    final normalized = query.trim().toLowerCase();
    if (normalized.isEmpty) return true;
    return searchCorpus.any((entry) => entry.toLowerCase().contains(normalized));
  }
}

String inferFileType(String mimeType, String filename) {
  final lower = filename.toLowerCase();
  if (lower.endsWith('.pdf') || mimeType.contains('pdf')) return 'pdf';
  if (lower.endsWith('.docx') ||
      lower.endsWith('.doc') ||
      mimeType.contains('word') ||
      mimeType.contains('msword')) {
    return 'docx';
  }
  if (lower.endsWith('.pptx') ||
      lower.endsWith('.ppt') ||
      mimeType.contains('presentationml') ||
      mimeType.contains('powerpoint')) {
    return 'pptx';
  }
  if (lower.endsWith('.md') ||
      lower.endsWith('.markdown') ||
      lower.endsWith('.txt') ||
      mimeType.contains('markdown') ||
      mimeType.contains('plain')) {
    return 'md';
  }
  if (mimeType.startsWith('image/')) return 'image';
  return 'file';
}

DateTime? _readDateTime(Object? raw) {
  if (raw is DateTime) return raw;
  if (raw is String) return DateTime.tryParse(raw);
  return null;
}
