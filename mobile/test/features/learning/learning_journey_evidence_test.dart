// V4-U10 · 旅程页证据采集：顶层截图（PNG）+ 语义树 dump。
//
// 常规跑 `flutter test`：本文件执行真实渲染断言（页面可构建、上下文头/
// 材料/检验卡就位），不写文件——保证套件全绿且无副作用。
// 设 `LEARNING_JOURNEY_EVIDENCE_DIR=<abs dir>` 时额外写出：
//   learning_journey_hub.png（旅程页顶层截图，dpr=2）
//   learning_journey_check.png（检验题面已放行的顶层截图，dpr=2）
//   learning_journey_semantics.txt（语义树 dump）
// 证据落盘路径见 v4/evidence/V4-U10/run_manifest.json。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/learning/data/learning_journey_models.dart';
import 'package:sparkle/features/learning/data/learning_journey_repository.dart';
import 'package:sparkle/features/learning/presentation/providers/learning_journey_provider.dart';
import 'package:sparkle/features/learning/presentation/screens/learning_journey_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../shared/i18n_test_helper.dart';
import '../../shared/u02_test_fonts.dart';

class _EvidenceRepository extends LearningJourneyRepository {
  _EvidenceRepository() : super(Dio());

  bool checkRequested = false;

  @override
  Future<LearningJourneyView> getJourney({required String goalTaskId}) async =>
      LearningJourneyView.fromJson(<Object?, Object?>{
        'goal': <Object?, Object?>{'task_id': goalTaskId, 'title': '力学单元巩固'},
        'scaffold': <Object?, Object?>{
          'stage': 'attempt',
          'hint_level': 'reduced',
          'segment': 'practice',
        },
        'materials': <Object?>[
          <Object?, Object?>{
            'file_name': '讲义-第3章-摩擦力.pdf',
            'mime_type': 'application/pdf',
            'source': <Object?, Object?>{
              'source_id': 'file-abc123',
              'source_version': '2026-09-28T10:00:00',
              'source_kind': 'document',
            },
            'parse': <Object?, Object?>{'status': 'parsed', 'manual_input_required': false},
          },
          <Object?, Object?>{
            'file_name': '手写题拍照.jpg',
            'mime_type': 'image/jpeg',
            'source': <Object?, Object?>{
              'source_id': 'file-img456',
              'source_version': '2026-09-28T09:00:00',
              'source_kind': 'document',
            },
            'parse': <Object?, Object?>{
              'status': 'unsupported',
              'reason': 'ocr_unavailable_for_image',
              'manual_input_required': true,
            },
          },
        ],
        'errors': <Object?>[
          <Object?, Object?>{
            'id': 'error-1',
            'subject_code': 'physics',
            'question_text': '斜面上的物体为什么匀速下滑？',
            'review_count': 2,
            'source': <Object?, Object?>{
              'source_id': 'error-1',
              'source_version': '2026-09-28T08:00:00',
              'source_kind': 'error_record',
            },
          },
        ],
        'practice': <Object?, Object?>{'evidence_supported': true},
        'check': <Object?, Object?>{'question': '独立解释：为什么滑动摩擦力与接触面积无关？'},
      });

  @override
  Future<CheckEnterResult> enterCheck({required String goalTaskId}) async {
    checkRequested = true;
    return CheckEnterResult(
      available: true,
      question: LearningCheckQuestion.sanitize(<Object?, Object?>{
        'check_available': true,
        'question': '独立解释：为什么滑动摩擦力与接触面积无关？',
      }),
    );
  }

  @override
  Future<LearningCheckVerdict> submitCheck({
    required String goalTaskId,
    required String answer,
  }) async =>
      LearningCheckVerdict.fromJson(<Object?, Object?>{
        'graded': true,
        'correct': true,
        'reason': 'OK.check_graded_correct',
        'feedback': '检验通过：这一步由你独立完成。',
      });
}

String _dumpSemantics(SemanticsNode node, int depth) {
  final data = node.getSemanticsData();
  final buf = StringBuffer(
    '${'  ' * depth}- label="${node.label}" '
    'isButton=${data.flagsCollection.isButton} '
    'rect=${node.rect}\n',
  );
  node.visitChildren((child) {
    buf.write(_dumpSemantics(child, depth + 1));
    return true;
  });
  return buf.toString();
}

Future<void> _capture(WidgetTester tester, String outPath) async {
  await tester.runAsync(() async {
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(const Key('learning-evidence-root')),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File(outPath).writeAsBytesSync(bytes!.buffer.asUint8List());
  });
}

void main() {
  testWidgets('[evidence] 旅程页真实渲染并按需落盘（hub + 检验题面）', (tester) async {
    tester.view.devicePixelRatio = 2.0;
    tester.view.physicalSize = const Size(800, 1600);
    addTearDown(() {
      tester.view.resetDevicePixelRatio();
      tester.view.resetPhysicalSize();
    });
    setUpI18nForTesting();
    await tester.runAsync(U02TestFonts.load);
    final repository = _EvidenceRepository();
    final journeyContext = LearningJourneyContext.fromLaunch(
      goalTaskId: 'goal-demo-1',
      goalTitle: '力学单元巩固',
    );
    final semantics = tester.ensureSemantics();
    await tester.pumpWidget(
      MaterialApp(
        theme: AppThemes.lightTheme,
        locale: const Locale('zh'),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        home: RepaintBoundary(
          key: const Key('learning-evidence-root'),
          child: ProviderScope(
            overrides: [learningJourneyRepositoryProvider.overrideWithValue(repository)],
            child: LearningJourneyScreen(journeyContext: journeyContext),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // 真实渲染断言（无论是否落盘都执行）。
    expect(find.byKey(const Key('learning_context_header')), findsOneWidget);
    expect(find.text('力学单元巩固'), findsOneWidget);
    expect(find.text('讲义-第3章-摩擦力.pdf'), findsOneWidget);
    expect(tester.takeException(), isNull);

    final dir = io.Platform.environment['LEARNING_JOURNEY_EVIDENCE_DIR'];
    if (dir != null && dir.isNotEmpty) {
      final outDir = io.Directory(dir);
      if (!outDir.existsSync()) outDir.createSync(recursive: true);
      await _capture(tester, '$dir/learning_journey_hub.png');

      // 真实操作：点「继续当前动作」→ 检验题面放行（证据门服务端放行）。
      await tester.tap(find.byKey(const Key('learning_continue_action')));
      await tester.pumpAndSettle();
      expect(repository.checkRequested, isTrue);
      expect(find.byKey(const Key('learning_check_question')), findsOneWidget);
      await tester.scrollUntilVisible(
        find.byKey(const Key('learning_check_card')),
        200,
        scrollable: find
            .descendant(
              of: find.byKey(const Key('learning_journey_screen')),
              matching: find.byType(Scrollable),
            )
            .first,
      );
      await tester.pumpAndSettle();
      await _capture(tester, '$dir/learning_journey_check.png');

      // 语义证据：优先语义树根；不可用时从 widget 树枚举 Semantics 节点
      // （label/flag——读屏可得的全部可读面）。
      await tester.pumpAndSettle();
      final owner = RendererBinding.instance.rootPipelineOwner.semanticsOwner;
      final root = owner?.rootSemanticsNode;
      final buf = StringBuffer();
      if (root != null) {
        buf.write(_dumpSemantics(root, 0));
      } else {
        buf.writeln('(渲染语义根不可用；widget 树 Semantics 枚举)');
        void walk(Element element, int depth) {
          final widget = element.widget;
          if (widget is Semantics) {
            buf.writeln(
              '${'  ' * depth}- Semantics label="${widget.properties.label}" '
              'button=${widget.properties.button} '
              'onTap=${widget.properties.onTap != null}',
            );
          } else if (widget is Tooltip) {
            buf.writeln('${'  ' * depth}- Tooltip message="${widget.message}"');
          }
          element.visitChildren((child) => walk(child, depth + 1));
        }

        tester.element(find.byKey(const Key('learning-evidence-root'))).visitChildren(
              (child) => walk(child, 0),
            );
      }
      io.File('$dir/learning_journey_semantics.txt').writeAsStringSync(buf.toString());
    }
    semantics.dispose();
  });
}
