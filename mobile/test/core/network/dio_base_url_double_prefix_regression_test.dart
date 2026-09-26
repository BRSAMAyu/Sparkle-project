import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/data_consistency_checker.dart';
import 'package:sparkle/core/services/evidence_resolve_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/data/repositories/chat_repository.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/file/data/repositories/file_repository.dart';

/// V3-FIX-145 second-layer regression — dio paths must be baseUrl-relative.
///
/// dio resolves a request URL by string-concatenating `baseUrl + path` for
/// relative paths (no normalization, no interceptor rewrites). Production
/// ApiClient already carries the full `/api/v1` prefix in its baseUrl
/// (`ApiEndpoints.baseUrl` = host + `/api/v1`), so any call site passing a
/// literal `'/api/v1/...'` path produced `/api/v1/api/v1/...` upstream — a
/// guaranteed 404 on every tap (copy-to-library was double-dead: the gateway
/// also lacked the route). These tests pin the invariant across every known
/// offender family: the two copy-to-library call sites plus the same-family
/// literal-prefix sites (evidence resolve, data-consistency cache/db checks).
///
/// Harness mirrors the in-repo network-test precedent
/// (api_interceptor_community401_regression_test.dart): the transport is
/// swapped for a recording HttpClientAdapter — dio itself stays real so the
/// baseUrl+path resolution under test actually happens. No real network.
void main() {
  // Mirrors production: ApiEndpoints.baseUrl = '${ApiConstants.baseUrl}$apiBasePath'
  // with apiBasePath = '/api/v1'.
  const host = 'https://gateway.test';
  const apiBasePath = '/api/v1';

  Dio dioWithProductionBasePath(_RecordingAdapter adapter) => Dio(
        BaseOptions(baseUrl: '$host$apiBasePath'),
      )..httpClientAdapter = adapter;

  group('dio request paths stay baseUrl-relative (no /api/v1 literal)', () {
    test('FileRepository.copyGroupFileToMyLibrary resolves a single-prefix URL',
        () async {
      final adapter = _RecordingAdapter();
      final repo = FileRepository(dioWithProductionBasePath(adapter));

      await repo.copyGroupFileToMyLibrary('g1', 'f1');

      expect(adapter.uris, hasLength(1));
      expect(
        adapter.uris.single.toString(),
        '$host/api/v1/community/groups/g1/files/f1/copy-to-library',
        reason: 'a literal /api/v1/ path on a /api/v1 baseUrl double-prefixes '
            'the request (/api/v1/api/v1/...) and 404s at the gateway',
      );
    });

    test('CommunityRepository.copyFileToMyLibrary resolves a single-prefix URL',
        () async {
      final adapter = _RecordingAdapter();
      final repo = CommunityRepository(
        _PassThroughApiClient(dioWithProductionBasePath(adapter)),
      );

      await repo.copyFileToMyLibrary('g1', 'f1');

      expect(adapter.uris, hasLength(1));
      expect(
        adapter.uris.single.toString(),
        '$host/api/v1/community/groups/g1/files/f1/copy-to-library',
      );
    });

    test('EvidenceResolveService.resolveEvidence resolves a single-prefix URL',
        () async {
      final adapter = _RecordingAdapter()
        ..responder = (_) => ResponseBody.fromString(
              '{"resolved": []}',
              200,
              headers: {
                Headers.contentTypeHeader: <String>['application/json'],
              },
            );
      final service = EvidenceResolveService(
        _PassThroughApiClient(dioWithProductionBasePath(adapter)),
      );

      await service.resolveEvidence([
        EvidenceRefModel(type: 'memory', id: 'e1'),
      ]);

      expect(adapter.uris, hasLength(1));
      expect(
        adapter.uris.single.toString(),
        '$host/api/v1/events/evidence/resolve',
      );
    });

    test('DataConsistencyChecker cache/db checks resolve single-prefix URLs',
        () async {
      final adapter = _RecordingAdapter()
        ..responder = (options) {
          final isCache = options.uri.path.contains('/chat/cache/check');
          final message = <String, dynamic>{
            'conversation_id': 'c1',
            'id': 'm1',
            'content': 'hello',
            'role': 'user',
          };
          return ResponseBody.fromString(
            jsonEncode(<String, dynamic>{
              'exists': true,
              'message': message,
              'source': isCache ? 'cache' : 'db',
            }),
            200,
            headers: {
              Headers.contentTypeHeader: <String>['application/json'],
            },
          );
        };
      final chatRepository = _StubChatRepository(
        [
          ChatMessageModel(
            conversationId: 'c1',
            id: 'm1',
            content: 'hello',
            role: MessageRole.user,
          ),
        ],
      );
      final checker = DataConsistencyChecker(
        chatRepository: chatRepository,
        dio: dioWithProductionBasePath(adapter),
      );

      final consistent = await checker.verifyMessageConsistency(
        messageId: 'm1',
        conversationId: 'c1',
        userId: 'u1',
      );

      expect(consistent, isTrue);
      final paths = adapter.uris.map((u) => u.path).toList();
      expect(
        paths,
        containsAll(<String>[
          '/api/v1/chat/cache/check',
          '/api/v1/chat/db/check',
        ]),
        reason: 'both checks must hit /api/v1 exactly once',
      );
      for (final path in paths) {
        expect(
          path,
          isNot(contains('/api/v1/api/v1/')),
          reason: 'double prefix re-introduced in $path',
        );
      }
    });
  });
}

class _RecordingAdapter implements HttpClientAdapter {
  final List<Uri> uris = <Uri>[];

  ResponseBody Function(RequestOptions options)? responder;

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    // Copy: dio reuses/mutates option objects; record the resolved URI.
    uris.add(options.uri);
    final respond = responder;
    if (respond != null) {
      return respond(options);
    }
    return ResponseBody.fromString(
      '{"exists": false}',
      200,
      headers: {
        Headers.contentTypeHeader: <String>['application/json'],
      },
    );
  }
}

/// Pass-through ApiClient shell: production ApiClient methods are pure
/// delegations to its dio (see api_client.dart); keeping that delegation real
/// lets dio perform the baseUrl+path resolution under test.
class _PassThroughApiClient implements ApiClient {
  _PassThroughApiClient(this._dio);

  final Dio _dio;

  @override
  Dio get dio => _dio;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      _dio.get<T>(path, queryParameters: queryParameters);

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _dio.post<T>(path, data: data, queryParameters: queryParameters);

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _dio.put<T>(path, data: data, queryParameters: queryParameters);

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _dio.patch<T>(path, data: data, queryParameters: queryParameters);

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      _dio.delete<T>(path, queryParameters: queryParameters);

  @override
  Stream<SSEEvent> getStream(
    String path, {
    Map<String, dynamic>? queryParameters,
    Map<String, dynamic>? headers,
  }) =>
      throw UnimplementedError('not exercised by these tests');

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      throw UnimplementedError('not exercised by these tests');
}

/// Hand-rolled stub (repo precedent: chat_provider_test.dart — mockito `when`
/// does not match invocations on this concrete class; direct overrides do).
class _StubChatRepository extends Mock implements ChatRepository {
  _StubChatRepository(this._history);

  final List<ChatMessageModel> _history;

  @override
  Future<List<ChatMessageModel>> getConversationHistory(
    String conversationId, {
    int? limit,
    int? offset,
  }) =>
      Future<List<ChatMessageModel>>.value(_history);
}
