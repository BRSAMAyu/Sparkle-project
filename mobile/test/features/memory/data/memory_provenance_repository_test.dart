import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';

/// U-03 操作接线测试：请求形状与 M-08 真实契约逐字段对齐
/// （backend/app/api/v1/memory_provenance.py）。
class _RecordingApiClient implements ApiClient {
  final List<(String method, String path, Object? body)> calls = [];

  Map<String, dynamic> response = {};

  void reply(Map<String, dynamic> json) => response = json;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    calls.add(('GET', _withQuery(path, queryParameters), null));
    return Response<T>(requestOptions: RequestOptions(path: path), data: response as T);
  }

  String _withQuery(String path, Map<String, dynamic>? query) {
    if (query == null || query.isEmpty) {
      return path;
    }
    final encoded = query.entries
        .map((e) => '${e.key}=${Uri.encodeQueryComponent('${e.value}')}')
        .join('&');
    return '$path?$encoded';
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    calls.add(('POST', path, data));
    return Response<T>(requestOptions: RequestOptions(path: path), data: response as T);
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    calls.add(('PUT', path, data));
    return Response<T>(requestOptions: RequestOptions(path: path), data: response as T);
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      throw UnimplementedError();

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Dio get dio => throw UnimplementedError();
}

ProvenanceMemoryItem _item({String bucket = 'told', String kind = 'episodic'}) =>
    ProvenanceMemoryItem(
      kind: kind,
      id: '11111111-1111-1111-1111-111111111111',
      ref: 'memory://$kind/11111111-1111-1111-1111-111111111111',
      bucket: understandingBucketFromName(bucket)!,
      bucketLabel: '你告诉我的',
      content: '我在准备离散数学期末考试',
      status: 'active',
      scope: const {'level': 'global'},
      correctionCount: 0,
      evidenceMissing: false,
      confidenceTier: 'confirmed',
      confidenceTierLabel: '已确认',
      sourceLabel: '你告诉我的',
      sourceKnown: true,
      actions: const ['update', 'revoke', 'view_source', 'pause'],
      updatedAt: DateTime(2026, 9, 20),
    );

void main() {
  group('MemoryProvenanceRepository request shapes (M-08 contract)', () {
    test('listItems hits GET /memory/provenance/items with bucket filter', () async {
      final api = _RecordingApiClient()
        ..reply({
          'items': [
            {
              'kind': 'episodic',
              'id': '11111111-1111-1111-1111-111111111111',
              'ref': 'memory://episodic/11111111-1111-1111-1111-111111111111',
              'bucket': 'told',
              'bucket_label': '你告诉我的',
              'content': '我在准备离散数学期末考试',
              'status': 'active',
              'scope': {'level': 'global'},
              'correction_count': 0,
              'evidence_missing': false,
              'confidence_tier': 'confirmed',
              'confidence_tier_label': '已确认',
              'source_label': '你告诉我的',
              'source_known': true,
              'epistemic_class': 'fact',
              'actions': ['update', 'revoke', 'view_source', 'pause'],
              'updated_at': '2026-09-20T10:00:00',
            }
          ],
          'bucket_counts': {'told': 1, 'observed': 0, 'uncertain': 0, 'effective': 0},
          'total': 1,
          'offset': 0,
          'limit': 200,
          'has_more': false,
          'scan_capped': false,
        });
      final repo = MemoryProvenanceRepository(api);

      final result = await repo.listItems(bucket: UnderstandingBucket.told);

      expect(api.calls.single.$1, 'GET');
      expect(api.calls.single.$2, startsWith('/memory/provenance/items?'));
      expect(api.calls.single.$2, contains('bucket=told'));
      expect(result.items, hasLength(1));
      expect(result.items.single.bucket, UnderstandingBucket.told);
      expect(result.items.single.bucketLabel, '你告诉我的');
      expect(result.items.single.actions, contains('pause'));
    });

    test('updateItem POSTs corrected content to the update endpoint', () async {
      final api = _RecordingApiClient()
        ..reply({
          ..._item().toJsonLike(),
          'superseded_id': '11111111-1111-1111-1111-111111111111',
          'memory_epoch': 7,
        });
      final repo = MemoryProvenanceRepository(api);

      await repo.updateItem(
        'episodic',
        '11111111-1111-1111-1111-111111111111',
        content: '其实是期中考试',
        reason: 'user_edit',
      );

      expect(api.calls.single.$1, 'POST');
      expect(
        api.calls.single.$2,
        '/memory/provenance/items/episodic/11111111-1111-1111-1111-111111111111/update',
      );
      final body = api.calls.single.$3! as Map<String, dynamic>;
      expect(body['content'], '其实是期中考试');
      expect(body['reason'], 'user_edit');
    });

    test('updateScope PUTs pause/resume/link_plan actions', () async {
      final api = _RecordingApiClient()..reply({'changed': true});
      final repo = MemoryProvenanceRepository(api);
      const id = '11111111-1111-1111-1111-111111111111';

      await repo.updateScope('episodic', id, action: 'pause');
      await repo.updateScope('episodic', id, action: 'resume');
      await repo.updateScope(
        'goal',
        id,
        action: 'link_plan',
        planId: '22222222-2222-2222-2222-222222222222',
      );

      expect(api.calls[0].$1, 'PUT');
      expect(api.calls[0].$2, '/memory/provenance/items/episodic/$id/scope');
      expect((api.calls[0].$3! as Map<String, dynamic>)['action'], 'pause');
      expect((api.calls[1].$3! as Map<String, dynamic>)['action'], 'resume');
      expect(api.calls[2].$2, '/memory/provenance/items/goal/$id/scope');
      final linkBody = api.calls[2].$3! as Map<String, dynamic>;
      expect(linkBody['action'], 'link_plan');
      expect(linkBody['plan_id'], '22222222-2222-2222-2222-222222222222');
    });

    test('revokeItem POSTs to the revoke endpoint with reason', () async {
      final api = _RecordingApiClient()
        ..reply({'status': 'revoked', 'revoked': true});
      final repo = MemoryProvenanceRepository(api);
      const id = '11111111-1111-1111-1111-111111111111';

      final result = await repo.revokeItem('preference', id, reason: 'user_revoked');

      expect(api.calls.single.$1, 'POST');
      expect(
        api.calls.single.$2,
        '/memory/provenance/items/preference/$id/revoke',
      );
      expect((api.calls.single.$3! as Map<String, dynamic>)['reason'],
          'user_revoked');
      expect(result['revoked'], isTrue);
    });

    test('whyThis POSTs the memory_use_receipt structure', () async {
      final api = _RecordingApiClient()
        ..reply({
          'memory': {
            'kind': 'episodic',
            'id': '11111111-1111-1111-1111-111111111111',
            'ref': 'memory://episodic/11111111-1111-1111-1111-111111111111',
            'content': '我在准备离散数学期末考试',
            'status_now': 'active',
            'bucket': 'told',
            'still_in_use': true,
            'paused': false,
            'replaced_by_ref': null,
          },
          'used_at': '2026-09-21T08:00:00',
          'run': null,
          'why_included': <Map<String, dynamic>>[
            const {'reason': 'rank_policy', 'known': true, 'label': '按与当轮内容的相关度排序选中'},
          ],
          'usage_decision': {
            'internal_only': <Map<String, dynamic>>[
              const {
                'id': 'a',
                'section': 's',
                'reason': 'selfcheck:phatic_query',
                'reason_known': true,
                'reason_label': '当轮只是问候或确认，不需要引用记忆',
              },
            ],
            'receipt_version': 'v1',
            'receipt_version_known': true,
          },
          'recent_uses': <Map<String, dynamic>>[],
          'source': const <String, dynamic>{
            'source_known': true,
            'source_label': '你告诉我的',
            'evidence_count': 0,
            'evidence_missing': false,
            'correction_count': 0,
            'confidence_tier_label': '已确认',
            'governance_history': <Map<String, dynamic>>[],
          },
          'correction': {
            'update': '/api/v1/memory/provenance/items/episodic/11111111-1111-1111-1111-111111111111/update',
            'revoke': '/api/v1/memory/provenance/items/episodic/11111111-1111-1111-1111-111111111111/revoke',
            'scope': '/api/v1/memory/provenance/items/episodic/11111111-1111-1111-1111-111111111111/scope',
          },
        });
      final repo = MemoryProvenanceRepository(api);

      final result = await repo.whyThis(
        memoryRef: 'memory://episodic/11111111-1111-1111-1111-111111111111',
        version: 3,
      );

      expect(api.calls.single.$1, 'POST');
      expect(api.calls.single.$2, '/memory/provenance/why-this');
      final body = api.calls.single.$3! as Map<String, dynamic>;
      expect(body['memory_ref'],
          'memory://episodic/11111111-1111-1111-1111-111111111111');
      expect(body['version'], '3');
      expect(result.whyIncluded.single.label, '按与当轮内容的相关度排序选中');
      expect(result.internalOnly.single.known, isTrue);
      expect(result.stillInUse, isTrue);
      expect(result.correctionUpdatePath, isNotEmpty);
    });
  });
}

extension on ProvenanceMemoryItem {
  Map<String, dynamic> toJsonLike() => {
        'kind': kind,
        'id': id,
        'ref': ref,
        'bucket': bucket.name,
        'bucket_label': bucketLabel,
        'content': content,
        'status': status,
        'scope': scope,
        'correction_count': correctionCount,
        'evidence_missing': evidenceMissing,
        'confidence_tier': confidenceTier,
        'confidence_tier_label': confidenceTierLabel,
        'source_label': sourceLabel,
        'source_known': sourceKnown,
        'actions': actions,
      };
}
