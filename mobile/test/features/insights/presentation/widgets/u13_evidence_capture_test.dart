// V4-U13 · 洞察三读面证据采集：顶层截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件仍执行真实渲染断言（撤回排除行、理解档行、
// 样本量定义行、报告定义行、观察档徽章），不写文件——保证套件全绿且无
// 副作用。设 `U13_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   u13_evidence_card_360x800.png / _semantics.txt（洞察卡三态行）
//   u13_pattern_tier_360x800.png / _semantics.txt（观察档替代置信%）
// 报告面截图由 test/features/report/learning_report_u13_definition_test.dart
// 的同名钩子落盘（其 harness 免触全局服务，稳定可复现）。
// 证据落盘路径见 v4/evidence/V4-U13/run_manifest.json。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/cognitive/data/models/behavior_pattern_model.dart';
import 'package:sparkle/features/cognitive/data/models/cognitive_fragment_model.dart';
import 'package:sparkle/features/cognitive/data/repositories/i_cognitive_repository.dart';
import 'package:sparkle/features/cognitive/presentation/providers/cognitive_provider.dart';
import 'package:sparkle/features/cognitive/presentation/screens/pattern_list_screen.dart';
import 'package:sparkle/features/insights/data/models/evidence_insight_card.dart';
import 'package:sparkle/features/insights/presentation/widgets/evidence_insight_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../../../shared/i18n_test_helper.dart';

EvidenceInsightCardData _helpedCardWithAllHonestLines() =>
    EvidenceInsightCardData.fromJson(<String, dynamic>{
      'id': 'interventions_that_helped:rescope:recall_gap',
      'kind': 'interventions_that_helped',
      'window_days': 30,
      'fact': <String, dynamic>{
        'intervention_type': 'rescope',
        'friction_tag': 'recall_gap',
        'n_exposed': 3,
        'n_accepted': 2,
        'n_observed': 2,
        'n_positive': 2,
        'n_negative': 0,
      },
      'interpretation': <String, dynamic>{
        'evidence_strength': 'accumulated',
        'direction': 'positive_association',
        'causal': false,
      },
      'uncertainty': <String, dynamic>{
        'qualifiers': <String>['correlation_not_causation', 'small_sample'],
        'samples': 2,
        'outcome_samples_raw': 3,
        'duplicate_outcome_samples_dropped': 1,
        'not_yet_observed': 1,
        'withdrawn_refs_excluded': 2,
      },
      'understanding': <String, dynamic>{
        'claim_allowed': false,
        'band': 'incomplete_evidence',
        'samples': 2,
        'missing': 0,
        'censored': 1,
      },
      'next_step': <String, dynamic>{
        'observation_id': 'interventions_that_helped:rescope:recall_gap',
        'user_can_reject': true,
        'reject_penalty': 'none',
      },
      'evidence': <dynamic>[
        <String, dynamic>{
          'label_key': 'evidence_directive_log',
          'deep_link': '/learning/insights/directives',
          'refs': <String>['d1', 'd2'],
        },
      ],
      'implication': <String, dynamic>{
        'action_key': 'review_directives',
        'deep_link': '/learning/insights/directives',
      },
    });

void _setUpI18n() {
  setUpI18nForTesting();
}

Future<void> _writeEvidence(
  WidgetTester tester,
  GlobalKey repaintKey,
  String basename,
) async {
  final dir = io.Platform.environment['U13_EVIDENCE_DIR'];
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
    final buffer = StringBuffer();
    void visit(Element element) {
      final widget = element.widget;
      if (widget is Text) {
        buffer.writeln(widget.data ?? widget.textSpan?.toPlainText());
      }
      element.visitChildren(visit);
    }

    visit(rootElement!);
    io.File('${outDir.path}/$basename${'_semantics.txt'}')
        .writeAsStringSync(buffer.toString());
  });
}

void main() {
  setUp(() {
    // 证据泵浦不触平台通道：secure_storage 返回空（AppEventStream 的鉴权
    // 读取在 runAsync 真异步窗口内不会命中缺失插件）。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (call) async => null,
      )
      // runAsync 真异步窗口内报告历史缓存会读 SharedPreferences——返回空库。
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.flutter.io/shared_preferences'),
        (call) async => switch (call.method) {
          'getAll' => <String, Object>{},
          _ => true,
        },
      );
  });

  testWidgets('洞察卡：撤回排除/理解档/样本量定义/可拒绝行如实呈现 + 证据落盘钩子',
      (tester) async {
    _setUpI18n();
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(360, 800) * 2.0;
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });
    final repaintKey = GlobalKey();
    await tester.pumpWidget(
      RepaintBoundary(
        key: repaintKey,
        child: MaterialApp(
          theme: ThemeData.light()
              .copyWith(extensions: [SparkleThemeExtension.light()]),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: Scaffold(
            body: SingleChildScrollView(
              child: EvidenceInsightCardWidget(
                card: _helpedCardWithAllHonestLines(),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.textContaining('已排除 2 条'), findsOneWidget);
    expect(find.textContaining('证据不足：1 条结果未到期'), findsOneWidget);
    expect(find.textContaining('样本＝去重后方向观察 2 条'), findsOneWidget);
    expect(find.textContaining('可以忽略'), findsOneWidget);
    expect(
      find.textContaining('%'),
      findsNothing,
      reason: 'D-07 卡契约禁百分比，呈现面不引入',
    );
    expect(tester.takeException(), isNull);

    await _writeEvidence(tester, repaintKey, 'u13_evidence_card_360x800');
  });

  testWidgets('认知定式卡：观察档替代置信% + 证据落盘钩子', (tester) async {
    _setUpI18n();
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(360, 800) * 2.0;
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });
    final repaintKey = GlobalKey();
    final seeded = <BehaviorPatternModel>[
      BehaviorPatternModel(
        id: 'bp-1',
        userId: 'u1',
        patternName: '计划乐观偏差',
        patternType: PatternType.cognitive,
        confidenceScore: 0.73,
        frequency: 3,
        isArchived: false,
        createdAt: DateTime(2026, 3, 15),
        updatedAt: DateTime(2026, 3, 20),
      ),
    ];
    final router = GoRouter(
      initialLocation: '/cognitive/patterns',
      routes: [
        GoRoute(
          path: '/cognitive/patterns',
          builder: (_, __) => const PatternListScreen(),
        ),
        GoRoute(
          path: '/focus',
          builder: (_, __) => const Scaffold(body: Text('FOCUS')),
        ),
      ],
    );
    await tester.pumpWidget(
      RepaintBoundary(
        key: repaintKey,
        child: ProviderScope(
          overrides: [
            cognitiveProvider.overrideWith(
              (ref) => _SeededNotifier(seeded),
            ),
            apiClientProvider.overrideWithValue(_EvidenceNoopApiClient()),
          ],
          child: MaterialApp.router(
            routerConfig: router,
            theme: ThemeData.light()
                .copyWith(extensions: [SparkleThemeExtension.light()]),
            locale: const Locale('zh'),
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            supportedLocales: AppLocalizations.supportedLocales,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('多次观察到'), findsOneWidget);
    expect(find.textContaining('置信'), findsNothing);
    expect(tester.takeException(), isNull);

    await _writeEvidence(tester, repaintKey, 'u13_pattern_tier_360x800');
  });
}

class _SeededNotifier extends CognitiveNotifier {
  _SeededNotifier(List<BehaviorPatternModel> patterns)
      : _seed = patterns,
        super(_EmptyRepo());

  final List<BehaviorPatternModel> _seed;

  @override
  Future<void> loadPatterns() async {
    state = CognitiveState(patterns: _seed);
  }
}

class _EmptyRepo implements ICognitiveRepository {
  @override
  Future<CognitiveFragmentModel> createFragment(
    CognitiveFragmentCreate data,
  ) async =>
      throw UnimplementedError();

  @override
  Future<List<CognitiveFragmentModel>> getFragments({
    int? limit,
    int? skip,
  }) async =>
      const [];

  @override
  Future<List<BehaviorPatternModel>> getBehaviorPatterns() async => const [];
}

/// 证据泵浦不触网：真 ApiClient 的 AuthInterceptor 会读 SharedPreferences/
/// secure_storage（平台通道缺失）——覆盖为空实现。
class _EvidenceNoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
