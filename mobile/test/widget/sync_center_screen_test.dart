import 'dart:async';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import '../shared/isar_test_helper.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/offline/sync_center_provider.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';
import 'package:sparkle/features/user/presentation/screens/sync_center_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../shared/i18n_test_helper.dart';

const _runSyncCenterWidget = bool.fromEnvironment('RUN_SYNC_CENTER_WIDGET');

void main() {

  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  if (!_runSyncCenterWidget) {
    testWidgets(
      'SyncCenterScreen shows stats and retry button',
      (tester) async {},
      // Stage 12 MOB1 isolate: requires downloadable IsarCore runtime in widget env.
      skip: true,
    );
    return;
  }

  late Isar isar;
  late LocalDatabase localDb;
  late Directory tempDir;

  setUpAll(() async {
    await initializeIsarCoreForTesting();
    SharedPreferences.setMockInitialValues({});
  });

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('sync_center_test');
    isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        UserAnalyticsEventSchema,
      ],
      directory: tempDir.path,
    );
    localDb = LocalDatabase();
    localDb.isar = isar;
  });

  tearDown(() async {
    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  });

  testWidgets('SyncCenterScreen shows stats and retry button', (tester) async {
    final fakeStats = SyncCenterStats(
      pendingByTopic: {'cognitive': 2, 'knowledge': 1},
      totalPending: 3,
      lastSuccessAt: DateTime(2025, 1, 1, 12),
    );

    final streamController = StreamController<SyncCenterStats>()
      ..add(fakeStats);
    final itemsController = StreamController<List<OutboxItem>>()
      ..add(<OutboxItem>[]);

    final engine =
        SyncEngine(localDb, _FakeWebSocketService(), _FakeApiClient());

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          localDatabaseProvider.overrideWithValue(localDb),
          syncEngineProvider.overrideWithValue(engine),
          syncCenterStatsProvider
              .overrideWith((ref) => streamController.stream),
          syncCenterItemsProvider.overrideWith(
            (ref, query) => itemsController.stream,
          ),
        ],
        child: testMaterialApp(
          home: SyncCenterScreen(),
        ),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.text('待同步总数：3'), findsOneWidget);
    expect(find.text('认知碎片'), findsOneWidget);
    expect(find.text('知识图谱'), findsOneWidget);
    expect(find.text('重试失败项'), findsOneWidget);

    await streamController.close();
    await itemsController.close();
  });
}

class _FakeApiClient implements ApiClient {
  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(String path,
      {Map<String, dynamic>? queryParameters,}) {
    throw UnimplementedError();
  }

  @override
  Stream<SSEEvent> getStream(String path,
          {Map<String, dynamic>? headers,
          Map<String, dynamic>? queryParameters,}) =>
      const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) =>
      const Stream<SSEEvent>.empty();

  @override
  Future<Response<T>> post<T>(String path,
      {Object? data, Map<String, dynamic>? queryParameters,}) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) {
    throw UnimplementedError();
  }
}

class _FakeWebSocketService extends WebSocketService {}
