/// B-04 · V3 视觉基线截图 harness（wt667）。
///
/// 复用 Q-03 截图链路（q03_harness.dart，不重建真源）：
/// - 泵真实 `routerProvider`（demo mode + 真 auth harness）+ 真实渲染
///   `matchesGoldenFile`，配方与 Q-03 完全同源；
/// - 按 B-04 canonical states 注册表（`scripts/devtools/visual_baseline/
///   states.py`）采集 9 surfaces × 主要状态，文件名走 B-04 naming.py
///   GBNF（surface__state__persona__platform__viewport__sha8.png）；
/// - 命名/manifest/verify/coverage 链由 visual_baseline Python 包承接，
///   本 harness 只负责「真实渲染出图」。
///
/// 采集口径（U-09 SCREENSHOT_MATRIX 同一 viewport 命名）：
/// - android：逻辑 360×800 @3（naming 段 1080x2400@3.0，物理 px 口径）；
/// - macos 小窗：逻辑 800×600 @2（800x600@2.0，逻辑 px 口径，沿 U-09）；
/// - macos 正常窗：逻辑 1280×800 @2（1280x800@2.0）。
///
/// 平台语义经 `debugDefaultTargetPlatformOverride` 设定（U-09 契约测试
/// 同源）；像素字体仍是 macOS 宿主渲染——与真机批次的差异属环境差，
/// 真机批次另行采集（U-09 交接清单）。
///
/// 用法：
/// ```
/// B04_VISUAL_CAPTURE=true B04_BUILD_SHA8=<sha8> \
///   flutter test --update-goldens test/goldens/b04_visual_baseline/
/// ```
/// 捕获关闭时只跑布局探针（不写 PNG），作为常驻回归测试。
library;

import 'dart:io';
import 'dart:typed_data' show Uint8List;

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart' show Override;
import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/chat/data/models/chat_message_model.dart';
import 'package:sparkle/features/chat/presentation/providers/chat_provider.dart';

import '../../goldens/q03_visual_qa/q03_harness.dart';

/// 证据输出根目录（相对本测试文件 test/goldens/b04_visual_baseline/，
/// 供 matchesGoldenFile 用；flutter test 的 CWD=mobile/）。
const String b04EvidenceRel = '../../../../v3-output/B-04/screenshots';

/// 构建 SHA8（naming 第 6 段）；缺省 `<sha8>` 仅用于探针模式的路径占位，
/// 不写盘。
const String b04BuildSha8 = String.fromEnvironment(
  'B04_BUILD_SHA8',
  defaultValue: '<sha8>',
);

/// 是否落盘截图（与 Q03 的 `Q03_VISUAL_CAPTURE` 同款开关）。
bool get b04CaptureEnabled =>
    Platform.environment['B04_VISUAL_CAPTURE'] == 'true';

/// 一批采集 = 目标平台语义 × viewport（逻辑 px + DPR）× naming 段。
class B04ViewportBatch {
  const B04ViewportBatch({
    required this.platformSegment,
    required this.viewportSegment,
    required this.logicalSize,
    required this.devicePixelRatio,
    required this.targetPlatform,
  });

  /// naming.py platform 段（android/macos；web 真浏览器批次不在本链路）。
  final String platformSegment;

  /// naming.py viewport 段（U-09 MATRIX 口径）。
  final String viewportSegment;

  /// 逻辑像素（tester.view.physicalSize = logical × DPR）。
  final Size logicalSize;

  final double devicePixelRatio;

  final TargetPlatform targetPlatform;

  /// golden 落盘子目录（`screenshots/<batch>/`）。
  String get dirName => [platformSegment, viewportSegment].join('__');

  /// canonical 文件名（B-04 naming.py GBNF）。
  String fileName({
    required String surface,
    required String state,
    required String persona,
  }) =>
      '${[
        surface,
        state,
        persona,
        platformSegment,
        viewportSegment,
        b04BuildSha8,
      ].join("__")}.png';
}

/// U-09 MATRIX 同口径的三批 golden 采集（android 手机 + macOS 小/正常窗）。
const List<B04ViewportBatch> b04ViewportBatches = [
  B04ViewportBatch(
    platformSegment: 'android',
    viewportSegment: '1080x2400@3.0',
    logicalSize: Size(360, 800),
    devicePixelRatio: 3.0,
    targetPlatform: TargetPlatform.android,
  ),
  B04ViewportBatch(
    platformSegment: 'macos',
    viewportSegment: '800x600@2.0',
    logicalSize: Size(800, 600),
    devicePixelRatio: 2.0,
    targetPlatform: TargetPlatform.macOS,
  ),
  B04ViewportBatch(
    platformSegment: 'macos',
    viewportSegment: '1280x800@2.0',
    logicalSize: Size(1280, 800),
    devicePixelRatio: 2.0,
    targetPlatform: TargetPlatform.macOS,
  ),
];

/// B-04 基线容差比较器：任务卡明确「轻量 diff、不要求像素完全一致」；
/// demo 相对时间标签与 Aurora/流式 shimmer 类周期动画的帧相位噪声实测
/// ≈0.01%（224px @ 1080×2400），容差取 0.5% 只放行此类噪声，真实回归
/// （布局漂移/文案变化）远超此界。
class B04TolerantGoldenComparator extends LocalFileComparator {
  B04TolerantGoldenComparator(super.testFile);

  static const double diffPercentTolerance = 0.5;

  @override
  Future<bool> compare(Uint8List imageBytes, Uri golden) async {
    final result = await GoldenFileComparator.compareLists(
      imageBytes,
      await getGoldenBytes(golden),
    );
    if (result.passed || result.diffPercent <= diffPercentTolerance) {
      result.dispose();
      return true;
    }
    final error = await generateFailureOutput(result, golden, basedir);
    result.dispose();
    throw FlutterError(error);
  }
}

/// 用容差比较器替换默认 golden comparator（须在 setUpAll、任何 golden
/// 比对发生前调用）。
void b04InstallTolerantComparator() {
  final defaultComparator = goldenFileComparator;
  if (defaultComparator is LocalFileComparator) {
    goldenFileComparator = B04TolerantGoldenComparator(
      defaultComparator.basedir.resolve('b04_visual_baseline_test.dart'),
    );
  }
}

/// 采集 + 布局探针（探针永远跑；golden 仅在 B04_VISUAL_CAPTURE=true 落盘）。
///
/// [fileName] 必须是 B-04 canonical 命名；PNG 落
/// `v3-output/B-04/screenshots/<batch>/<fileName>`。
Future<void> b04Capture(
  WidgetTester tester,
  Q03Harness harness,
  B04ViewportBatch batch,
  String fileName,
) async {
  final exception = tester.takeException();
  // 复用 Q-03 的布局探针口径（溢出/截断候选越界 widget），结果并入
  // Q-03 探针报告流（suite 名前缀 b04_，同一份 JSON 结构）。
  final probe = probeLayout(tester);
  q03ProbeResults.add(<String, Object?>{
    'screen': 'b04/$fileName',
    'state': batch.viewportSegment,
    'pump_exception': exception?.toString(),
    'logical_size':
        '${batch.logicalSize.width}x${batch.logicalSize.height}',
    'text_widget_count': probe.textCount,
    'truncation_candidates': probe.truncationCandidates,
    'overflow_bounds_widgets': probe.offBoundsCount,
  });

  if (b04CaptureEnabled) {
    final path = '$b04EvidenceRel/${batch.dirName}/$fileName';
    final file = File(
      '$b04EvidenceRel/${batch.dirName}/$fileName',
    );
    file.parent.createSync(recursive: true);
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile(path),
    );
  }
}

/// 给 chat 会话补一条带 citations 的 assistant 消息（canonical 状态
/// chat/history_citations 的引用块语义）。
///
/// demo 历史消息（DemoDataService.demoChatHistory）不带 citations 字段
/// （亲证 demo_data_service.dart msg_1..11），引用条（真实渲染路径
/// AssistantCitationStrip）需要消息带 rawMetadata['citations']——此处以
/// canonical fixture 注入一条，走真实 ChatBubble/引用条渲染管线。
class _B04CitationChatNotifier extends ChatNotifier {
  _B04CitationChatNotifier(super.chatRepository, super.ref);

  /// canonical 状态 chat/history_citations 的引用块语义：demo 历史
  /// （DemoDataService.demoChatHistory msg_1..11 亲证）不带 citations，
  /// 引用条（真实渲染路径 AssistantCitationStrip）需要消息带
  /// rawMetadata['citations']——注入一条 fixture，走真实渲染管线。
  void appendCitationFixture() {
    state = state.copyWith(
      messages: [
        ...state.messages,
        ChatMessageModel(
          id: 'b04_citation_fixture_1',
          conversationId: 'demo_conv_1',
          role: MessageRole.assistant,
          content: '从你的错题本看，「判别式为 0 时两根相等」这条已经稳了；'
              '下一步建议把「韦达定理反向构造」再过一遍。',
          createdAt: DateTime.now(),
          rawMetadata: const <String, dynamic>{
            'citations': <Map<String, dynamic>>[
              <String, dynamic>{
                'id': 'cite_fixture_1',
                'title': '高等数学（第七版）· 第三章 微分中值定理',
                'excerpt':
                    '若 f(x) 在闭区间 [a,b] 连续、开区间 (a,b) 可导……由罗尔定理'
                        '存在 ξ∈(a,b) 使 f\'(ξ)=0。',
                'section_title': '§3.1 罗尔定理',
                'page_number': 148,
                'score': 0.87,
              },
              <String, dynamic>{
                'id': 'cite_fixture_2',
                'title': '错题本 · 一元二次方程判别式专题',
                'excerpt': 'Δ=b²−4ac：Δ>0 两不等实根；Δ=0 两相等实根；Δ<0 无实根。',
                'section_title': '判别式与韦达定理',
                'page_number': 12,
                'score': 0.82,
              },
            ],
          },
        ),
      ],
    );
  }
}

/// 在 ChatScreen 初始加载稳定后注入引用块 fixture 消息（构造期注入会被
/// demo 历史 reload 整体覆盖——红测实证）。
void b04SeedCitationMessage(Q03Harness harness) {
  final notifier = harness.container.read(chatProvider.notifier);
  if (notifier is _B04CitationChatNotifier) {
    notifier.appendCitationFixture();
  }
}

/// memory 面板的 canned API（真 ApiClient 契约面，仅覆写读通道）。
///
/// memory 链路无 demo 分支（亲证 memory_api_service.dart /
/// memory_provenance_repository.dart），golden 采集以契约形状 JSON 走
/// 真实 fromJson 解析 + 真实渲染管线；JSON 形状对齐
/// /memory/provenance/items 真实响应契约（ProvenanceListResult）。
class _B04MemoryApi implements ApiClient {
  /// chatRepositoryProvider（Dashboard 底部输入坞初始化链）要读
  /// `apiClient.dio`——demo 模式下不真发请求，给一个空实例即可。
  final Dio _dio = Dio();

  @override
  Dio get dio => _dio;

  Response<T> _ok<T>(String path, Object? payload) => Response<T>(
        statusCode: 200,
        data: payload as T?,
        requestOptions: RequestOptions(path: path),
      );

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final payload = path.startsWith('/memory/provenance/items')
        ? _provenanceItemsPayload
        : const <String, dynamic>{};
    return _ok<T>(path, payload);
  }

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _ok<T>(path, const <String, dynamic>{});

  @override
  Future<Response<T>> put<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _ok<T>(path, const <String, dynamic>{});

  @override
  Future<Response<T>> patch<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async =>
      _ok<T>(path, const <String, dynamic>{});

  @override
  Future<Response<T>> delete<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async =>
      _ok<T>(path, const <String, dynamic>{});

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

/// /memory/provenance/items 最小契约形状（U-03 四桶；字段缺省全走
/// fromJson 兜底，与真实响应同构）。
const Map<String, dynamic> _provenanceItemsPayload = <String, dynamic>{
  'items': <Map<String, dynamic>>[
    <String, dynamic>{
      'kind': 'preference',
      'id': 'b04_prov_1',
      'ref': 'preference:b04_prov_1',
      'bucket': 'told',
      'bucket_label': '我告诉过',
      'content': '晚上效率低，希望把输出型任务安排在上午，晚间只做轻量跟说。',
      'status': 'active',
      'confidence_tier_label': '已稳定',
      'source_label': '来自建模对话 · 3 次纠正',
      'source_known': true,
      'actions': <String>['view_source', 'revoke'],
      'updated_at': '2026-09-20T10:00:00Z',
      'pref_key': 'schedule.output_morning',
      'version': 3,
    },
    <String, dynamic>{
      'kind': 'episodic',
      'id': 'b04_prov_2',
      'ref': 'episodic:b04_prov_2',
      'bucket': 'observed',
      'bucket_label': '我观察到',
      'content': '连续 4 天完成 10 分钟口语跟说，晚间弃学比例明显下降。',
      'status': 'active',
      'confidence_tier_label': '部分佐证',
      'source_label': '来自任务执行记录',
      'source_known': true,
      'actions': <String>['view_source', 'revoke'],
      'updated_at': '2026-09-22T21:30:00Z',
      'occurred_at': '2026-09-22T21:00:00Z',
    },
    <String, dynamic>{
      'kind': 'goal',
      'id': 'b04_prov_3',
      'ref': 'goal:b04_prov_3',
      'bucket': 'effective',
      'bucket_label': '对我有效',
      'title': '把抽象概念讲给别人听（费曼式复盘）',
      'content': '费曼式复盘后错题重做正确率从 52% 升到 78%。',
      'status': 'active',
      'confidence_tier_label': '有证据',
      'source_label': '来自复盘效果对照',
      'source_known': true,
      'actions': <String>['view_source', 'revoke'],
      'updated_at': '2026-09-23T09:15:00Z',
    },
  ],
  'total': 3,
  'has_more': false,
  'scan_capped': false,
};

/// B-04 采集泵：Q-03 配方 + 批次 viewport/平台语义 + 可选 canned API。
///
/// demo 模式在本泵统一开启（配方同 Q03 各测试：`DemoDataService.isDemoMode
/// = true` 须在 provider 构建前置位，否则 demo 面直打真网端点——测试
/// binding 下一律 400，且 dashboard 错误重试链会留 pending timer）。
Future<Q03Harness> pumpB04App(
  WidgetTester tester,
  B04ViewportBatch batch, {
  bool onboardingCompleted = true,
  bool memoryCannedApi = false,
  bool chatCitations = false,
  List<Override> extraOverrides = const <Override>[],
}) {
  DemoDataService.isDemoMode = true;
  addTearDown(() => DemoDataService.isDemoMode = false);
  return pumpQ03App(
      tester,
      onboardingCompleted: onboardingCompleted,
      physicalSize: Size(
        batch.logicalSize.width * batch.devicePixelRatio,
        batch.logicalSize.height * batch.devicePixelRatio,
      ),
      devicePixelRatio: batch.devicePixelRatio,
      targetPlatform: batch.targetPlatform,
      extraOverrides: [
        if (memoryCannedApi)
          apiClientProvider.overrideWithValue(_B04MemoryApi()),
        if (chatCitations)
          chatProvider.overrideWith(
            (ref) => _B04CitationChatNotifier(
              ref.watch(chatRepositoryProvider),
              ref,
            ),
          ),
        ...extraOverrides,
      ],
  );
}
