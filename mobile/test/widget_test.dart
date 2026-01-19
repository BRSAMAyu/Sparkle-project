// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:isar/isar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/app.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/offline_providers.dart';
import 'package:sparkle/core/offline/sync_engine.dart';
import 'package:sparkle/core/services/websocket_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('App smoke test', (WidgetTester tester) async {
    await Isar.initializeIsarCore(download: true);
    SharedPreferences.setMockInitialValues({});

    final tempDir = await Directory.systemTemp.createTemp('sparkle_app_test');
    final isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        UserAnalyticsEventSchema,
      ],
      directory: tempDir.path,
    );
    final localDb = LocalDatabase()..isar = isar;
    final engine = SyncEngine(localDb, _FakeWebSocketService(), _FakeApiClient());

    // Build our app and trigger a frame.
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          localDatabaseProvider.overrideWithValue(localDb),
          syncEngineProvider.overrideWithValue(engine),
        ],
        child: const SparkleApp(),
      ),
    );

    // Verify that the splash screen or login screen is shown (simplified check)
    expect(find.byType(SparkleApp), findsOneWidget);

    // Dispose app to avoid lingering timers during tests.
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pumpAndSettle();

    await isar.close(deleteFromDisk: true);
    await tempDir.delete(recursive: true);
  }, skip: true,);
}

class _FakeApiClient implements ApiClient {
  @override
  Dio get dio => Dio();

  @override
  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? queryParameters}) {
    throw UnimplementedError();
  }

  @override
  Stream<SSEEvent> getStream(String path, {Map<String, dynamic>? queryParameters}) => const Stream<SSEEvent>.empty();

  @override
  Stream<SSEEvent> postStream(String path, {Object? data}) => const Stream<SSEEvent>.empty();

  @override
  Future<Response<T>> post<T>(String path, {Object? data}) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> put<T>(String path, {Object? data}) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> patch<T>(String path, {Object? data}) {
    throw UnimplementedError();
  }

  @override
  Future<Response<T>> delete<T>(String path) {
    throw UnimplementedError();
  }
}

class _FakeWebSocketService extends WebSocketService {}
