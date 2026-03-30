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

// Mock Classes
@GenerateMocks([
  ApiClient,
])

void main() {
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
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('event · evt-1'), findsOneWidget);
      expect(find.text('Type: task_completed'), findsOneWidget);
      expect(find.text('Timestamp: 1234567890'), findsOneWidget);
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
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('Subject: MATH101'), findsOneWidget);
      expect(find.text('Root Cause: Concept misunderstanding'), findsOneWidget);
      expect(find.text('Suggestion: Review chapter 5'), findsOneWidget);
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
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('Name: Photosynthesis'), findsOneWidget);
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
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('Title: Complete assignment'), findsOneWidget);
      expect(find.text('Status: in_progress'), findsOneWidget);
      expect(find.text('Due: 2026-04-01'), findsOneWidget);
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
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('Date: 2026-03-30'), findsOneWidget);
      expect(find.text('Summary: Weekly progress completed'), findsOneWidget);
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
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('Focus: deep'), findsOneWidget);
      expect(find.text('Load: high'), findsOneWidget);
      expect(find.text('Sprint: active'), findsOneWidget);
    });

    testWidgets('should render redacted evidence with reason', (tester) async {
      final item = EvidenceResolveItem(
        type: 'sensitive',
        id: 'redacted-1',
        status: 'redacted',
        redactionReason: 'Contains personal information',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('Contains personal information'), findsOneWidget);
    });

    testWidgets('should render missing evidence placeholder', (tester) async {
      final item = EvidenceResolveItem(
        type: 'missing',
        id: 'missing-1',
        status: 'missing',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('无法解析证据'), findsOneWidget);
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
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      // Should show truncated value with ellipsis
      expect(find.textContaining('...'), findsOneWidget);
      expect(find.text(longText), findsNothing);
    });

    testWidgets('should handle null payload gracefully', (tester) async {
      final item = EvidenceResolveItem(
        type: 'empty',
        id: 'empty-1',
        status: 'ok',
        payload: null,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('证据记录'), findsOneWidget);
    });

    testWidgets('should display OK status badge', (tester) async {
      final item = EvidenceResolveItem(
        type: 'event',
        id: 'evt-1',
        status: 'ok',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('OK'), findsOneWidget);
      // Verify success color (green-ish)
      final chip = tester.widget<Chip>(
        find.ancestor(
          of: find.text('OK'),
          matching: find.byType(Chip),
        ),
      );
      expect(chip.backgroundColor, DS.semanticSuccess.withValues(alpha: 0.12));
    });

    testWidgets('should display redacted status badge', (tester) async {
      final item = EvidenceResolveItem(
        type: 'sensitive',
        id: 'sens-1',
        status: 'redacted',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('已隐藏'), findsOneWidget);
      final chip = tester.widget<Chip>(
        find.ancestor(
          of: find.text('已隐藏'),
          matching: find.byType(Chip),
        ),
      );
      expect(chip.backgroundColor, DS.semanticWarning.withValues(alpha: 0.12));
    });

    testWidgets('should display missing status badge', (tester) async {
      final item = EvidenceResolveItem(
        type: 'missing',
        id: 'miss-1',
        status: 'missing',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('缺失'), findsOneWidget);
      final chip = tester.widget<Chip>(
        find.ancestor(
          of: find.text('缺失'),
          matching: find.byType(Chip),
        ),
      );
      expect(chip.backgroundColor, DS.semanticError.withValues(alpha: 0.12));
    });

    testWidgets('should handle empty payload dict', (tester) async {
      final item = EvidenceResolveItem(
        type: 'empty',
        id: 'empty-2',
        status: 'ok',
        payload: {},
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('证据记录'), findsOneWidget);
    });

    testWidgets('should display missing keys as hyphen', (tester) async {
      final item = EvidenceResolveItem(
        type: 'event',
        id: 'evt-2',
        status: 'ok',
        payload: {
          'event': {
            'event_type': 'test',
            // ts_ms missing
          },
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      expect(find.text('Timestamp: -'), findsOneWidget);
    });
  });

  group('MemoryEvidenceBadge Tests', () {
    testWidgets('should render OK badge with success color', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
          ),
        ),
      );

      expect(find.text('OK'), findsOneWidget);

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.backgroundColor, DS.semanticSuccess.withValues(alpha: 0.12));
      expect(chip.label, isA<Text>().having(
        (t) => t.style?.color,
        'color',
        DS.semanticSuccess,
      ));
    });

    testWidgets('should render redacted badge with warning color', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.redacted),
          ),
        ),
      );

      expect(find.text('已隐藏'), findsOneWidget);

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.backgroundColor, DS.semanticWarning.withValues(alpha: 0.12));
    });

    testWidgets('should render missing badge with error color', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.missing),
          ),
        ),
      );

      expect(find.text('缺失'), findsOneWidget);

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.backgroundColor, DS.semanticError.withValues(alpha: 0.12));
    });

    testWidgets('should have rounded border shape', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
          ),
        ),
      );

      final chip = tester.widget<Chip>(find.byType(Chip));
      expect(chip.shape, isA<RoundedRectangleBorder>());
    });

    testWidgets('should work in different contexts', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Row(
              children: const [
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.missing),
                MemoryEvidenceBadge(status: MemoryEvidenceStatus.redacted),
              ],
            ),
          ),
        ),
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

    testWidgets('should show drawer with loading state', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ];

      // Mock incomplete future to keep loading state
      final completer = Completer<Response<Map<String, dynamic>>>();
      when(mockApiClient.post(any, data: anyNamed('data'))).thenAnswer(
        (_) => completer.future,
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: refs,
                    evidenceMissing: false,
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pump();

      // Should show loading indicator
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Complete the future to avoid timer issues
      completer.complete(Response<Map<String, dynamic>>(
        requestOptions: RequestOptions(path: ''),
        data: {'resolved': []},
        statusCode: 200,
      ));
      await tester.pumpAndSettle();
    });

    testWidgets('should show drawer with missing evidence banner', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ];

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: refs,
                    evidenceMissing: true, // Evidence is missing
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pumpAndSettle();

      expect(find.text('Evidence missing'), findsOneWidget);
    });

    testWidgets('should show drawer when evidence viewer disabled', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = false;

      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ];

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: refs,
                    evidenceMissing: false,
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pumpAndSettle();

      expect(find.text('Evidence viewer disabled'), findsOneWidget);
    });

    testWidgets('should show resolved evidence grouped by type', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
        EvidenceRefModel(type: 'event', id: 'evt-2'),
        EvidenceRefModel(type: 'task', id: 'task-1'),
      ];

      when(mockApiClient.post(any, data: anyNamed('data'))).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ''),
          data: {
            'resolved': [
              {
                'type': 'event',
                'id': 'evt-1',
                'status': 'ok',
                'event': {'event_type': 'test_event'},
              },
              {
                'type': 'event',
                'id': 'evt-2',
                'status': 'ok',
                'event': {'event_type': 'test_event_2'},
              },
              {
                'type': 'task',
                'id': 'task-1',
                'status': 'ok',
                'task': {'title': 'Test Task'},
              },
            ],
          },
          statusCode: 200,
        ),
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: refs,
                    evidenceMissing: false,
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pumpAndSettle();

      // Should show grouped headers
      expect(find.text('EVENT'), findsOneWidget);
      expect(find.text('TASK'), findsOneWidget);

      // Should show evidence cards
      expect(find.byType(EvidenceCard), findsNWidgets(3));
    });

    testWidgets('should show empty state when no evidence', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      when(mockApiClient.post(any, data: anyNamed('data'))).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ''),
          data: {'resolved': []},
          statusCode: 200,
        ),
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: [],
                    evidenceMissing: false,
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pumpAndSettle();

      expect(find.text('No Evidence'), findsOneWidget);
    });

    testWidgets('should show error message on resolve failure', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      final refs = [
        EvidenceRefModel(type: 'event', id: 'evt-1'),
      ];

      when(mockApiClient.post(any, data: anyNamed('data'))).thenThrow(
        Exception('Network error'),
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: refs,
                    evidenceMissing: false,
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pumpAndSettle();

      // Should show error state
      expect(find.textContaining('failed'), findsOneWidget);
    });

    testWidgets('should handle empty refs list', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: [],
                    evidenceMissing: false,
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pumpAndSettle();

      // Should show empty state or no error
      expect(find.byType(EvidenceDrawer), findsNothing); // Drawer closed
    });

    testWidgets('should group evidence in alphabetical order', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      final refs = [
        EvidenceRefModel(type: 'zebra', id: 'z-1'),
        EvidenceRefModel(type: 'alpha', id: 'a-1'),
        EvidenceRefModel(type: 'beta', id: 'b-1'),
      ];

      when(mockApiClient.post(any, data: anyNamed('data'))).thenAnswer(
        (_) async => Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: ''),
          data: {
            'resolved': [
              {'type': 'zebra', 'id': 'z-1', 'status': 'ok'},
              {'type': 'alpha', 'id': 'a-1', 'status': 'ok'},
              {'type': 'beta', 'id': 'b-1', 'status': 'ok'},
            ],
          },
          statusCode: 200,
        ),
      );

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: Scaffold(
              body: Builder(
                builder: (context) => ElevatedButton(
                  onPressed: () => EvidenceDrawer.show(
                    context,
                    refs: refs,
                    evidenceMissing: false,
                  ),
                  child: const Text('Show Evidence'),
                ),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Show Evidence'));
      await tester.pumpAndSettle();

      // Get all text widgets
      final texts = find.byType(Text);
      final alphaIndex = tester.getTopLeft(find.text('ALPHA')).dy;
      final betaIndex = tester.getTopLeft(find.text('BETA')).dy;
      final zebraIndex = tester.getTopLeft(find.text('ZEBRA')).dy;

      // Verify alphabetical order: alpha < beta < zebra
      expect(alphaIndex, lessThan(betaIndex));
      expect(betaIndex, lessThan(zebraIndex));
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
    testWidgets('should show badge in card', (tester) async {
      final item = EvidenceResolveItem(
        type: 'event',
        id: 'evt-1',
        status: 'ok',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EvidenceCard(item: item),
          ),
        ),
      );

      // Find the status badge (it's a private class _StatusBadge, but we can find the Chip)
      expect(find.byType(Chip), findsOneWidget);
      expect(find.text('OK'), findsOneWidget);
    });

    testWidgets('should display evidence chain title in drawer', (tester) async {
      AppFeatureFlags.enableEvidenceViewer = true;

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: ProviderContainer(),
          child: MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
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

      // The drawer should show evidence chain title
      expect(find.text('Evidence Chain'), findsOneWidget);
    });
  });
}
