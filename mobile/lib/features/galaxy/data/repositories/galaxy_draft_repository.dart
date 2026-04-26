import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/galaxy/data/models/galaxy_draft_review_models.dart';

final galaxyDraftRepositoryProvider = Provider<GalaxyDraftRepository>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GalaxyDraftRepository(apiClient.dio);
});

class GalaxyDraftRepository {
  GalaxyDraftRepository(this._dio);

  final Dio _dio;

  Future<List<GalaxyDraftBatch>> listPendingDrafts() async {
    if (DemoDataService.isDemoMode) {
      return _buildMockBatches();
    }

    try {
      final response = await _dio.get<dynamic>(ApiEndpoints.galaxyDrafts);
      final batches = _parseDraftBatches(response.data);
      if (batches.isNotEmpty) {
        return batches;
      }
      if (kDebugMode) {
        return _buildMockBatches();
      }
      return const <GalaxyDraftBatch>[];
    } on DioException catch (error) {
      if (kDebugMode) {
        debugPrint('Using mock galaxy drafts after API error: $error');
        return _buildMockBatches();
      }
      throw Exception(_extractMessage(error));
    }
  }

  List<GalaxyDraftBatch> _parseDraftBatches(dynamic raw) {
    if (raw == null) {
      return const <GalaxyDraftBatch>[];
    }

    if (raw is Map<String, dynamic>) {
      final draftList = raw['batches'] ??
          raw['draft_batches'] ??
          raw['drafts'] ??
          raw['items'] ??
          raw['data'];
      if (draftList is List<dynamic>) {
        return _buildBatchesFromList(draftList);
      }
      if (raw.containsKey('drafts') || raw.containsKey('nodes')) {
        return [GalaxyDraftBatch.fromJson(raw)];
      }
    }

    final items = ApiResponseParser.unwrapList(
      raw,
      action: 'listPendingDrafts',
    );
    return _buildBatchesFromList(items);
  }

  List<GalaxyDraftBatch> _buildBatchesFromList(List<dynamic> items) {
    if (items.isEmpty) {
      return const <GalaxyDraftBatch>[];
    }

    final normalized = items
        .where((item) => item is Map)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList(growable: false);

    if (normalized.isEmpty) {
      return const <GalaxyDraftBatch>[];
    }

    final looksBatched = normalized.any(
      (item) => item.containsKey('drafts') || item.containsKey('nodes'),
    );
    if (looksBatched) {
      return normalized
          .map(GalaxyDraftBatch.fromJson)
          .where((batch) => batch.drafts.isNotEmpty)
          .toList(growable: false);
    }

    final grouped = <String, List<Map<String, dynamic>>>{};
    final metadata = <String, Map<String, dynamic>>{};
    for (final item in normalized) {
      final batchId = _readString(
        item,
        const ['batch_id', 'draft_batch_id', 'document_id', 'source_file_id'],
      );
      grouped.putIfAbsent(batchId, () => <Map<String, dynamic>>[]).add(item);
      metadata.putIfAbsent(batchId, () => item);
    }

    return grouped.entries.map((entry) {
      final seed = metadata[entry.key]!;
      return GalaxyDraftBatch(
        id: entry.key,
        documentId: _readString(
          seed,
          const ['document_id', 'file_id', 'source_file_id'],
        ),
        documentName: _readString(
          seed,
          const ['document_name', 'file_name', 'filename', 'source_file_name'],
        ),
        createdAt: DateTime.tryParse(
              _readString(
                seed,
                const ['created_at', 'updated_at', 'generated_at'],
              ),
            ) ??
            DateTime.now(),
        drafts:
            entry.value.map(GalaxyDraftNode.fromJson).toList(growable: false),
      );
    }).toList(growable: false);
  }

  List<GalaxyDraftBatch> _buildMockBatches() {
    final now = DateTime.now();
    return [
      GalaxyDraftBatch(
        id: 'mock-os-pdf',
        documentId: 'mock-doc-os',
        documentName: 'OS.pdf',
        createdAt: now.subtract(const Duration(minutes: 3)),
        drafts: const [
          GalaxyDraftNode(
            id: 'draft-process-scheduling',
            proposedName: 'Process Scheduling',
            proposedDescription:
                'How the operating system decides which process gets CPU time, and why fairness, responsiveness, and throughput trade off against each other.',
            excerpts: [
              'Round-robin scheduling improves responsiveness by assigning each runnable process a small time slice before the CPU rotates to the next task.',
              'Shortest-job-first minimizes average waiting time, but it depends on a prediction of future burst length that is rarely perfect in practice.',
              'Preemption lets the kernel interrupt a running process so higher-priority work can run immediately.',
            ],
            similarity: GalaxyDraftSimilarity(
              existingNodeId: 'existing-os-concepts',
              existingNodeName: 'OS Concepts',
              similarityPercent: 87,
            ),
          ),
          GalaxyDraftNode(
            id: 'draft-deadlocks',
            proposedName: 'Deadlocks',
            proposedDescription:
                'Conditions that cause processes to wait on one another forever, plus the detection and prevention strategies used to escape them.',
            excerpts: [
              'A deadlock requires mutual exclusion, hold-and-wait, no preemption, and circular wait to all exist at the same time.',
              'Banker-style avoidance keeps the system in a safe state by only granting requests that preserve a completion path.',
              'Detection-based systems allow deadlocks to occur, then recover by terminating or rolling back one of the blocked processes.',
            ],
          ),
          GalaxyDraftNode(
            id: 'draft-virtual-memory',
            proposedName: 'Virtual Memory',
            proposedDescription:
                'How paging, page faults, and replacement policies create the illusion of large continuous memory while protecting processes from one another.',
            excerpts: [
              'Demand paging delays loading a page until the process actually touches an address mapped to that page.',
              'A page fault traps into the kernel, which must locate the missing page, possibly evict another frame, and then resume execution.',
              'Locality matters because replacement policies work best when recently used pages predict near-future accesses.',
            ],
            similarity: GalaxyDraftSimilarity(
              existingNodeId: 'existing-memory-hierarchy',
              existingNodeName: 'Memory Hierarchy',
              similarityPercent: 74,
            ),
          ),
          GalaxyDraftNode(
            id: 'draft-file-systems',
            proposedName: 'File System Journaling',
            proposedDescription:
                'Why journals exist, what metadata they protect, and how they shorten crash recovery after an interrupted write.',
            excerpts: [
              'A journal records intended filesystem updates before applying them to the main data structures.',
              'Metadata journaling speeds recovery because the filesystem can replay or discard a short log instead of scanning the entire disk.',
              'Write ordering is crucial: if the log hits disk after the metadata mutation, the recovery guarantee breaks.',
            ],
          ),
          GalaxyDraftNode(
            id: 'draft-synchronization',
            proposedName: 'Thread Synchronization',
            proposedDescription:
                'Locks, semaphores, and condition variables coordinate concurrent access to shared state while balancing safety and performance.',
            excerpts: [
              'Critical sections protect shared state so only one thread mutates it at a time.',
              'Condition variables let threads sleep until some state predicate becomes true instead of spinning wastefully.',
              'Fine-grained locking increases concurrency, but it also raises the risk of deadlocks and lock-ordering bugs.',
            ],
            similarity: GalaxyDraftSimilarity(
              existingNodeId: 'existing-concurrency',
              existingNodeName: 'Concurrency Basics',
              similarityPercent: 81,
            ),
          ),
        ],
      ),
    ];
  }

  String _extractMessage(DioException error) {
    final responseData = error.response?.data;
    if (responseData is Map<String, dynamic>) {
      final detail = responseData['detail']?.toString();
      if (detail != null && detail.isNotEmpty) {
        return detail;
      }
      final message = responseData['message']?.toString();
      if (message != null && message.isNotEmpty) {
        return message;
      }
    }
    return error.message ?? 'Failed to load galaxy drafts';
  }
}

String _readString(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    final text = json[key]?.toString().trim() ?? '';
    if (text.isNotEmpty) {
      return text;
    }
  }
  return '';
}
