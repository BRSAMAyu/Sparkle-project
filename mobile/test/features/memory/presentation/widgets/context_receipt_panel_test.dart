import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/design/pixel/pixel_state.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/memory/presentation/widgets/context_receipt_panel.dart';

import '../../../../shared/i18n_test_helper.dart';

/// V4-U03 · 「这次的理解」回执面板 widget 测试。
///
/// 覆盖面（每面一正一反，全部可失败）：
/// - 回执说什么就显示什么（选中/拒用归因/未归因显式；debug note 永不渲染）；
/// - 空态彼此分立（modeGated off/shadow、empty、unsupported、offline）；
/// - 验收③：budget_exhausted 不禁用、不阻断「忘记」（真实 revoke 链）；
/// - 验收①：200% 字体无溢出、操作键盘可达可激活（Space 与点按等效）；
/// - F03 纪律：memory 操作永不出现成功徽章（PixelSuccessBadge findsNothing）。
class _StubReceiptApi implements ApiClient {
  _StubReceiptApi(this.response);

  /// GET 响应体。
  Object? response;

  /// 非空时 GET 直接抛出（模拟断网）。
  DioException? getError;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final error = getError;
    if (error != null) {
      throw error;
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: response as T,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeProvenanceRepository implements MemoryProvenanceRepository {
  _FakeProvenanceRepository();

  String? revokedKind;
  String? revokedId;
  DioException? revokeError;

  @override
  Future<Map<String, dynamic>> revokeItem(
    String kind,
    String id, {
    String? reason,
  }) async {
    revokedKind = kind;
    revokedId = id;
    final error = revokeError;
    if (error != null) {
      throw error;
    }
    return {'status': 'revoked', 'revoked': true};
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('${invocation.memberName}');
}

const String _resolvedRef = 'memory://episodic/11111111-1111-1111-1111-111111111111';

Map<String, dynamic> _readyPayload({
  List<Map<String, dynamic>> candidates = const [],
  List<Map<String, dynamic>> verifications = const [],
  int resolvedSelectedCount = 0,
}) =>
    {
      'mode': 'live',
      'schema_version': 'context_selection_receipt.v1',
      'receipt': {
        'schema_version': 'context_selection_receipt.v1',
        'receipt_id': 'csr_01ARZ3NDEKTSV4RRFFQ69G5FAV',
        'selection_role': 'chat_context',
        'input_versions': {'memory_epoch': 7, 'selector_version': 'context_pack.v4-i06.v1'},
        'candidates': candidates,
        'budget': {'candidate_scan_limit': 12, 'selected_max': 6, 'clarifications_used': 0},
        'why_now': null,
      },
      'source_verification': verifications,
      'resolved_selected_count': resolvedSelectedCount,
    };

Future<void> _pumpPanel(
  WidgetTester tester, {
  required _StubReceiptApi api,
  required _FakeProvenanceRepository repo,
  TextScaler textScaler = TextScaler.noScaling,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        contextReceiptProvider.overrideWith(
          (ref) {
            final notifier = ContextReceiptNotifier(api);
            unawaited(notifier.load());
            return notifier;
          },
        ),
        memoryProvenanceRepositoryProvider.overrideWithValue(repo),
      ],
      child: testMaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: MediaQuery(
              data: MediaQueryData(textScaler: textScaler),
              child: const ContextReceiptPanel(),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 120));
}

InkWell _forgetInkWell(WidgetTester tester) => tester.widget<InkWell>(
      find.ancestor(
        of: find.text('忘记'),
        matching: find.byType(InkWell),
      ).first,
    );

/// 用「忘记」文字元素定位其外包 InkWell 的内部 Focus 节点并聚焦。
void _focusForget(WidgetTester tester) {
  final focus = Focus.maybeOf(tester.element(find.text('忘记').first));
  focus!.requestFocus();
}

/// 打开确认对话框并点确认（对话框确认键文案同为「忘记」→ 取最后一个）。
Future<void> _confirmForget(WidgetTester tester) async {
  await tester.tap(find.text('忘记').first);
  await tester.pump();
  expect(find.text('忘记这条内容？'), findsOneWidget);
  await tester.tap(find.text('忘记').last);
  await tester.pumpAndSettle();
}

void main() {
  setUp(setUpI18nForTesting);

  testWidgets('正：ready 态如实呈现——选中（来源已核对）+ 拒用归因 + 忘记可用',
      (tester) async {
    final api = _StubReceiptApi(_readyPayload(
      candidates: [
        {'ref': _resolvedRef, 'status': 'selected', 'reason_code': null, 'note': 'DEBUG_GATE'},
        {
          'ref': 'memory://goal/22222222-2222-2222-2222-222222222222',
          'status': 'rejected',
          'reason_code': 'out_of_scope_memory',
          'note': null,
        },
      ],
      verifications: [
        {'ref': _resolvedRef, 'resolution': 'resolved', 'status_code': 'ok'},
      ],
      resolvedSelectedCount: 1,
    ),
    );

    await _pumpPanel(tester, api: api, repo: _FakeProvenanceRepository());

    expect(find.text('这次的理解'), findsOneWidget);
    expect(find.textContaining('这次用了 1 条'), findsOneWidget);
    expect(find.textContaining('来源已核对'), findsOneWidget);
    expect(find.textContaining('不在这次的范围里'), findsOneWidget);
    // 未归因面：本回执没有 unknown 码，不应出现。
    expect(find.textContaining('未归因'), findsNothing);
    // debug note 永不进用户面。
    expect(find.textContaining('DEBUG_GATE'), findsNothing);
    // resolved 才有「忘记」。
    expect(find.text('忘记'), findsOneWidget);
  });

  testWidgets('正：unresolved selected 显式 unattributed，不给操作', (tester) async {
    final api = _StubReceiptApi(_readyPayload(
      candidates: [
        {'ref': 'memory://goal/22222222-2222-2222-2222-222222222222', 'status': 'selected'},
      ],
    ),);


    await _pumpPanel(tester, api: api, repo: _FakeProvenanceRepository());

    expect(find.textContaining('1 条来源已不可定位'), findsOneWidget);
    // 不可定位 = 无操作（不对不可溯来源行使忘记——防误删未知对象）。
    expect(find.text('忘记'), findsNothing);
  });

  testWidgets('正：空候选（selected=0）=「这次没有引用记忆」如实呈现', (tester) async {
    await _pumpPanel(
      tester,
      api: _StubReceiptApi(_readyPayload()),
      repo: _FakeProvenanceRepository(),
    );

    expect(find.text('这次没有引用你的记忆内容。'), findsOneWidget);
  });

  testWidgets('正：candidates 缺失（旧生产者）→ 暂缺明细，不当空集渲染', (tester) async {
    final payload = _readyPayload();
    (payload['receipt'] as Map<String, dynamic>)['candidates'] = null;

    await _pumpPanel(
      tester,
      api: _StubReceiptApi(payload),
      repo: _FakeProvenanceRepository(),
    );

    expect(find.text('这次回执暂缺候选明细。'), findsOneWidget);
    expect(find.text('这次没有引用你的记忆内容。'), findsNothing);
  });

  testWidgets('反：modeGated shadow =「记录中展示未开」，不是无回执', (tester) async {
    await _pumpPanel(
      tester,
      api: _StubReceiptApi({
        'mode': 'shadow',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': null,
      }),
      repo: _FakeProvenanceRepository(),
    );
    expect(find.text('理解回执在记录中，展示尚未开启。'), findsOneWidget);
    expect(find.text('这次没有产生理解回执（例如只是简单回答时）。'), findsNothing);
  });

  testWidgets('反：live 无回执 = 诚实 empty 态，与 modeGated 分立', (tester) async {
    await _pumpPanel(
      tester,
      api: _StubReceiptApi({
        'mode': 'live',
        'schema_version': 'context_selection_receipt.v1',
        'receipt': null,
      }),
      repo: _FakeProvenanceRepository(),
    );
    expect(find.text('这次没有产生理解回执（例如只是简单回答时）。'), findsOneWidget);
    expect(find.text('理解回执在记录中，展示尚未开启。'), findsNothing);
  });

  testWidgets('反：断网 → 诚实错误态 + 重试，绝不渲染为空数据或成功', (tester) async {
    final api = _StubReceiptApi(null)
      ..getError = DioException(
        requestOptions: RequestOptions(path: '/x'),
        type: DioExceptionType.connectionError,
      );

    await _pumpPanel(tester, api: api, repo: _FakeProvenanceRepository());

    expect(find.textContaining('现在连不上'), findsOneWidget);
    expect(find.text('这次没有产生理解回执（例如只是简单回答时）。'), findsNothing);
    expect(find.byType(PixelSuccessBadge), findsNothing);
    expect(find.text('重试'), findsOneWidget);
  });

  testWidgets('验收③ 正：budget_exhausted 面前「忘记」仍走真实 revoke 链',
      (tester) async {
    final repo = _FakeProvenanceRepository();
    final api = _StubReceiptApi(_readyPayload(
      candidates: [
        {'ref': _resolvedRef, 'status': 'selected'},
        {
          'ref': 'memory://goal/22222222-2222-2222-2222-222222222222',
          'status': 'rejected',
          'reason_code': 'budget_exhausted',
        },
      ],
      verifications: [
        {'ref': _resolvedRef, 'resolution': 'resolved', 'status_code': 'ok'},
      ],
      resolvedSelectedCount: 1,
    ),
    );

    await _pumpPanel(tester, api: api, repo: repo);

    // 预算面如实说明存在，且明示不影响更改/忘记。
    expect(find.textContaining('（1）'), findsOneWidget);
    expect(find.textContaining('只是当时的选择空间'), findsOneWidget);
    // 忘记可点、可走完确认 → 真实 revoke（kind/id 来自回执 ref）。
    expect(_forgetInkWell(tester).onTap, isNotNull);
    await _confirmForget(tester);

    expect(repo.revokedKind, 'episodic');
    expect(repo.revokedId, '11111111-1111-1111-1111-111111111111');
    // 成功 = 中性文案确认；绝不出现成功徽章（F03：memory 永不成功面孔）。
    expect(find.textContaining('已忘记'), findsWidgets);
    expect(find.byType(PixelSuccessBadge), findsNothing);
  });

  testWidgets('验收③ 反（变异守护）：budget_exhausted 面没有禁用态忘记',
      (tester) async {
    final api = _StubReceiptApi(_readyPayload(
      candidates: [
        {'ref': _resolvedRef, 'status': 'selected'},
        {
          'ref': 'memory://goal/22222222-2222-2222-2222-222222222222',
          'status': 'rejected',
          'reason_code': 'budget_exhausted',
        },
      ],
      verifications: [
        {'ref': _resolvedRef, 'resolution': 'resolved', 'status_code': 'ok'},
      ],
      resolvedSelectedCount: 1,
    ),
    );

    await _pumpPanel(tester, api: api, repo: _FakeProvenanceRepository());

    // 若有人把忘记按钮在预算面下禁用，本断言即红。
    expect(_forgetInkWell(tester).onTap, isNotNull);
    final button = tester.widget<SparkleButton>(
      find.byWidgetPredicate(
        (w) => w is SparkleButton && w.label == '忘记',
      ),
    );
    expect(button.disabled, isFalse);
  });

  testWidgets('忘记失败（后端拒绝）如实呈现错误文本，无成功视觉', (tester) async {
    final repo = _FakeProvenanceRepository()
      ..revokeError = DioException(
        requestOptions: RequestOptions(path: '/x'),
        response: Response<Map<String, dynamic>>(
          requestOptions: RequestOptions(path: '/x'),
          statusCode: 404,
          data: {'detail': 'not found'},
        ),
      );
    final api = _StubReceiptApi(_readyPayload(
      candidates: [
        {'ref': _resolvedRef, 'status': 'selected'},
      ],
      verifications: [
        {'ref': _resolvedRef, 'resolution': 'resolved', 'status_code': 'ok'},
      ],
      resolvedSelectedCount: 1,
    ),
    );

    await _pumpPanel(tester, api: api, repo: repo);
    await _confirmForget(tester);

    expect(find.textContaining('没有成功'), findsOneWidget);
    expect(find.byType(PixelSuccessBadge), findsNothing);
  });

  testWidgets('验收① 正：200% 字体下面板完整渲染，忘记按钮可见可走完流程',
      (tester) async {
    final repo = _FakeProvenanceRepository();
    final api = _StubReceiptApi(_readyPayload(
      candidates: [
        {'ref': _resolvedRef, 'status': 'selected'},
        {
          'ref': 'memory://goal/22222222-2222-2222-2222-222222222222',
          'status': 'rejected',
          'reason_code': 'duplicate',
        },
      ],
      verifications: [
        {'ref': _resolvedRef, 'resolution': 'resolved', 'status_code': 'ok'},
      ],
      resolvedSelectedCount: 1,
    ),
    );

    await _pumpPanel(
      tester,
      api: api,
      repo: repo,
      textScaler: const TextScaler.linear(2.0),
    );

    expect(tester.takeException(), isNull);
    expect(find.text('这次的理解'), findsOneWidget);
    expect(find.text('忘记'), findsOneWidget);
    await _confirmForget(tester);
    expect(repo.revokedId, '11111111-1111-1111-1111-111111111111');
  });

  testWidgets('验收① 正：忘记键盘可达——聚焦后 Space 激活与点按等效', (tester) async {
    final repo = _FakeProvenanceRepository();
    final api = _StubReceiptApi(_readyPayload(
      candidates: [
        {'ref': _resolvedRef, 'status': 'selected'},
      ],
      verifications: [
        {'ref': _resolvedRef, 'resolution': 'resolved', 'status_code': 'ok'},
      ],
      resolvedSelectedCount: 1,
    ),
    );

    await _pumpPanel(tester, api: api, repo: repo);

    // 「忘记」按钮可聚焦（键盘可达），聚焦后 Space 激活等同点按。
    _focusForget(tester);
    await tester.pump();
    final focus = Focus.maybeOf(tester.element(find.text('忘记').first))!;
    expect(focus.hasFocus, isTrue);
    await tester.sendKeyEvent(LogicalKeyboardKey.space);
    await tester.pumpAndSettle();

    expect(find.text('忘记这条内容？'), findsOneWidget);
  });
}
