import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/constants/api_constants.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_button_v2.dart';
import 'package:sparkle/core/state/surface_state.dart';
import 'package:sparkle/core/state/surface_state_view.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/core/storage/token_storage_web.dart';
import 'package:sparkle/core/utils/responsive_utils.dart';
import 'package:sparkle/features/chat/presentation/widgets/chat_input.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';

import '../features/home/dashboard_test_harness.dart';
import '../shared/canonical_state_fixture.dart';
import '../shared/i18n_test_helper.dart';

/// U-09 · 三端（Android / Web / macOS）canonical state 渲染契约测试。
///
/// 契约口径（headless 段；真机截图矩阵为第二段交付，见
/// v3-output/U-09/SCREENSHOT_MATRIX.md）：
/// - C1 状态管线：同一 canonical 状态（U-06 SurfacePhase）在
///   Android/iOS/macOS 目标下渲染出**同一份**层级+文案+下一步动作
///   （指纹逐字相等）——「核心状态三端渲染契约」的主体；
/// - C2 URL：网端地址/WS scheme 的平台分支与允许差异登记一致；
/// - C3 平台判定接缝：ResponsiveUtils 与框架 defaultTargetPlatform
///   同源（红测先行修复面：原实现读 dart:io Platform，宿主相关且
///   无法被平台覆盖测试）；
/// - C4 session：io/web 两套 TokenStorage 后端满足同一读写删契约；
/// - C5 keyboard：enter-to-send 是用户偏好而非平台分支——三端
///   textInputAction/onSubmitted 行为一致；
/// - C6 layout overflow：canonical home（dashboard harness 同一
///   persona/goal/task 样本）在 MULTIPLATFORM 三端 viewport 下
///   真实泵入零 overflow + 滚动可达锚点在位；
/// - C7 允许差异登记表：逐条有 reason（验收「允许差异写 reason」）。
///
/// web 段说明：`kIsWeb` 是编译期常量，VM 测试不可翻转——web 以
/// viewport 几何近似 + 平台分支静态审计（C2/C7 登记）覆盖，
/// 真机 web 断言交截图矩阵段。
void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('U-09 C1 · 状态管线三端渲染契约（同一 canonical state 同一渲染）', () {
    /// 当前树上的「渲染指纹」：可见文案 + 可操作动作标签（排序后）。
    ///
    /// 动作标签同时收 SparkleButton（失败族/横幅动作行）与 TextButton
    /// （StagedSurfaceLoader 的 longRunning 可离开退路是 TextButton.icon，
    /// 与 SurfaceStateView 动作行的 SparkleButton 不同源——如实同收，
    /// 不漏计任何一端的下一步）。
    (List<String>, List<String>) renderFingerprint(WidgetTester tester) {
      final texts = tester
          .widgetList<Text>(find.byType(Text))
          .map((t) => t.data ?? '')
          .where((s) => s.trim().isNotEmpty)
          .toList()
        ..sort();
      final buttons = [
        ...tester
            .widgetList<SparkleButton>(find.byType(SparkleButton))
            .map((b) => b.label),
        // TextButton.icon 的 child 是 icon+label 的 Row（非裸 Text），
        // 经后代 finder 取全部 Text 拼接，才能拿到 longRunning 退路的
        // 「返回」标签。
        ...tester.widgetList<TextButton>(find.byType(TextButton)).map(
              (b) => tester
                  .widgetList<Text>(
                    find.descendant(
                      of: find.byWidget(b),
                      matching: find.byType(Text),
                    ),
                  )
                  .map((t) => t.data ?? '')
                  .where((s) => s.trim().isNotEmpty)
                  .join(' '),
            ).where((s) => s.trim().isNotEmpty),
      ]..sort();
      return (texts, buttons);
    }

    /// 以 [platform] 目标泵入 canonical 相位并收集指纹；泵完卸载
    /// （StagedSurfaceLoader 持 Timer，不卸载会 pending timer）并当场
    /// 还原平台覆盖（binding 的 invariant 检查在 tearDown 之前跑）。
    Future<(List<String>, List<String>)> pumpPhase(
      WidgetTester tester,
      SurfacePhase phase,
      TargetPlatform platform,
    ) async {
      debugDefaultTargetPlatformOverride = platform;
      await tester.pumpWidget(
        testMaterialApp(
          home: Scaffold(
            body: Center(
              child: SurfaceStateView(state: SurfaceState(phase)),
            ),
          ),
        ),
      );
      await tester.pump();
      // 统一推进 600ms 越过 500ms 升格阈值：longRunning 的可离开退路
      //（stage feedback + onLeave 按钮）与 loading 的 stage 文案在阈值后
      // 才进树——三端都在同一时点取样，指纹可比且覆盖长等待契约。
      await tester.pump(const Duration(milliseconds: 600));
      final fingerprint = renderFingerprint(tester);
      debugDefaultTargetPlatformOverride = null;
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      return fingerprint;
    }

    testWidgets('canonical 相位在 android/iOS/macOS 渲染指纹逐字一致',
        (tester) async {
      const targets = [
        TargetPlatform.android,
        TargetPlatform.iOS,
        TargetPlatform.macOS,
      ];
      for (final phase in canonicalContractPhases) {
        final fingerprints = <TargetPlatform, (List<String>, List<String>)>{};
        for (final platform in targets) {
          fingerprints[platform] = await pumpPhase(tester, phase, platform);
        }
        final androidFingerprint = fingerprints[TargetPlatform.android]!;
        // 逐分量比较（record 的 == 走字段同一性，List 会被判不等）。
        expect(
          androidFingerprint.$1,
          fingerprints[TargetPlatform.iOS]!.$1,
          reason:
              'canonical 相位 $phase 的可见文案在 android 与 iOS 必须'
              '一致（状态语义一致性契约，允许差异见 C7 登记表）',
        );
        expect(
          androidFingerprint.$2,
          fingerprints[TargetPlatform.iOS]!.$2,
          reason:
              'canonical 相位 $phase 的下一步动作在 android 与 iOS 必须'
              '一致（状态语义一致性契约，允许差异见 C7 登记表）',
        );
        expect(
          androidFingerprint.$1,
          fingerprints[TargetPlatform.macOS]!.$1,
          reason:
              'canonical 相位 $phase 的可见文案在 android 与 macOS '
              '必须一致——桌面端不允许出现缺标题的死胡同形态',
        );
        expect(
          androidFingerprint.$2,
          fingerprints[TargetPlatform.macOS]!.$2,
          reason:
              'canonical 相位 $phase 的下一步动作在 android 与 macOS '
              '必须一致——桌面端不允许出现缺下一步的死胡同形态',
        );
        // 失败族不变式（U-06 语义在三端各目标下都成立）：失败族必有
        // 至少一个可操作下一步按钮。
        if (SurfaceStateMatrix.isFailure(phase)) {
          for (final platform in targets) {
            expect(
              fingerprints[platform]!.$2,
              isNotEmpty,
              reason: '$platform 下失败相位 $phase 必须渲染可操作下一步',
            );
          }
        }
      }
    });
  });

  group('U-09 C2 · URL/网端契约（api_constants 平台分支审计）', () {
    tearDown(() => debugDefaultTargetPlatformOverride = null);

    test('android 默认走模拟器宿主别名 10.0.2.2（允许差异登记项）', () {
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      expect(ApiConstants.baseUrl, 'http://10.0.2.2:8080');
      expect(ApiConstants.wsBaseUrl, 'ws://10.0.2.2:8080');
      expect(ApiConstants.grpcHost, '10.0.2.2');
    });

    test('iOS 默认 localhost（真机需 dart-define 覆盖，登记于实现头注释）',
        () {
      debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
      expect(ApiConstants.baseUrl, 'http://localhost:8080');
      expect(ApiConstants.wsBaseUrl, 'ws://localhost:8080');
      expect(ApiConstants.grpcHost, 'localhost');
    });

    test('macOS 桌面 fallback localhost（U-09 三端之第三端口径）', () {
      debugDefaultTargetPlatformOverride = TargetPlatform.macOS;
      expect(ApiConstants.baseUrl, 'http://localhost:8080');
      expect(ApiConstants.wsBaseUrl, 'ws://localhost:8080');
      expect(ApiConstants.grpcHost, 'localhost');
    });

    test('WS scheme 不变式：所有交付目标只允许 ws/wss，绝不 http/https',
        () {
      for (final platform in TargetPlatform.values) {
        debugDefaultTargetPlatformOverride = platform;
        final ws = Uri.parse(ApiConstants.wsBaseUrl);
        expect(
          ws.scheme,
          anyOf('ws', 'wss'),
          reason: '$platform 的 wsBaseUrl scheme 必须 ws/wss，'
              '实得 ${ws.scheme}（http(s) 系 WebSocket 在多数运行时直接抛错）',
        );
      }
    });
  });

  group('U-09 C3 · 平台判定接缝契约（红测修复面：ResponsiveUtils）', () {
    tearDown(() => debugDefaultTargetPlatformOverride = null);

    test('isMobilePlatform/isDesktopPlatform 与 defaultTargetPlatform 同源',
        () {
      // 红测根因（修复前）：实现读 dart:io Platform.isIOS/isMacOS——
      // 判定结果取决于**宿主机器**而非目标平台：本测试机是 macOS 宿主，
      // debugDefaultTargetPlatformOverride=android 时 isMobilePlatform
      // 仍返回 false，与 app 其余平台分支（defaultTargetPlatform 同源）
      // 相互矛盾，且任何平台模拟测试都无法钉住移动端行为。
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      expect(
        ResponsiveUtils.isMobilePlatform,
        isTrue,
        reason: '目标平台 android 必须判为移动端（宿主机器是什么无关紧要）',
      );
      debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
      expect(ResponsiveUtils.isMobilePlatform, isTrue);
      debugDefaultTargetPlatformOverride = TargetPlatform.macOS;
      expect(ResponsiveUtils.isDesktopPlatform, isTrue);
      expect(ResponsiveUtils.isMobilePlatform, isFalse);
      debugDefaultTargetPlatformOverride = TargetPlatform.windows;
      expect(ResponsiveUtils.isDesktopPlatform, isTrue);
      debugDefaultTargetPlatformOverride = TargetPlatform.linux;
      expect(ResponsiveUtils.isDesktopPlatform, isTrue);
      debugDefaultTargetPlatformOverride = null;
      expect(
        ResponsiveUtils.isWeb,
        isFalse,
        reason: 'VM 测试宿主非 web（kIsWeb 编译期常量，web 断言交真机段）',
      );
    });
  });

  group('U-09 C4 · session 存储后端契约（io/web 同一 TokenStorage 契约）', () {
    test('两套后端对同一脚本序列产生同一可见状态', () async {
      SharedPreferences.setMockInitialValues({});
      final ioBackend = SecureTokenStorage(
        storage: _MemorySecureStorage(),
      );
      final webBackend = TokenStorageWeb();

      Future<Map<String, String?>> runScript(TokenStorage backend) async {
        final seen = <String, String?>{};
        seen['miss'] = await backend.read('u09_token');
        await backend.write('u09_token', 'access-1');
        seen['after_write'] = await backend.read('u09_token');
        await backend.write('u09_token', 'access-2');
        seen['after_overwrite'] = await backend.read('u09_token');
        await backend.delete('u09_token');
        seen['after_delete'] = await backend.read('u09_token');
        await backend.delete('u09_token'); // 再删：必须 no-op 不抛
        return seen;
      }

      final ioResult = await runScript(ioBackend);
      final webResult = await runScript(webBackend);
      expect(
        ioResult,
        equals(webResult),
        reason: 'session 契约必须与后端'
            '条件导入无关：read 未命中 null / write 覆盖 / delete no-op',
      );
      expect(ioResult['miss'], isNull);
      expect(ioResult['after_write'], 'access-1');
      expect(ioResult['after_overwrite'], 'access-2');
      expect(ioResult['after_delete'], isNull);
    });
  });

  group('U-09 C5 · keyboard 契约（enter-to-send 是偏好而非平台分支）', () {
    setUp(() => SharedPreferences.setMockInitialValues({}));
    tearDown(() => debugDefaultTargetPlatformOverride = null);

    testWidgets('默认偏好下三端 textInputAction=send 且提交动作真发送',
        (tester) async {
      var sentCount = 0;
      const targets = [
        TargetPlatform.android,
        TargetPlatform.iOS,
        TargetPlatform.macOS,
      ];
      for (final platform in targets) {
        debugDefaultTargetPlatformOverride = platform;
        sentCount = 0;
        await tester.pumpWidget(
          ProviderScope(
            child: testMaterialApp(
              home: Scaffold(
                body: ChatInput(
                  onSend: (_, {replyToId}) => sentCount++,
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();

        final field = tester.widget<TextField>(
          find.byType(TextField).first,
        );
        expect(
          field.textInputAction,
          TextInputAction.send,
          reason: '$platform：enter-to-send 默认开启（用户偏好），'
              '键盘动作语义不得随平台漂移',
        );
        await tester.enterText(find.byType(TextField).first, '三端一致');
        await tester.pump();
        await tester.testTextInput.receiveAction(TextInputAction.send);
        // 300ms：冲刷发送后 200ms 回声防护 Timer（N-6），否则
        // pending timer 令用例失败。
        await tester.pump(const Duration(milliseconds: 300));
        expect(
          sentCount,
          1,
          reason: '$platform：send 提交动作必须触发真实发送回调',
        );
        debugDefaultTargetPlatformOverride = null;
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump();
      }
    });

    testWidgets('偏好关闭后三端一致回落 newline（多行输入不被吞）',
        (tester) async {
      const targets = [TargetPlatform.android, TargetPlatform.macOS];
      for (final platform in targets) {
        debugDefaultTargetPlatformOverride = platform;
        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              enterToSendProvider.overrideWith((ref) => _StaticEnterToSendOff()),
            ],
            child: testMaterialApp(
              home: Scaffold(
                body: ChatInput(onSend: (_, {replyToId}) {}),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        final field = tester.widget<TextField>(
          find.byType(TextField).first,
        );
        expect(
          field.textInputAction,
          TextInputAction.newline,
          reason: '$platform：偏好关闭后回车必须换行而非发送（三端一致）',
        );
        debugDefaultTargetPlatformOverride = null;
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump();
      }
    });
  });

  group('U-09 C6 · canonical home 三端 viewport 渲染契约（overflow 面）', () {
    testWidgets('MULTIPLATFORM 三端 viewport：真实泵入零 overflow+锚点可达',
        (tester) async {
      await initializeDashboardTestEnvironment();
      for (final viewport in [...canonicalViewports, ...webViewports]) {
        debugDefaultTargetPlatformOverride = viewport.platform;
        addTearDown(() => debugDefaultTargetPlatformOverride = null);
        await pumpOnViewport(
          tester,
          viewport,
          // wt296 全展开 slot 基线（与存量结构测试同口径）：折叠态下
          // section key 不进树，无法做滚动可达断言；全展开同时让沿途
          // 内容更厚，overflow 覆盖更实。
          () => buildDashboardTestHarness(
            size: viewport.logicalSize,
            extraOverrides: [dashboardSlotConfigAllExpandedOverride()],
          ),
        );
        // RenderFlex overflow 在 pump 时由框架直接抛错（即红）；
        // 此处钉 canonical 结构锚点在树。
        expect(
          find.byType(DashboardScreen),
          findsOneWidget,
          reason: '${viewport.label} 下 canonical home 必须渲染',
        );
        // 滚动可达锚点（briefing→updates→workspace 顺序由存量结构测试
        // 钉死，此处只验证各 viewport 下可滚到工作区——列表虚拟化下
        // 沿途子行被真实布局，overflow 缺陷无处藏）。
        final workspace = find.byKey(
          const ValueKey('dashboard-workspace-section'),
        );
        await tester.scrollUntilVisible(
          workspace,
          240,
          scrollable: find.byType(Scrollable).first,
        );
        for (var i = 0; i < 4; i++) {
          await tester.pump(const Duration(milliseconds: 100));
        }
        expect(
          find.byKey(const ValueKey('dashboard-workspace-section')),
          findsOneWidget,
          reason: '${viewport.label} 下工作区锚点必须滚动可达',
        );
        debugDefaultTargetPlatformOverride = null;
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.pump();
      }
    });
  });

  group('U-09 C7 · 允许差异登记表契约（差异必须有 reason）', () {
    test('登记表非空且逐条 point/platforms/reason 齐备', () {
      expect(platformDivergences, isNotEmpty);
      for (final d in platformDivergences) {
        expect(d.point, isNotEmpty, reason: '允许差异必须指明差异点');
        expect(d.platforms, isNotEmpty, reason: '允许差异必须指明涉及平台');
        expect(d.reason, isNotEmpty, reason: '允许差异必须写 reason');
      }
      // 审计钉死的三类已知差异必须登记在案（layout/URL/session 面）。
      expect(
        platformDivergences.map((d) => d.point).join('\n'),
        contains('token_storage'),
        reason: 'session 后端差异必须显式登记',
      );
      expect(
        platformDivergences.map((d) => d.point).join('\n'),
        contains('api_constants'),
        reason: 'URL 默认主机差异必须显式登记',
      );
      expect(
        platformDivergences.map((d) => d.point).join('\n'),
        contains('pageTransitionsTheme'),
        reason: '平台转场差异必须显式登记',
      );
    });
  });
}

/// enter-to-send 关闭态静态 notifier（C5 偏好面）。
///
/// setUp 已 mock SharedPreferences（空表 → _loadSettings 无键可读，
/// 不改状态），构造后钉 state=false。
class _StaticEnterToSendOff extends EnterToSendNotifier {
  _StaticEnterToSendOff() {
    state = false;
  }
}

class _MemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values[key];

  @override
  Future<void> write({
    required String key,
    String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      _values.remove(key);
    } else {
      _values[key] = value;
    }
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.remove(key);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
