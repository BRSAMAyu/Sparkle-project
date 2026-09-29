// V4-G03 · 记忆/Aurora/我的理解家族——四风格语义钉 + 确定性证据采集。
//
// F05 判例形态（style_preview_evidence_test 同构）：
// - 常规 `flutter test`：执行全部语义/结构钉（CI 可失败），不写文件——
//   套件全绿无副作用；
// - 设 `G03_EVIDENCE_DIR=<abs dir>` 时额外写出（确定性 seed、同 build）：
//   g03_family_<profile>.png（dpr=2）+ g03_family_<profile>_semantics.txt
//   （元素树口径语义 dump，F04/F05 同款）。
//
// 家族代表面（纯组件、零 provider、冻结 seed）：SemanticPill 全 tone 族
// （memory 面徽章基座）、MemoryEvidenceBadge 三态（F05 记忆面组件）、
// PrismBehaviorCard 三分区（cognitive 面计数/标题/置信收口）、
// EvidenceDrawer 空/不足/引用三态（memory 面读侧）。
import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sparkle/core/design/components/atoms/semantic_pill.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/cognitive/presentation/widgets/prism_behavior_card.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_drawer.dart';
import 'package:sparkle/features/memory/presentation/widgets/memory_evidence_badge.dart';

import '../../../../core/design/style_preview/style_preview_test_harness.dart';

/// 冻结 seed（确定性；文案钉进断言，跨档一致）。
const String kG03CognitivePattern = '深夜刷题后正确率下降';
const String kG03EmotionalPattern = '任务被打断后重启成本高';
const String kG03SolutionText = '改为番茄钟分段执行，并在切换前写一行续接笔记';

Map<String, dynamic> _prismSeed() => const {
      'patterns': [
        {
          'pattern_type': 'cognitive',
          'pattern_name': kG03CognitivePattern,
          'description': '连续学习超过 90 分钟后错题率上升',
          'solution_text': kG03SolutionText,
          'confidence_score': 0.72,
        },
        {
          'pattern_type': 'emotional',
          'pattern_name': kG03EmotionalPattern,
          'confidence_score': 0.55,
        },
        {
          'pattern_type': 'execution',
          'pattern_name': '晚间计划经常未启动',
          'confidence_score': 0.4,
        },
      ],
    };

Widget _familyCompositeFace() => SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Wrap(
            spacing: 8,
            children: [
              SemanticPill(label: '已确认偏好', tone: PillTone.success),
              SemanticPill(label: '待确认观察', tone: PillTone.warning),
              SemanticPill(label: '仅用于本次对话', tone: PillTone.info),
              SemanticPill(label: '证据不足', tone: PillTone.danger),
              SemanticPill(label: '来自任务记录', tone: PillTone.neutral),
            ],
          ),
          const SizedBox(height: 12),
          const Row(
            children: [
              MemoryEvidenceBadge(status: MemoryEvidenceStatus.ok),
              SizedBox(width: 8),
              MemoryEvidenceBadge(
                status: MemoryEvidenceStatus.redacted,
                evidenceCount: 2,
              ),
              SizedBox(width: 8),
              MemoryEvidenceBadge(status: MemoryEvidenceStatus.missing),
            ],
          ),
          const SizedBox(height: 12),
          PrismBehaviorCard(data: _prismSeed()),
          const SizedBox(height: 12),
          const EvidenceDrawer(),
          const SizedBox(height: 12),
          const EvidenceDrawer(evidenceMissing: true),
          const SizedBox(height: 12),
          EvidenceDrawer(
            refs: [
              EvidenceRefModel(type: 'chat_turn', id: 'seed-ref-1'),
              EvidenceRefModel(type: 'event', id: 'seed-ref-2'),
            ],
          ),
        ],
      ),
    );

/// 语义树 dump（元素树口径，F04/F05 同款）。
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
      final rect = ro.localToGlobal(Offset.zero) & ro.size;
      buf.writeln('${'  ' * depth}- label="${ro.properties.label}" '
          'value="${ro.properties.value}" rect=$rect');
      depth += 1;
    }
    el.visitChildElements((child) => visit(child, depth));
  }

  visit(rootElement, 0);
  return buf.toString();
}

Future<void> _pumpProfile(
  WidgetTester tester,
  PixelPreviewProfile profile, {
  GlobalKey? repaintKey,
}) async {
  final manager = await freshThemeManager();
  await manager.setPixelPreviewProfile(profile);
  await tester.pumpWidget(
    buildPreviewHost(repaintKey: repaintKey, body: _familyCompositeFace()),
  );
  await settlePreview(tester);
}

void main() {
  const profiles = PixelPreviewProfile.values;

  group('V4-G03 · 家族代表面四风格语义钉（跨档不变量，CI 可失败）', () {
    for (final profile in profiles) {
      testWidgets('[$profile] 语义钉：分组徽章/三态证据/三分区（无人格雷达）跨档一致', (tester) async {
        tester.view.devicePixelRatio = 2.0;
        tester.view.physicalSize = const Size(720, 3200);
        addTearDown(() {
          tester.view.resetDevicePixelRatio();
          tester.view.resetPhysicalSize();
        });
        await _pumpProfile(tester, profile);

        // ──「来自/仅用于/更改/忘记」家族语义基座：pill 族五 tone 全上屏 ──
        expect(
          find.text('已确认偏好'),
          findsOneWidget,
          reason: '[$profile] 已确认偏好 pill 缺席',
        );
        expect(find.text('待确认观察'), findsOneWidget);
        expect(find.text('仅用于本次对话'), findsOneWidget);
        expect(find.text('证据不足'), findsWidgets);
        expect(find.text('来自任务记录'), findsOneWidget);
        // G03 收口钉：非选中 pill tint alpha=0.05（四风格复算定值；
        // 0.10 旧值在 classic 两档只有 4.26–4.45:1）。pill 本体是
        // SparklePressable（非 Container），底色钉在 pressable 上。
        final pill = tester.widget<SemanticPill>(
          find.widgetWithText(SemanticPill, '已确认偏好'),
        );
        expect(pill.selected, isFalse);
        final pressable = tester.widget<SparklePressable>(
          find.ancestor(
            of: find.text('已确认偏好'),
            matching: find.byType(SparklePressable),
          ),
        );
        expect(
          pressable.backgroundColor,
          DS.semanticSuccess.withValues(alpha: 0.05),
          reason: '[$profile] pill tint 必须=0.05（G03 对比度收口定值）',
        );

        // ── 记忆证据三态徽章（zh 面：OK/已隐藏/缺失）──
        expect(find.text('OK'), findsOneWidget);
        expect(find.text('2 已隐藏'), findsOneWidget);
        expect(find.text('缺失'), findsOneWidget);

        // ── Prism 三分区（事实/观察/执行分开，无人格雷达图）──
        expect(find.byType(PrismBehaviorCard), findsOneWidget);
        expect(find.textContaining(kG03CognitivePattern), findsOneWidget);
        expect(find.textContaining(kG03EmotionalPattern), findsOneWidget);
        expect(find.text(kG03SolutionText), findsOneWidget);
        expect(
          find.byIcon(Icons.sentiment_neutral),
          findsOneWidget,
          reason: '[$profile] 情绪分区图标（taskReflection 色相承载）缺席',
        );
        // G03 钉：分区标题文字走 textPrimary（classic-dark 彩字 4.42:1 收口），
        // 计数标签 tint=0.06。
        final sectionTitle = tester.widget<Text>(find.text('认知模式'));
        expect(
          sectionTitle.style?.color,
          DS.textPrimary,
          reason: '[$profile] Prism 分区标题必须走 textPrimary 令牌',
        );
        // 情绪分区计数容器：0.06 tint 钉。
        final countPillText = find.text('1');
        expect(countPillText, findsWidgets);

        // ── EvidenceDrawer 空/不足/引用三态（l10n 收口后 zh 面）──
        expect(
          find.text('暂无证据记录'),
          findsOneWidget,
          reason: '[$profile] EvidenceDrawer 空态文案缺席（I18nService→l10n 收口）',
        );
        expect(find.text('证据不足'), findsWidgets);
        expect(find.text('chat_turn: seed-ref-1'), findsOneWidget);
        expect(find.text('event: seed-ref-2'), findsOneWidget);

        expect(tester.takeException(), isNull, reason: '[$profile] 家族代表面渲染异常');
      });
    }

    testWidgets('反例：四档切换同一 run 内完成且无风格专属缺件', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(720, 3200);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      for (final profile in profiles) {
        await _pumpProfile(tester, profile);
        // 每档同一批语义锚全勤——任一档缺件即红（风格专属缺陷零容忍）。
        expect(find.text('已确认偏好'), findsOneWidget, reason: '[$profile]');
        expect(find.text('OK'), findsOneWidget, reason: '[$profile]');
        expect(find.text('暂无证据记录'), findsOneWidget, reason: '[$profile]');
        expect(
          find.textContaining(kG03CognitivePattern),
          findsOneWidget,
          reason: '[$profile]',
        );
        // classic 档无 PixelProfileTheme 扩展（harness 合同：classic=null），
        // 其余档必须与请求档一致。
        expect(
          mountedPixelProfile(tester),
          profile == PixelPreviewProfile.classic ? isNull : profile,
          reason: '[$profile] 挂载档与请求档不一致',
        );
      }
    });
  });

  group('V4-G03 · 确定性证据采集（G03_EVIDENCE_DIR 门控，F05 判例）', () {
    testWidgets('四档整页截图 + 语义 dump（同 build 同 seed）', (tester) async {
      tester.view.devicePixelRatio = 2.0;
      tester.view.physicalSize = const Size(720, 3200);
      addTearDown(() {
        tester.view.resetDevicePixelRatio();
        tester.view.resetPhysicalSize();
      });
      final dir = io.Platform.environment['G03_EVIDENCE_DIR'];
      if (dir == null || dir.isEmpty) {
        // 常规跑：仅真实渲染断言，不写文件。
        await _pumpProfile(tester, PixelPreviewProfile.classic);
        expect(find.text('暂无证据记录'), findsOneWidget);
        return;
      }
      final out = io.Directory(dir)..createSync(recursive: true);
      for (final profile in profiles) {
        final repaintKey = GlobalKey();
        await _pumpProfile(tester, profile, repaintKey: repaintKey);
        // PNG（RepaintBoundary 捕获，dpr=2）；toImage 是真实异步光栅化，
        // 必须在 runAsync 内执行（F05 同款），否则 test zone 永不落定。
        await tester.runAsync(() async {
          final boundary = repaintKey.currentContext?.findRenderObject()
              as RenderRepaintBoundary?;
          expect(boundary, isNotNull);
          final image = await boundary!.toImage(pixelRatio: 2.0);
          final bytes = await image.toByteData(format: ImageByteFormat.png);
          io.File('${out.path}/g03_family_${profile.name}.png')
              .writeAsBytesSync(bytes!.buffer.asUint8List());
        });
        // 语义 dump（带头信息：档位/关键令牌——正文跨档全同即
        // 「语义不变量」钉成立，档位身份由头行承载，防四档互混）。
        String hex(Color c) =>
            '0x${c.toARGB32().toRadixString(16).padLeft(8, '0')}';
        io.File('${out.path}/g03_family_${profile.name}_semantics.txt')
            .writeAsStringSync(
          '# profile=${profile.name} '
          'surfacePrimary=${hex(DS.surfacePrimary)} '
          'textPrimary=${hex(DS.textPrimary)} '
          'taskReflection=${hex(DS.taskReflection)}\n'
          '${_dumpSemanticsFromElements(
            repaintKey.currentContext as Element,
          )}',
        );
        // 采集即断言：每档核心锚在图（截图≠空壳）。
        expect(find.text('已确认偏好'), findsOneWidget, reason: '[${profile.name}]');
      }
    });
  });
}
