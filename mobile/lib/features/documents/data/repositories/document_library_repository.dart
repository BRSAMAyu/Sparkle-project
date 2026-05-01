import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/features/documents/data/models/document_library_models.dart';

final documentLibraryRepositoryProvider =
    Provider<DocumentLibraryRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return DocumentLibraryRepository(apiClient.dio);
});

class DocumentLibraryRepository {
  DocumentLibraryRepository(this._dio);

  final Dio _dio;

  Future<List<DocumentLibraryItem>> listDocuments({
    int limit = 100,
    int offset = 0,
  }) async {
    final response = await _dio.get<dynamic>(
      ApiEndpoints.myFiles,
      queryParameters: {
        'limit': limit,
        'offset': offset,
      },
    );
    final data = ApiResponseParser.unwrapList(
      response.data,
      action: 'listDocuments',
    );
    return data
        .map(
          (item) => DocumentLibraryItem.fromJson(
            item as Map<String, dynamic>,
          ),
        )
        .toList();
  }

  Future<DocumentProcessingStatus?> getDocumentStatus(String fileId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        ApiEndpoints.documentStatus(fileId),
      );
      final payload = response.data;
      if (payload == null || payload.isEmpty) return null;
      return DocumentProcessingStatus.fromJson(payload);
    } on DioException catch (error) {
      debugPrint('Document status fetch failed for $fileId: $error');
      return null;
    }
  }

  Future<List<DocumentGalaxyNode>> listDocumentNodes(String fileId) async {
    try {
      final response = await _dio.get<dynamic>(
        ApiEndpoints.galaxyDocumentNodes(fileId),
      );
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'listDocumentNodes',
      );
      return data
          .map(
            (item) => DocumentGalaxyNode.fromJson(
              item as Map<String, dynamic>,
            ),
          )
          .toList();
    } on DioException catch (error) {
      debugPrint('Document nodes fetch failed for $fileId: $error');
      return const <DocumentGalaxyNode>[];
    }
  }

  Future<Map<String, String>> loadNodeSectorCodes() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        ApiEndpoints.galaxyGraph,
      );
      final payload = response.data ?? const <String, dynamic>{};
      final rawNodes = payload['nodes'] as List<dynamic>? ?? const <dynamic>[];
      final map = <String, String>{};
      for (final node in rawNodes) {
        if (node is! Map) continue;
        final nodeMap = Map<String, dynamic>.from(node);
        final nodeId = nodeMap['id']?.toString() ?? '';
        if (nodeId.isEmpty) continue;
        final sectorCode = nodeMap['sector_code']?.toString() ??
            (nodeMap['subject'] is Map
                ? (nodeMap['subject'] as Map)['sector_code']?.toString()
                : null) ??
            'VOID';
        map[nodeId] = sectorCode;
      }
      return map;
    } on DioException catch (error) {
      debugPrint('Galaxy graph fetch failed for document library: $error');
      return const <String, String>{};
    }
  }

  Future<Map<String, DocumentCitationInsight>> loadCitationInsights({
    int maxConversations = 12,
  }) async {
    final sessions = await _loadRecentSessions(limit: maxConversations);
    if (sessions.isEmpty) {
      return const <String, DocumentCitationInsight>{};
    }

    final now = DateTime.now();
    final weekBoundary = now.subtract(const Duration(days: 7));
    final aggregates = <String, _CitationAggregate>{};

    await Future.wait(
      sessions.map(
        (session) => _collectConversationCitations(
          session: session,
          weekBoundary: weekBoundary,
          aggregates: aggregates,
        ),
      ),
    );

    return {
      for (final entry in aggregates.entries)
        entry.key: entry.value.toInsight(),
    };
  }

  Future<void> deleteDocument(String fileId) async {
    await _dio.delete<void>(ApiEndpoints.file(fileId));
  }

  Future<void> shareDocumentToGroup({
    required String fileId,
    required String groupId,
  }) async {
    await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.groupFileShare(groupId, fileId),
      data: const {
        'send_message': true,
      },
    );
  }

  Future<List<_ConversationSummary>> _loadRecentSessions({
    required int limit,
  }) async {
    try {
      final response = await _dio.get<dynamic>('/chat/sessions');
      final data = ApiResponseParser.unwrapList(
        response.data,
        action: 'getRecentConversations',
      );
      final sessions = data
          .whereType<Map<String, dynamic>>()
          .map(_ConversationSummary.fromJson)
          .where((item) => item.sessionId.isNotEmpty)
          .toList()
        ..sort((left, right) => right.updatedAt.compareTo(left.updatedAt));
      return sessions.take(limit).toList(growable: false);
    } on DioException catch (error) {
      debugPrint('Recent conversation fetch failed: $error');
      return const <_ConversationSummary>[];
    }
  }

  Future<void> _collectConversationCitations({
    required _ConversationSummary session,
    required DateTime weekBoundary,
    required Map<String, _CitationAggregate> aggregates,
  }) async {
    try {
      final response = await _dio.get<dynamic>(
        '/chat/history/${session.sessionId}',
        queryParameters: const {
          'limit': 80,
        },
      );
      var data = response.data;
      if (data is Map<String, dynamic> && data['data'] is List) {
        data = data['data'];
      }
      if (data is! List) return;

      for (final item in data) {
        if (item is! Map<String, dynamic>) continue;
        final widgets = _extractWidgets(item);
        if (widgets.isEmpty) continue;
        final messageTime = _readDateTime(item['created_at']) ?? session.updatedAt;
        for (final widget in widgets) {
          if (widget['type']?.toString() != 'source_summary') continue;
          final citationList = (widget['data'] as Map<String, dynamic>?)?['citations'];
          if (citationList is! List) continue;

          for (final rawCitation in citationList) {
            if (rawCitation is! Map) continue;
            final citation = Map<String, dynamic>.from(rawCitation);
            final fileId = citation['file_id']?.toString() ??
                citation['source_file_id']?.toString() ??
                '';
            if (fileId.isEmpty) continue;
            final aggregate =
                aggregates.putIfAbsent(fileId, _CitationAggregate.new);
            aggregate.addCitation(
              sessionId: session.sessionId,
              citation: citation,
              referencedAt: messageTime,
              isWithinWeek: !messageTime.isBefore(weekBoundary),
            );
          }
        }
      }
    } on DioException catch (error) {
      debugPrint(
        'Conversation history fetch failed for ${session.sessionId}: $error',
      );
    }
  }

  List<Map<String, dynamic>> _extractWidgets(Map<String, dynamic> rawMessage) {
    final widgets = <Map<String, dynamic>>[];

    void addWidgetCandidate(Object? source) {
      if (source is! List) return;
      for (final item in source) {
        if (item is! Map) continue;
        final map = Map<String, dynamic>.from(item);
        final widgetType = map['type']?.toString().trim();
        final widgetData = map['data'];
        if (widgetType != null && widgetType.isNotEmpty && widgetData is Map) {
          widgets.add({
            'type': widgetType,
            'data': Map<String, dynamic>.from(widgetData),
          });
          continue;
        }

        final toolWidgetType = map['widget_type']?.toString().trim();
        final toolWidgetData = map['widget_data'];
        if (toolWidgetType != null &&
            toolWidgetType.isNotEmpty &&
            toolWidgetData is Map) {
          widgets.add({
            'type': toolWidgetType,
            'data': Map<String, dynamic>.from(toolWidgetData),
          });
        }
      }
    }

    addWidgetCandidate(rawMessage['widgets']);
    if (widgets.isEmpty) {
      addWidgetCandidate(rawMessage['actions']);
    }
    return widgets;
  }

  DateTime? _readDateTime(Object? raw) {
    if (raw is DateTime) return raw;
    if (raw is String) return DateTime.tryParse(raw);
    return null;
  }
}

class _ConversationSummary {
  const _ConversationSummary({
    required this.sessionId,
    required this.updatedAt,
  });

  factory _ConversationSummary.fromJson(Map<String, dynamic> json) {
    final updatedAt = DateTime.tryParse(
          json['updated_at']?.toString() ?? '',
        ) ??
        DateTime.tryParse(json['created_at']?.toString() ?? '') ??
        DateTime.now();
    return _ConversationSummary(
      sessionId:
          json['id']?.toString() ?? json['session_id']?.toString() ?? '',
      updatedAt: updatedAt,
    );
  }

  final String sessionId;
  final DateTime updatedAt;
}

class _CitationAggregate {
  int referencesThisWeek = 0;
  int totalReferences = 0;
  final Set<String> conversationIds = <String>{};
  final List<String> searchSnippets = <String>[];
  final Map<String, _CitationChunkAggregate> chunkAggregates =
      <String, _CitationChunkAggregate>{};

  void addCitation({
    required String sessionId,
    required Map<String, dynamic> citation,
    required DateTime referencedAt,
    required bool isWithinWeek,
  }) {
    totalReferences += 1;
    if (isWithinWeek) {
      referencesThisWeek += 1;
    }
    conversationIds.add(sessionId);

    final title = citation['title']?.toString().trim() ?? '';
    final content = citation['content']?.toString().trim() ?? '';
    final sectionTitle = citation['section_title']?.toString().trim();
    final preview = title.isNotEmpty ? title : content;
    if (preview.isNotEmpty) {
      searchSnippets.add(preview);
    }
    if ((sectionTitle ?? '').isNotEmpty) {
      searchSnippets.add(sectionTitle!);
    }

    final chunkIndex = (citation['chunk_index'] as num?)?.toInt();
    final key = [
      chunkIndex?.toString() ?? 'na',
      sectionTitle ?? '',
      title,
      content,
    ].join('|');

    final aggregate = chunkAggregates.putIfAbsent(
      key,
      () => _CitationChunkAggregate(
        label: title.isNotEmpty
            ? title
            : (sectionTitle?.isNotEmpty ?? false)
                ? sectionTitle!
                : 'Chunk ${chunkIndex ?? '?'}',
        preview: content.isNotEmpty ? content : title,
        chunkIndex: chunkIndex,
        sectionTitle: sectionTitle,
      ),
    );
    aggregate.addReference(referencedAt);
  }

  DocumentCitationInsight toInsight() {
    final chunks = chunkAggregates.values.toList()
      ..sort((left, right) {
        final hitCompare = right.hitCount.compareTo(left.hitCount);
        if (hitCompare != 0) return hitCompare;
        final rightTime = right.lastReferencedAt;
        final leftTime = left.lastReferencedAt;
        if (leftTime == null && rightTime == null) return 0;
        if (leftTime == null) return 1;
        if (rightTime == null) return -1;
        return rightTime.compareTo(leftTime);
      });

    return DocumentCitationInsight(
      referencesThisWeek: referencesThisWeek,
      totalReferences: totalReferences,
      conversationCount: conversationIds.length,
      topChunks: chunks.take(3).map((chunk) => chunk.toChunk()).toList(),
      searchSnippets: searchSnippets.take(24).toList(growable: false),
    );
  }
}

class _CitationChunkAggregate {
  _CitationChunkAggregate({
    required this.label,
    required this.preview,
    this.chunkIndex,
    this.sectionTitle,
  });

  final String label;
  final String preview;
  final int? chunkIndex;
  final String? sectionTitle;
  int hitCount = 0;
  DateTime? lastReferencedAt;

  void addReference(DateTime referencedAt) {
    hitCount += 1;
    if (lastReferencedAt == null || referencedAt.isAfter(lastReferencedAt!)) {
      lastReferencedAt = referencedAt;
    }
  }

  DocumentCitationChunk toChunk() {
    return DocumentCitationChunk(
      label: label,
      preview: preview,
      hitCount: hitCount,
      chunkIndex: chunkIndex,
      sectionTitle: sectionTitle,
      lastReferencedAt: lastReferencedAt,
    );
  }
}
