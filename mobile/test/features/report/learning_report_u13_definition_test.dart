import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/theme/sparkle_context_extension.dart';
import 'package:sparkle/core/design/theme/sparkle_theme_extension.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/report/data/models/learning_report.dart';
import 'package:sparkle/features/report/presentation/screens/learning_report_screen.dart';
import 'package:sparkle/features/report/presentation/widgets/mastery_radar_chart.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// 首份报告会触发成就庆祝对话框（真实产品行为；SharedPreferences mock 使
/// 其真实完成并弹出）——先关闭再滚动，否则拖拽被对话框吸收。
Future<void> _dismissCelebrationIfAny(WidgetTester tester) async {
  // 首份报告庆祝对话框 barrierDismissible=true——点 barrier 关闭
  // （对话框自带入场动画，'关闭' 文本无 hit-test 目标）。
  final barrier = find.byType(ModalBarrier);
  if (barrier.evaluate().isNotEmpty) {
    await tester.pump(const Duration(milliseconds: 500));
    await tester.tap(barrier.last, warnIfMissed: false);
    await tester.pump(const Duration(milliseconds: 300));
    await tester.pump(const Duration(milliseconds: 500));
  }
}

/// 报告面较长：有界循环滚动直到目标出现（360dp 小屏视口；默认 800 宽
/// 视口下拖拽起点会落到内容列外导致 hit-test miss，故先锁视口再滚）。
Future<void> dragTo(WidgetTester tester, Finder finder) async {
  final vertical = find.byWidgetPredicate(
    (widget) =>
        widget is Scrollable && widget.axisDirection == AxisDirection.down,
  ).first;
  for (var i = 0; i < 40 && finder.evaluate().isEmpty; i++) {
    await tester.drag(vertical, const Offset(0, -300));
    await tester.pump(const Duration(milliseconds: 100));
  }
}

/// U13_EVIDENCE_DIR 设置时落盘报告面截图+文本树（v4/evidence/V4-U13）。
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

/// V4-U13 · 学习报告面守卫：百分比/样本/时间窗有真实定义 + 跳原始记录 +
/// 图表标签现代读数（低刺激等价）。
///
/// 每面一正一反：
/// - 掌握度定义行随行（定义+样本数），节点行可跳星图原始记录（node_id）；
/// - node_id 缺失 → 按钮回落「打开知识星图」（不编造节点地址）；
/// - 雷达图定义行 + 标签 bodySmall（非像素字）；低刺激档同构渲染（等价）。
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() {
    // runAsync 真异步窗口（证据落盘）内不触平台通道：secure_storage 返回空、
    // SharedPreferences 返回空库（历史缓存/鉴权读取 fail-closed 降级）。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
        (call) async => null,
      )
      ..setMockMethodCallHandler(
        const MethodChannel('plugins.flutter.io/shared_preferences'),
        (call) async => switch (call.method) {
          // 预置「首份报告」里程碑已解锁：庆祝对话框不弹（真实弹窗链
          // 依赖平台通道动画，测试面只需要报告内容本身）。
          'getAll' => <String, Object>{
            'flutter.mirofish_milestone_v1:firstReport': true,
          },
          _ => true,
        },
      );
  });

  LearningReport reportWithNodes({bool withNodeId = true}) => LearningReport(
        reportId: 'report-u13',
        markdown: '# 本周总结',
        sections: const <String>['summary'],
        mastery: <LearningMasteryDatum>[
          LearningMasteryDatum(
            nodeName: '特征值',
            masteryScore: 82,
            nodeId: withNodeId ? 'node-1' : null,
            relatedErrorCount: 3,
          ),
          const LearningMasteryDatum(
            nodeName: '特征向量',
            masteryScore: 76,
          ),
          const LearningMasteryDatum(
            nodeName: '行列式',
            masteryScore: 58,
          ),
          const LearningMasteryDatum(
            nodeName: '线性变换',
            masteryScore: 71,
          ),
        ],
      );

  group('LearningMasteryDatum 原始数值解析（跳原始记录的身份随行）', () {
    test('node_id/related_error_count 如实解析；masteryPercent 取整', () {
      final item = LearningMasteryDatum.fromJson(<String, dynamic>{
        'node_name': '特征值',
        'mastery_score': 82.4,
        'node_id': 'node-1',
        'related_error_count': 3,
      });
      expect(item.nodeId, 'node-1');
      expect(item.relatedErrorCount, 3);
      expect(item.masteryPercent, 82);
    });

    test('node_id 缺失/空串 → null（不编造地址），计数缺省 0', () {
      final missing = LearningMasteryDatum.fromJson(<String, dynamic>{
        'node_name': '特征值',
        'mastery_score': 50,
      });
      final empty = LearningMasteryDatum.fromJson(<String, dynamic>{
        'node_name': '特征值',
        'mastery_score': 50,
        'node_id': '',
      });
      expect(missing.nodeId, isNull);
      expect(missing.relatedErrorCount, 0);
      expect(empty.nodeId, isNull);
    });
  });

  group('MasteryRadarChart 定义行与现代标签（低刺激等价）', () {
    Future<void> pumpRadar(
      WidgetTester tester, {
      bool lowStimulation = false,
    }) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.light().copyWith(
            extensions: [
              SparkleThemeExtension.light(
                stimulationLevel:
                    lowStimulation ? StimulationLevel.low : StimulationLevel.standard,
              ),
            ],
          ),
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
          home: const Scaffold(
            body: SingleChildScrollView(
              child: MasteryRadarChart(
                labels: ['特征值', '特征向量', '行列式'],
                values: [0.82, 0.76, 0.58],
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('定义行随行（0–100 证据融合读数 + 样本＝3 个节点）', (tester) async {
      await pumpRadar(tester);
      expect(
        find.text('图上每个轴是一条 0–100 的证据融合掌握度读数；样本＝当前绘制的 3 个能力节点。'),
        findsOneWidget,
      );
      // 图例数值是真实读数（0–100 融合值取整），不是像素装饰。
      expect(find.text('特征值 82%'), findsOneWidget);
    });

    testWidgets('标签走现代排版（bodySmall，非像素字族）——低刺激档同构等价',
        (tester) async {
      await pumpRadar(tester, lowStimulation: true);
      expect(
        find.text('图上每个轴是一条 0–100 的证据融合掌握度读数；样本＝当前绘制的 3 个能力节点。'),
        findsOneWidget,
      );
      final labelStyle = tester.widget<Text>(find.text('特征值').last).style;
      // 雷达轴标签显式 bodySmall（现代排版），没有任何像素字族替换。
      final bodySmall = Theme.of(tester.element(find.text('特征值').last))
          .textTheme
          .bodySmall;
      expect(labelStyle?.fontSize, bodySmall?.fontSize);
      expect(labelStyle?.fontFamily, isNot(contains('Pixel')));

      // 低刺激档下颜色语义等价：info/success 槽仍来自令牌（非高饱和装饰色）。
      final context = tester.element(find.text('特征值').last);
      expect(context.colors.info, isNotNull);
    });
  });

  group('报告面定义行与节点原始记录深链', () {
    Future<void> pumpReport(
      WidgetTester tester,
      LearningReport report, {
      required GoRouter router,
      GlobalKey? repaintKey,
    }) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(360, 800) * 2.0;
      tester.view.platformDispatcher.textScaleFactorTestValue = 1.0;
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
        tester.view.platformDispatcher.clearTextScaleFactorTestValue();
      });
      await tester.pumpWidget(
        RepaintBoundary(
          key: repaintKey,
          child: ProviderScope(
            overrides: [
              apiClientProvider.overrideWithValue(_NoopApiClient()),
            ],
            child: MaterialApp.router(
              routerConfig: router,
              theme: ThemeData.light().copyWith(
                extensions: [SparkleThemeExtension.light()],
              ),
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
      await tester.pump(const Duration(milliseconds: 150));
      await tester.pump(const Duration(milliseconds: 350));
      await tester.pump(const Duration(milliseconds: 350));
    }

    testWidgets('关键指标定义行随行（掌握度定义 + 样本＝4 个能力节点）+ 证据落盘钩子',
        (tester) async {
      final repaintKey = GlobalKey();
      final router = GoRouter(
        initialLocation: '/learning-report',
        routes: [
          GoRoute(
            path: '/learning-report',
            builder: (_, __) =>
                LearningReportScreen(report: reportWithNodes()),
          ),
          GoRoute(
            path: '/galaxy',
            builder: (_, __) => const Scaffold(body: Text('GALAXY_HOME')),
          ),
          GoRoute(
            path: '/galaxy/node/:id',
            builder: (_, __) => const Scaffold(body: Text('NODE_OK')),
          ),
        ],
      );
      await pumpReport(
        tester,
        reportWithNodes(),
        router: router,
        repaintKey: repaintKey,
      );

      await _dismissCelebrationIfAny(tester);

      // 360dp 小屏视口（内容列宽 360，默认 800 宽视口下拖拽起点会落到
      // 内容列外导致 hit-test miss）；报告面较长，用有界循环滚到定义行。
      await dragTo(tester, find.textContaining('掌握度＝星图能力节点的证据融合值'));
      expect(find.textContaining('样本＝4 个能力节点'), findsOneWidget);
      expect(tester.takeException(), isNull);

      await _writeEvidence(
        tester,
        repaintKey,
        'u13_report_definition_360x800',
      );
    });

    testWidgets('节点明细 sheet：定义随行 + 直达该节点原始记录（跳原始记录）', (tester) async {
      final router = GoRouter(
        initialLocation: '/learning-report',
        routes: [
          GoRoute(
            path: '/learning-report',
            builder: (_, __) =>
                LearningReportScreen(report: reportWithNodes()),
          ),
          GoRoute(
            path: '/galaxy',
            builder: (_, __) => const Scaffold(body: Text('GALAXY_HOME')),
          ),
          GoRoute(
            path: '/galaxy/node/:id',
            builder: (context, state) => Scaffold(
              body: Text('NODE_OK ${state.pathParameters['id']}'),
            ),
          ),
        ],
      );
      await pumpReport(tester, reportWithNodes(), router: router);

      await dragTo(tester, find.text('重点知识维度'));
      // 「特征值 82%」同时出现在雷达图例与维度 chips（同一真实读数两处
      // 渲染）；此处点维度 chip（ActionChip）进明细 sheet。
      await tester.tap(find.text('特征值 82%').first);
      await tester.pumpAndSettle();

      // 数值真实定义随行（关联错题计数如实）。
      expect(find.textContaining('掌握度＝这个能力节点的证据融合值'), findsOneWidget);
      expect(find.textContaining('3 条可核对的错题记录'), findsOneWidget);
      // node_id 在册 → 节点级原始记录入口。
      expect(find.text('查看星图原始记录'), findsOneWidget);

      await tester.ensureVisible(find.text('查看星图原始记录'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('查看星图原始记录'));
      await tester.pumpAndSettle();
      expect(find.text('NODE_OK node-1'), findsOneWidget);
    });
  });
}

class _NoopApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
