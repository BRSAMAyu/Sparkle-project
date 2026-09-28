import 'dart:io' as io;
import 'dart:ui' show ImageByteFormat;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/presentation/providers/guest_provider.dart';
import 'package:sparkle/features/galaxy/domain/capability_channel.dart';
import 'package:sparkle/features/galaxy/galaxy.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/galaxy/star_map_painter.dart';
import 'package:sparkle/features/galaxy/presentation/widgets/node_detail_sheet.dart';
import 'package:sparkle/l10n/app_localizations.dart';

import '../../../shared/i18n_test_helper.dart';

/// V4-U05 · 证据采集：星图四态轨迹 + 证据详情来源抽屉的顶页截图与语义树。
///
/// 常规跑 `flutter test`：执行真实渲染断言（三种通道节点同屏、抽屉通道
/// 文案齐备），不写文件——套件全绿且无副作用。设 `U05_EVIDENCE_DIR=<abs>`
/// 时额外写出（证据落盘路径见 v4/evidence/V4-U05/run_manifest.json）：
///   u05_galaxy_tiers.png / u05_galaxy_tiers_semantics.txt
///   u05_sheet_verified.png / u05_sheet_verified_semantics.txt
///   u05_sheet_practiced.png / u05_sheet_practiced_semantics.txt
///
/// 语义 dump 口径与 F04 shell_evidence_test 同款（元素树 RenderParagraph）。
String _dumpSemanticsFromElements(Element rootElement) {
  final buf = StringBuffer();
  void visit(Element el) {
    final ro = el.renderObject;
    if (ro is RenderParagraph) {
      final text = ro.text.toPlainText();
      if (text.trim().isNotEmpty) {
        final rect = ro.localToGlobal(Offset.zero) & ro.size;
        buf.writeln('- label="$text" rect=$rect');
      }
    }
    el.visitChildren(visit);
  }

  visit(rootElement);
  return buf.toString();
}

Future<void> _capture(
  WidgetTester tester,
  String outPath,
  String semanticsPath,
) async {
  await tester.runAsync(() async {
    final outDir = io.Directory(io.File(outPath).parent.path);
    if (!outDir.existsSync()) {
      outDir.createSync(recursive: true);
    }
    final boundary = tester.renderObject<RenderRepaintBoundary>(
      find.byKey(const ValueKey('u05-evidence-root')),
    );
    final image = await boundary.toImage(pixelRatio: 2.0);
    final bytes = await image.toByteData(format: ImageByteFormat.png);
    io.File(outPath).writeAsBytesSync(bytes!.buffer.asUint8List());
    final rootElement = tester.binding.rootElement;
    io.File(semanticsPath).writeAsStringSync(
      rootElement == null ? '(无元素根)' : _dumpSemanticsFromElements(rootElement),
    );
  });
}

void main() {
  setUp(() async {
    setUpI18nForTesting();
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();
    // 证据采集用 runAsync 打开真实事件循环——星图页挂载后的延迟刷新会走
    // 认证拦截器读安全存储（测试环境无插件实现）。打桩：读令牌返回空，
    // 请求方按离线路径自行降级，不影响本卡的星图/抽屉渲染面。
    TestWidgetsFlutterBinding.ensureInitialized().defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('plugins.it_nomads.com/flutter_secure_storage'),
      (call) async => null,
    );
  });

  testWidgets(
    '星图四态轨迹同屏（verified 双环亮星 / practiced 封顶单环 / trace 虚线）',
    (tester) async {
      tester.view.physicalSize = const Size(1170, 2100);
      tester.view.devicePixelRatio = 3.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final container = ProviderContainer(
        overrides: [
          galaxyProvider.overrideWith(
            (ref) => _EvidenceGalaxyNotifier(_tierNodes()),
          ),
          ...await _evidenceOverrides(),
        ],
      );
      addTearDown(container.dispose);
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: RepaintBoundary(
            key: const ValueKey('u05-evidence-root'),
            child: MaterialApp(
              theme: AppThemes.lightTheme,
              locale: const Locale('zh'),
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              supportedLocales: AppLocalizations.supportedLocales,
              home: const Scaffold(body: GalaxyScreen()),
            ),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 120));
      for (var i = 0; i < 8; i++) {
        await tester.pump(const Duration(milliseconds: 100));
      }
      expect(tester.takeException(), isNull);
      // 画布面：三种通道节点全部进入星图 painter（名称由画布绘制，非
      // Text widget——断言走 painter 的节点字典）。
      final painter = tester
          .widget<CustomPaint>(
            find.byWidgetPredicate(
              (widget) =>
                  widget is CustomPaint && widget.painter is StarMapPainter,
            ),
          )
          .painter! as StarMapPainter;
      expect(
        painter.nodesById.keys,
        containsAll(<String>[
          'node_verified',
          'node_practiced',
          'node_trace',
        ]),
      );

      // 画布顶页截图在 headless 环境不可得（相机就位/入场动画依赖真实
      // 运行时）——四态视觉档由 capability_channel_visual_test 纯函数钉
      // （17 测）+ 本测 painter 集成断言承载；截图证据为来源抽屉两变体。
      final dir = io.Platform.environment['U05_EVIDENCE_DIR'];
      if (dir != null && dir.isNotEmpty) {
        final rootElement = tester.binding.rootElement;
        await tester.runAsync(() async {
          final outDir = io.Directory(dir);
          if (!outDir.existsSync()) {
            outDir.createSync(recursive: true);
          }
          io.File('$dir/u05_galaxy_tiers_semantics.txt').writeAsStringSync(
            rootElement == null
                ? '(无元素根)'
                : _dumpSemanticsFromElements(rootElement),
          );
        });
      }
    },
  );

  testWidgets(
    '证据详情来源抽屉（verified）：独立检验 + 溯源行 + 投影版本',
    (tester) async {
      await _pumpSheet(
        tester,
        capability: const GalaxyNodeCapabilityEvidence(
          channel: GalaxyCapabilityChannel.verified,
          hasChannelData: true,
          projectionVersion: 7,
          evidenceCount: 2,
        ),
        sources: const [
          {
            'source_type': 'quiz_feedback',
            'label': '第 3 章单元测验',
            'recorded_at': '2026-09-20T10:00:00.000Z',
          },
        ],
      );
      expect(find.text('独立检验通过'), findsOneWidget);
      expect(find.text('投影版本 v7'), findsOneWidget);
      final dir = io.Platform.environment['U05_EVIDENCE_DIR'];
      if (dir != null && dir.isNotEmpty) {
        await _capture(
          tester,
          '$dir/u05_sheet_verified.png',
          '$dir/u05_sheet_verified_semantics.txt',
        );
      }
    },
  );

  testWidgets(
    '证据详情来源抽屉（practiced）：练习过如实呈现，绝无已掌握/检验通过声称',
    (tester) async {
      await _pumpSheet(
        tester,
        capability: const GalaxyNodeCapabilityEvidence(
          channel: GalaxyCapabilityChannel.practiced,
          hasChannelData: true,
          projectionVersion: 7,
        ),
        sources: const [
          {
            'source_type': 'focus_session',
            'recorded_at': '2026-09-22T08:00:00.000Z',
          },
        ],
      );
      expect(find.text('练习过 · 未独立检验'), findsOneWidget);
      expect(find.text('独立检验通过'), findsNothing);
      expect(find.text('已掌握'), findsNothing);
      final dir = io.Platform.environment['U05_EVIDENCE_DIR'];
      if (dir != null && dir.isNotEmpty) {
        await _capture(
          tester,
          '$dir/u05_sheet_practiced.png',
          '$dir/u05_sheet_practiced_semantics.txt',
        );
      }
    },
  );
}

/// 证据采集环境桩：runAsync 会放行星图页挂载后的延迟刷新（认证拦截器
/// 读安全存储/共享偏好——测试环境无插件实现），按值打桩后请求方走离线
/// 降级，不影响本卡的星图/抽屉渲染面。
Future<List<Override>> _evidenceOverrides() async {
  final prefs = await SharedPreferences.getInstance();
  return [
    sharedPreferencesProvider.overrideWithValue(prefs),
  ];
}

/// 三种通道节点（同一 legacy 高分 92 / 低分痕迹 18，通道不同 → 视觉档不同）。
List<GalaxyNodeModel> _tierNodes() => <GalaxyNodeModel>[
      GalaxyNodeModel.fromJson(const {
        'id': 'node_verified',
        'name': '独立检验的星',
        'importance': 4,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 92,
        'study_count': 9,
        'position_x': -120.0,
        'position_y': 0.0,
        'user_status': {
          'mastery_evidence': {'capability_channel': 'verified'},
          'projection_version': 7,
        },
      }),
      GalaxyNodeModel.fromJson(const {
        'id': 'node_practiced',
        'name': '练习过的星',
        'importance': 4,
        'sector_code': 'TECH',
        'is_unlocked': true,
        'mastery_score': 92,
        'study_count': 9,
        'position_x': 0.0,
        'position_y': 0.0,
        'user_status': {
          'mastery_evidence': {'capability_channel': 'practiced'},
          'projection_version': 7,
        },
      }),
      GalaxyNodeModel.fromJson(const {
        'id': 'node_trace',
        'name': '只留痕迹的星',
        'importance': 3,
        'sector_code': 'ART',
        'is_unlocked': true,
        'mastery_score': 18,
        'study_count': 2,
        'position_x': 120.0,
        'position_y': 0.0,
        'user_status': {
          'mastery_evidence': {'capability_channel': 'trace_only'},
          'projection_version': 7,
        },
      }),
    ];

Future<void> _pumpSheet(
  WidgetTester tester, {
  required GalaxyNodeCapabilityEvidence capability,
  required List<Map<String, dynamic>> sources,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: await _evidenceOverrides(),
      child: RepaintBoundary(
        key: const ValueKey('u05-evidence-root'),
        child: testMaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: NodeDetailSheet(
                nodeId: 'cn.tcp_flow',
                nodeLabel: 'TCP 流量控制',
                initialHistory: const GalaxyNodeHistory(
                  nodeId: 'cn.tcp_flow',
                  nodeLabel: 'TCP 流量控制',
                  mastery: 0.85,
                  studyCount: 6,
                ),
                capability: capability,
                graphEventSources: sources,
              ),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

class _EvidenceGalaxyNotifier extends StateNotifier<GalaxyState>
    implements GalaxyNotifier {
  _EvidenceGalaxyNotifier(List<GalaxyNodeModel> nodes)
      : super(
          GalaxyState(
            nodes: nodes,
            nodePositions: <String, Offset>{
              for (final node in nodes)
                if (node.positionX != null && node.positionY != null)
                  node.id: Offset(node.positionX!, node.positionY!),
            },
            visibleNodes: nodes,
            userFlameIntensity: 0.4,
          ),
        );

  @override
  void selectNode(String nodeId) {
    state = state.copyWith(
      selectedNodeId: nodeId,
      expandedEdgeNodeIds: {nodeId},
    );
  }

  @override
  void deselectNode() {}

  @override
  void updateScale(double scale) {
    state = state.copyWith(currentScale: scale);
  }

  @override
  void updateViewport(Rect viewport) {
    state = state.copyWith(viewport: viewport);
  }

  @override
  Stream<MasteryMilestoneEvent> get masteryMilestones => const Stream.empty();

  @override
  Future<void> loadGalaxy({
    bool forceRefresh = false,
    bool showLoading = true,
  }) async {
    state = state.copyWith(isLoading: true);
    await Future<void>.delayed(const Duration(milliseconds: 10));
    state = state.copyWith(isLoading: false);
  }

  @override
  Future<GalaxyError?> sparkNode(String id) async => null;

  @override
  Future<String?> predictNextNode() async => null;

  @override
  Future<List<GalaxySearchResult>> searchNodes(String query) async => [];

  @override
  Future<void> refreshForTaskCompletion({
    Map<String, dynamic>? galaxyUpdate,
  }) async {}

  @override
  void beginNodeDrag(String nodeId) {
    state = state.copyWith(draggingNodeId: nodeId);
  }

  @override
  void updateDraggedNodePosition(String nodeId, Offset newPosition) {
    final positions = Map<String, Offset>.from(state.nodePositions)
      ..[nodeId] = newPosition;
    state = state.copyWith(nodePositions: positions);
  }

  @override
  Future<void> endNodeDrag() async {
    state = state.copyWith(draggingNodeId: null);
  }

  @override
  void setEvidenceHighlight(Set<String> ids, {String? focusId}) {
    state = state.copyWith(
      highlightedNodeIdHashes: ids.map((e) => e.hashCode).toSet(),
    );
  }

  @override
  void clearFocusBounds() {
    state = state.copyWith(focusBounds: null);
  }

  @override
  void clearFocusNode() {
    state = state.copyWith(focusNodeId: null);
  }

  @override
  void clearEvidenceHighlight() {
    state = state.copyWith(
      highlightedNodeIdHashes: const {},
      highlightRevision: state.highlightRevision + 1,
    );
  }

  @override
  void setFocusNode(String nodeId) {
    state = state.copyWith(focusNodeId: nodeId);
  }
}
