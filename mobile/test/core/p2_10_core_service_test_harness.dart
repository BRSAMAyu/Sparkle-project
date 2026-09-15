// ignore_for_file: avoid_slow_async_io, depend_on_referenced_packages

import 'dart:async';
import 'dart:convert';
import 'dart:ffi' show Abi;
import 'dart:io';
import 'dart:typed_data';

import 'package:connectivity_plus/connectivity_plus.dart'
    show ConnectivityResult;
import 'package:connectivity_plus_platform_interface/connectivity_plus_platform_interface.dart'
    show ConnectivityPlatform;
import 'package:dio/dio.dart';
import 'package:isar/isar.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';

bool _isarInitialized = false;

Future<void> initializeP2TestIsar() async {
  if (_isarInitialized) return;
  await Isar.initializeIsarCore(
    libraries: <Abi, String>{Abi.current(): _isarCoreLibraryPath()},
  );
  _isarInitialized = true;
}

String _isarCoreLibraryPath() {
  final root = Directory.current.path;
  if (Platform.isMacOS) {
    return '$root/third_party_plugins/isar_flutter_libs/macos/libisar.dylib';
  }
  if (Platform.isLinux) {
    return '$root/third_party_plugins/isar_flutter_libs/linux/libisar.so';
  }
  return '';
}

Future<P2TestIsar> openP2TestIsar(String prefix) async {
  final tempDir = await Directory.systemTemp.createTemp(prefix);
  final isar = await Isar.open(
    [
      LocalKnowledgeNodeSchema,
      PendingUpdateSchema,
      LocalCRDTSnapshotSchema,
      OutboxItemSchema,
      UserAnalyticsEventSchema,
    ],
    directory: tempDir.path,
    name: '${prefix}_${DateTime.now().microsecondsSinceEpoch}',
  );
  final localDb = LocalDatabase()..isar = isar;
  return P2TestIsar(isar: isar, localDb: localDb, tempDir: tempDir);
}

class P2TestIsar {
  const P2TestIsar({
    required this.isar,
    required this.localDb,
    required this.tempDir,
  });

  final Isar isar;
  final LocalDatabase localDb;
  final Directory tempDir;

  Future<void> dispose() async {
    if (isar.isOpen) {
      await isar.close(deleteFromDisk: true);
    }
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  }
}

class ApiRequestRecord {
  const ApiRequestRecord({
    required this.method,
    required this.path,
    this.data,
    this.queryParameters,
  });

  final String method;
  final String path;
  final Object? data;
  final Map<String, dynamic>? queryParameters;
}

class RecordingApiClient implements ApiClient {
  RecordingApiClient({Dio? dio}) : _dio = dio ?? Dio();

  final Dio _dio;
  final List<ApiRequestRecord> requests = <ApiRequestRecord>[];
  Future<Response<dynamic>> Function(ApiRequestRecord request)? onGet;
  Future<Response<dynamic>> Function(ApiRequestRecord request)? onPost;
  Future<Response<dynamic>> Function(ApiRequestRecord request)? onPut;
  Future<Response<dynamic>> Function(ApiRequestRecord request)? onPatch;
  Future<Response<dynamic>> Function(ApiRequestRecord request)? onDelete;

  @override
  Dio get dio => _dio;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      _handle<T>(
        ApiRequestRecord(
          method: 'GET',
          path: path,
          queryParameters: queryParameters,
        ),
        onGet,
      );

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _handle<T>(
        ApiRequestRecord(
          method: 'POST',
          path: path,
          data: data,
          queryParameters: queryParameters,
        ),
        onPost,
      );

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _handle<T>(
        ApiRequestRecord(
          method: 'PUT',
          path: path,
          data: data,
          queryParameters: queryParameters,
        ),
        onPut,
      );

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) =>
      _handle<T>(
        ApiRequestRecord(method: 'PATCH', path: path, data: data),
        onPatch,
      );

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) =>
      _handle<T>(
        ApiRequestRecord(
          method: 'DELETE',
          path: path,
          queryParameters: queryParameters,
        ),
        onDelete,
      );

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

  Future<Response<T>> _handle<T>(
    ApiRequestRecord request,
    Future<Response<dynamic>> Function(ApiRequestRecord request)? handler,
  ) async {
    requests.add(request);
    final response = handler == null ? null : await handler(request);
    return Response<T>(
      requestOptions: RequestOptions(path: request.path),
      statusCode: response?.statusCode ?? 200,
      data: response?.data as T?,
    );
  }
}

class StubWebSocketService extends WebSocketService {
  final StreamController<dynamic> controller =
      StreamController<dynamic>.broadcast();
  final List<dynamic> sentMessages = <dynamic>[];

  @override
  Stream<dynamic> get stream => controller.stream;

  @override
  void send(dynamic data) {
    sentMessages.add(data);
  }

  Future<void> close() => controller.close();
}

class RecordedSyncEnqueue {
  const RecordedSyncEnqueue({
    required this.topic,
    required this.opType,
    required this.payload,
    required this.priority,
    required this.requiresAuth,
    this.entityType,
    this.entityId,
    this.dedupeKey,
    this.traceId,
  });

  final String topic;
  final String opType;
  final Map<String, dynamic> payload;
  final String? entityType;
  final String? entityId;
  final String? dedupeKey;
  final int priority;
  final bool requiresAuth;
  final String? traceId;
}

class RecordingSyncEngine extends SyncEngine {
  factory RecordingSyncEngine(LocalDatabase localDb) {
    final ws = StubWebSocketService();
    final api = RecordingApiClient();
    return RecordingSyncEngine._(localDb, ws, api);
  }

  RecordingSyncEngine._(
    LocalDatabase localDb,
    this.fakeWebSocket,
    this.fakeApiClient,
  ) : super(localDb, fakeWebSocket, fakeApiClient);

  final StubWebSocketService fakeWebSocket;
  final RecordingApiClient fakeApiClient;
  final List<RecordedSyncEnqueue> enqueued = <RecordedSyncEnqueue>[];
  bool started = false;
  bool stopped = false;

  @override
  void start() {
    started = true;
  }

  @override
  void stop() {
    stopped = true;
  }

  @override
  Future<void> enqueue({
    required String topic,
    required String opType,
    required Map<String, dynamic> payload,
    String? entityType,
    String? entityId,
    String? dedupeKey,
    int priority = 0,
    bool requiresAuth = true,
    String? traceId,
  }) async {
    enqueued.add(
      RecordedSyncEnqueue(
        topic: topic,
        opType: opType,
        payload: Map<String, dynamic>.from(payload),
        entityType: entityType,
        entityId: entityId,
        dedupeKey: dedupeKey,
        priority: priority,
        requiresAuth: requiresAuth,
        traceId: traceId,
      ),
    );
  }
}

class FakeConnectivityPlatform extends ConnectivityPlatform {
  FakeConnectivityPlatform([
    List<ConnectivityResult> initial = const <ConnectivityResult>[
      ConnectivityResult.none,
    ],
  ]) : _result = initial;

  List<ConnectivityResult> _result;
  final StreamController<List<ConnectivityResult>> _controller =
      StreamController<List<ConnectivityResult>>.broadcast();

  @override
  Future<List<ConnectivityResult>> checkConnectivity() async => _result;

  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged =>
      _controller.stream;

  void emit(List<ConnectivityResult> result) {
    _result = result;
    _controller.add(result);
  }

  Future<void> close() => _controller.close();
}

Future<Map<String, dynamic>> readJsonRequestBody(
  Stream<Uint8List>? requestStream,
) async {
  final chunks = <int>[];
  if (requestStream != null) {
    // ignore: prefer_foreach
    await for (final chunk in requestStream) {
      chunks.addAll(chunk);
    }
  }
  if (chunks.isEmpty) return <String, dynamic>{};
  return Map<String, dynamic>.from(
    jsonDecode(utf8.decode(chunks)) as Map<String, dynamic>,
  );
}
