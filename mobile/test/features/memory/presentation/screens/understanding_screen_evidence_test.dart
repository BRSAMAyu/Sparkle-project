// V4-U03 · 「这次的理解」证据采集：顶层截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（回执面板四态、
// 来源已核对行、budget 归因、黑话清理后的操作词），不写文件——保证套件
// 全绿且无副作用。设 `U03_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   u03_receipt_ready_360x800.png / _semantics.txt
//   u03_receipt_offline_360x800.png / _semantics.txt
// 证据落盘路径见 v4/evidence/V4-U03/run_manifest.json。
import 'dart:async' show unawaited;
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/memory/data/memory_provenance_models.dart';
import 'package:sparkle/features/memory/data/memory_provenance_repository.dart';
import 'package:sparkle/features/memory/presentation/providers/context_receipt_provider.dart';
import 'package:sparkle/features/memory/presentation/screens/understanding_screen.dart';
import 'package:sparkle/features/settings/presentation/providers/accessibility_provider.dart';

import '../../../../shared/i18n_test_helper.dart';

/// 空载可访问性设置：全屏泵浦下 SparkleButton 会 watch 该 provider，
/// 其构造即发起服务端同步（真实 dio → fake async 内挂起 Timer）——证据
/// 泵浦不触网，覆盖为立即就绪的子类。
class _IdleAccessibilitySettingsNotifier extends AccessibilitySettingsNotifier {
  _IdleAccessibilitySettingsNotifier(super.ref);

  @override
  Future<void> load() async {
    state = state.copyWith(isLoaded: true);
  }
}

class _EvidenceApi implements ApiClient {
  _EvidenceApi(this.response);

  Object? response;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final body = response;
    if (body is DioException) {
      throw body;
    }
    return Response<T>(
      requestOptions: RequestOptions(path: path),
      data: body as T,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _EvidenceProvenanceRepository implements MemoryProvenanceRepository {
  @override
  Future<ProvenanceListResult> listItems({
    UnderstandingBucket? bucket,
    String? kind,
    int limit = 200,
    int offset = 0,
    bool includeInactive = false,
  }) async =>
      ProvenanceListResult(
        items: [
          ProvenanceMemoryItem(
            kind: 'episodic',
            id: '11111111-1111-1111-1111-111111111111',
            ref: 'memory://episodic/11111111-1111-1111-1111-111111111111',
            bucket: UnderstandingBucket.told,
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
            updatedAt: DateTime(2026, 9, 27),
          ),
        ],
        total: 1,
        hasMore: false,
        scanCapped: false,
      );

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('evidence test only lists items');
}

Map<String, dynamic> _readyPayload() => {
      'mode': 'live',
      'schema_version': 'context_selection_receipt.v1',
      'receipt': {
        'schema_version': 'context_selection_receipt.v1',
        'receipt_id': 'csr_01ARZ3NDEKTSV4RRFFQ69G5FAV',
        'selection_role': 'chat_context',
        'decision_id': null,
        'input_versions': {
          'memory_epoch': 7,
          'goal_version': null,
          'task_version': null,
          'policy_version': null,
          'selector_version': 'context_pack.v4-i06.v1',
        },
        'candidates': [
          {
            'ref': 'memory://episodic/11111111-1111-1111-1111-111111111111',
            'status': 'selected',
            'reason_code': null,
            'note': null,
          },
          {
            'ref': 'memory://goal/22222222-2222-2222-2222-222222222222',
            'status': 'rejected',
            'reason_code': 'out_of_scope_memory',
            'note': null,
          },
          {
            'ref': 'memory://preference/33333333-3333-3333-3333-333333333333',
            'status': 'rejected',
            'reason_code': 'budget_exhausted',
            'note': null,
          },
        ],
        'budget': {
          'candidate_scan_limit': 12,
          'selected_max': 6,
          'clarifications_used': 0,
        },
        'why_now': {
          'statement': '你最近在准备离散数学的考试，所以带上了这条记录',
          'basis_refs': ['memory://episodic/11111111-1111-1111-1111-111111111111'],
          'expires_at': null,
          'confidence_band': 'high',
        },
      },
      'source_verification': [
        {
          'ref': 'memory://episodic/11111111-1111-1111-1111-111111111111',
          'resolution': 'resolved',
          'status_code': 'ok',
          'detail': 'episodic',
        },
      ],
      'resolved_selected_count': 1,
    };

/// 语义树 dump（元素树口径，同 F04 证据测试）。
String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el, int depth) {
    final ro = el.renderObject;
    if (ro is RenderParagraph) {
      final text = ro.text.toPlainText();
      if (text.trim().isNotEmpty) {
        final rect = ro.localToGlobal(Offset.zero) & ro.size;
        buf.writeln('${'  ' * depth}- label="$text" isText=true rect=$rect');
      }
    }
    if (ro is RenderSemanticsAnnotations) {
      var isButton = false;
      try {
        isButton = (ro as dynamic).button as bool? ?? false;
      } on NoSuchMethodError {
        isButton = false;
      }
      final rect = ro.localToGlobal(Offset.zero) & ro.size;
      buf.writeln(
        '${'  ' * depth}- label="${ro.properties.label}" '
        'value="${ro.properties.value}" '
        'isButton=$isButton rect=$rect',
      );
    }
    el.visitChildElements((child) => visit(child, depth));
  }

  visit(rootElement, 0);
  return buf.toString();
}

Future<SemanticsHandle> _pumpEvidence(
  WidgetTester tester, {
  required _EvidenceApi api,
  required GlobalKey repaintKey,
}) async {
  tester.view.devicePixelRatio = 2.0;
  tester.view.physicalSize = const Size(360, 800) * 2.0;
  addTearDown(() {
    tester.view.resetDevicePixelRatio();
    tester.view.resetPhysicalSize();
  });
  setUpI18nForTesting();

  final semantics = tester.ensureSemantics();
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        accessibilitySettingsProvider.overrideWith(
          _IdleAccessibilitySettingsNotifier.new,
        ),
        contextReceiptProvider.overrideWith(
          (ref) {
            final notifier = ContextReceiptNotifier(api);
            unawaited(notifier.load());
            return notifier;
          },
        ),
        memoryProvenanceRepositoryProvider
            .overrideWithValue(_EvidenceProvenanceRepository()),
      ],
      child: RepaintBoundary(
        key: repaintKey,
        child: testMaterialApp(home: const UnderstandingScreen()),
      ),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 200));
  await tester.pump(const Duration(milliseconds: 400));
  return semantics;
}

Future<void> _writeEvidence(
  WidgetTester tester,
  GlobalKey repaintKey,
  String basename,
) async {
  final dir = io.Platform.environment['U03_EVIDENCE_DIR'];
  if (dir == null || dir.isEmpty) {
    return;
  }
  final rootElement = tester.binding.rootElement;
  await tester.runAsync(() async {
    final outDir = io.Directory(dir);
    if (!outDir.existsSync()) {
      outDir.createSync(recursive: true);
    }
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(repaintKey),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File('${outDir.path}/$basename.png')
        .writeAsBytesSync(bytes!.buffer.asUint8List());
    io.File('${outDir.path}/$basename${'_semantics.txt'}')
        .writeAsStringSync(_dumpSemanticsFromElements(rootElement!));
  });
}

void main() {
  testWidgets('ready 态：回执面板如实呈现（选中/归因/budget）+ 证据落盘钩子',
      (tester) async {
    final repaintKey = GlobalKey();
    final semantics = await _pumpEvidence(
      tester,
      api: _EvidenceApi(_readyPayload()),
      repaintKey: repaintKey,
    );

    // 真实渲染断言（无论是否落盘都执行）。
    expect(find.text('这次的理解'), findsOneWidget);
    expect(find.textContaining('这次用了 1 条'), findsOneWidget);
    expect(find.textContaining('来源已核对'), findsOneWidget);
    expect(find.textContaining('不在这次的范围里'), findsOneWidget);
    expect(find.textContaining('只是当时的选择空间'), findsOneWidget);
    expect(find.textContaining('未归因'), findsNothing);
    // 回执行 + 四组条目操作条各有一个「忘记」（同词表、同一真实链）。
    expect(find.text('忘记'), findsWidgets);
    expect(find.text('你告诉我的'), findsWidgets);
    expect(tester.takeException(), isNull);

    await _writeEvidence(tester, repaintKey, 'u03_receipt_ready_360x800');
    semantics.dispose();
  });

  testWidgets('断网态：诚实错误 + 重试，绝不渲染为空数据或成功', (tester) async {
    final repaintKey = GlobalKey();
    final semantics = await _pumpEvidence(
      tester,
      api: _EvidenceApi(
        DioException(
          requestOptions: RequestOptions(path: '/x'),
          type: DioExceptionType.connectionError,
        ),
      ),
      repaintKey: repaintKey,
    );

    expect(find.textContaining('现在连不上'), findsOneWidget);
    expect(find.text('这次没有产生理解回执（例如只是简单回答时）。'), findsNothing);
    expect(find.text('重试'), findsOneWidget);
    expect(tester.takeException(), isNull);

    await _writeEvidence(tester, repaintKey, 'u03_receipt_offline_360x800');
    semantics.dispose();
  });
}
