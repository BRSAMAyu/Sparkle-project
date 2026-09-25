/*
O11 red/green harness (J-01 first3, evidence v3/09_evidence/j01_first3):
the wizard's final "创建" step failed against the real backend while the same
payload POSTed straight to the engine succeeded (curl 307→200). Root cause is
in the submission chain's URL shape: the gateway registers only
POST /api/v1/goals/ (the engine-canonical trailing-slash face), so a POST to
the bare /api/v1/goals is answered by gin's RedirectTrailingSlash with 307 —
and dart:io (dio's transport) does not auto-follow redirects for POST
requests, so dio raises and the wizard swallows it into 创建失败.

This test mocks ONLY the network layer (an HttpClientAdapter that reproduces
the gateway's routing semantics): the real ApiGoalRepository, real
GoalIntentService and the real wizard screen run unmocked. The wizard must
reach the created state through POST /goals/ (canonical), never through the
bare path's unfollowable 307.
*/
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/auth/data/models/token_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart'
    show sharedPreferencesProvider;
import 'package:sparkle/features/goal/presentation/screens/goal_creation_wizard_screen.dart';

import '../../../shared/i18n_test_helper.dart';

/// Captures requests at the transport boundary and answers with the gateway's
/// routing semantics: bare-collection POST → 307 (gin RedirectTrailingSlash,
/// unfollowable for POST by dart:io); canonical /goals/ → engine-shaped 200.
class _GatewaySemanticsAdapter implements HttpClientAdapter {
  final List<_RecordedRequest> requests = <_RecordedRequest>[];

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(
      _RecordedRequest(
        method: options.method,
        path: options.path,
      ),
    );
    // O10 pre-fix gateway behavior: analyze-intent had no gateway route →
    // NoRoute 404. The real GoalIntentService must fall back to the legacy
    // form on this network outcome (documented catch-all path).
    if (options.method == 'POST' && options.path == '/goals/analyze-intent') {
      return _jsonBody(404, <String, dynamic>{'error': 'route not found'});
    }
    if (options.method == 'POST' && options.path == '/goals/decompose-preview') {
      return _jsonBody(200, <String, dynamic>{
        'goal_type': 'exam',
        'time_horizon': 'short',
        'suggested_target_date': '2026-10-10',
        'rationale': 'Visible checkpoints keep the goal editable.',
        'milestones': <Map<String, dynamic>>[
          <String, dynamic>{
            'id': 'm1',
            'title': 'Map the baseline',
            'description': 'Confirm weak topics.',
            'estimated_days': 7,
            'acceptance_criteria': <String>['Baseline exists'],
          },
        ],
      });
    }
    // Gateway semantics: only the trailing-slash face is registered for goal
    // creation; the bare face 307s to it.
    if (options.method == 'POST' && options.path == '/goals') {
      return ResponseBody.fromString(
        '',
        307,
        headers: <String, List<String>>{
          'location': <String>['/goals/'],
        },
      );
    }
    if (options.method == 'POST' && options.path == '/goals/') {
      final body = await _readJson(requestStream);
      return _jsonBody(200, <String, dynamic>{
        'id': 'goal-1',
        'title': body['title'],
        'goal_type': body['goal_type'],
        'status': 'active',
        'first_task_id': 'task-1',
      });
    }
    // Anything else (e.g. scenario-pack matching) — empty success payload.
    return _jsonBody(200, <String, dynamic>{});
  }

  static ResponseBody _jsonBody(int code, Map<String, dynamic> body) =>
      ResponseBody.fromString(
        jsonEncode(body),
        code,
        headers: <String, List<String>>{
          Headers.contentTypeHeader: <String>['application/json'],
        },
      );

  static Future<Map<String, dynamic>> _readJson(
    Stream<Uint8List>? stream,
  ) async {
    final chunks = <int>[];
    if (stream != null) {
      await stream.forEach(chunks.addAll);
    }
    if (chunks.isEmpty) return <String, dynamic>{};
    return Map<String, dynamic>.from(
      jsonDecode(utf8.decode(chunks)) as Map<String, dynamic>,
    );
  }
}

class _RecordedRequest {
  const _RecordedRequest({required this.method, required this.path});

  final String method;
  final String path;
}

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<String?> getAccessToken() async => 'test-access';

  @override
  Future<String?> getToken() async => 'test-access';

  @override
  Future<String?> getRefreshToken() async => 'test-refresh';

  @override
  Future<TokenResponse> refreshToken() async => TokenResponse(
        accessToken: 'test-access',
        refreshToken: 'test-refresh',
      );

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  testWidgets('O11: wizard confirm step creates the goal through POST /goals/', (
    tester,
  ) async {
    SharedPreferences.setMockInitialValues(<String, Object>{});
    final prefs = await SharedPreferences.getInstance();
    final container = ProviderContainer(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
      ],
    );
    addTearDown(container.dispose);
    final client = container.read(apiClientProvider);
    final adapter = _GatewaySemanticsAdapter();
    client.dio.httpClientAdapter = adapter;

    Object? created;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiClientProvider.overrideWithValue(client),
        ],
        child: testMaterialApp(
          home: GoalCreationWizardScreen(
            onCreated: (goal) => created = goal,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Walk the legacy wizard path (intent analysis answers 404 → documented
    // fallback to the type chooser, as measured 5/5 in J-01).
    await tester.enterText(find.byType(TextField), '通过高数考试');
    await tester.tap(find.widgetWithText(FilledButton, '让我先看看你的情况'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(0), '通过高数考试');
    await tester.pump();
    await tester.enterText(find.byType(TextField).at(1), '奖学金需要这门成绩');
    await tester.pump();
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '继续'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('继续'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('创建'));
    await tester.pump(const Duration(milliseconds: 250));

    // The create request must have reached the canonical face.
    final createRequests = adapter.requests
        .where((r) => r.method == 'POST' && r.path == '/goals/')
        .toList();
    expect(createRequests, isNotEmpty,
        reason: '创建必须走引擎规范面 POST /goals/（无尾斜杠会被网关 307 且 dart:io '
            '不跟随 POST 重定向——J-01 O11 根因）',);

    // The bare face must not be used for creation.
    final barePathCreate = adapter.requests
        .where((r) => r.method == 'POST' && r.path == '/goals')
        .toList();
    expect(barePathCreate, isEmpty,
        reason: 'POST /goals（无尾斜杠）只会换来不可跟随的 307——提交链不得落到该面',);

    // Wizard endpoint success state: onCreated fired with the parsed engine
    // response (semantics unmocked — parse happened in the real repository).
    expect(created, isNotNull, reason: '向导终点必须是创建成功态，而不是「创建失败，请检查目标内容」');
    expect(find.text('创建失败，请检查目标内容'), findsNothing);
  });
}
