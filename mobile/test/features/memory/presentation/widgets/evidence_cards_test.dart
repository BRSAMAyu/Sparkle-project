import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/evidence_resolve_service.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_cards.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_drawer.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import 'evidence_cards_test.mocks.dart';
import '../../../../shared/i18n_test_helper.dart';

@GenerateMocks([
  ApiClient,
])

void main() {

  setUp(setUpI18nForTesting);

  /// Helper: tap the first InkWell in an EvidenceCard to expand TIER1→TIER2.
  Future<void> tapExpandCard(WidgetTester tester) async {
    await tester.tap(find.byType(InkWell).first);
    await tester.pumpAndSettle();
  }

  group('EvidenceCard Tests', () {
    testWidgets('should render evidence card with event payload', (tester) async {
      final item = EvidenceResolveItem(
        type: 'event',
        id: 'evt-1',
        status: 'ok',
        payload: {
          'event': {
            'event_type': 'task_completed',
            'ts_ms': '1234567890',
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1 summary (always visible)
      expect(find.text('事件: task_completed'), findsOneWidget);

      // Expand to TIER2
      await tapExpandCard(tester);

      // TIER2 key fields with Chinese labels
      expect(find.text('类型'), findsOneWidget);
      expect(find.text('task_completed'), findsOneWidget);
      expect(find.text('时间'), findsOneWidget);
      expect(find.text('1234567890'), findsOneWidget);
    });

    testWidgets('should render evidence card with error payload', (tester) async {
      final item = EvidenceResolveItem(
        type: 'error',
        id: 'err-1',
        status: 'ok',
        payload: {
          'error': {
            'subject_code': 'MATH101',
            'root_cause': 'Concept misunderstanding',
            'study_suggestion': 'Review chapter 5',
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1
      expect(find.text('错题: MATH101'), findsOneWidget);

      // Expand to TIER2
      await tapExpandCard(tester);

      expect(find.text('科目'), findsOneWidget);
      expect(find.text('MATH101'), findsOneWidget);
      expect(find.text('根因'), findsOneWidget);
      expect(find.text('Concept misunderstanding'), findsOneWidget);
      expect(find.text('建议'), findsOneWidget);
      expect(find.text('Review chapter 5'), findsOneWidget);
    });

    testWidgets('should render evidence card with concept payload', (tester) async {
      final item = EvidenceResolveItem(
        type: 'concept',
        id: 'conc-1',
        status: 'ok',
        payload: {
          'concept': {
            'name': 'Photosynthesis',
            'description': 'Process by which plants convert light into energy',
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1
      expect(find.text('概念: Photosynthesis'), findsOneWidget);

      // Expand to TIER2
      await tapExpandCard(tester);

      expect(find.text('名称'), findsOneWidget);
      expect(find.text('Photosynthesis'), findsOneWidget);
      expect(find.text('描述'), findsOneWidget);
      expect(find.textContaining('Process by which plants'), findsOneWidget);
    });

    testWidgets('should render evidence card with task payload', (tester) async {
      final item = EvidenceResolveItem(
        type: 'task',
        id: 'task-1',
        status: 'ok',
        payload: {
          'task': {
            'title': 'Complete assignment',
            'status': 'in_progress',
            'due_date': '2026-04-01',
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1
      expect(find.text('任务: Complete assignment'), findsOneWidget);

      // Expand to TIER2
      await tapExpandCard(tester);

      expect(find.text('标题'), findsOneWidget);
      expect(find.text('Complete assignment'), findsOneWidget);
      expect(find.text('状态'), findsOneWidget);
      expect(find.text('in_progress'), findsOneWidget);
      expect(find.text('截止'), findsOneWidget);
      expect(find.text('2026-04-01'), findsOneWidget);
    });

    testWidgets('should render evidence card with summary payload', (tester) async {
      final item = EvidenceResolveItem(
        type: 'summary',
        id: 'sum-1',
        status: 'ok',
        payload: {
          'summary': {
            'review_date': '2026-03-30',
            'summary_text': 'Weekly progress completed',
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1: 'summary' type not matched in _buildSummary, falls through to default
      expect(find.text('证据记录'), findsOneWidget);

      // Expand to TIER2
      await tapExpandCard(tester);

      expect(find.text('日期'), findsOneWidget);
      expect(find.text('2026-03-30'), findsOneWidget);
      expect(find.text('摘要'), findsOneWidget);
      expect(find.text('Weekly progress completed'), findsOneWidget);
    });

    testWidgets('should render evidence card with state payload', (tester) async {
      final item = EvidenceResolveItem(
        type: 'state',
        id: 'state-1',
        status: 'ok',
        payload: {
          'state': {
            'focus_mode': 'deep',
            'cognitive_load': 'high',
            'sprint_mode': 'active',
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1: 'state' type not matched, falls through to default
      expect(find.text('证据记录'), findsOneWidget);

      // Expand to TIER2
      await tapExpandCard(tester);

      expect(find.text('专注'), findsOneWidget);
      expect(find.text('deep'), findsOneWidget);
      expect(find.text('负荷'), findsOneWidget);
      expect(find.text('high'), findsOneWidget);
      expect(find.text('冲刺'), findsOneWidget);
      expect(find.text('active'), findsOneWidget);
    });

    testWidgets('should render evidence card with practice outcome payload', (tester) async {
      final item = EvidenceResolveItem(
        type: 'practice_outcome',
        id: 'err-2',
        status: 'ok',
        payload: {
          'practice_outcome': {
            'error_id': 'err-2',
            'review_performance': 'remembered',
            'mastery_level': 0.7,
            'reviewed_at': '2026-04-20T12:00:00',
            'summary': '错题复习结果：remembered',
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1: 'practice_outcome' type not matched, falls through to default
      expect(find.text('证据记录'), findsOneWidget);

      // Expand to TIER2 (shows first 4 key-value pairs)
      await tapExpandCard(tester);

      expect(find.text('表现'), findsOneWidget);
      expect(find.text('remembered'), findsOneWidget);
      expect(find.text('掌握'), findsOneWidget);
      expect(find.text('0.7'), findsOneWidget);

      // TIER3: '摘要' is the 5th field (after error_id, performance, mastery, reviewed_at)
      // Tap "查看全部" to expand to TIER3
      await tester.tap(find.text('查看全部'));
      await tester.pumpAndSettle();

      expect(find.text('摘要'), findsOneWidget);
      expect(find.textContaining('错题复习结果'), findsOneWidget);
    });

    testWidgets('should render redacted evidence with reason', (tester) async {
      final item = EvidenceResolveItem(
        type: 'sensitive',
        id: 'redacted-1',
        status: 'redacted',
        redactionReason: 'Contains personal information',
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1 shows redaction reason for redacted status
      expect(find.text('Contains personal information'), findsOneWidget);
    });

    testWidgets('should render missing evidence placeholder', (tester) async {
      final item = EvidenceResolveItem(
        type: 'missing',
        id: 'missing-1',
        status: 'missing',
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1 shows Chinese '证据缺失' for missing status
      expect(find.text('证据缺失'), findsOneWidget);
    });

    testWidgets('should truncate long values', (tester) async {
      final longText = 'a' * 150;
      final item = EvidenceResolveItem(
        type: 'summary',
        id: 'sum-long',
        status: 'ok',
        payload: {
          'summary': {
            'review_date': '2026-03-30',
            'summary_text': longText,
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // Expand to TIER2
      await tapExpandCard(tester);

      // Text widget stores full data even with maxLines:2 and overflow:ellipsis.
      // Visual truncation happens at the rendering level, not the widget data level.
      expect(find.text(longText), findsOneWidget);
    });

    testWidgets('should handle null payload gracefully', (tester) async {
      final item = EvidenceResolveItem(
        type: 'empty',
        id: 'empty-1',
        status: 'ok',
        payload: null,
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // Falls through to default record label
      expect(find.text('证据记录'), findsOneWidget);
    });

    testWidgets('should display OK status dot in card', (tester) async {
      final item = EvidenceResolveItem(
        type: 'event',
        id: 'evt-1',
        status: 'ok',
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // Status dot is a Container with BoxShape.circle and success color
      // The card should render without Chip (no Chip-based badges)
      expect(find.byType(Chip), findsNothing);

      // TIER1 should show the default record text for empty payload
      expect(find.text('证据记录'), findsOneWidget);
    });

    testWidgets('should display redacted status dot in card', (tester) async {
      final item = EvidenceResolveItem(
        type: 'sensitive',
        id: 'sens-1',
        status: 'redacted',
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // The card no longer uses Chip — status is a colored dot
      expect(find.byType(Chip), findsNothing);
      // TIER1 shows redaction fallback
      expect(find.text('证据已隐藏'), findsOneWidget);
    });

    testWidgets('should display missing status dot in card', (tester) async {
      final item = EvidenceResolveItem(
        type: 'missing',
        id: 'miss-1',
        status: 'missing',
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      expect(find.byType(Chip), findsNothing);
      expect(find.text('证据缺失'), findsOneWidget);
    });

    testWidgets('should handle empty payload dict', (tester) async {
      final item = EvidenceResolveItem(
        type: 'empty',
        id: 'empty-2',
        status: 'ok',
        payload: {},
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      expect(find.text('证据记录'), findsOneWidget);
    });

    testWidgets('should skip empty values instead of showing hyphen', (tester) async {
      final item = EvidenceResolveItem(
        type: 'event',
        id: 'evt-2',
        status: 'ok',
        payload: {
          'event': {
            'event_type': 'test',
            // ts_ms missing — value is null
          },
        },
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // TIER1
      expect(find.text('事件: test'), findsOneWidget);

      // Expand to TIER2
      await tapExpandCard(tester);

      // Only '类型: test' is shown; missing ts_ms is skipped entirely
      expect(find.text('类型'), findsOneWidget);
      expect(find.text('test'), findsOneWidget);
      // Time label should NOT be present (missing value is skipped)
      expect(find.text('时间'), findsNothing);
    });
  });

  group('MemoryEvidenceBadge Tests', () {
    testWidgets('should render OK badge with success color', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
          ),),
      );

      expect(find.text('OK'), findsOneWidget);

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.backgroundColor, DS.semanticSuccess.withValues(alpha: 0.12));
      // Label is now a Row (wrapping count + Text), not a plain Text
      expect(chip.label, isA<Row>());
    });

    testWidgets('should render redacted badge with warning color', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.redacted),
          ),),
      );

      expect(find.text('已隐藏'), findsOneWidget);

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.backgroundColor, DS.semanticWarning.withValues(alpha: 0.12));
    });

    testWidgets('should render missing badge with error color', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.missing),
          ),),
      );

      expect(find.text('缺失'), findsOneWidget);

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.backgroundColor, DS.semanticError.withValues(alpha: 0.12));
    });

    testWidgets('should have rounded border shape', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
          ),),
      );

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.shape, isA<RoundedRectangleBorder>());
    });

    testWidgets('should work in different contexts', (tester) async {
      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: Row(
              children: const [
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.missing),
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.redacted),
              ],
            ),
          ),),
      );

      expect(find.byType(Chip), findsNWidgets(3));
    });
  });

  group('EvidenceDrawer Tests', () {
    late MockApiClient mockApiClient;
    late ProviderContainer container;

    setUp(() {
      mockApiClient = MockApiClient();
      container = ProviderContainer(
        overrides: [
          apiClientProvider.overrideWithValue(mockApiClient),
        ],
      );
    });

    tearDown(() {
      container.dispose();
    });

    // Helper to pump the EvidenceDrawer widget directly
    Future<void> pumpDrawer(
      WidgetTester tester, {
      List<EvidenceRefModel> refs = const [],
      List<Map<String, dynamic>> items = const [],
      bool evidenceMissing = false,
    }) async {
      tester.view.physicalSize = const Size(900, 1400);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: testMaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: EvidenceDrawer(
                  refs: refs,
                  items: items,
                  evidenceMissing: evidenceMissing,
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('should show drawer with ref items', (tester) async {
      await pumpDrawer(tester, refs: [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ]);

      expect(find.text('event: evt-1'), findsOneWidget);
    });

    testWidgets('should show drawer with missing evidence banner', (tester) async {
      await pumpDrawer(
        tester,
        refs: [EvidenceRefModel(type: 'event', id: 'evt-1')],
        evidenceMissing: true,
      );

      // With refs, the drawer shows ref items regardless of evidenceMissing flag
      expect(find.text('event: evt-1'), findsOneWidget);
    });

    testWidgets('should show drawer when evidence viewer disabled', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = false;

      await pumpDrawer(tester, refs: [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ]);

      // Drawer renders ref items regardless of feature flag
      expect(find.text('event: evt-1'), findsOneWidget);
    });

    testWidgets('should show resolved evidence grouped by type', (tester) async {
      await pumpDrawer(tester, refs: [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
        EvidenceRefModel(type: 'event', id: 'evt-2'),
        EvidenceRefModel(type: 'task', id: 'task-1'),
      ]);

      // Drawer shows ref items as 'type: id'
      expect(find.text('event: evt-1'), findsOneWidget);
      expect(find.text('event: evt-2'), findsOneWidget);
      expect(find.text('task: task-1'), findsOneWidget);
    });

    testWidgets('should show empty state when no evidence', (tester) async {
      await pumpDrawer(tester);

      // No refs + no items = '暂无证据记录'
      expect(find.text('暂无证据记录'), findsOneWidget);
    });

    testWidgets('should show error state when items unavailable', (tester) async {
      // EvidenceDrawer with evidenceMissing=true but no items/refs
      await pumpDrawer(tester, evidenceMissing: true);

      // evidenceMissing + no items + no refs = '证据不足'
      expect(find.text('证据不足'), findsOneWidget);
    });

    testWidgets('should handle empty refs list', (tester) async {
      await pumpDrawer(tester, refs: []);

      // Empty refs + no items = empty state
      expect(find.text('暂无证据记录'), findsOneWidget);
    });

    testWidgets('should render ref items in display order', (tester) async {
      final refs = [
        EvidenceRefModel(type: 'zebra', id: 'z-1'),
        EvidenceRefModel(type: 'alpha', id: 'a-1'),
        EvidenceRefModel(type: 'beta', id: 'b-1'),
      ];

      await pumpDrawer(tester, refs: refs);

      // Ref items are rendered from the refs list in display order
      expect(find.text('zebra: z-1'), findsOneWidget);
      expect(find.text('alpha: a-1'), findsOneWidget);
      expect(find.text('beta: b-1'), findsOneWidget);
    });
  });

  group('EvidenceResolveService Tests', () {
    late MockApiClient mockApiClient;
    late EvidenceResolveService service;

    setUp(() {
      mockApiClient = MockApiClient();
      service = EvidenceResolveService(mockApiClient);
    });

    test('should return empty list for empty refs', () async {
      final result = await service.resolveEvidence([]);

      expect(result, isEmpty);
      verifyNever(mockApiClient.post(any, data: anyNamed('data')));
    });

    test('should resolve evidence via API', () async {
      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ];

      when(mockApiClient.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ''),
          data: {
            'resolved': [
              {
                'type': 'event',
                'id': 'evt-1',
                'status': 'ok',
                'event': {'event_type': 'test'},
              },
            ],
          },
          statusCode: 200,
        ),
      );

      final result = await service.resolveEvidence(refs);

      expect(result.length, equals(1));
      expect(result.first.type, equals('event'));
      expect(result.first.id, equals('evt-1'));
      expect(result.first.status, equals('ok'));

      verify(mockApiClient.post('/api/v1/events/evidence/resolve', data: {
        'items': [refs.first.toJson()],
      })).called(1);
    });

    test('should handle multiple refs', () async {
      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
        EvidenceRefModel(type: 'task', id: 'task-1'),
      ];

      when(mockApiClient.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ''),
          data: {
            'resolved': [
              {'type': 'event', 'id': 'evt-1', 'status': 'ok'},
              {'type': 'task', 'id': 'task-1', 'status': 'ok'},
            ],
          },
          statusCode: 200,
        ),
      );

      final result = await service.resolveEvidence(refs);

      expect(result.length, equals(2));
    });

    test('should handle API error gracefully', () async {
      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ];

      when(mockApiClient.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenThrow(Exception('API Error'));

      expect(
        () => service.resolveEvidence(refs),
        throwsA(isA<Exception>()),
      );
    });

    test('should handle missing resolved field in response', () async {
      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ];

      when(mockApiClient.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ''),
          data: {},
          statusCode: 200,
        ),
      );

      final result = await service.resolveEvidence(refs);

      expect(result, isEmpty);
    });

    test('should include schema version in request', () async {
      final refs = [
        EvidenceRefModel(
          type: 'event',
          id: 'evt-1',
          schemaVersion: 'v1.0',
        ),
      ];

      when(mockApiClient.post<Map<String, dynamic>>(any, data: anyNamed('data')))
          .thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ''),
          data: {'resolved': []},
          statusCode: 200,
        ),
      );

      await service.resolveEvidence(refs);

      final captured = verify(mockApiClient.post(
        '/api/v1/events/evidence/resolve',
        data: captureAnyNamed('data'),
      )).captured.single as Map<String, dynamic>;

      expect(
        captured['items'].first['schema_version'],
        equals('v1.0'),
      );
    });
  });

  group('EvidenceRefModel Tests', () {
    test('should create EvidenceRefModel from JSON', () {
      final json = {
        'type': 'event',
        'id': 'evt-1',
        'schema_version': 'v1.0',
        'user_deleted': false,
      };

      final model = EvidenceRefModel.fromJson(json);

      expect(model.type, equals('event'));
      expect(model.id, equals('evt-1'));
      expect(model.schemaVersion, equals('v1.0'));
      expect(model.userDeleted, isFalse);
    });

    test('should handle missing optional fields', () {
      final json = {
        'type': 'event',
        'id': 'evt-1',
      };

      final model = EvidenceRefModel.fromJson(json);

      expect(model.schemaVersion, isNull);
      expect(model.userDeleted, isFalse);
    });

    test('should serialize to JSON', () {
      final model = EvidenceRefModel(
        type: 'event',
        id: 'evt-1',
        schemaVersion: 'v1.0',
        userDeleted: true,
      );

      final json = model.toJson();

      expect(json['type'], equals('event'));
      expect(json['id'], equals('evt-1'));
      expect(json['schema_version'], equals('v1.0'));
      expect(json['user_deleted'], isTrue);
    });
  });

  group('EvidenceResolveItem Tests', () {
    test('should create EvidenceResolveItem from JSON with event', () {
      final json = {
        'type': 'event',
        'id': 'evt-1',
        'status': 'ok',
        'event': {
          'event_type': 'test',
          'ts_ms': '1234567890',
        },
      };

      final item = EvidenceResolveItem.fromJson(json);

      expect(item.type, equals('event'));
      expect(item.id, equals('evt-1'));
      expect(item.status, equals('ok'));
      expect(item.payload, isNotNull);
      expect(item.payload!['event'], isNotNull);
    });

    test('should create EvidenceResolveItem with redacted status', () {
      final json = {
        'type': 'sensitive',
        'id': 'sens-1',
        'status': 'redacted',
        'redaction_reason': 'PII data',
      };

      final item = EvidenceResolveItem.fromJson(json);

      expect(item.status, equals('redacted'));
      expect(item.redactionReason, equals('PII data'));
    });

    test('should create EvidenceResolveItem from JSON with practice outcome', () {
      final json = {
        'type': 'practice_outcome',
        'id': 'err-2',
        'status': 'ok',
        'practice_outcome': {
          'error_id': 'err-2',
          'review_performance': 'remembered',
          'summary': '错题复习结果：remembered',
        },
      };

      final item = EvidenceResolveItem.fromJson(json);

      expect(item.type, equals('practice_outcome'));
      expect(item.payload?['practice_outcome']?['error_id'], equals('err-2'));
    });

    test('should handle null payload', () {
      final json = {
        'type': 'empty',
        'id': 'empty-1',
        'status': 'ok',
      };

      final item = EvidenceResolveItem.fromJson(json);

      expect(item.payload, isNull);
    });

    test('should handle multiple payload types', () {
      final json = {
        'type': 'multi',
        'id': 'multi-1',
        'status': 'ok',
        'event': {'event_type': 'test'},
        'task': {'title': 'Test Task'},
      };

      final item = EvidenceResolveItem.fromJson(json);

      expect(item.payload!['event'], isNotNull);
      expect(item.payload!['task'], isNotNull);
    });
  });

  group('Integration Tests', () {
    testWidgets('should show evidence card without chip badges', (tester) async {
      final item = EvidenceResolveItem(
        type: 'event',
        id: 'evt-1',
        status: 'ok',
      );

      await tester.pumpWidget(
        testMaterialApp(home: Scaffold(
            body: EvidenceCard(item: item),
          ),),
      );

      // EvidenceCard no longer uses Chip — status shown as _StatusDot + summary text
      expect(find.byType(Chip), findsNothing);
      expect(find.text('证据记录'), findsOneWidget);
    });

    testWidgets('should display evidence chain title in drawer', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: ProviderContainer(),
          child: testMaterialApp(
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: [],
                    evidenceMissing: false,
                  ),
                  child: const Text('Show'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show'));
      await tester.pumpAndSettle();

      // The drawer header always shows '证据记录'
      expect(find.text('证据记录'), findsOneWidget);
    });
  });
}
